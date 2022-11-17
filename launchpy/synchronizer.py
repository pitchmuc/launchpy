import re
# Non standard libraries
from .admin import Admin
from .property import Property
from .library import Library
from .launchpy import Translator, copySettings

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
            self.targets[target]['libraryStack'] = {'dataElements':[],'rules':[]}
            #self.targets[target]['rcs'] = self.targets[target]['api'].getRuleComponents()
            self.translator.extendExtensions(self.targets[target]['extensions'],self.targets[target]['name'])
            self.translator.extendRules(self.targets[target]['rules'],self.targets[target]['name'])

    def syncComponent(self,componentName:str=None,componentId:str=None,publishedVersion:bool=False)->None:
        """
        Synchronize a component from the base property to the different target properties.
        It will detect the component with the same name in target properties.
        It will delete the components related objects (ruleComponents, data element code) in the target property and push the template version.
        Arguments:
            componentName : REQUIRED : the name of the component to sync
            componentID : REQUIRED : the id of the component to sync
            publishedVersion : OPTIONAL : if you want to take the version that has been published
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
        if publishedVersion:
            data = self.base['api'].getRevisions(cmp_baseDict['component'])
            publishedVersion = self.base['api'].getLatestPublishedVersion(data)
            cmp_baseDict['component'] = publishedVersion
        ## handling the data element
        if cmp_baseDict['component']['type'] == 'data_elements':
            latestCompVersion = self.base['api'].getDataElement(cmp_base['id']).get('data',cmp_baseDict['component'])
            cmp_baseDict = {'id':latestCompVersion['id'],'name':latestCompVersion['attributes']['name'],'component':latestCompVersion,'copy':copySettings(latestCompVersion)}
            for target in list(self.targets.keys()):
                translatedComponent = self.translator.translate(target,data_element=cmp_baseDict['copy'])
                ## if it does not exist
                if cmp_baseDict['name'] not in [de['attributes']['name'] for de in self.targets[target]['dataElements']]:
                    comp = self.targets[target]['api'].createDataElement(
                        name=cmp_baseDict['name'],
                        descriptor= translatedComponent['descriptor'],
                        settings=translatedComponent['settings'],
                        extension=translatedComponent['extension'],
                        storage_duration = translatedComponent["storage_duration"],
                        force_lower_case = translatedComponent["force_lower_case"],
                        clean_text = translatedComponent["clean_text"],
                        )
                    if cmp_baseDict['component']['attributes']['enabled'] != comp['attributes']['enabled']:
                        updateDE = self.targets[target]['api'].updateDataElement(
                            dataElement_id=comp['id'],
                            attr_dict=translatedComponent)
                    self.targets[target]['libraryStack']['dataElements'].append(comp)
                    self.targets[target]['dataElements'].append(comp)
                else:
                    index,old_component = [(index,de) for index,de in enumerate(self.targets[target]['dataElements']) if de['attributes']['name'] == cmp_baseDict['name']][0]
                    attributes = {
                        "name" : translatedComponent['name'],
                        "enabled" : translatedComponent["enabled"],
                        "delegate_descriptor_id" : translatedComponent["descriptor"],
                        "storage_duration" : translatedComponent["storage_duration"],
                        "force_lower_case" : translatedComponent["force_lower_case"],
                        "clean_text" : translatedComponent["clean_text"],
                        "settings" : translatedComponent["settings"]
                    }
                    comp = self.targets[target]['api'].updateDataElement(
                        dataElement_id=old_component['id'],
                        attr_dict=attributes,
                        )
                    del self.targets[target]['dataElements'][index]
                    self.targets[target]['dataElements'].append(comp)
                    self.targets[target]['libraryStack']['dataElements'].append(comp)
                

        if cmp_baseDict['component']['type'] == 'rules':
            latestCompVersion = self.base['api'].getRule(cmp_base['id']).get('data',cmp_baseDict['component'])
            cmp_baseDict = {'id':latestCompVersion['id'],'name':latestCompVersion['attributes']['name'],'component':latestCompVersion,'copy':copySettings(latestCompVersion)}
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
                    targetRule = self.targets[target]['api'].createRule(
                        name=cmp_baseDict['name']
                        )
                    targetRuleId = targetRule['id']
                    self.targets[target]['rules'].append(targetRule)
                    self.targets[target]['libraryStack']['rules'].append(targetRule)
                    for rc in template_ruleComponents.reverse():
                        translatedComponent = self.translator.translate(target,rule_component=copySettings(rc))
                        translatedComponent['rule_setting']['data'][0]['id'] = targetRuleId
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
                        translatedComponent = self.translator.translate(target,rule_component=copySettings(rc))
                        translatedComponent['rule_setting']['data'][0]['id'] = targetRuleId
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

        
