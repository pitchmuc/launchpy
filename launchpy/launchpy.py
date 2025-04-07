import json
from collections import defaultdict
from copy import deepcopy
# Non standard libraries
from pathlib import Path
from typing import IO, Union
from .configs import saveFile

def extensionsInfo(data: list)->dict:
    """
    Return a dictionary from the list provided from the extensions request.
    Arguments: 
        - data : REQUIRED : list information returned by the getExtension method. 
    """
    extensions = {}
    for extension in data:
        extensions[extension['attributes']['name']] = {
            'created_at': extension['attributes']['created_at'],
            'updated_at': extension['attributes']['updated_at'],
            'published': extension['attributes']['published'],
            'dirty': extension['attributes']['dirty'],
            'review_status': extension['attributes']['review_status'],
            'revision_number': extension['attributes']['revision_number'],
            'version': extension['attributes']['version'],
            'settings': extension['attributes']['settings'],
            'id': extension['id'],
            'extension_id': extension['relationships']['extension_package']['data']['id']
        }
        if 'deleted_at' in extension['meta'].keys():
            extensions[extension['attributes']['name']]['deteled'] = True
        else:
            extensions[extension['attributes']['name']]['deteled'] = False
    return extensions


def rulesInfo(data: list)-> dict:
    """
    Return a dictionary from the list provided from the rules request.
    Arguments : 
        - data : REQUIRED : list information returned by the getRules method. 
    """
    rules = defaultdict(None)
    for rule in data:
        rules[rule['attributes']['name']] = {
            'created_at': rule['attributes']['created_at'],
            'updated_at': rule['attributes']['updated_at'],
            'published': rule['attributes']['published'],
            'dirty': rule['attributes']['dirty'],
            'enabled': rule['attributes']['enabled'],
            'review_status': rule['attributes']['review_status'],
            'revision_number': rule['attributes']['revision_number'],
            'id': rule['id'],
            'latest_revision_number': rule['meta']['latest_revision_number'],
            'rule_components': rule['links'].get('rule_components')
        }
    return rules


def ruleComponentInfo(data: list)->dict:
    """
    Return a dictionary from the list provided from the rules component request.
    Arguments : 
        - data : REQUIRED : list information returned by the getRuleComponent method. 
    """
    components = {}
    for component in data:
        components[component['attributes']['name']] = {
            'id': component['id'],
            'created_at': component['attributes']['created_at'],
            'updated_at': component['attributes']['updated_at'],
            'delegate_descriptor_id': component['attributes']['delegate_descriptor_id'],
            'name': component['attributes']['name'],
            'dirty': component['attributes']['dirty'],
            'order': component['attributes']['order'],
            'rule_order': component['attributes']['rule_order'],
            'published': component['attributes']['published'],
            'revision_number': component['attributes']['revision_number'],
            'settings': component['attributes']['settings']
        }
    return components


def dataElementInfo(data: list)->dict:
    """
    return information about data elements as dictionary.
    arguments : 
        - data : list return by the getDataElement value
    """
    elements = defaultdict(None)
    for element in data:
        elements[element['attributes']['name']] = {
            'id': element['id'],
            'created_at': element['attributes']['created_at'],
            'updated_at': element['attributes']['updated_at'],
            'dirty': element['attributes']['dirty'],
            'enabled': element['attributes']['enabled'],
            'name': element['attributes']['name'],
            'published': element['attributes']['published'],
            'revision_number': element['attributes']['revision_number'],
            'delegate_descriptor_id': element['attributes']['delegate_descriptor_id'],
            'default_value': element['attributes']['default_value'],
            'force_lower_case': element['attributes']['force_lower_case'],
            'storage_duration': element['attributes']['storage_duration'],
            'settings': element['attributes']['settings']
        }
    return elements


def _defineSearchType(_name: str = None, _id: str = None)->tuple:
    if _name is not None:
        condition = 'name'
        value = _name
    elif _id is not None:
        condition = 'id'
        value = _id
    else:
        raise SyntaxError('The ruleName or ruleId should be provided')
    return condition, value


def extractSettings(element: Union[dict,IO], analyticsCode:bool=True, save: bool = False,encoding:str='utf-8',useIdForFileName:bool=True)->dict:
    """
    Extract the settings from your element. For your custom code, it will extract the javaScript. 
    Arguments: 
        element : REQUIRED : element from which you would like to extract the setting from (dictionary or path to JSON file)
        analyticsCode : OPTIONAL : if set to True (default), extract the Analytics code when there is one and not global setting.
        save : OPTIONAL : bool, if you want to save the setting in a JS or JSON file, set it to true. (default False)
        encoding : OPTIONAL : encoding to be used for saving the file.
        useIdForFileName : OPTIONAL : use the ID of the Component as the fileName.
            if set to False, use the name of the component to save the file.
    """
    if type(element) == str:
        with open(Path(element)) as f:
            element = json.load(f)
    element_type = element['type']
    if element_type == 'data_elements':
        if element['attributes']['delegate_descriptor_id'] == 'core::dataElements::custom-code':
            settings = element['attributes']['settings']
            code = json.loads(settings)['source']
            if save is True:
                if useIdForFileName:
                    name = f"DE - {element['id']}.js"
                else:
                    name = f'DE - {str(element["attributes"]["name"])}.js'
                    name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                        '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                saveFile(code,name,type='js',encoding=encoding)
            return code
        else:
            settings = element['attributes']['settings']
            if save:
                if useIdForFileName:
                    name = f"DE - {element['id']}.js"
                else:
                    name = f'DE - {str(element["attributes"]["name"])} - settings.json'
                    name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                        '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                saveFile(settings,name,type='json',encoding=encoding)
            return settings
    elif element_type == 'extensions':
        if element['attributes']['delegate_descriptor_id'] == "adobe-analytics::extensionConfiguration::config":
            settings = json.loads(element['attributes']['settings'])
            if save is True:
                if useIdForFileName:
                    name = f"EXT - {element['id']}.js"
                else:
                    name = f'EXT - {str(element["attributes"]["name"])}.json'
                    name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                        '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                saveFile(settings,name,type='json',encoding=encoding)
            return settings
        else:
            settings = element['attributes']['settings']
            if save:
                if useIdForFileName:
                    name = f"EXT - {element['id']}.js"
                else:
                    name = f'EXT - {str(element["attributes"]["name"])} - settings.json'
                    name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                        '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                saveFile(settings,name,type='json',encoding=encoding)
            return settings
    elif element_type == 'rule_components':
        rule_name = element.get('rule_name','Rule Name Unknown')
        element_place = element['attributes']['delegate_descriptor_id'].split('::')[
            1]
        if element['attributes']['delegate_descriptor_id'] == "core::conditions::custom-code":
            settings = element['attributes']['settings']
            code = json.loads(settings)['source']
            if save is True:
                if useIdForFileName:
                    name = f"RC - {rule_name} - {element['id']}.js"
                else:
                    name = f'RC - {rule_name} - {element_place} - {element["attributes"]["name"]}.js'
                    name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                        '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                saveFile(code,name,type='js',encoding=encoding)
            return code
        elif element['attributes']['delegate_descriptor_id'] == "core::events::custom-code":
            settings = element['attributes']['settings']
            code = json.loads(settings)['source']
            if save is True:
                if useIdForFileName:
                    name = f"RC - {rule_name} - {element['id']}.js"
                else:
                    name = f'RC - {rule_name} - {element_place} - {element["attributes"]["name"]}.js'
                    name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                saveFile(code,name,type='js',encoding=encoding)
            return code
        elif element['attributes']['delegate_descriptor_id'] == "core::actions::custom-code":
            settings = element['attributes']['settings']
            code = json.loads(settings)['source']
            if save is True:
                if useIdForFileName:
                    name = f"RC - {rule_name} - {element['id']}.js"
                else:
                    name = f'RC - {rule_name} - {element_place} - {element["attributes"]["name"]}.js'
                    name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                saveFile(code,name,type='js',encoding=encoding)
            return code
        else:
            settings = element['attributes']['settings']
            if 'customSetup' in json.loads(settings).keys() and analyticsCode:
                if 'source' in json.loads(settings)['customSetup']:
                    code = json.loads(settings)['customSetup'].get('source','')
                    if save:
                        if useIdForFileName:
                            name = f"RC - {rule_name} - {element['id']}.js"
                        else:
                            name = f'RC - {rule_name} - {element_place} - {element["attributes"]["name"]} - code settings.js'
                            name = name.replace('"', "'").replace('|', '').replace('>', '').replace('<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                        saveFile(code,name,type='js',encoding=encoding)
                    return code

            if save:
                if useIdForFileName:
                    name = f"RC - {rule_name} - {element['id']}.json"
                else:
                    name = f'RC - {rule_name} - {element_place} - {element["attributes"]["name"]} - settings.json'
                    name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                saveFile(settings,name,type='json',encoding=encoding)
            return settings

def findRuleComponentSettingsFileName(rc:dict=None)->str:
    """
    Return the filename used to save your custom code of your ruleComponent in a file using the extractSettings method.
    Returns None when this is not a Custom code from CORE or Adobe Analytics.
    Argument:
        rc : REQUIRED : rule component object you want to retrieve the filename for.
    """
    element_type = rc['type']
    if element_type != 'rule_components':
        raise TypeError('Require a rule component element')
    elif element_type == 'rule_components':
        rule_name = rc['rule_name']
        element_place = rc['attributes']['delegate_descriptor_id'].split('::')[
            1]
        if rc['attributes']['delegate_descriptor_id'] == "core::conditions::custom-code":
            name = f'RC - {rule_name} - {element_place} - {rc["attributes"]["name"]}.js'
            name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
            return name
        elif rc['attributes']['delegate_descriptor_id'] == "core::events::custom-code":
            name = f'RC - {rule_name} - {element_place} - {rc["attributes"]["name"]}.js'
            name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
            return name
        elif rc['attributes']['delegate_descriptor_id'] == "core::actions::custom-code":
            name = f'RC - {rule_name} - {element_place} - {rc["attributes"]["name"]}.js'
            name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
            return name
        else:
            settings = rc['attributes']['settings']
            if 'customSetup' in json.loads(settings).keys() and "adobe-analytics::" in rc['attributes']['delegate_descriptor_id']:
                if 'source' in json.loads(settings)['customSetup']:
                    name = f'RC - {rule_name} - {element_place} - {rc["attributes"]["name"]} - code settings.js'
                    name = name.replace('"', "'").replace('|', '').replace('>', '').replace('<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                    return name
            else:
                return None
    else:
        return None


def extractAttributes(element: Union[dict,IO], save: bool = False,encoding:str='utf-8')->dict:
    """
    Extract the attributes of your element. You can save it in a file as well. 
    Arguments:
        element : REQUIRED : either dictionary representing the element you want to extract attribute from or JSON file path.
        save : OPTIONAL : do you want to save it in a JSON file.
        encoding : OPTIONAL : encoding to be used for saving the file.
    """
    if type(element) == str:
        with open(Path(element)) as f:
            element = json.load(f)
    attributes = element['attributes']
    el_name = element['attributes']['name']
    element_type = element['type']
    if save:
        name = f'{element_type} - {el_name} - attributes.json'
        name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
            '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
        saveFile(attributes,name,type='json',encoding=encoding)
    return attributes


def duplicateAttributes(base_elements: list = None, target_elements: list = None, **kwargs)->list:
    """
    Take a list of element and copy their settings (default) to another list of element.
    returns a new list of the elements attributes. 
    Arguments:
        base_elements : REQUIRED : list of elements you want to copy
        target_elements : REQUIRED : list of elements you want to change

    Possible kwargs : 
        key : OPTIONAL : the type of element you want to copy paste (settings, name,enabled ,etc...)
        default value for the key is "settings".
        name_filter : OPTIONAL : Filter the elements to copy to only the ones containing the string in the filter.
        example : name_filter='analytics' will only copy the element that has analytics in their name
    """
    if base_elements == None or target_elements == None:
        raise AttributeError(
            'expecting base_element and target elements to be filled')
    if type(base_elements) != list or type(target_elements) != list:
        raise AttributeError(
            'expecting base_element and target elements to be list')
    key = kwargs.get('key', 'settings')
    if kwargs.get('name_filter') != None:
        base_elements = [element for element in base_elements if element['attributes']['name'].find(
            kwargs.get('name_filter'))]
    index = {ext['attributes']['name']: i for i,
             ext in enumerate(target_elements)}
    new_list = []
    for element in base_elements:
        check_name = element['attributes']['name']
        if check_name in index.keys():
            base_setting = element['attributes'][key]
            copy_target = deepcopy(target_elements[index[check_name]])
            copy_target_attr = copy_target['attributes']
            copy_target_attr[key] = base_setting
            new_list.append(copy_target_attr)
    return new_list


def copySettings(data: dict=None)->object:
    """
    copy the settings from an element and returns an object with required information
    Returns an object with the information required to create copy this element.  
    Arguments:
        data : REQUIRED : Single Element Object that you want to copy (not a list of elements)
    """
    if data is None:
        raise ValueError("require an object")
    if type(data) != dict:
        raise TypeError("require a dictionary")
    obj = {}
    if data['type'] == 'extensions':
        obj['name'] = data['attributes']['name']
        obj['settings'] = data['attributes']['settings']
        obj['descriptor'] = data['attributes']['delegate_descriptor_id']
        obj['extension_id'] = data['relationships']['extension_package']['data']['id']
    elif data['type'] == 'data_elements':
        obj['name'] = data['attributes']['name']
        obj['settings'] = data['attributes']['settings']
        obj['descriptor'] = data['attributes']['delegate_descriptor_id']
        obj['storage_duration'] = data['attributes']['storage_duration']
        obj['force_lower_case'] = data['attributes']['force_lower_case']
        obj['default_value'] = data['attributes']['default_value']
        obj['clean_text'] = data['attributes']['clean_text']
        obj['extension'] = data['relationships']['extension']['data']
        obj['enabled'] = data['attributes']['enabled']
    elif data['type'] == 'rules':
        obj['name'] = data['attributes']['name']
        obj['enabled'] = data['attributes']['enabled']
    elif data['type'] == 'rule_components':
        obj['name'] = data['attributes']['name']
        obj['order'] = data['attributes']['order']
        obj['descriptor'] = data['attributes']['delegate_descriptor_id']
        obj['negate'] = data['attributes']['negate']
        obj['delay_next'] = data['attributes']['delay_next']
        obj['timeout'] = data['attributes']['timeout']
        obj['rule_order'] = data['attributes']['rule_order']
        obj['settings'] = data['attributes']['settings']
        obj['extension'] = data['relationships']['extension']['data']
        obj['rule_name'] = data['rule_name']
        obj['rule_id'] = data['rule_id']
        obj['rule_setting'] = {
            'data': [{
                'id': data['rule_id'],
                'type':'rules'}
            ]}
    return obj


class Translator:
    """
    A class to store the translator dataframe for extensions ids. 
    It has multiple methods, you should set the Extensions and the Rules. 
    1. setBaseExtensions
    2. extendExtensions
    --> You can use the translate method to translate Data Element settings 
    3. setBaseRules
    4. extendRules
    --> You can use the translate method to translate Rule Components settings 
    """

    def __init__(self):
        self.rules = {}
        self.baseRuleIdName = {}
        self.extensions = {}
        self.baseExtensionIdName = {}

    def setBaseExtensions(self, base_property_extensions: list, property_name: str):
        """
        Pass all the extensions from the base property to start building the table. 
        Arguments: 
            base_property_extensions : REQUIRED : list of all extensions retrieve through getExtensions method
            property_name : REQUIRED : name of your base property.
        """
        self.baseExtensionIdName = {ext['id'] : ext['attributes']['name'] for ext in base_property_extensions}
        self.extensions = {ext['attributes']['name']:{property_name:ext['id']} for ext in base_property_extensions}

    def extendExtensions(self, new_property_extensions: list, new_prop_name: str)-> None:
        """
        Add the extensions id from a target property.
        Arguments: 
            new_property_extensions: REQUIRED : the extension list from your target property. 
            new_prop_name : REQUIRED : target property name. 
        """
        for ext in new_property_extensions:
            if ext['attributes']['name'] in list(self.extensions.keys()):
                self.extensions[ext['attributes']['name']][new_prop_name] = ext['id']
        return self.extensions

    def setBaseRules(self, base_property_rules: list, property_name: str):
        """
        Pass all the rules from the base property to start building the table. 
        Arguments: 
            base_property : REQUIRED : list of all rules retrieve through getExtensions method
            property_name : REQUIRED : name of your base property.
        """
        self.baseRuleIdName = {rule['id']:rule['attributes']['name'] for rule in base_property_rules}
        self.rules = {rule['attributes']['name']:{property_name:rule['id']} for rule in base_property_rules}
    
    def extendBaseRules(self,ruleName:str=None,ruleId:str=None,property_name: str=None)->None:
        """
        Add a new rule name in the translator mapping table.
        In case you have created the rule after instantiation of the Translator.
        Arguments:
            ruleName : REQUIRED : the name of the rule to create
            ruleId : REQUIRED : The ID of the rule to create
            property_name : REQUIRED : The base property used.
        """
        if ruleName is None:
            raise ValueError("Require a rule name to be loaded")
        if property_name is None:
            raise ValueError("Require the main property name")
        self.baseRuleIdName[ruleId] = ruleName
        self.rules[ruleName] = {property_name : ruleId}
        

    def extendRules(self, new_property_rules: list, new_prop_name: str):
        """
        Add the extensions id from a target property.
        Arguments: 
            new_property_rules: REQUIRED : the rules list from your target property. 
            new_prop_name : REQUIRED : target property name. 
        """
        for rule in new_property_rules:
            if rule['attributes']['name'] in list(self.rules.keys()):
                self.rules[rule['attributes']['name']][new_prop_name] = rule['id']
        return self.rules
    
    def extendTargetRules(self,ruleName:str=None,ruleId:str=None,property_name: str=None)->None:
        """
        Add a new rule name in the translator mapping table for the target property.
        In case you have created the rule after instantiation of the Translator.
        If the rule name is not present in the base property, the update will not happen.
        Arguments:
            ruleName : REQUIRED : the name of the rule to create
            ruleId : REQUIRED : The ID of the rule to create
            property_name : REQUIRED : The base property used.
        """
        if ruleName is None:
            raise ValueError("Require a rule name to be loaded")
        if property_name is None:
            raise ValueError("Require the main property name")
        self.rules[ruleName][property_name] = ruleId

    def translate(self, target_property: str, data_element: dict = None, rule_component: dict = None)->dict:
        """
        change the id from the base element to the new property. 
        Pre checked should be done beforehands (updating Extension & Rules elements)
        Arguments: 
            target_property : REQUIRED : property that is targeted to translate the element to
            data_element : OPTIONAL : if the elements passed are data elements
            rule_component : OPTIONAL : if the elements passed are rule components
        """
        if len(self.extensions) == 0:
            raise AttributeError(
                "You didn't import the base extensions or the target extensions")
        if data_element is not None:
            new_de = deepcopy(data_element)
            base_id = new_de['extension']['id']
            based_ext_name = self.baseExtensionIdName[base_id]
            new_extension_id = self.extensions[based_ext_name][target_property]
            new_de['extension']['id'] = new_extension_id
            return new_de
        elif rule_component is not None:
            if len(self.rules) == 0:
                raise AttributeError(
                    "The rules have not been imported, the rule id needs to be changed")
            new_rc = deepcopy(rule_component)
            base_id = new_rc['extension']['id']
            based_ext_name = self.baseExtensionIdName[base_id]
            new_extension_id = self.extensions[based_ext_name][target_property]
            new_rc['extension']['id'] = new_extension_id
            if len(self.rules) > 0:
                new_rc['rule_setting'] = {
                    'data': [{
                        'id': self.rules[rule_component['rule_name']][target_property],
                        'type':'rules'}
                    ]}
                new_rc['rule_id'] = self.rules[rule_component['rule_name']][target_property]
            else:
                print(
                    "You didn't load the rules. Please use setExtensions and setRules, and extendExtensions and extendRules")
                del new_rc['rules']
            return new_rc


def extractAnalyticsCustomCode(rcSettings: str, save: bool = False, filename: str = None,encoding:str='utf-8')->None:
    """
    Extract the custom code of the rule and save it in a file.
    Arguments:
        rcSettings: REQUIRED : it is the analytics rule component settings retrieved by the extractSettings method. 
        save : OPTIONAL : if you want to save the code as external js file. UTF-16. Default False. 
        filename : OPTIONAL : name of the file you want to use to save the code. 
        encoding : OPTIONAL : encoding to be used for saving the file.
    """
    if rcSettings is None:
        raise ValueError("Require settings to be passed from the Data Element")
    json_data = json.loads(rcSettings)
    if 'customSetup' in json_data.keys():
        json_code = json_data['customSetup']['source']
        if filename is None:
            filename = 'code'
        filename = filename.replace('/', '_').replace('|', '_')
        if save:
            saveFile(json_code,filename,type='js',encoding=encoding)
        return json_code
