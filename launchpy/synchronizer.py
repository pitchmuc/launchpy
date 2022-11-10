import json
from collections import defaultdict
from concurrent import futures
from copy import deepcopy
import os
# Non standard libraries
import pandas as pd
from pathlib import Path
from launchpy import config, connector
from typing import IO, Union
from .admin import Admin
from .property import Property
from .launchpy import Translator, copySettings,extensionsInfo,rulesInfo

class Synchronizer:
    """
    The synchronizer class provides an abstaction layer for synchronizing the rule components and the data elements.
    It combined the usage of elements provided by the launchpy library: 
    - Property class
    - Translator class
    - copySetting method
    - extensionInfo method
    - RulesInfo method
    It takes 2 arguments, the base property (template) where all information will be fetched from. The target properties where the element will be copied to.
    It requires that you have imported a configuration file.
    """

    def __init__(self,base:str=None,targets:list=None)->None:
        """
        Instantiating the Synchronizer taking 2 parameters, base property name, target property list.
        Arguments:
            base : REQUIRED : The name of your base/template property
            targets : REQUIRED : The list of property names that you want to sync with.
        """
        tmp_admin = Admin()
        cid = tmp_admin.getCompanyId()
        properties = tmp_admin.getProperties(cid)
        base_property = [prop for prop in properties if prop['attributes']['name'] == base]
        if len(base_property) ==0:
            raise KeyError("The base property name has not been found in your account")
        self.base = {}
        self.base["name"] = base
        self.base["api"] = Property(base_property[0])
        self.base['rules'] = self.base['api'].getRules()
        self.base['dataElements'] = self.base['api'].getDataElements()
        self.base['extensions'] = self.base['api'].getExtensions()
        self.translator = Translator()
        self.translator.setBaseExtensions(self.base['extensions'],self.base['name'])
        self.translator.setBaseRules(self.base['rules'],self.base['name'])
        self.targets = {}
        for target in targets:
            tmp_target = [prop for prop in properties if prop['attributes']['name'] == target]
            if len(tmp_target) == 0:
                raise KeyError(f"The target property : {target} cannot be found. Please, fix it")
            self.targets[target] = {'api' : Property(tmp_target[0]),'name':target}
            self.targets[target]['rules'] = self.targets[target]['api'].getRules()
            self.targets[target]['extensions'] = self.targets[target]['api'].getExtensions()
            self.targets[target]['dataElements'] = self.targets[target]['api'].getDataElements()
            #self.targets[target]['rcs'] = self.targets[target]['api'].getRuleComponents()
            self.translator.extendExtensions(self.targets[target]['extensions'],self.targets[target]['name'])
            self.translator.extendRules(self.targets[target]['rules'],self.targets[target]['name'])

    def syncComponent(self,componentName:str=None,componentId:str=None)->None:
        """
        Synchronize a component from the base property to the different target properties.
        It will detect the component with the same name in target properties.
        It will delete the components related objects (ruleComponents, data element code) in the target property and push the template version.
        Arguments:
            componentName : REQUIRED : the name of the component to sync
            componentID : REQUIRED : the id of the component to sync
        """
        if componentName is None and componentId is None:
            raise ValueError('Require a component Name of a component ID')
        cmp_base=None
        if componentId is not None:
            if componentId.startswith('DE'): ## if data element
                componentBase = [de for de in self.base['dataElements'] if de['id'] == componentId]
                if len(componentBase)==0:
                    raise KeyError("Component ID cannot be found")
                cmp_base = componentBase[0]
            elif componentId.startswith('RL'): ## if a rule
                componentBase = [de for de in self.base['rules'] if de['id'] == componentId]
                if len(componentBase)==0:
                    raise KeyError("Component ID cannot be found")
                cmp_base = componentBase[0]
        if componentId is None and componentName is not None: ## If only componentName
            for rule in self.base['rules']:
                if componentName == rule['attributes']['name']:
                    cmp_base = rule
            if cmp_base is None:
                for de in self.base['dataElements']:
                    if componentName == de['attributes']['name']:
                        cmp_base = de
        ## In case we do not find any match
        if cmp_base is None:
            raise KeyError("The component ID or component Name cannot be matched in your template property")
        ## Here creating a dictionary that provide all information related to your component 
        cmp_baseDict = {'id':cmp_base['id'],'name':cmp_base['attributes']['name'],'component':cmp_base,'copy':copySettings(cmp_base)}
        if[cmp_base['type'] == 'rule_components']:
            cmp_baseDict['rule_name'] = cmp_base.get('rule_name','')
        ## handling the data element
        if cmp_baseDict['component']['type'] == 'data_elements':
            for target in list(self.targets.keys()):
                translatedComponent = self.translator.translate(target,data_element=cmp_baseDict['copy'])
                ## if it does not exist
                if cmp_baseDict['name'] not in [de['attributes']['name'] for de in self.targets[target]['dataElements']]:
                    res = self.targets[target]['api'].createDataElement(
                        name=cmp_baseDict['name'],
                        descriptor= translatedComponent['descriptor'],
                        settings=translatedComponent['settings'],
                        extension=translatedComponent['extension']
                        )
                else:
                    old_component = [de for de in self.targets[target]['dataElements'] if de['attributes']['name'] == cmp_baseDict['name']][0]
                    res = self.targets[target]['api'].updateDataElement(
                        dataElement_id=old_component['id'],
                        attr_dict=translatedComponent,
                        )
        if cmp_baseDict['component']['type'] == 'rules':
            ## fetching all rule components associated with a rule.
            rcsLink = cmp_baseDict['component'].get('relationships',{}).get('rule_components',{}).get('links',{}).get('related')
            resResource = self.base['api'].getRessource(rcsLink)
            template_ruleComponents:list = resResource['data']
            for rc in template_ruleComponents:
                rc['rule_name'] = cmp_baseDict['name']
                rc['rule_id'] = cmp_baseDict['id']
            for target in list(self.targets.keys()):
                ## if rule does not exist
                if cmp_baseDict['name'] not in [rule['attributes']['name'] for rule in self.targets[target]['rules']]:
                    res = self.targets[target]['api'].createRule(
                        name=cmp_baseDict['name']
                        )
                    rule_id = res['id']
                    for rc in template_ruleComponents:
                        translatedComponent = self.translator.translate(target,rule_component=copySettings(rc))
                        translatedComponent['rule_setting']['data'][0]['id'] = rule_id
                        self.targets[target]['api'].createRuleComponent(
                            name=translatedComponent['name'],
                            settings = translatedComponent['settings'],
                            descriptor = translatedComponent['descriptor'],
                            extension_infos = translatedComponent['extension'],
                            rule_infos = translatedComponent['rule_setting'],
                            order=translatedComponent['order']
                        )
                else: ## if a rule exist with the same name
                    targetRule = [rule for rule in self.targets[target]['rules'] if rule['attributes']['name'] == cmp_baseDict['name']][0]
                    targetRuleId = targetRule['id']
                    rcsLinkTarget = targetRule.get('relationships',{}).get('rule_components',{}).get('links',{}).get('related')
                    resResource = self.targets[target]['api'].getRessource(rcsLinkTarget)
                    old_components:list = resResource['data']
                    ## deleting the old version of rule component
                    if len(old_components)>0:
                        for component in old_components:
                            self.targets[target]['api'].deleteRuleComponent(component['id'])
                    ## creating the new version of the old version
                    for rc in template_ruleComponents:
                        translatedComponent = self.translator.translate(target,rule_component=copySettings(rc))
                        translatedComponent['rule_setting']['data'][0]['id'] = targetRuleId
                        res = self.targets[target]['api'].createRuleComponent(
                            name=translatedComponent['name'],
                            settings = translatedComponent['settings'],
                            descriptor = translatedComponent['descriptor'],
                            extension_infos = translatedComponent['extension'],
                            rule_infos = translatedComponent['rule_setting'],
                            order=translatedComponent['order']
                        )                    
        


            

        
        
        
