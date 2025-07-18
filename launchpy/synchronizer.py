import re,json
# Non standard libraries
from .admin import Admin
from .property import Property
from .library import Library
from .launchpy import Translator, copySettings
from collections import defaultdict
from copy import deepcopy
from aepp import som

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

    def __init__(self,base:str=None,targets:list=None,**kwargs)->None:
        """
        Instantiating the Synchronizer taking 2 parameters, base property name, target property list.
        Arguments:
            base : REQUIRED : The name of your base/template property
            targets : REQUIRED : The list of property names that you want to sync with.
        possible kwargs:
            dynamicRuleComponent: A data element name that contains rule for synchronization on the property.
        """
        tmp_admin = Admin()
        cid = tmp_admin.getCompanyId()
        properties = tmp_admin.getProperties(cid)
        base_property = [prop for prop in properties if prop['attributes']['name'] == base]
        if len(base_property) ==0:
            raise KeyError("The base property name has not been found in your account")
        self.base = {}
        self.base["name"] = base
        self.base["api"]:Property = Property(base_property[0])
        self.base['rules'] = self.base['api'].getRules()
        self.base['dataElements'] = self.base['api'].getDataElements()
        self.base['extensions'] = self.base['api'].getExtensions()
        self.translator = Translator()
        self.translator.setBaseExtensions(self.base['extensions'],self.base['name'])
        self.translator.setBaseRules(self.base['rules'],self.base['name'])
        self.targets = {}
        self.target_configs = {}
        for target in targets:
            tmp_target = [prop for prop in properties if prop['attributes']['name'] == target]
            if len(tmp_target) == 0:
                raise KeyError(f"The target property : {target} cannot be found. Please, fix it")
            self.targets[target] = {'api' : Property(tmp_target[0]),'name':target}
            self.targets[target]['rules'] = self.targets[target]['api'].getRules()
            self.targets[target]['extensions'] = self.targets[target]['api'].getExtensions()
            self.targets[target]['dataElements'] = self.targets[target]['api'].getDataElements()
            self.targets[target]['libraryStack'] = {'dataElements':[],'rules':[],"extensions":[]}
            self.translator.extendExtensions(self.targets[target]['extensions'],self.targets[target]['name'])
            if len(self.targets[target]['rules']) > 0:
                self.translator.extendRules(self.targets[target]['rules'],self.targets[target]['name'])
            else:
                self.translator.rules[self.targets[target]['name']] = None
        if kwargs.get("dynamicRuleComponent",None) is not None:
            configRules = [de for de in self.base['dataElements'] if de['attributes']['name'] == kwargs.get("dynamicRuleComponent",None)]
            if len(configRules)==1:
                configRules = configRules[0]
            else:
                raise ValueError("The dynamicRuleComponent is using a value that does not match any data element.")
            codeConfig:list = json.loads(json.loads(configRules['attributes']['settings'])['source'])## list expected from the code
            self.dynamicFiltering(codeConfig)

    def dynamicFiltering(self,dynamicFilterJSON:dict,override:bool=True)->None:
        """
        Building the dynamic rule filtering for each of the target properties.
        Base on this code format
        [
            {
                'name':'myName',
                'targetProperties':'.+ some condition .+ ',
                'exclComponents':[
                    'DE - My Data Element',
                    'RL - My Rule'
                ],
                'inclComponents':[
                    'somecomponent name'
                ]
            }
        ]
        Arguments: 
            dynamicFilterJSON : REQUIRED : The JSON representation of your rules.
            override : OPTIONAL : Replace the existing dynamic filtering. Default True.
                If set to False, apply the logic on top of the existing one loaded before.
        """
        if override == True:
            self.dict_config = {} ## global dynamic rule filtering
            self.target_configs = {} ## dynamic rule filtering apply to target
        for rule in dynamicFilterJSON:
            self.dict_config[rule['targetProperties']] = {'inclComponents':[],'exclComponents':[]}
            if 'inclComponents' in rule.keys():
                self.dict_config[rule['targetProperties']]['inclComponents'] += rule['inclComponents']
            if 'exclComponents' in rule.keys():
                self.dict_config[rule['targetProperties']]['exclComponents'] += rule['exclComponents']
        for rule in self.dict_config.keys():
            for target in self.targets.keys():
                if re.search(rule,target) is not None:
                    if target in self.target_configs.keys():
                        if self.dict_config[rule]['exclComponents'] not in self.target_configs[target]['exclComponents']:
                            self.target_configs[target]['exclComponents'] += deepcopy(self.dict_config[rule]['exclComponents'])
                        if self.dict_config[rule]['inclComponents'] not in self.target_configs[target]['inclComponents']:
                            self.target_configs[target]['inclComponents'] += deepcopy(self.dict_config[rule]['inclComponents'])
                    else:
                        self.target_configs[target] = {
                            'exclComponents': deepcopy(self.dict_config[rule]['exclComponents']),
                            'inclComponents': deepcopy(self.dict_config[rule]['inclComponents'])
                        }
    
    def __prepareBaseComponent__(self,componentName:str=None,componentId:str=None,publishedVersion:bool=False)->dict:
        """
        Prepare the base component to be used in the syncComponent method.
        Arguments:
            componentName : REQUIRED : the name of the component to sync
            componentID : REQUIRED : the id of the component to sync
            publishedVersion : OPTIONAL : if you want to take the version that has been published
        """
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
            elif componentId.startswith('EX'): ## if an extension
                componentBase = [ext for ext in self.base['extensions'] if ext['id'] == componentId]
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
            if cmp_base is None:
                for ext in self.base['extensions']:
                    if componentName == ext['attributes']['name']:
                        cmp_base = ext
        ## In case we do not find any match
        if cmp_base is None:
            raise KeyError("The component ID or component Name cannot be matched in your template property")
        ## Here creating a dictionary that provide all information related to your component 
        cmp_baseDict = {'id':cmp_base['id'],'name':cmp_base['attributes']['name'],'component':cmp_base,'copy':copySettings(cmp_base)}
        if cmp_baseDict['component']['type'] == 'extensions':
            cmp_baseDict['version'] = cmp_base['attributes'].get('version','1.0.0')
        if publishedVersion and cmp_baseDict['component']['type'] not in ['extensions']:
            data = self.base['api'].getRevisions(cmp_baseDict['component'])
            publishedVersion = self.base['api'].getLatestPublishedVersion(data) 
            if publishedVersion['attributes']['name'] != cmp_baseDict['name']:
                ## Updating mapping table with old name when published version name diff than last versio name.
                if cmp_baseDict['component']['type'] == 'rules':
                    self.translator.extendBaseRules(
                    ruleName=publishedVersion['attributes']['name'],
                    ruleId=publishedVersion['id'],
                    property_name=self.base["name"])
                    self.base['rules'].append(publishedVersion)
                if cmp_baseDict['component']['type'] == 'data_elements':
                    self.base['dataElements'].append(publishedVersion)
            cmp_baseDict['id'] = publishedVersion['id']
            cmp_baseDict['name'] = publishedVersion['attributes']['name']
            cmp_baseDict['component'] = publishedVersion
            cmp_baseDict['copy'] = copySettings(publishedVersion)
        return cmp_baseDict

    def syncComponent(self,componentName:str=None,componentId:str=None,publishedVersion:bool=False,**kwargs)->None:
        """
        Synchronize a component from the base property to the different target properties.
        It will detect the component with the same name in target properties.
        It will delete the components related objects (ruleComponents, data element code) in the target property and push the template version.
        If you uploaded a dynamicRuleComponent data element config during the init method, any element that are not sync because of the exclComponentList will return a dict: {componentName:False} 
        Arguments:
            componentName : REQUIRED : the name of the component to sync
            componentID : REQUIRED : the id of the component to sync
            publishedVersion : OPTIONAL : if you want to take the version that has been published
        possible kwargs:
            timeout : OPTIONAL : The timeout to be used for the rule component. If not provided, the existing timeout will be used.
        """
        timeout = kwargs.get('timeout',None)
        if componentName is None and componentId is None:
            raise ValueError('Require a component Name of a component ID')
        cmp_baseDict = self.__prepareBaseComponent__(componentName=componentName,componentId=componentId,publishedVersion=publishedVersion)
        ## handling the data element
        if cmp_baseDict['component']['type'] == 'data_elements':
            for target in list(self.targets.keys()):
                flagAllowList = False
                ## check if the component is in the exclComponentList
                if any([bool(re.search(key,cmp_baseDict['name'])) for key in self.target_configs.get(target,{}).get('exclComponents',[])]):
                    return {cmp_baseDict['name']:False}
                ## if there is an allow list for that property
                if len(self.target_configs.get(target,{}).get('inclComponents',[]))>0:
                    if any([bool(re.search(key,cmp_baseDict['name'])) for key in self.target_configs.get(target,{}).get('inclComponents',[])]):
                        flagAllowList = True
                ## if there is no allow list for that property, or no match in the list of target properties, or component was allow
                if len(self.target_configs.get(target,{}).get('inclComponents',[]))==0 or flagAllowList:
                    translatedComponent = self.translator.translate(target,data_element=cmp_baseDict['copy'])
                    ## if it does not exist
                    if cmp_baseDict['name'] not in [de.get('attributes',{}).get('name') for de in self.targets[target]['dataElements']]:
                        comp = self.targets[target]['api'].createDataElement(
                            name=cmp_baseDict['name'],
                            descriptor= translatedComponent['descriptor'],
                            settings=translatedComponent['settings'],
                            extension=translatedComponent['extension'],
                            storage_duration = translatedComponent["storage_duration"],
                            force_lower_case = translatedComponent["force_lower_case"],
                            clean_text = translatedComponent["clean_text"],
                            default_value= translatedComponent["default_value"]
                            )
                        if cmp_baseDict['component']['attributes']['enabled'] != comp['attributes']['enabled']:
                            updateDE = self.targets[target]['api'].updateDataElement(
                                dataElement_id=comp['id'],
                                attr_dict=translatedComponent)
                        self.targets[target]['libraryStack']['dataElements'].append(comp)
                        self.targets[target]['dataElements'].append(comp)
                    else:
                        index,old_component = [(index,de) for index,de in enumerate(self.targets[target]['dataElements']) if de.get('attributes',{}).get('name') == cmp_baseDict['name']][0]
                        attributes = {
                            "name" : translatedComponent['name'],
                            "enabled" : translatedComponent["enabled"],
                            "delegate_descriptor_id" : translatedComponent["descriptor"],
                            "storage_duration" : translatedComponent["storage_duration"],
                            "force_lower_case" : translatedComponent["force_lower_case"],
                            "clean_text" : translatedComponent["clean_text"],
                            "settings" : translatedComponent["settings"],
                            "default_value": translatedComponent["default_value"]
                        }
                        comp = self.targets[target]['api'].updateDataElement(
                            dataElement_id=old_component['id'],
                            attr_dict=attributes,
                            )
                        del self.targets[target]['dataElements'][index]
                        self.targets[target]['dataElements'].append(comp)
                        self.targets[target]['libraryStack']['dataElements'].append(comp)
        ## Rules part
        if cmp_baseDict['component']['type'] == 'rules':
            ## fetching all rule components associated with a rule.
            rcsLink = cmp_baseDict['component'].get('relationships',{}).get('rule_components',{}).get('links',{}).get('related')
            resResource = self.base['api'].getRessource(rcsLink)
            template_ruleComponents:list = resResource['data']
            for rc in template_ruleComponents:
                rc['rule_name'] = cmp_baseDict['name']
                rc['rule_id'] = cmp_baseDict['id']
            for target in list(self.targets.keys()):
                flagAllowList = False
                ## check if the component is in the exclComponentList
                if any([bool(re.search(key,cmp_baseDict['name'])) for key in self.target_configs.get(target,{}).get('exclComponents',[])]):
                    return {cmp_baseDict['name']:False}
                ## if there is an allow list for that property
                if len(self.target_configs.get(target,{}).get('inclComponents',[]))>0:
                    if any([bool(re.search(key,cmp_baseDict['name'])) for key in self.target_configs.get(target,{}).get('inclComponents',[])]):
                        flagAllowList = True
                ## if there is no allow list for that property, or no match in the list of target properties, or component was allow
                if len(self.target_configs.get(target,{}).get('inclComponents',[]))==0 or flagAllowList:
                    ## if rule does not exist
                    if cmp_baseDict['name'] not in [rule['attributes']['name'] for rule in self.targets[target]['rules']]:
                        targetRule = self.targets[target]['api'].createRule(
                            name=cmp_baseDict['name']
                            )
                        targetRuleId = targetRule['id']
                        self.translator.extendTargetRules(ruleName=cmp_baseDict['name'],ruleId=targetRuleId,property_name=target)
                        self.targets[target]['rules'].append(targetRule)
                        index = len(self.targets[target]['rules'])-1
                        self.targets[target]['libraryStack']['rules'].append(targetRule)
                        for rc in template_ruleComponents:
                            try:
                                translatedComponent = self.translator.translate(target,rule_component=copySettings(rc))
                            except:
                                raise KeyError("Could not translate the component. Please check if your extensions are aligned in the properties.")
                            translatedComponent['rule_setting']['data'][0]['id'] = targetRuleId
                            if timeout is not None:
                                translatedComponent['timeout'] = timeout
                            targetRuleComponent = self.targets[target]['api'].createRuleComponent(
                                name=translatedComponent['name'],
                                settings = translatedComponent['settings'],
                                descriptor = translatedComponent['descriptor'],
                                extension_infos = translatedComponent['extension'],
                                rule_infos = translatedComponent['rule_setting'],
                                rule_order=translatedComponent['rule_order'],
                                order=translatedComponent['order'],
                                negate=translatedComponent['negate'],
                                delay_next=translatedComponent['delay_next'],
                                timeout=translatedComponent['timeout'],
                            )
                    else: ## if a rule exist with the same name
                        index, targetRule = [(index,rule) for index, rule in enumerate(self.targets[target]['rules']) if rule['attributes']['name'] == cmp_baseDict['name']][0]
                        self.targets[target]['libraryStack']['rules'].append(targetRule)
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
                            try:
                                translatedComponent = self.translator.translate(target,rule_component=copySettings(rc))
                            except:
                                raise KeyError("Could not translate the component. Please check if your extensions are aligned in the properties.")
                            translatedComponent['rule_setting']['data'][0]['id'] = targetRuleId
                            if timeout is not None:
                                translatedComponent['timeout'] = timeout
                            targetRuleComponent = self.targets[target]['api'].createRuleComponent(
                                name=translatedComponent['name'],
                                settings = translatedComponent['settings'],
                                descriptor = translatedComponent['descriptor'],
                                extension_infos = translatedComponent['extension'],
                                rule_infos = translatedComponent['rule_setting'],
                                rule_order=translatedComponent['rule_order'],
                                order=translatedComponent['order'],
                                negate=translatedComponent['negate'],
                                delay_next=translatedComponent['delay_next'],
                                timeout=translatedComponent['timeout'],
                            )
                    ## updating rule attribute if difference between base and target
                    if cmp_baseDict['component']['attributes']['enabled'] != targetRule['attributes']['enabled']:
                        baseRuleAttr = copySettings(cmp_baseDict['component'])
                        targetRule = self.targets[target]['api'].updateRule(rule_id=targetRuleId,attr_dict=baseRuleAttr) ## keeping in a var for debug
                        del self.targets[target]['rules'][index]
                        self.targets[target]['rules'].append(targetRule)

    def syncComponents(self,componentsName:list=None,componentsId:list=None,publishedVersion:bool=False)->None:
        """
        Sync multiple components by looping through the list of name passed.
        Arguments:
            componentsName : REQUIRED : The list of component names to sync
            componentsId : REQUIRED : The list of component ID to sync
            publishedVersion : OPTIONAL : if you want to take the version that has been published
        """
        if componentsName is not None:
            for component in componentsName:
                self.syncComponent(componentName=component,publishedVersion=publishedVersion)
        if componentsId is not None:
            for component in componentsId:
                self.syncComponent(componentId=component,publishedVersion=publishedVersion)
    
    def createTargetsLibrary(self,name:str="syncComponents")->None:
        """
        This method will create or update a Library in all of the target properties to gather all elements changed.
        If a library exists and **contains** the same name, it will be used.
        Argument:
            name : REQUIRED : The name of the library to create. Default : "syncComponents"
        """
        for target in list(self.targets.keys()):
            if 'library' not in list(self.targets[target].keys()):
                librariesDev = self.targets[target]['api'].getLibraries(state="development")
                if True in [bool(re.search(name,lib['attributes']['name'])) for lib in librariesDev]:
                    lib = [lib for lib in librariesDev if name in lib['attributes']['name']][0]
                else:
                    lib = self.targets[target]['api'].createLibrary(name=name,return_class=False)
                library = Library(lib)
                self.targets[target]['library'] = library
            self.targets[target]['library'].getFullLibrary()
            ## taking care of rule update
            existingRules = [rule['id'] for rule in self.targets[target]['library'].relationships['rules'] if rule['id'] in [r['id'] for r in self.targets[target]['libraryStack']['rules']]]
            newRules = [rule['id'] for rule in self.targets[target]['libraryStack']['rules'] if rule['id'] not in existingRules]
            if len(existingRules) > 0:
                self.targets[target]['library'].updateRules(existingRules)
            if len(newRules)>0:
                self.targets[target]['library'].addRules(newRules)
            ## taking care of data elements
            existingDataElements = [de['id'] for de in self.targets[target]['library'].relationships['data_elements'] if de['id'] in [d['id'] for d in self.targets[target]['libraryStack']['dataElements']]]
            newDataElements = [de['id'] for de in self.targets[target]['libraryStack']['dataElements'] if de['id'] not in existingDataElements]
            if len(existingDataElements) > 0:
                self.targets[target]['library'].updateDataElements(existingDataElements)
            if len(newDataElements)>0:
                self.targets[target]['library'].addDataElements(newDataElements)
            ## taking care of the extensions
            existingExtensions = [ext['id'] for ext in self.targets[target]['library'].relationships['extensions'] if ext['id'] in [e['id'] for e in self.targets[target]['libraryStack']['extensions']]]
            newExtensions = [ext['id'] for ext in self.targets[target]['libraryStack']['extensions'] if ext['id'] not in existingExtensions]
            if len(existingExtensions) > 0:
                self.targets[target]['library'].updateExtensions(existingExtensions)
            if len(newExtensions)>0:
                self.targets[target]['library'].addExtensions(newExtensions)

    def upgradeTargetExtension(self,extensionName:str=None,platform:str="web")->dict:
        """
        Upgrade the name extension in the target properties.
        Arguments:
            extensionName : REQUIRED : The name of the extension to upgrade.
                                        ex : "core" or "adobe-analytics"
            platform : OPTIONAL : If you want to update the extension of a specific platform (default "web")
        """
        if extensionName is None:
            raise ValueError("Require an extension name")
        for prop, target in self.targets.items():
            try:
                extensionUpdate = target['api'].checkExtensionUpdate(extensionName)
                for extName, extUpdateDict in extensionUpdate.items():
                    if extUpdateDict["update"]:
                        res = target['api'].upgradeExtension(extUpdateDict['internal_id'],extUpdateDict["package_id"])
                        target['libraryStack']['extensions'].append(res)
                        if len([index for index, ext in enumerate(target['extensions']) if ext['attributes']['name'] == extName])>0:
                            index = [index for index, ext in enumerate(target['extensions']) if ext['attributes']['name'] == extName][0]
                            del target['extensions'][index]
                        target['extensions'].append(res)
                        
            except:
                raise ValueError(f"Could not find an extension name: {extensionName}")


    def renameComponent(self,old_name:str=None,new_name:str=None)->None:
        """
        Passing the old and new name of a component, it will rename the component in the different target properties.
        If the old name cannot be found in the target properties, nothing is done.
        Arguments
            old_name : REQUIRED : The name of the component that you would like to rename
            new_name : REQUIRED : The new name to be given to that component.
        """
        if old_name is None:
            raise ValueError("Require the old name to be passed")
        if new_name is None:
            raise ValueError("Require the new name to be passed")        
        for target in self.targets:
            if old_name in [de['attributes']['name'] for de in self.targets[target]['dataElements']]:
                component = [de for de in self.targets[target]['dataElements'] if de['attributes']['name']== old_name][0]
                copy = copySettings(component)
                attributes = {
                    "name" : new_name,
                    "enabled" : copy["enabled"],
                    "delegate_descriptor_id" : copy["descriptor"],
                    "storage_duration" : copy["storage_duration"],
                    "force_lower_case" : copy["force_lower_case"],
                    "clean_text" : copy["clean_text"],
                    "default_value": copy['default_value'],
                    "settings" : copy["settings"]
                    }
                comp = self.targets[target]['api'].updateDataElement(
                    dataElement_id=component['id'],
                    attr_dict=attributes,
                    )
                self.targets[target]['libraryStack']['dataElements'].append(comp)
            if old_name in [rule['attributes']['name'] for rule in self.targets[target]['rules']]:
                component = [rule for rule in self.targets[target]['rules'] if rule['attributes']['name']== old_name][0]
                copy = copySettings(component)
                copy['name'] = new_name
                comp = self.targets[target]['api'].updateRule(rule_id=component['id'],attr_dict=copy)
                self.targets[target]['libraryStack']['rules'].append(comp)


    def checkComponentSync(self,componentName:str=None,componentId:str=None,publishedVersion:bool=False,excludeSimilar:bool=False,**kwargs)->bool:
        """
        Check if the component,from the base property, is synced to the different target properties.
        It can also check for the Extensions.
        It will return a dictionary with the key being the target property and the value being the result of the evaluation, such as {targetProperty: 'similar'} when component have same settings or {targetPropery : False} when component do not have same settings.
        Arguments:
            componentName : REQUIRED : the name of the component to compare
            componentID : REQUIRED : the id of the component to compare
            publishedVersion : OPTIONAL : if you want to compare to the version that has been published in your base vs the published version of your target.
            excludeSimilar : OPTIONAL : If you do not want to see the result if the comparison provide a "similar" result. Similar means that the elements are about the same. Default: False. 
        possible kwargs:
            action_setting_path : [str,list] : The dot notation of the paths you want to verify for the settings object. ex: ["code","customAttributes"]. If not provided, the complete settings are compared.
            condition_setting_path : [str,list] : The dot notation of the paths you want to verify for the setting object . ex: ["id",""]. If not provided, the complete settings are compared
            event_setting_path : [str,list] : The dot notation of the paths you want to verify for the setting object . ex: ["id",""]. If not provided, the complete settings are compared
        """
        if componentName is None and componentId is None:
            raise ValueError('Require a component Name of a component ID')
        cmp_baseDict = self.__prepareBaseComponent__(componentName=componentName,componentId=componentId,publishedVersion=publishedVersion)
        dict_result = {tar:"" for tar in self.targets.keys()}
        dict_result['base-enabled'] = cmp_baseDict['component']['attributes'].get('enabled',False)
        dict_result['base-published'] = cmp_baseDict['component']['attributes'].get('published',False)
        if cmp_baseDict['component']['attributes'].get('latest',False):
            dict_result['base-state'] = "Latest"
        else:
            if cmp_baseDict['component']['attributes'].get('latest','unknown') == 'unknown':
                if dict_result['base-enabled']:
                    dict_result['base-state'] = "Draft"
                else:
                    dict_result['base-state'] = "Unknown"
            elif dict_result['base-published'] == False:
                dict_result['base-state'] = "Draft"
            else:
                dict_result['base-state'] = "Edited"
        if cmp_baseDict['component']['type'] == 'data_elements':
            for target in list(self.targets.keys()):
                ## if it does not exist
                if cmp_baseDict['name'] not in [de.get('attributes',{}).get('name') for de in self.targets[target]['dataElements']]:
                    dict_result[target] = f'Data Element "{cmp_baseDict["name"]}" does not exist in Target'
                else:
                    index,target_de = [(index,de) for index,de in enumerate(self.targets[target]['dataElements']) if de['attributes']['name'] == cmp_baseDict['name']][0]
                    issue_pub = ""
                    if publishedVersion:
                        try:
                            revisions_dataElement = self.targets[target]["api"].getRevisions(target_de)
                            target_de = self.targets[target]["api"].getLatestPublishedVersion(revisions_dataElement) 
                        except:
                            issue_pub = " (draft)"
                        if target_de['attributes']['enabled'] != cmp_baseDict['component']['attributes']['enabled']:
                            dict_result[target] = "Data Element enabled status is different"+issue_pub
                        if target_de['attributes']['published'] != cmp_baseDict['component']['attributes']['published']:
                            dict_result[target] = "Data Element published status is different"+issue_pub
                    if target_de['attributes']['settings'] == cmp_baseDict['component']['attributes']['settings']:
                        if not excludeSimilar:
                            dict_result[target] = "Similar"+issue_pub
                    else:
                        dict_result[target] = "Data Element settings are different"+issue_pub
        if cmp_baseDict['component']['type'] == 'rules':
            rcsLink = cmp_baseDict['component'].get('relationships',{}).get('rule_components',{}).get('links',{}).get('related')
            resResource = self.base['api'].getRessource(rcsLink)
            template_ruleComponents:list = resResource['data']
            for rc in template_ruleComponents:
                rc['rule_name'] = cmp_baseDict['name']
                rc['rule_id'] = cmp_baseDict['id']
            for target in list(self.targets.keys()):
                ## if rule does not exist
                if cmp_baseDict['name'] not in [rule['attributes']['name'] for rule in self.targets[target]['rules']]:
                    dict_result[target] = "Rule does not exist in Target"
                else:
                    index, targetRule = [(index,rule) for index, rule in enumerate(self.targets[target]['rules']) if rule['attributes']['name'] == cmp_baseDict['name']][0]
                    issue_pub = ""
                    componentsDifferences = [] ## list of differences for rule components for rule to check difference
                    if publishedVersion:
                        try:
                            revisions_targetRule = self.targets[target]["api"].getRevisions(targetRule)
                            targetRule = self.targets[target]["api"].getLatestPublishedVersion(revisions_targetRule) 
                        except:
                            issue_pub = " (not published)"
                        if targetRule['attributes']['enabled'] != cmp_baseDict['component']['attributes']['enabled']:
                            componentsDifferences.append("Rule enabled status is different")
                        if targetRule['attributes']['published'] != cmp_baseDict['component']['attributes']['published']:
                            componentsDifferences.append("Rule published status is different")
                    rcsLinkTarget = targetRule.get('relationships',{}).get('rule_components',{}).get('links',{}).get('related')
                    resResource = self.targets[target]['api'].getRessource(rcsLinkTarget)
                    target_rule_components:list = resResource['data']
                    #if not same amunt of rule component 
                    if len(template_ruleComponents) != len(target_rule_components):
                        dict_result[target] = "The rule does not have the same number of components"
                    for base_comp in template_ruleComponents:
                        checkExist = False
                        for comp in target_rule_components:
                            if comp['attributes']['name'] == base_comp['attributes']['name']:
                                checkExist = True
                                if '::events::' in base_comp['attributes']['delegate_descriptor_id']:
                                    if comp['attributes']['rule_order'] != base_comp['attributes']['rule_order']:
                                        componentsDifferences.append("rule_order is different")
                                    if kwargs.get('event_setting_path',None) is not None:
                                        list_event_path = kwargs.get('event_setting_path',None)
                                        if type(list_event_path) == str:
                                            list_event_path = list(list_event_path)
                                        mySettings_base = som.Som(json.loads(base_comp['attributes']['settings']))
                                        mySettings_target = som.Som(json.loads(comp['attributes']['settings']))
                                        for path in list_event_path:
                                            tmp_base = mySettings_base.get(path,'')
                                            tmp_target = mySettings_target.get(path,'')
                                            if tmp_base != tmp_target:
                                                componentsDifferences.append(f'event "{comp['attributes']['name']}" has different settings')
                                    else:
                                        if base_comp['attributes']['settings'] != comp['attributes']['settings']:
                                            componentsDifferences.append(f'event "{comp['attributes']['name']}" has different settings')
                                elif '::conditions::' in base_comp['attributes']['delegate_descriptor_id']:
                                    if comp['attributes']['timeout'] != base_comp['attributes']['timeout']:
                                        componentsDifferences.append(f'condition "{comp['attributes']['name']}" timeout is different')
                                    if kwargs.get('condition_setting_path',None) is not None:
                                        list_event_path = kwargs.get('condition_setting_path',None)
                                        if type(list_event_path) == str:
                                            list_event_path = list(list_event_path)
                                        mySettings_base = som.Som(json.loads(base_comp['attributes']['settings']))
                                        mySettings_target = som.Som(json.loads(comp['attributes']['settings']))
                                        for path in list_event_path:
                                            tmp_base = mySettings_base.get(path,'')
                                            tmp_target = mySettings_target.get(path,'')
                                            if tmp_base != tmp_target:
                                                componentsDifferences.append(f'condition "{comp['attributes']['name']}" has different settings')
                                    else:
                                        if base_comp['attributes']['settings'] != comp['attributes']['settings']:
                                            componentsDifferences.append(f'condition "{comp['attributes']['name']}" has different settings')
                                elif '::actions::' in base_comp['attributes']['delegate_descriptor_id']:
                                    if comp['attributes']['timeout'] != base_comp['attributes']['timeout']:
                                        componentsDifferences.append(f'action "{comp['attributes']['name']}" timeout is different')
                                    if kwargs.get('action_setting_path',None) is not None:
                                        list_actions_path = kwargs.get('action_setting_path',None)
                                        if type(list_actions_path) == str:
                                            list_actions_path = list(list_actions_path)
                                        mySettings_base = som.Som(json.loads(base_comp['attributes']['settings']))
                                        mySettings_target = som.Som(json.loads(comp['attributes']['settings']))
                                        for path in list_actions_path:
                                            tmp_base = mySettings_base.get(path,'')
                                            tmp_target = mySettings_target.get(path,'')
                                            if tmp_base != tmp_target:
                                                componentsDifferences.append(f'action "{comp['attributes']['name']}" has different settings')
                                    else:
                                        if base_comp['attributes']['settings'] != comp['attributes']['settings']:
                                            componentsDifferences.append(f'action "{comp['attributes']['name']}" has different settings')
                        if checkExist == False: ## does not exist
                            componentsDifferences.append(f'component "{base_comp['attributes']['name']}" does not exist in Target')
                    if len(componentsDifferences)>0:
                        dict_result[target] = ','.join(componentsDifferences) + issue_pub
                    else:
                        if not excludeSimilar:
                            dict_result[target] = 'Similar' + issue_pub
        if cmp_baseDict['component']['type'] == 'extensions':
            for target in list(self.targets.keys()):
                if cmp_baseDict['name'] not in [ext['attributes']['name'] for ext in self.targets[target]['extensions']]:
                    dict_result[target] = f'Extension "{cmp_baseDict['name']}" is not present'
                else:
                    index, extensionTarget = [(index,ext) for index, ext in enumerate(self.targets[target]['extensions']) if ext['attributes']['name'] == cmp_baseDict['name']][0]
                    issue_pub = ""
                    if publishedVersion:
                        try:
                            revisions_targetExt = self.targets[target]["api"].getRevisions(extensionTarget)
                            extensionTarget = self.targets[target]["api"].getLatestPublishedVersion(revisions_targetExt)
                        except:
                            issue_pub = " (not published)"
                        if extensionTarget['attributes']['enabled'] != cmp_baseDict['component']['attributes']['enabled']:
                            dict_result[target] = f'Extension enabled status is different: {cmp_baseDict["component"]["attributes"]["enabled"]} vs {extensionTarget["attributes"]["enabled"]}'+issue_pub
                        if extensionTarget['attributes']['published'] != cmp_baseDict['component']['attributes']['published']:
                            dict_result[target] = f'Extension published status is different: {cmp_baseDict["component"]["attributes"]["published"]} vs {extensionTarget["attributes"]["published"]}'+issue_pub
                    if extensionTarget['attributes']['version'] != cmp_baseDict['component']['attributes']['version']:
                        dict_result[target] = f'Extension version is different: {cmp_baseDict['component']['attributes']['version']} vs {extensionTarget['attributes']['version']}'+issue_pub
                    else:
                        if extensionTarget['attributes']['settings'] != cmp_baseDict['component']['attributes']['settings']:
                            dict_result[target] = 'Extension settings are different'+issue_pub
                        else:
                            if not excludeSimilar:
                                dict_result[target] = 'Similar'+issue_pub
        return dict_result