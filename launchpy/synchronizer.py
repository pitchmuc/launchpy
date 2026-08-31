import re,json,threading
# Non standard libraries
from launchpy.admin import Admin
from launchpy.property import Property
from launchpy.library import Library
from launchpy.launchpy import Translator, copySettings
from launchpy import connector
from copy import deepcopy
from aepp import som
from concurrent.futures import ThreadPoolExecutor

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

    def __init__(self,base:str | Property = None,targets:list=None,**kwargs)->None:
        """
        Instantiating the Synchronizer taking 2 parameters, base property name, target property list.
        Arguments:
            base : REQUIRED : The name of your base/template property or the instance of Property class
            targets : REQUIRED : The list of property names that you want to sync with.
                the list of target can be string of property name or Property instance for other organization.
        possible kwargs:
            dynamicRuleComponent: A data element name that contains rule for synchronization on the property.
            mapping_extensions : A dictionary of {"target-extension-name" : "base-extension-name"} when in different IMS org and 2 private extensions are name differently for the same purpose.
        """
        tmp_admin = Admin()
        cid = tmp_admin.getCompanyId()
        properties = tmp_admin.getProperties(cid)
        mapping_extensions = kwargs.get('mapping_extensions',None)
        self.base = {}
        if type(base) == str:
            if '@' in base:
                new_connector = connector.AdobeRequest(org_name=base.split('@')[1])
                new_admin = Admin(_connector=new_connector)
                new_cid = new_admin.getCompanyId()
                new_properties = new_admin.getProperties(new_cid)
                base_property = [prop for prop in new_properties if prop['attributes']['name'] == base.split('@')[0]]
                if len(base_property) == 0:
                    raise KeyError("The base property name has not been found in your account")
                self.base["name"] = base.split('@')[0]
                self.base["api"]:Property = Property(base_property[0],_connector=new_connector)
            else:
                base_property = [prop for prop in properties if prop['attributes']['name'] == base]
                if len(base_property) ==0:
                    raise KeyError("The base property name has not been found in your account")
                self.base["name"] = base
                self.base["api"]:Property = Property(base_property[0])
        elif type(base) == Property:
            self.base["name"] = base.name
            self.base["api"]:Property = base
        self.base['rules'] = self.base['api'].getRules()
        self.base['dataElements'] = self.base['api'].getDataElements()
        self.base['extensions'] = self.base['api'].getExtensions()
        self.translator = Translator(mapping_extensions=mapping_extensions)
        self.translator.setBaseExtensions(self.base['extensions'],self.base['name'])
        self.translator.setBaseRules(self.base['rules'],self.base['name'])
        self.targets = {}
        self.target_configs = {}
        for target in targets:
            if isinstance(target,str):
                if '@' in target:
                    prop_name = target.split('@')[0]
                    new_org = target.split('@')[1]
                    new_connector = connector.AdobeRequest(org_name=new_org)
                    new_admin = Admin(_connector=new_connector,org_name=new_org)
                    new_cid = new_admin.getCompanyId()
                    new_properties = new_admin.getProperties(new_cid)
                    tmp_target = [prop for prop in new_properties if prop['attributes']['name'] == prop_name]
                    if len(tmp_target) == 0:
                        raise KeyError(f"The target property : {prop_name} cannot be found. Please, fix it")
                    self.targets[target] = {'api' : Property(tmp_target[0],_connector=new_connector,org_name=new_org),'name':prop_name}
                else:
                    tmp_target = [prop for prop in properties if prop['attributes']['name'] == target]
                    if len(tmp_target) == 0:
                        raise KeyError(f"The target property : {target} cannot be found. Please, fix it")
                    self.targets[target] = {'api' : Property(tmp_target[0]),'name':target}
            elif isinstance(target,Property):
                self.targets[target.name] = {'api' : deepcopy(target),'name':target.name}
                target = target.name
            self.targets[target]['rules'] = self.targets[target]['api'].getRules()
            self.targets[target]['extensions'] = self.targets[target]['api'].getExtensions()
            self.targets[target]['dataElements'] = self.targets[target]['api'].getDataElements()
            self.targets[target]['libraryStack'] = {'dataElements':[],'rules':[],"extensions":[]}
            self.translator.extendExtensions(self.targets[target]['extensions'],target)
            if len(self.targets[target]['rules']) > 0:
                self.translator.extendRules(self.targets[target]['rules'],target)
            else:
                self.translator.rules[target] = None
        self._base_lock = threading.Lock()
        self._target_locks = {target: threading.Lock() for target in self.targets}
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
    
    def __prepareBaseComponent__(self,componentName:str=None,componentId:str=None,publishedVersion:bool=False,**kwargs)->dict:
        """
        Prepare the base component to be used in the syncComponent method.
        Arguments:
            componentName : REQUIRED : the name of the component to sync
            componentID : REQUIRED : the id of the component to sync
            publishedVersion : OPTIONAL : if you want to take the version that has been published
        kwargs: 
            libraryLinked : OPTIONAL : If you want to pass ID that are associated to a specific library. Default: False
        """
        cmp_base=None
        componentBase = None
        lib_cmp_base = None
        if componentId is not None:
            if componentId.startswith('DE'): ## if data element
                if kwargs.get('libraryLinked',False):
                    lib_cmp_base = self.base['api'].getDataElement(componentId)
                    if lib_cmp_base is None:
                         raise KeyError("Component ID cannot be found")
                    componentId = lib_cmp_base['links']['origin'].split('/').pop()
                componentBase = [de for de in self.base['dataElements'] if de['id'] == componentId]
                if len(componentBase)==0:
                    raise KeyError("Component ID cannot be found")
                if type(componentBase) == list and len(componentBase)>0:
                    cmp_base = componentBase[0]
            elif componentId.startswith('RL'): ## if a rule
                if kwargs.get('libraryLinked',False):
                    lib_cmp_base = self.base['api'].getRule(componentId)
                    if lib_cmp_base is None:
                         raise KeyError("Component ID cannot be found")
                    componentId = lib_cmp_base['links']['origin'].split('/').pop()
                componentBase = [de for de in self.base['rules'] if de['id'] == componentId]
                if len(componentBase)==0:
                    raise KeyError("Component ID cannot be found")
                if type(componentBase) == list and len(componentBase)>0:
                    cmp_base = componentBase[0]
            elif componentId.startswith('EX'): ## if an extension
                if kwargs.get('libraryLinked',False):
                    lib_cmp_base = self.base['api'].getExtension(componentId)
                    if lib_cmp_base is None:
                         raise KeyError("Component ID cannot be found")
                    componentId = lib_cmp_base['links']['origin'].split('/').pop()
                componentBase = [ext for ext in self.base['extensions'] if ext['id'] == componentId]
                if len(componentBase)==0:
                        raise KeyError("Component ID cannot be found")
                if type(componentBase) == list and len(componentBase)>0:
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
                ## Updating mapping table with old name when published version name diff than last version name.
                with self._base_lock:
                    if cmp_baseDict['component']['type'] == 'rules':
                        self.translator.extendBaseRules(
                        ruleName=publishedVersion['attributes']['name'],
                        ruleId=publishedVersion['id'],
                        property_name=self.base["name"])
                        self.base['rules'].append(publishedVersion)
                    if cmp_baseDict['component']['type'] == 'data_elements':
                        self.base['dataElements'].append(publishedVersion)
            cmp_baseDict = {'id':publishedVersion['id'],'name':publishedVersion['attributes']['name'],'component':publishedVersion,'copy':copySettings(publishedVersion)}
        if lib_cmp_base is not None and kwargs.get('libraryLinked',False) and cmp_baseDict['component']['type'] in ['rules','data_elements']:
            if lib_cmp_base['attributes']['name'] != cmp_baseDict['name']:
                with self._base_lock:
                    if cmp_baseDict['component']['type'] == 'rules':
                        self.translator.extendBaseRules(
                        ruleName=lib_cmp_base['attributes']['name'],
                        ruleId=lib_cmp_base['id'],
                        property_name=self.base["name"])
                        self.base['rules'].append(lib_cmp_base)
                    if cmp_baseDict['component']['type'] == 'data_elements':
                        self.base['dataElements'].append(lib_cmp_base)
            cmp_baseDict = {'id':lib_cmp_base['id'],'name':lib_cmp_base['attributes']['name'],'component':lib_cmp_base,'copy':copySettings(lib_cmp_base)}
        return cmp_baseDict

    def syncComponent(self,componentName:str=None,componentId:str=None,publishedVersion:bool=False,forceCreation:bool=False,**kwargs)->None:
        """
        Synchronize a component from the base property to the different target properties.
        It will detect the component with the same name in target properties.
        It will delete the components related objects (ruleComponents, data element code) in the target property and push the template version.
        If you uploaded a dynamicRuleComponent data element config during the init method, any element that are not sync because of the exclComponentList will return a dict: {componentName:False} 
        Arguments:
            componentName : REQUIRED : the name of the component to sync
            componentID : REQUIRED : the id of the component to sync
            publishedVersion : OPTIONAL : if you want to take the version that has been published
            forceCreation : OPTIONAL : If the component does not exist in the target property, create it. Default: False
        possible kwargs:
            timeout : OPTIONAL : The timeout to be used for the rule component. If not provided, the existing timeout will be used.
            libraryLinked : OPTIONAL : If you want to take a component ID that are associated to a specific library. Default: False. If set to True, the method will look for the component in the library and take the version linked to the library instead of the latest version in the property. Do not work for Extensions.
            verbose : OPTIONAL : If set to True, it will print the synchronization status of each property. Default: False.
        """
        timeout = kwargs.get('timeout',None)
        libraryLinked = kwargs.get('libraryLinked',False)
        verbose = kwargs.get('verbose',False)
        if componentName is None and componentId is None:
            raise ValueError('Require a component Name of a component ID')
        cmp_baseDict = self.__prepareBaseComponent__(componentName=componentName,componentId=componentId,publishedVersion=publishedVersion,libraryLinked=libraryLinked)
        ## handling the data element
        if cmp_baseDict['component']['type'] == 'data_elements':
            for target in list(self.targets.keys()):
                flagAllowList = False
                ## check if the component is in the exclComponentList
                if any([bool(re.search(key,cmp_baseDict['name'])) for key in self.target_configs.get(target,{}).get('exclComponents',[])]):
                    if kwargs.get('verbose',False):
                        print(f'The data element "{cmp_baseDict["name"]}" is in the exclusion list for the target property "{target}". Skipping it.')
                    continue
                ## if there is an allow list for that property
                if len(self.target_configs.get(target,{}).get('inclComponents',[]))>0:
                    if any([bool(re.search(key,cmp_baseDict['name'])) for key in self.target_configs.get(target,{}).get('inclComponents',[])]):
                        flagAllowList = True
                ## if there is no allow list for that property, or no match in the list of target properties, or component was allow
                if len(self.target_configs.get(target,{}).get('inclComponents',[]))==0 or flagAllowList:
                    with self._target_locks[target]:
                        translatedComponent = self.translator.translate(target,data_element=cmp_baseDict['copy'])
                        ## if it does not exist
                        if cmp_baseDict['name'] not in [de.get('attributes',{}).get('name') for de in self.targets[target]['dataElements']]:
                            if forceCreation:
                                if verbose:
                                    print(f'The data element "{cmp_baseDict["name"]}" does not exist in the target property "{target}". Creating it')
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
                                print(f'The data element "{cmp_baseDict["name"]}" does not exist in the target property "{target}". Set forceCreation to True if you want to create it.')
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
                flagSkipCreation = False ## do not check for new rule config if rule has not been created
                ## check if the component is in the exclComponentList
                if any([bool(re.search(key,cmp_baseDict['name'])) for key in self.target_configs.get(target,{}).get('exclComponents',[])]):
                    if kwargs.get('verbose',False):
                        print(f'The rule "{cmp_baseDict["name"]}" is in the exclusion list for the target property "{target}". Skipping it.')
                    continue
                ## if there is an allow list for that property
                if len(self.target_configs.get(target,{}).get('inclComponents',[]))>0:
                    if any([bool(re.search(key,cmp_baseDict['name'])) for key in self.target_configs.get(target,{}).get('inclComponents',[])]):
                        flagAllowList = True
                ## if there is no allow list for that property, or no match in the list of target properties, or component was allow
                if len(self.target_configs.get(target,{}).get('inclComponents',[]))==0 or flagAllowList:
                    with self._target_locks[target]:
                        ## if rule does not exist
                        if cmp_baseDict['name'] not in [rule['attributes']['name'] for rule in self.targets[target]['rules']]:
                            if forceCreation:## creating the rule
                                if verbose:
                                    print(f'The rule "{cmp_baseDict["name"]}" does not exist in the target property "{target}". Creating it')
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
                            else:
                                flagSkipCreation = True
                                print(f'The rule "{cmp_baseDict["name"]}" does not exist in the target property "{target}". Not creating it')
                        else: ## if a rule exist with the same name
                            if verbose:
                                    print(f'The rule "{cmp_baseDict["name"]}" exists in the target property "{target}". Updating it')
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
                                except Exception as e:
                                    print(e)
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
                        if not flagSkipCreation: ## if the rule was created or updated, we want to make sure that the attribute are the same as the template
                            if cmp_baseDict['component']['attributes']['enabled'] != targetRule['attributes']['enabled']:
                                baseRuleAttr = copySettings(cmp_baseDict['component'])
                                targetRule = self.targets[target]['api'].updateRule(rule_id=targetRuleId,attr_dict=baseRuleAttr) ## keeping in a var for debug
                                del self.targets[target]['rules'][index]
                                self.targets[target]['rules'].append(targetRule)
        if cmp_baseDict['component']['type'] == 'extensions':
            for target in list(self.targets.keys()):
                flagAllowList = False
                ## check if the component is in the exclComponentList
                if any([bool(re.search(key,cmp_baseDict['name'])) for key in self.target_configs.get(target,{}).get('exclComponents',[])]):
                    if kwargs.get('verbose',False):
                        print(f'The extension "{cmp_baseDict["name"]}" is in the exclusion list for the target property "{target}". Skipping it.')
                    continue
                ## if there is an allow list for that property
                if len(self.target_configs.get(target,{}).get('inclComponents',[]))>0:
                    if any([bool(re.search(key,cmp_baseDict['name'])) for key in self.target_configs.get(target,{}).get('inclComponents',[])]):
                        flagAllowList = True
                ## if there is no allow list for that property, or no match in the list of target properties, or component was allow
                if len(self.target_configs.get(target,{}).get('inclComponents',[]))==0 or flagAllowList:
                    with self._target_locks[target]:
                        comp_base_settings = cmp_baseDict['copy']['settings']
                        comp_base_extension_id = cmp_baseDict['copy']['extension_id']
                        descriptor = cmp_baseDict['copy']['descriptor']
                        if cmp_baseDict['name'] not in [ext['attributes']['name'] for ext in self.targets[target]['extensions']]: ## if extension does not exist
                            if forceCreation:
                                if verbose:
                                    print(f'The extension "{cmp_baseDict["name"]}" does not exist in the target property "{target}". Creating it')
                                comp = self.targets[target]['api'].createExtension(
                                    extension_id=comp_base_extension_id,
                                    settings=comp_base_settings,
                                    descriptor=descriptor
                                )
                                if 'id' not in comp.keys():
                                    raise Exception("The extension could not be created. Please check if your extensions' versions are aligned in the properties.")
                                self.targets[target]['libraryStack']['extensions'].append(comp)
                                self.targets[target]['extensions'].append(comp)
                                self.translator.extendExtensions(self.targets[target]['extensions'],target)
                            else:
                                print(f'The extension "{cmp_baseDict["name"]}" does not exist in the target property "{target}". Set forceCreation to True if you want to create it.')
                        else: ## if extension exist, we will update it
                            if verbose:
                                print(f'The extension "{cmp_baseDict["name"]}" exists in the target property "{target}". Updating it')
                            index, targetExt = [(index,ext) for index, ext in enumerate(self.targets[target]['extensions']) if ext['attributes']['name'] == cmp_baseDict['name']][0]
                            comp = self.targets[target]['api'].updateExtension( ## create and update used the POST method both
                                extension_id=targetExt['id'],
                                attr_dict=cmp_baseDict['copy']
                            )
                            if 'id' not in comp.keys():
                                raise Exception("The extension could not be updated. Please check if your extensions' versions are aligned in the properties.")
                            del self.targets[target]['extensions'][index]
                            self.targets[target]['extensions'].append(comp)
                            self.targets[target]['libraryStack']['extensions'].append(comp)
                            self.translator.extendExtensions(self.targets[target]['extensions'],target)


    def syncComponents(self,componentsName:list=None,componentsId:list=None,publishedVersion:bool=False,forceCreation:bool=False)->None:
        """
        Sync multiple components by looping through the list of name passed.
        Arguments:
            componentsName : REQUIRED : The list of component names to sync
            componentsId : REQUIRED : The list of component ID to sync
            publishedVersion : OPTIONAL : if you want to take the version that has been published
            forceCreation : OPTIONAL : If set to True, it will sync the components even if they do not exist in the target properties. If set to False, it will only sync the components that already exist in the target properties. Default: False.
        """
        if componentsName is not None:
            for component in componentsName:
                self.syncComponent(componentName=component,publishedVersion=publishedVersion,forceCreation=forceCreation)
        if componentsId is not None:
            for component in componentsId:
                self.syncComponent(componentId=component,publishedVersion=publishedVersion,forceCreation=forceCreation)
    
    def syncRules(self,regex:str=None,forceCreation:bool=False,publishedVersion:bool=False)->None:
        """
        Synchronizing the rules in the base property to the target properties.
        Arguments:
            regex : OPTIONAL : If you want to filter the rules to sync based on a regex pattern. Default: None (sync all rules)
            forceCreation : OPTIONAL : If set to True, it will sync the rules even if they do not exist in the target properties. If set to False, it will only sync the rules that already exist in the target properties. Default: False.
            publishedVersion : OPTIONAL : If set to True, it will sync the latest published version of the rules. Default: False.
        """
        base_rule_names = [rule['attributes']['name'] for rule in self.base['rules']]
        if regex is not None:
            base_rule_names = [rule for rule in base_rule_names if re.search(regex,rule)]
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.syncComponent, componentName=rule, forceCreation=forceCreation, publishedVersion=publishedVersion) for rule in base_rule_names]
            for future in futures:
                future.result()

    def syncDataElements(self,regex:str=None,forceCreation:bool=False,publishedVersion:bool=False)->None:
        """
        Synchronizing the data elements in the base property to the target properties.
        Arguments:
            regex : OPTIONAL : If you want to filter the data elements to sync based on a regex pattern. Default: None (sync all data elements)
            forceCreation : OPTIONAL : If set to True, it will sync the data elements even if they do not exist in the target properties. If set to False, it will only sync the data elements that already exist in the target properties. Default: False.
            publishedVersion : OPTIONAL : If set to True, it will sync the latest published version of the data elements. Default: False.
        """
        base_de_names = [de['attributes']['name'] for de in self.base['dataElements']]
        if regex is not None:
            base_de_names = [de for de in base_de_names if re.search(regex,de)]
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.syncComponent, componentName=de, forceCreation=forceCreation, publishedVersion=publishedVersion) for de in base_de_names]
            for future in futures:
                future.result()
    
    def syncExtensions(self,regex:str=None,forceCreation:bool=False, **kwargs)->None:
        """
        Take extensions from the Base and try to install them on the target properties.
        It will check if the extension is already installed in the target property, if not it will install it.
        Arguments:
            regex : OPTIONAL : If you want to filter the extensions name to sync based on a regex pattern. Default: None (sync all extensions)
            forceCreation : OPTIONAL : If set to True, will force the creation of the extension even if it already exists. Default: False
        """
        base_extensions = self.base['extensions']
        base_extension_names = [ext['attributes']['name'] for ext in base_extensions]
        if regex is not None:
            base_extension_names = [ext for ext in base_extension_names if re.search(regex,ext)]
        for ext_name in base_extension_names:
            self.syncComponent(componentName=ext_name,forceCreation=forceCreation,**kwargs)

    
    def createTargetsLibrary(self,name:str="syncComponents",assignEnv:bool|str=False,**kwargs)->None:
        """
        This method will create or update a Library in all of the target properties to gather all elements changed.
        If a library exists and **contains** the same name, it will be used.
        Argument:
            name : REQUIRED : The name of the library to create. Default : "syncComponents"
            assignEnv : REQUIRED : If you want to assign a library to an environment. 
                    If set to True, the library will be assigned to an available environment in the Target Property if available and build it.
                    If set to a string (regex supported), the library will be assigned to the environment with the name provided if it exists, and build it. If that environment is used in a Library, it will remove that environment from the library and assign it to the new one. Default: False  
        """
        response = {target:{'libraryName':name} for target in self.targets.keys()}
        for target in list(self.targets.keys()):
            if 'library' not in list(self.targets[target].keys()):
                librariesDev = self.targets[target]['api'].getLibraries(state="development")
                if True in [bool(re.search(name,lib['attributes']['name'])) for lib in librariesDev]:
                    lib = [lib for lib in librariesDev if name in lib['attributes']['name']][0]
                else:
                    lib = self.targets[target]['api'].createLibrary(name=name,return_class=False)
                library = Library(lib, _connector=self.targets[target]['api'].connector)
                self.targets[target]['library'] = library
            self.targets[target]['library'].getFullLibrary()
            ## taking care of rule update
            ## PATCH replaces the whole relationship, so the payload must keep components the library already has
            currentRuleIds = {rule['id'] for rule in self.targets[target]['library'].relationships['rules']}
            stackRuleIds = {rule['id'] for rule in self.targets[target]['libraryStack']['rules']}
            newRules = list(stackRuleIds - currentRuleIds)
            ruleIdsToKeep = list(currentRuleIds | stackRuleIds)
            if len(ruleIdsToKeep) > 0:
                self.targets[target]['library'].updateRules(ruleIdsToKeep)
            if len(newRules)>0:
                self.targets[target]['library'].addRules(newRules)
            ## taking care of data elements
            currentDataElementIds = {de['id'] for de in self.targets[target]['library'].relationships['data_elements']}
            stackDataElementIds = {de['id'] for de in self.targets[target]['libraryStack']['dataElements']}
            newDataElements = list(stackDataElementIds - currentDataElementIds)
            dataElementIdsToKeep = list(currentDataElementIds | stackDataElementIds)
            if len(dataElementIdsToKeep) > 0:
                self.targets[target]['library'].updateDataElements(dataElementIdsToKeep)
            if len(newDataElements)>0:
                self.targets[target]['library'].addDataElements(newDataElements)
            ## taking care of the extensions
            currentExtensionIds = {ext['id'] for ext in self.targets[target]['library'].relationships['extensions']}
            stackExtensionIds = {ext['id'] for ext in self.targets[target]['libraryStack']['extensions']}
            newExtensions = list(stackExtensionIds - currentExtensionIds)
            extensionIdsToKeep = list(currentExtensionIds | stackExtensionIds)
            if len(extensionIdsToKeep) > 0:
                self.targets[target]['library'].updateExtensions(extensionIdsToKeep)
            if len(newExtensions)>0:
                self.targets[target]['library'].addExtensions(newExtensions)
            if type(assignEnv) == bool and assignEnv == True:
                envs = self.targets[target]['api'].getEnvironments()
                prod = [env for env in envs if env['attributes']['stage'].lower() == 'production']
                if len(prod) == 0:
                    prod_script = "https://assets.adobedtm.com/" ## default script source when no production environment exist, with a random id to avoid any conflict with an existing environment script source.
                else:
                    prod = prod[0]
                    prod_script = prod['meta'].get('script_sources',[{}])[0].get('minified')
                found_free_env = False
                if len(envs)>0:
                    for env in envs:
                        library_rel = env['relationships']['library'].get('data')
                        if library_rel is None: ## no associated library
                            found_free_env = True
                            envId = env['id']
                            envName = env['attributes']['name']
                            scriptSource = env['meta'].get('script_sources',[{}])[0].get('minified')
                            break ## take the first one available
                if found_free_env:
                    self.targets[target]['library'].setEnvironment(envId)
                    self.targets[target]['library'].build()
                    response[target]['environment'] = envName
                    response[target]['script'] = {f"{target} - {self.targets[target]['library'].name}" : {
                        "replace": prod_script,
                        "with": scriptSource
                    }}
                    response[target]['build_status'] = self.targets[target]['library'].build_status
                else:
                    response[target]['environment'] = "No free environment to assign"
                    response[target]['script'] = None
            elif type(assignEnv) == str:
                envs = self.targets[target]['api'].getEnvironments()
                prod = [env for env in envs if env['attributes']['stage'].lower() == 'production']
                if len(prod) == 0:
                    prod_script = "https://assets.adobedtm.com/" ## default script source when no production environment exist, with a random id to avoid any conflict with an existing environment script source.
                else:
                    prod = prod[0]
                    prod_script = prod['meta'].get('script_sources',[{}])[0].get('minified')
                env = [env for env in envs if re.search(assignEnv, env['attributes']['name'], re.IGNORECASE)]
                if len(env) == 0:
                    response[target]['environment'] = f"No environment with the name {assignEnv} to assign"
                    response[target]['script'] = None
                elif len(env) == 1:
                    env = env[0]
                    envId = env['id']
                    envName = env['attributes']['name']
                    scriptSource = env['meta'].get('script_sources',[{}])[0].get('minified')
                    libraryUsed = self.targets[target]["api"].getEnvironmentLibrary(envId)
                    if libraryUsed is not None:
                        print(f'Environment is already used by library "{libraryUsed["attributes"]["name"]}" in "{target}" property. Removing the environment from that library.')
                        libraryUsedId = libraryUsed['id']
                        tmp_lib = Library(libraryUsedId, _connector=self.targets[target]['api'].connector)
                        tmp_lib.removeEnvironment()
                    self.targets[target]['library'].setEnvironment(envId)
                    self.targets[target]['library'].build()
                    response[target]['environment'] = envName
                    response[target]['script'] = {f"{target} - {self.targets[target]['library'].name}" : {
                    "replace": prod_script,
                    "with": scriptSource
                    }}
                    response[target]['build_status'] = self.targets[target]['library'].build_status
                else:
                    response[target]['environment'] = f"Multiple environment with the name {assignEnv} to assign"
                    response[target]['script'] = None
        return response

    def upgradeTargetExtension(self,extensionName:str=None,platform:str="web",verbose:bool=False)->dict:
        """
        Upgrade the name extension in the target properties.
        Arguments:
            extensionName : REQUIRED : The name of the extension to upgrade.
                                        ex : "core" or "adobe-analytics"
            platform : OPTIONAL : If you want to update the extension of a specific platform (default "web")
            verbose : OPTIONAL : If set to True, will print detailed information about the upgrade process. Default False.
        """
        if extensionName is None:
            raise ValueError("Require an extension name")
        response = {}
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
                        response[prop] = f"Extension '{extName}' upgraded successfully."
                        if verbose:
                            print(f"Extension '{extName}' upgraded successfully in '{prop}' property.")
                    else:
                        response[prop] = f"Extension '{extName}' is already up to date."
                        if verbose:
                            print(f"Extension '{extName}' is already up to date in '{prop}' property.")
            except Exception as e:
                response[prop] = f"Could not upgrade extension '{extensionName}': {e}"
                if verbose:
                    print(f"Could not upgrade extension '{extensionName}' in '{prop}' property: {e}")
        return response


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
                self.targets[target]['rules'].append(comp)
                self.translator.extendTargetRules(ruleName=new_name,ruleId=comp['id'],property_name=target) 


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
            libraryLinked : bool : If you want to pass ID that are associated to a specific library. Default: False
        """
        if componentName is None and componentId is None:
            raise ValueError('Require a component Name of a component ID')
        cmp_baseDict = self.__prepareBaseComponent__(componentName=componentName,componentId=componentId,publishedVersion=publishedVersion,libraryLinked=kwargs.get('libraryLinked',False))
        dict_result = {tar:"" for tar in self.targets.keys()}
        dict_result['base-enabled'] = cmp_baseDict['component']['attributes'].get('enabled',False)
        dict_result['base-published'] = cmp_baseDict['component']['attributes'].get('published',False)
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
    
    def __checkLibrarySync__(self,library:str=None,state='published',excludeSimilar:bool=False,libraryLinked:bool=True,publishedVersion:bool=False)->dict:
        """
        Check if the components in a library, from the base property, is synced to the different target properties.
        By default, it will compare the version of the library to the latest version in the target properties.
        It will return a dictionary with the key being the component name and the value being the result of the evaluation, such as {componentName: {'targetProperty': 'similar'}} when library have same settings.
        Arguments:
            library : REQUIRED : the library name or the library ID to get the components.
            state : OPTIONAL : the state of the library to compare. Default: 'published', possible states: "development", "submitted", "approved", "rejected", "published"
            excludeSimilar : OPTIONAL : If you do not want to see the result if the comparison provide a "similar" result. Similar means that the elements are about the same. Default: False. 
            libraryLinked : OPTIONAL : If set to True, it will use library linked components for comparison. Default: True.
            publishedVersion : OPTIONAL : If set to True, it will compare the components to the published version in the target properties. Default: False.
        """
        if library is None:
            raise ValueError('Require a library Name of a library ID')
        libraryLink = True
        base_libraries = self.base['api'].getLibraries(state=state)
        if library in [lib['attributes']['name'] for lib in base_libraries]:
            base_library = [lib for lib in base_libraries if lib['attributes']['name'] == library][0]
        elif library in [lib['id'] for lib in base_libraries]:
            base_library = [lib for lib in base_libraries if lib['id'] == library][0]
        else:
            raise ValueError('The library name or ID provided does not exist in the base property')
        myLib = Library(base_library['id'], _connector=self.base['api'].connector)
        components = myLib.getFullLibrary()
        rules = components['rules']
        dataElements = components['data_elements']
        extensions = components['extensions']
        elements = rules + dataElements + extensions
        if publishedVersion == True:
            element_ids = {elem['id']: elem['attributes']['name'] for elem in elements}
            libraryLink = False
        elif libraryLinked == True:
            element_ids ={elem['links']['self'].split('/').pop():elem['attributes']['name'] for elem in elements}
        else:
            element_ids = {elem['id']: elem['attributes']['name'] for elem in elements}
        dict_check = {}
        for element_id, element_name in element_ids.items():
            dict_check[element_name] = self.checkComponentSync(componentId=element_id, excludeSimilar=excludeSimilar,publishedVersion=publishedVersion,libraryLinked=libraryLink)
        return dict_check
    
    def syncFromLibrary(self,library:str=None,state='published',forceCreation:bool=False,libraryLinked:bool=True,publishedVersion:bool=False,dryRun:bool=False,**kwargs)->None:
        """
        Sync the components in a library, from the base property, to the different target properties by using the createTargetsLibrary method.
        Arguments:
            library : REQUIRED : the library name or the library ID to get the components.
            state : OPTIONAL : the state of the library to compare. Default: 'published', possible states: "development", "submitted", "approved", "rejected", "published"
            forceCreation : OPTIONAL : If set to True, it will sync the components even if they do not exist in the target properties. If set to False, it will only sync the components that already exist in the target properties. Default: False.
            libraryLinked : OPTIONAL : If set to True, it will sync the components using the library version. Default: False.
            publishedVersion : OPTIONAL : if you want to sync the version of the library that has been published in your base vs the published version of your target. Default: False.
            dryRun : OPTIONAL : If set to True, it will not actually sync the components but will return a dictionary with the components that would be synced and the target properties they would be synced to. Default: False.
        Possible kwargs: 
            verbose : bool : If set to True, it will print the name of the components and the property that are being synced and the target property. Default: False.
        """
        verbose = kwargs.get('verbose', False)
        if library is None:
            raise ValueError('Require a library Name of a library ID')
        libs = self.base['api'].getLibraries(state=state)
        if library in [lib['attributes']['name'] for lib in libs]:
            libraryId = [lib for lib in libs if lib['attributes']['name'] == library][0]['id']
        elif library in [lib['id'] for lib in libs]:
            libraryId = [lib for lib in libs if lib['id'] == library][0]['id']
        else:
            raise ValueError('The library name or ID provided does not exist in the base property')
        if dryRun:
            return self.__checkLibrarySync__(library=library,state=state,excludeSimilar=False,libraryLinked=libraryLinked,publishedVersion=publishedVersion)
        myLib = self.base['api'].getLibrary(libraryId,return_class=True)
        rules = myLib.getRules()
        dataelements = myLib.getDataElements()
        extensions = myLib.getExtensions()
        if len(extensions)>0:
            for ext in extensions:
                try:
                    self.upgradeTargetExtension(extensionName=ext['attributes']['name'],platform=ext['attributes']['platform'],verbose=verbose)
                except:
                    print(f'Extension {ext["attributes"]["name"]} could not be updated in the target properties. Please check if the extension exist and if there is an update available.')
        if len(rules)>0:
            for rule in rules:
                try:
                    if libraryLinked:
                        ruleId = rule['links']['self'].split('/').pop()
                    else:
                        ruleId = rule['id']
                    self.syncComponent(componentId=ruleId,publishedVersion=publishedVersion, forceCreation=forceCreation,libraryLinked=libraryLinked,verbose=verbose)
                except:
                    print(f'Rule {rule["attributes"]["name"]} could not be updated in the target properties. Please check if the rule exist.')
        if len(dataelements)>0:
            for de in dataelements:
                try:
                    if libraryLinked:
                        deId = de['links']['self'].split('/').pop()
                    else:
                        deId = de['id']
                    self.syncComponent(componentId=deId,publishedVersion=publishedVersion,forceCreation=forceCreation,libraryLinked=libraryLinked,verbose=verbose)
                except:
                    print(f'Data Element {de["attributes"]["name"]} could not be updated in the target properties. Please check if the data element exist.')
        return 