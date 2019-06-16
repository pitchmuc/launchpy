# -*- coding: utf-8 -*-
"""
May  15 12:04:49 2019
@author: Julien Piccini
"""
import time as _time
import json as _json
from collections import defaultdict as _defaultdict
from concurrent import futures as _futures
## Non standard libraries
import pandas as _pd
import requests as _requests
import jwt as _jwt
from pathlib import Path


### Set up default values
_org_id, _api_key, _tech_id, _pathToKey, _secret = "","","","","",
_TokenEndpoint = "https://ims-na1.adobelogin.com/ims/exchange/jwt"
_orga_admin ={'_org_admin','_deployment_admin','_support_admin'}
_cwd = Path.as_posix(Path.cwd())
_date_limit = 0
_token = ''
_header = {}

def createConfigFile(verbose : object = False)->None:
    """
    This function will create a 'config_admin.json' file where you can store your access data. 
    """
    json_data = {
        'org_id': '<orgID>',
        'api_key': "<APIkey>",
        'tech_id': "<something>@techacct.adobe.com",
        'secret': "<YourSecret>",
        'pathToKey': '<path/to/your/privatekey.key>',
    }
    with open('config_admin.json', 'w') as cf:
        cf.write(_json.dumps(json_data, indent=4))
    if verbose:
        print(' file created at this location : '+_cwd + '/config_admin.json')


def importConfigFile(file : str)-> None:
    """
    This function will read the 'config_admin.json' to retrieve the information to be used by this module. 
    """
    global _org_id
    global _api_key
    global _tech_id
    global _pathToKey
    global _secret
    global _endpoint
    with open(file, 'r') as file:
        f = _json.load(file)
        _org_id = f['org_id']
        _api_key = f['api_key']
        _tech_id = f['tech_id']
        _secret = f['secret']
        _pathToKey = f['pathToKey']

#### Launch API Endpoint
_endpoint = 'https://reactor.adobe.io/'

    
def retrieveToken(verbose: bool = False)->str:
    """ Retrieve the token by using the information provided by the user during the import importConfigFile function. 
    
    Argument : 
        verbose : OPTIONAL : Default False. If set to True, print information.
    """
    global _token
    with open(_pathToKey, 'r') as f:
        private_key_unencrypted = f.read()
        header_jwt = {'cache-control':'no-cache','content-type':'application/x-www-form-urlencoded'}
    jwtPayload = {
        "exp": round(24*60*60+ int(_time.time())),###Expiration set to 24 hours
        "iss": _org_id, ###org_id
        "sub": _tech_id,###technical_account_id
        "https://ims-na1.adobelogin.com/s/ent_reactor_admin_sdk":True,
        "aud": "https://ims-na1.adobelogin.com/c/"+_api_key
    }
    encoded_jwt = _jwt.encode(jwtPayload, private_key_unencrypted , algorithm='RS256')##working algorithm
    payload = {
            "client_id":_api_key,
            "client_secret":_secret,
            "jwt_token" : encoded_jwt.decode("utf-8")
            }
    response = _requests.post(_TokenEndpoint, headers=header_jwt, data=payload)
    json_response = response.json()
    token = json_response['access_token']
    _updateHeader(token)
    expire = json_response['expires_in']
    global _date_limit ## getting the scope right
    _date_limit= _time.time()+ expire/1000 -500 ## end of time for the token
    with open('token.txt','w') as f: ##save the token
        f.write(token)
    if verbose == True:
        print('token valid till : ' + _time.ctime(_time.time()+ expire/1000))
        print('token has been saved here : ' + Path.as_posix(Path.cwd()))
    return token

def _checkToken(func):
    """    decorator that checks that the token is valid before calling the API    """
    def checking(*args,**kwargs):## if function is not wrapped, will fire
        global _date_limit
        now = _time.time()
        if now > _date_limit - 1000:
            global _token
            _token = retrieveToken(*args,**kwargs)
            return func(*args,**kwargs)
        else:## need to return the function for decorator to return something
            return func(*args,**kwargs)
    return checking ## return the function as object

### 
def _updateHeader(token:str)->None:
    """ update the header when new token is generated"""
    global _header
    global _api_key
    global _org_id
    global _token
    _token = token
    _header = {"Accept": "application/vnd.api+json;revision=1",
           "Content-Type": "application/vnd.api+json",
           "Authorization": "Bearer "+token,
           "X-Api-Key": _api_key,
           "X-Gw-Ims-Org-Id": _org_id
           }


### Endpoint
_getCompanies ='/companies'
_getProfile = '/profile'
_getProperties = '/companies/{_company_id}/properties'## string format

#profile_response = _requests.get(_endpoint+getProfile,headers=header)
#json_profile = profile_response.json()
#
#
@_checkToken
def getCompanyId()->object:
    companies = _requests.get(_endpoint+_getCompanies,headers=_header)
    companyID = companies.json()['data'][0]['id']
    return companyID

@_checkToken
def getProperties(companyID:str)->object:
    """
    Retrieve the different properties available for a specific company.
    Parameter :
        companyID : REQUIRED : Company from where you want the properties
    """
    req_properties = _requests.get(_endpoint+_getProperties.format(_company_id=companyID),headers=_header)
    properties = req_properties.json()
    data = properties['data'] ## will fetch the list of properties, not using the "meta" key
    return data


class Property: 
    
    header = {"Accept": "application/vnd.api+json;revision=1",
           "Content-Type": "application/vnd.api+json",
           "Authorization": "Bearer "+_token,
           "X-Api-Key": _api_key,
           "X-Gw-Ims-Org-Id": _org_id
           }
    
    def __init__(self,data:object) -> None:
        """
        Data object that is pass on is coming from the property return by getProperties.
        Attributes : 
          dict : the data that has been passed to the class for the instance creation
          name : name of the property 
          id : id of the property 
          platform : platform of the property 
          development : boolean, if the property is a dev environment or not. 
          domains : domain(s) associated with the property
          libraries : the different libraries associated with the property (rules, data elements, etc...)
          rules : dictionnary to extract ruleComponents from rules. Filled when running getRules
        """
        self.dict = data
        self.name = data['attributes']['name']
        self.id = data['id']
        self.platform = data['attributes']['platform']
        self.development = data['attributes']['development']
        self.domains = data['attributes']['domains']
        self._DataElement = data['links']['data_elements']
        self._Extensions = data['links']['extensions']
        self._Rules = data['links']['rules']
        self._RuleComponents = 'https://reactor.adobe.io/properties/'+data['id']+'/rule_components'
        self._Environments = data['links']['environments']
        self.libraries = data['relationships']['libraries']['links']['related']
        self.ruleComponents = {}
        
    def __repr__(self)-> dict:
        return self.dict
    
    def __str__(self)-> str:
        return str(_json.dumps(self.dict,indent=4))
    
    def importRuleComponents(self,rules:list)->dict:
        """
        Takes the list of rules and create a dictionary to assign each rule to a name 
        """
    
    @_checkToken
    def getExtensions(self)-> object:
        """
        retrieve the different information from url retrieve in the properties
        """
        extensions = _requests.get(self._Extensions,headers=_header)
        data = extensions.json()['data'] ## skip meta for now
        return data
    
    @_checkToken
    def getRules(self)->object:
        """
        Return the list of the rules data.
        On top, it fills the ruleComponents attribute with a dictionnary based on rule id and their rule name and the ruleComponent of each.
        """
        rules = _requests.get(self._Rules,headers=_header)
        data = rules.json()['data'] ## skip meta for now
        for rule in data:
            self.ruleComponents[rule['id']] = {
            'name' : rule['attributes']['name'],
            'url' : rule['links']['rule_components']
            }
        return data
    
    @_checkToken
    def getRuleComponents(self)->dict:
        ruleComponents = self.ruleComponents
        list_urls = [ruleComponents[_id]['url'] for _id in ruleComponents]
        names = [ruleComponents[_id]['name'] for _id in ruleComponents]
        headers = [_header  for nb in range(len(list_urls))]
        workers = min((len(list_urls),5))
        def request_data(url, header,name):
            rule_component = _requests.get(url,headers=_header)
            data = rule_component.json()['data']
            for element in data:
                element['rule_name'] = name
            return data
        with _futures.ThreadPoolExecutor(workers) as executor:
            res = executor.map(request_data,list_urls,headers,names)
        list_data = list(res)
        expanded_list = []
        for element in list_data: 
            if type(element) is list:
                for sub_element in element:
                    expanded_list.append(sub_element)
            else:
                expanded_list.append(element)
        return expanded_list
    
    @_checkToken
    def getDataElements(self)->object:
        dataElements = _requests.get(self._DataElement,headers=_header)
        data = dataElements.json()['data'] ## skip meta for now
        return data 
    
    @_checkToken
    def getEnvironment(self)->object:
        env = _requests.get(self._Environments,headers=_header)
        data = env.json()['data'] ## skip meta for now
        return data 
    
    @_checkToken
    def createExtensions(self,extension_id:str,**kwargs)-> object:
        """
        retrieve the different information from url retrieve in the properties
        argument : 
            - extension_id : REQUIRED : ID for the extension to be created
        """
        obj={
              "data": {
                "attributes": {
                },
                "relationships": {
                  "extension_package": {
                    "data": {
                      "id": extension_id,
                      "type": "extension_packages"
                    }
                  }
                },
                "type": "extensions"
              }
            }
        if kwargs.get('settings') is not None:
            obj['data']['attributes']['settings'] = str(kwargs.get('settings')['settings'])
            obj['data']['attributes']['delegate_descriptor_id'] = kwargs.get('settings')['delegate_descriptor_id']
        extensions = _requests.post(self._Extensions,headers=_header,data=_json.dumps(obj))
        data = extensions.json() ## skip meta for now
        return data
    
    @_checkToken
    def createRules(self,name:str)->object:
        """
        Create a rule by provided a rule name
        """
        
        obj = {
          "data": {
            "attributes": {
              "name": name
            },
            "type": "rules"
          }
        }
        rules = _requests.post(self._Rules,headers=_header,data=_json.dumps(obj))
        data = rules.json()['data'] ## skip meta for now
        self.ruleComponents[data['id']]= {'name' :data['attributes']['name'],
                           'url': data['links']['rule_components']}
        return data
    
    def createRuleComponents(self,name:str,descriptor:str,settings:str=None,extension_id:dict=None,rule_id:dict=None,**kwargs)->object:
        """
        Create a ruleComponent by provided a rule name and descriptor (minimum). It returns an object.
        It can takes additional information in order to link the ruleCompoment to a rule and with an Extension
        Arguments : 
            name : REQUIRED : name of the rule component
            descriptor : REQUIRED : delegate_descriptor_id for the rule component
            extension_id : REQUIRED : Extension used for that rule component (dictionary)
            rule_id : REQUIRED : rule information link to that rule component (dictionary)
            settings : OPTIONAL : settings for that rule component
        """
        
        obj = {
          "data": {
            "attributes": {
              "name": name,
              "delegate_descriptor_id":descriptor
            },
            "relationships":{
                "extension":{
                    "data" : extension_id
                        },
                "rules":rule_id
                    },
            "type": "rule_components"
          }
        }
        if settings is not None: 
            obj['data']['attributes']['settings'] = settings
        if 'order' in kwargs:
            obj['data']['attributes']['order'] = kwargs.get('order')
        rc = _requests.post(self._RuleComponents,headers=_header,data=_json.dumps(obj))
        data = rc.json()
        return data
            
        
    
    @_checkToken
    def createDataElements(self,name:str,descriptor:str,settings:str,extension:dict,**kwargs:dict)->object:
        """
        Create Data Elements following the usage of required arguments. 
        Arguments : 
            name : REQUIRED : name of the data element
            descriptor : REQUIRED : delegate_descriptor_id for the data element
            extension : REQUIRED : extension id used for the data element. (dictionary)
            settings : OPTIONAL : settings for the data element
        """
        obj = {
          "data": {
            "attributes": {
              "name": name,
              "delegate_descriptor_id" : descriptor,
            },
            "relationships":{
                "extension":{
                    "data":extension
                        }
                    },
            
            "type": "data_elements"
          }
        }
        try:
            if kwargs.get['settings'] is not None:
                obj['data']['attributes']['settings'] = kwargs.get['settings']
        except:
            pass
        dataElements = _requests.post(self._DataElement,headers=_header,data=_json.dumps(obj))
        data = dataElements.json()
        return data 
    
    @_checkToken
    def createEnvironment(self,name:str)->object:
        rules = _requests.post(self._Environments,headers=_header)
        data = rules.json()
        return data 
    
    @_checkToken
    def updateExtensions(self,extension_id,extension_dict:dict)-> object:
        """
        update the extension with the information provided in the argument.
        argument: 
            extension_dict : REQUIRED : object that will be passed to Launch for update
        
        """
        obj=extension_dict
        extensions = _requests.patch(self._Extensions,headers=_header,data=_json.dumps(obj))
        data = extensions.json()['data']
        return data
    
    @_checkToken
    def updateRules(self,data:object)->object:
        """
        Update the rule 
        """
        obj = data
        rules = _requests.patch(self._Rules,headers=_header,data=_json.dumps(obj))
        data = rules.json()['data']
        return data
    
    @_checkToken
    def updateRuleComponents(self,data:object)->object:
        """
        Update the ruleComponents based on the information provided
        """
        obj = data
        rules = _requests.patch(self.something,headers=_header,data=_json.dumps(obj))
        data = rules.json()['data']
        return data
    
    
    @_checkToken
    def updateDataElements(self)->object:
        dataElements = _requests.patch(self._DataElement,headers=_header)
        data = dataElements.json()['data']
        return data 
    
    @_checkToken
    def updateEnvironment(self)->object:
        rules = _requests.patch(self._Environments,headers=_header)
        data = rules.json()['data']
        return data 
    


def extensionsInfo(data:list)->dict:
    """
    Return a dictionary from the list provided from the extensions request.
    Arguments : 
        - data : REQUIRED : list information returned by the getExtension method. 
    """
    extensions = {}
    for extension in data:
        extensions[extension['attributes']['name']] = {
                'published':extension['attributes']['published'],
                'dirty':extension['attributes']['dirty'],
                'review_status':extension['attributes']['review_status'],
                'revision_number':extension['attributes']['revision_number'],
                'version':extension['attributes']['version'],
                'settings':extension['attributes']['settings'],
                'updated_at': extension['attributes']['updated_at'],
                'id':extension['id'],
                'extension_id':extension['relationships']['extension_package']['data']['id']               
                       }
        if 'deleted_at' in extension['meta'].keys():
            extensions[extension['attributes']['name']]['deteled'] = True
        else:
            extensions[extension['attributes']['name']]['deteled'] = False
    return extensions
            
def rulesInfo(data:list)-> dict:
    """
    Return a dictionary from the list provided from the rules request.
    Arguments : 
        - data : REQUIRED : list information returned by the getRules method. 
    """
    rules = _defaultdict(None)
    for rule in data:
        rules[rule['attributes']['name']] = {
                'published':rule['attributes']['published'],
                'dirty':rule['attributes']['dirty'],
                'review_status':rule['attributes']['review_status'],
                'revision_number':rule['attributes']['revision_number'],
                'updated_at': rule['attributes']['updated_at'],
                'id':rule['id'],
                'latest_revision_number':rule['meta']['latest_revision_number'],
                'rule_components':rule['links'].get('rule_components')
                       }
    return rules

def ruleComponentInfo(data:list)->dict:
    """
    Return a dictionary from the list provided from the rules component request.
    Arguments : 
        - data : REQUIRED : list information returned by the getRuleComponent method. 
    """
    components={}
    for component in data:
        components[component['attributes']['name']] = {
                'id': component['id'],
                'updated_at': component['attributes']['updated_at'],
                'delegate_descriptor_id' : component['attributes']['delegate_descriptor_id'],
                'name' : component['attributes']['name'],
                'dirty':component['attributes']['dirty'],
                'order' : component['attributes']['order'],
                'rule_order' : component['attributes']['rule_order'],
                'published': component['attributes']['published'],
                'revision_number' : component['attributes']['revision_number'],
                'settings':component['attributes']['settings']
                }

def dataElementInfos(data:list)->dict:
    """
    return information about data elements as dictionary.
    arguments : 
        - data : list return by the getDataElement value
    """
    elements = _defaultdict(None)
    for element in data:
        elements[element['attributes']['name']] = {
                'id' : element['id'],
                'updated_at' : element['attributes']['updated_at'],
                'dirty' : element['attributes']['dirty'],
                'enabled' : element['attributes']['enabled'],
                'name' : element['attributes']['name'],
                'published' : element['attributes']['published'],
                'revision_number' : element['attributes']['revision_number'],
                'delegate_descriptor_id' : element['attributes']['delegate_descriptor_id'],
                'default_value' : element['attributes']['default_value'],
                'force_lower_case' : element['attributes']['force_lower_case'],
                'storage_duration' : element['attributes']['storage_duration'],
                'settings' : element['attributes']['settings']
                }

def _defineSearchType(_name:str=None,_id:str=None)->tuple:
    if _name is not None:
        condition='name'
        value = _name
    elif _id is not None: 
        condition = 'id'
        value = _id
    else:
        raise SyntaxError('The ruleName or ruleId should be provided') 
    return condition, value

def copySettings(data:object)->object:
    """
    copy the settings from an element and returns an object with required information
    """
    obj={}
    if data['type'] == 'extensions':
        obj['settings'] = data['attributes']['settings']
        obj['delegate_descriptor_id'] = data['attributes']['delegate_descriptor_id']
    elif data['type'] == 'data_elements':
        obj['name'] = data['attributes']['name']
        obj['settings'] = data['attributes']['settings']
        obj['delegate_descriptor_id'] = data['attributes']['delegate_descriptor_id']
        obj['storage_duration']=  data['attributes']['storage_duration']
        obj['force_lower_case']=  data['attributes']['force_lower_case']
        obj['default_value']=  data['attributes']['default_value']
        obj['clean_text']=  data['attributes']['clean_text']
        obj['extension']=data['relationships']['extension']['data']
    elif data['type'] == 'rules':
        obj['name'] = data['attributes']['name']
    elif data['type'] == 'rule_components':
        obj['name'] = data['attributes']['name']
        obj['order'] = data['attributes']['order']
        obj['delegate_descriptor_id'] = data['attributes']['delegate_descriptor_id']
        obj['negate'] = data['attributes']['negate']
        obj['rule_order'] = data['attributes']['rule_order']
        obj['settings'] = data['attributes']['settings']
        obj['extension'] = data['relationships']['extension']['data']
        obj['rule_name'] = data['rule_name']
    return obj


class Translator:
    """
    A class to store the translator dataframe for extensions ids. 
    
    It will return dataframe
    """
    
    def __init__(self):
        pass
    
    def setBaseExtensions(self,base_property_extensions:object,property_name:str):
        """
        Pass all the extensions from the base property to start building the table. 
        arguments : 
            - base_property : REQUIRED : list of all extensions retrieve through getExtensions method
            - property_name : REQUIRED : name of your base property.
        """
        df = _pd.DataFrame(extensionsInfo(base_property_extensions)).T
        df = _pd.DataFrame(df['id'])
        df.columns = [property_name]
        self.extensions = df
    
    def extendExtensions(self,new_property_extensions:object,new_prop_name:str):
        df = _pd.DataFrame(extensionsInfo(new_property_extensions)).T
        df = _pd.DataFrame(df['id'])
        self.extensions[new_prop_name] = df
        return self.extensions
    
    def translate(self,target_property:str,data_element:dict=None, rule_component:dict=None):
        """
        change the id from the base element to the new property. 
        Pre checked should be done beforehands (updating Extension & Rules elements)
        """
        if data_element is not None:
            new_de = data_element
            base_id = new_de['extension']['id']
            row = self.extensions[self.extensions.iloc[:,0] == base_id].index.values[0]
            new_value = self.extensions.loc[row,target_property]
            data_element['extension']['id'] = new_value
            return new_de
        elif rule_component is not None:
            new_rc = rule_component
            base_id = new_rc['extension']['id']
            row = self.extensions[self.extensions.eq(base_id).any(1)].index.values[0]
            new_value = self.extensions.loc[row,target_property]
            new_rc['extension']['id'] = new_value
            new_rc['rules'] = { 
                    'data' : [{
                    'id' : self.rules.loc[rule_component['rule_name'],target_property],
                    'type':'rules'}
            ]}
            return new_rc
    
    def setBaseRules(self,base_property_rules:object,property_name:str):
        """
        Pass all the extensions from the base property to start building the table. 
        arguments : 
            - base_property : REQUIRED : list of all rules retrieve through getExtensions method
            - property_name : REQUIRED : name of your base property.
        """
        df = _pd.DataFrame(rulesInfo(base_property_rules)).T
        df = _pd.DataFrame(df['id'])
        df.columns = [property_name]
        self.rules = df

    def extendRules(self,new_property_rules:object,new_prop_name:str):
        df = _pd.DataFrame(rulesInfo(new_property_rules)).T
        df = _pd.DataFrame(df['id'])
        self.rules[new_prop_name] = df
        return self.rules

    
    
@_checkToken    
def createProperty(companyId:str,name:str,platform:str='web',**kwargs):
    """
    Create a property with default information. Will return empty value as default value. 
    Returns the response.
    Arguments : 
        - companyId : REQUIRED : id of the company
        - name : REQUIRED : name of the property
        - platform : REQUIRED : default 'web', can be 'app'
        **kwargs : can use the different parameter reference here : https://developer.adobelaunch.com/api/reference/1.0/properties/create/
        
    """
    obj = {}
    obj['data']={}
    obj['data']['attributes']={}
    ### in case some optional value are filled in
    undefined_vars_return_empty = kwargs.get('undefined_vars_return_empty',True)
    development = kwargs.get('development',False)
    domains = kwargs.get('domains',['example.com'])
    if type(domains) == str:## change the domains to list as required
        if ',' in domains : 
           domains = domains.split(',') 
        else:
            domains = list(domains)
    obj['data']['attributes']['name'] = name
    obj['data']['attributes']['domains']=domains
    obj['data']['attributes']['platform']=platform
    obj['data']['attributes']['development']=development
    obj['data']['attributes']['undefined_vars_return_empty']=undefined_vars_return_empty
    obj['data']['type']='properties'
    print(_json.dumps(obj))
    new_property = _requests.post(_endpoint+_getProperties.format(_company_id=companyId),headers=_header,data=_json.dumps(obj))
    return new_property.json()

    
### https://reactor.adobe.io/rules/RL2a1ddbebffbd47d9973d395e77eb98e9/rule_components        
