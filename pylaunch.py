# -*- coding: utf-8 -*-
"""
May  15 12:04:49 2019
@author: Julien Piccini
"""
import time as _time
import json as _json
from collections import defaultdict as _defaultdict
from concurrent import futures as _futures
from copy import deepcopy as _deepcopy
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

    
def retrieveToken(verbose: bool = False,save:bool=False)->str:
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
    if save:
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


@_checkToken
def _getData(url:str,*args:str)->object:
    try:## try to set pagination if exists
        url = url + args[0]
    except:
        url = url
    res = _requests.get(url,headers=_header)
    return res.json()

@_checkToken
def _postData(url:str,obj:dict,**kwargs)->object:
    res = _requests.post(url,headers=_header,data=_json.dumps(obj))
    if kwargs.get('print') == True:
        print(res.text)
    return res.json()

@_checkToken
def _patchData(url:str,obj:dict,**kwargs)->object:
    res = _requests.patch(url,headers=_header,data=_json.dumps(obj))
    if kwargs.get('print') == True:
        print(res.text)
    return res.json()

@_checkToken
def _deleteData(url:str,**kwargs)->object:
    res = _requests.delete(url,headers=_header)
    if kwargs.get('print') == True:
        print(res.text)
    return res.status_code

#profile_response = _requests.get(_endpoint+getProfile,headers=header)
#json_profile = profile_response.json()
#
#
@_checkToken
def getCompanyId()->object:
    """
    Retrieve the company id for later call for the properties
    """
    companies = _requests.get(_endpoint+_getCompanies,headers=_header)
    companyID = companies.json()['data'][0]['id']
    return companyID

def getProperties(companyID:str)->object:
    """
    Retrieve the different properties available for a specific company.
    Parameter :
        companyID : REQUIRED : Company from where you want the properties
    """
    req_properties = _getData(_endpoint+_getProperties.format(_company_id=companyID))
    properties = req_properties
    data = properties['data'] ## properties information for page 1
    pagination = properties['meta']['pagination'] ##searching if page 1 is enough
    if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:## requesting all the pages
            pages_left = pagination['total_pages'] - pagination['current_page'] ## calculate how many page to download
            workers = min(pages_left,5)## max 5 threads
            list_page_number = ['?page%5Bnumber%5D='+str(x) for x in range(2,pages_left+2)] ##starting page 2
            urls = [_endpoint+_getProperties.format(_company_id=companyID) for x in range(2,pages_left+2)]
            with _futures.ThreadPoolExecutor(workers) as executor:
                res = executor.map(_getData,urls,list_page_number)
            res = list(res)
            append_data = [val for sublist in [data['data'] for data in res] for val in sublist] ##flatten list of list
            data = data + append_data
    return data


class Property: 
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
        self._Host = 'https://reactor.adobe.io//properties/'+data['id']+'/hosts'
        self._Environments = data['links']['environments']
        self._Libraries = data['relationships']['libraries']['links']['related']
        self.ruleComponents = {}
        
    def __repr__(self)-> dict:
        return _json.dumps(self.dict,indent=4)
    
    def __str__(self)-> str:
        return str(_json.dumps(self.dict,indent=4))
    
    def importRuleComponents(self,rules:list)->dict:
        """
        Takes the list of rules and create a dictionary to assign each rule to a name 
        """
    
    def getEnvironments(self)->object:
        """
        Retrieve the environment sets for this property
        """
        env = _getData(self._Environments)
        data = env['data'] ## skip meta for now
        return data 
    
    def getHost(self)->object:
        """
        Retrieve the hosts sets for this property
        """
        host = _getData(self._Host)
        data = host['data'] ## skip meta for now
        return data 
    
    def getExtensions(self)-> object:
        """
        retrieve the different information from url retrieve in the properties
        """
        extensions = _getData(self._Extensions)
        pagination = extensions['meta']['pagination']
        data = extensions['data'] ## keep only information on extensions
        if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:## requesting all the pages
            pages_left = pagination['total_pages'] - pagination['current_page'] ## calculate how many page to download
            workers = min(pages_left,5)## max 5 threads
            list_page_number = ['?page%5Bnumber%5D='+str(x) for x in range(2,pages_left+2)]
            urls = [ self._Extensions for x in range(2,pages_left+2)]
            with _futures.ThreadPoolExecutor(workers) as executor:
                res = executor.map(_getData,urls,list_page_number)
            res = list(res)
            append_data = [val for sublist in [data['data'] for data in res] for val in sublist] ##flatten list of list
            data = data + append_data
        return data
    
    def getRules(self)->object:
        """
        Return the list of the rules data.
        On top, it fills the ruleComponents attribute with a dictionnary based on rule id and their rule name and the ruleComponent of each.
        """
        rules = _getData(self._Rules)
        data = rules['data'] ## skip meta for now
        pagination = rules['meta']['pagination']
        if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:## requesting all the pages
            pages_left = pagination['total_pages'] - pagination['current_page'] ## calculate how many page to download
            workers = min(pages_left,5)## max 5 threads
            list_page_number = ['?page%5Bnumber%5D='+str(x) for x in range(2,pages_left+2)]
            urls = [self._Rules for x in range(2,pages_left+2)]
            with _futures.ThreadPoolExecutor(workers) as executor:
                res = executor.map(_getData,urls,list_page_number)
            res = list(res)
            append_data = [val for sublist in [data['data'] for data in res] for val in sublist]
            data = data + append_data
        for rule in data:
            self.ruleComponents[rule['id']] = {
            'name' : rule['attributes']['name'],
            'url' : rule['links']['rule_components']
            }
        return data
    
    def searchRules(self,name:str=None,enabled:bool=None,published:bool=None,dirty:bool=None,**kwargs)->object:
        """
        Returns the rules searched through the different operator. One argument is required in order to return a result. 
        Arguments: 
            name : OPTIONAL : string of what is searched (used as "contains")
            enabled : OPTIONAL : boolean if search for enabled rules or not
            published : OPTIONAL : boolean if search for published rules or not
            dirty : OPTIONAL : boolean if search for dirty rules or not
        """
        filters = []
        if name != None:
            filters.append('filter%5Bname%5D=CONTAINS%20'+name)
        if dirty != None:
            filters.append('filter%5Bdirty%5D=EQ%20'+str(dirty).lower())
        if enabled != None:
            filters.append('filter%5Benabled%5D=EQ%20'+str(enabled).lower())
        if published != None:
            filters.append('filter%5Bpublished%5D=EQ%20'+str(published).lower())
        if 'created_at' in kwargs:
            pass ## documentation unclear on how to handle it
        parameters = '?'+'&'.join(filters)
        rules = _getData(self._Rules,parameters)
        data = rules['data'] ## skip meta for now
        pagination = rules['meta']['pagination']
        if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:## requesting all the pages
            pages_left = pagination['total_pages'] - pagination['current_page'] ## calculate how many page to download
            workers = min(pages_left,5)## max 5 threads
            list_parameters = [parameters+'&page%5Bnumber%5D='+str(x) for x in range(2,pages_left+2)]
            urls = [self._Rules for x in range(2,pages_left+2)]
            with _futures.ThreadPoolExecutor(workers) as executor:
                res = executor.map(_getData,urls,list_parameters)
            res = list(res)
            append_data = [val for sublist in [data['data'] for data in res] for val in sublist]
            data = data + append_data
        for rule in data:
            self.ruleComponents[rule['id']] = {
            'name' : rule['attributes']['name'],
            'url' : rule['links']['rule_components']
            }
        return data
        
    
    @_checkToken
    def getRuleComponents(self)->dict:
        """
        Returns a list of all the ruleComponents gathered in the ruleComponents attributes. 
        It will also enrich the RuleCompoment JSON data with the rule_name attached to it. 
        """        
        ruleComponents = self.ruleComponents
        if len(ruleComponents) == 0:
            raise AttributeError('Rules should have been retrieved in order to retrieve Rule Component.\n {}.ruleComponent is empty'.format(self.name))
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
    
    def getDataElements(self)->object:
        """
        Retrieve data elements of that property.
        Returns a list.
        """
        dataElements = _getData(self._DataElement)
        data = dataElements['data'] ## data for page 1
        pagination = dataElements['meta']['pagination']
        if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:## requesting all the pages
            pages_left = pagination['total_pages'] - pagination['current_page'] ## calculate how many page to download
            workers = min(pages_left,5)## max 5 threads
            list_page_number = ['?page%5Bnumber%5D='+str(x) for x in range(2,pages_left+2)]
            urls = [self._DataElement for x in range(2,pages_left+2)]
            with _futures.ThreadPoolExecutor(workers) as executor:
                res = executor.map(_getData,urls,list_page_number)
            res = list(res)
            append_data = [val for sublist in [data['data'] for data in res] for val in sublist]
            data = data + append_data
        return data
    
    def searchDataElements(self,name:str=None,enabled:bool=None,published:bool=None,dirty:bool=None,**kwargs)->object:
        """
        Returns the rules searched through the different operator. One argument is required in order to return a result. 
        Arguments: 
            name : OPTIONAL : string of what is searched (used as "contains")
            enabled : OPTIONAL : boolean if search for enabled rules or not
            published : OPTIONAL : boolean if search for published rules or not
            dirty : OPTIONAL : boolean if search for dirty rules or not
        """
        filters = []
        if name != None:
            filters.append('filter%5Bname%5D=CONTAINS%20'+name)
        if dirty != None:
            filters.append('filter%5Bdirty%5D=EQ%20'+str(dirty).lower())
        if enabled != None:
            filters.append('filter%5Benabled%5D=EQ%20'+str(enabled).lower())
        if published != None:
            filters.append('filter%5Bpublished%5D=EQ%20'+str(published).lower())
        if 'created_at' in kwargs:
            pass ## documentation unclear on how to handle it
        parameters = '?'+'&'.join(filters)
        dataElements = _getData(self._DataElement,parameters)
        data = dataElements['data'] ## skip meta for now
        pagination = dataElements['meta']['pagination']
        if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:## requesting all the pages
            pages_left = pagination['total_pages'] - pagination['current_page'] ## calculate how many page to download
            workers = min(pages_left,5)## max 5 threads
            list_parameters = [parameters+'&page%5Bnumber%5D='+str(x) for x in range(2,pages_left+2)]
            urls = [self._Rules for x in range(2,pages_left+2)]
            with _futures.ThreadPoolExecutor(workers) as executor:
                res = executor.map(_getData,urls,list_parameters)
            res = list(res)
            append_data = [val for sublist in [data['data'] for data in res] for val in sublist]
            data = data + append_data
        return data
    
    def getLibraries(self)->object:
        """
        Retrieve libraries of the property.
        Returns a list.
        """
        libs = _getData(self._Libraries)
        data = libs['data'] ## dat for page 1
        pagination = libs['meta']['pagination']
        if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:## requesting all the pages
            print(pagination['current_page'])
            print(pagination['total_pages'])
            pages_left = pagination['total_pages'] - pagination['current_page'] ## calculate how many page to download
            workers = min(pages_left,5)## max 5 threads
            list_page_number = ['?page%5Bnumber%5D='+str(x) for x in range(2,pages_left+2)]
            urls = [self._Rules for x in range(2,pages_left+2)]
            with _futures.ThreadPoolExecutor(workers) as executor:
                res = executor.map(_getData,urls,list_page_number)
            res = list(res)
            append_data = [val for sublist in [data['data'] for data in res] for val in sublist]
            data = data + append_data
        return data 
    
    
    def createExtensions(self,extension_id:str,settings:str=None,descriptor:str=None,**kwargs)-> object:
        """
        Create an extension in your property. Your extension_id argument should be the latest one extension id available.
        Arguments : 
            extension_id : REQUIRED : ID for the extension to be created
            settings : OPTIONAL: setting to set in the extension
            delegate_descriptor_id : OPTIONAL : delegate descriptor id
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
        if settings is not None and descriptor is not None :
            obj['data']['attributes']['settings'] = str(settings)
            obj['data']['attributes']['delegate_descriptor_id'] = descriptor
        extensions = _postData(self._Extensions,obj)
        data = extensions['data']
        return data
    
    def createRules(self,name:str)->object:
        """
        Create a rule by provided a rule name. 
        """
        
        obj = {
          "data": {
            "attributes": {
              "name": name
            },
            "type": "rules"
          }
        }
        rules = _postData(self._Rules,obj)
        data = rules['data']
        self.ruleComponents[data['id']]= {'name' :data['attributes']['name'],
                           'url': data['links']['rule_components']}
        return data
    
    def createRuleComponents(self,name:str,descriptor:str,settings:str=None,extension_id:dict=None,rule_id:dict=None,**kwargs)->object:
        """
        Create a ruleComponent by provided a rule name and descriptor (minimum). It returns an object.
        It takes additional information in order to link the ruleCompoment to a rule and with an Extension.
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
        rc = _postData(self._RuleComponents,obj)
        data = rc['data']
        return data
            
    def createDataElements(self,name:str,descriptor:str,extension:dict,settings:str=None,**kwargs:dict)->object:
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
            if settings is not None:
                obj['data']['attributes']['settings'] = settings
        except:
            pass
        dataElements = _postData(self._DataElement,obj)
        data = dataElements['data']
        return data 
    
    def createEnvironment(self,name:str,host_id:str,stage:str='development',**kwargs)->object:
        """
        Create an environment. Note that you cannot create more than 1 environment for Staging and Production stage. 
        Arguments : 
            name : REQUIRED : name of your environment
            host_id : REQUIRED : The host id that you would need to connect to the correct host. 
            stage : OPTIONAL : Default Development. can be staging, production as well. 
        
        documentation : https://developer.adobelaunch.com/api/reference/1.0/environments/create/
        """
        obj = {
                "data": {
                    "attributes": {
                        "name": name,
                        "stage": stage
                    },
                    "relationships": {
                        "host": {
                            "data": {
                            "id": host_id,
                             "type": "hosts"
                            }
                        }
                    },
                "type": "environments"
                }
            }
        env = _postData(self._Environments,obj)
        data = env['data']
        return data 
    
    def createHost(self,name:str,host_type:str='akamai',**kwargs):
        """
        Create a host in that property. By default Akamai host. 
        Argument : 
            name : REQUIRED : name of the host
            host_type : OPTIONAL : type of host. 'akamai' or 'sftp'. Default 'akamai'
        
        If the host type is sftp, additional info can be enter as kwargs:
            username : REQUIRED : str : username of the sftp
            encrypted_private_key : REQUIRED : str : private key for the sftp as string
            server : REQUIRED : str : server for the sftp.
            path : REQUIRED : str : path of the sftp
            port : REQUIRED : int : port to use
        documentation : https://developer.adobelaunch.com/api/reference/1.0/hosts/create/
        """
        obj = {
            "data": {
                "attributes": {
                    "name": name,
                    "type_of":host_type
                    },
                "type": "hosts"
                }
            }
        if host_type == 'sftp':
            if 'encrypted_private_key' not in kwargs: 
                raise KeyError('missing the encrypted_private_key key')
            else:
                obj['data']['attributes']['username'] = kwargs.get('username')
                obj['data']['attributes']['encrypted_private_key'] = kwargs.get('encrypted_private_key')
                obj['data']['attributes']['server'] = kwargs.get('server')
                obj['data']['attributes']['path'] = kwargs.get('path','/')
                obj['data']['attributes']['port'] = kwargs.get('port',22)
        host = _postData(self._Host,obj)
        data = host['data']
        return data
    
    def createLibrary(self,name:str,return_class:bool=True)->object:
        """
        Create a library with the name provided. Returns an object.
        Arguments:
            name : REQUIRED : name of the library
        """
        obj={
          "data": {
            "attributes": {
              "name": name
            },
            "type": "libraries"
          }
        }
        lib = _postData(self._Libraries,obj)
        data = lib['data']
        if return_class:
            new_instance = Library(data)
            return new_instance
        else:
            return data
    
    
    def reviseExtensions(self,extension_id,attr_dict:dict,**kwargs)-> object:
        """
        update the extension with the information provided in the argument.
        argument: 
            attr_dict : REQUIRED : dictionary that will be passed to Launch for update
        """
        obj={
            "data": {
                "attributes": attr_dict,
            "meta": {
              "action": "revise"
            },
            "id": extension_id,
            "type": "extensions"
          }
        }
        extensions = _patchData(_endpoint+'/extensions/'+extension_id,obj)
        data = extensions.json()['data']
        return data
    
    def reviseRules(self,rule_id:str,attr_dict:object)->object:
        """
        Update the rule.
        arguments: 
            rule_id : REQUIRED : Rule ID
            attr_dict : REQUIRED : dictionary that will be passed to Launch for update
        """
        obj = {
              "data": {
                "attributes": {},
                "meta": {
                  "action": "revise"
                },
                "id": rule_id,
                "type": "rules"
              }
            }
        rules = _patchData(_endpoint+'/rules/'+rule_id,obj)
        data = rules
        return data
    
    def reviseDataElements(self,dataElement_id:str,attr_dict:object,**kwargs)->object:
        """
        Update the data element information based on the information provided.
        arguments: 
            dataElement_id : REQUIRED : Data Element ID
            attr_dict : REQUIRED : dictionary that will be passed to Launch for update
        """
        obj = {
              "data": {
                "attributes": {},
                "type": "data_elements",
                "id": dataElement_id,
                "meta": {
                  "action": "revise"
                }
              }
            }
        dataElements = _patchData(_endpoint+'/data_elements/'+dataElement_id,obj)
        data = dataElements.json()['data']
        return data 
    
    def updateRules(self,rule_id:str,attr_dict:object)->object:
        """
        Update the rule.
        arguments: 
            rule_id : REQUIRED : Rule ID
            attr_dict : REQUIRED : dictionary that will be passed to Launch for update
        """
        obj = {
              "data": {
                "attributes": attr_dict,
                "meta": {
                  "action": "revise"
                },
                "id": rule_id,
                "type": "rules"
              }
            }
        rules = _patchData(_endpoint+'/rules/'+rule_id,obj)
        data = rules
        return data
    
    def updateRuleComponents(self,rc_id:str,attr_dict:object,**kwargs)->object:
        """
        Update the ruleComponents based on the information provided
        arguments: 
            rc_id : REQUIRED : Rule Component ID
            attr_dict : REQUIRED : dictionary that will be passed to Launch for update
        """
        obj = {
              "data": {
                "attributes": attr_dict,
                "type": "rule_components",
                "id": rc_id
              }
            }
        rules = _patchData(_endpoint+'/rule_components/'+rc_id,obj)
        data = rules
        return data
    
    
    def updateDataElements(self,dataElement_id:str,attr_dict:object,**kwargs)->object:
        """
        Update the data element information based on the information provided.
        arguments: 
            dataElement_id : REQUIRED : Data Element ID
            attr_dict : REQUIRED : dictionary that will be passed to Launch for update
        """
        obj = {
              "data": {
                "attributes": attr_dict,
                "type": "data_elements",
                "id": dataElement_id
              }
            }
        dataElements = _patchData(_endpoint+'/data_elements/'+dataElement_id,obj)
        data = dataElements.json()['data']
        return data 
    
    def updateEnvironment(self,name:str,env_id:str,**kwargs)->object:
        """
        Update an environment. Note :only support name change
            name : REQUIRED : name of your environment
            env_id : REQUIRED : The environement id.
            stage : OPTIONAL : Default Development. can be staging, production as well. 
        
        documentation : https://developer.adobelaunch.com/api/reference/1.0/environments/create/
        """
        obj = {
                "data": {
                    "attributes": {
                        "name": name
                    },
                'id':env_id,
                "type": "environments"
                }
            }
        env = _patchData(_endpoint+'/environments/'+env_id,obj)
        return env
    
    def deleteRule(self,rule_id:str)->object:
        """
        Delete the rule 
        Arguments : 
            rule_id : REQUIRED : Rule ID that needs to be deleted
        """
        data = _deleteData('https://reactor.adobe.io/rules/'+rule_id)
        return data
    
    def deleteDataElement(self,dataElement_id:str)->object:
        """
        Delete the rule 
        Arguments : 
            dataElement_id : REQUIRED : Data Element ID that needs to be deleted
        """
        data = _deleteData('https://reactor.adobe.io/data_elements/'+dataElement_id)
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
                'created_at':rule['attributes']['created_at'],
                'published':rule['attributes']['published'],
                'dirty':rule['attributes']['dirty'],
                'enabled':rule['attributes']['enabled'],
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
    return components

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
                'created_at' : element['attributes']['created_at'],
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
    return elements

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

def extractSettings(element:dict,save:bool=False)->dict:
    element_type = element['type']
    if element_type == 'data_elements':
        if element['attributes']['delegate_descriptor_id'] == 'core::dataElements::custom-code':
            settings = element['attributes']['settings']
            code = _json.loads(settings)['source']
            if save is True:
                name = 'DE - '+ str(element['attributes']['name'])
                with open(f'{name}.js','w') as f:
                    f.write(code)        
            return code
        else:
            settings=element['attributes']['settings']
            if save:
                name = 'DE - '+ str(element['attributes']['name']) + ' - settings.json'
                with open(name,'w') as f:
                    f.write(settings)
            return settings
    elif element_type == 'extensions':
        if element['attributes']['delegate_descriptor_id'] == "adobe-analytics::extensionConfiguration::config":
            settings = _json.loads(element['attributes']['settings'])
            code = settings['source']
            if save is True:
                name = 'EXT - '+ str(element['attributes']['name'])
                with open(f'{name}.js','w') as f:
                    f.write(code)        
            return code
        else:
            settings=element['attributes']['settings']
            if save:
                name = 'EXT - '+ str(element['attributes']['name']) + ' - settings.json'
                with open(name,'w') as f:
                    f.write(settings)
            return settings

def copySettings(data:object)->object:
    """
    copy the settings from an element and returns an object with required information
    """
    obj={}
    if data['type'] == 'extensions':
        obj['name'] = data['attributes']['name']
        obj['settings'] = data['attributes']['settings']
        obj['delegate_descriptor_id'] = data['attributes']['delegate_descriptor_id']
        obj['extension_id'] = data['relationships']['extension_package']['data']['id'] 
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
        Arguments: 
            target_property : REQUIRED : property that is targeted to translate the element to
            data_element : OPTIONAL : if the elements passed are data elements
            rule_component : OPTIONAL : if the elements passed are rule components
        """
        if data_element is not None:
            new_de = _deepcopy(data_element)
            base_id = new_de['extension']['id']
            row = self.extensions[self.extensions.iloc[:,0] == base_id].index.values[0]
            new_value = self.extensions.loc[row,target_property]
            new_de['extension']['id'] = new_value
            return new_de
        elif rule_component is not None:
            new_rc = _deepcopy(rule_component)
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

def createProperty(companyId:str,name:str,platform:str='web',return_class:bool=True,**kwargs)->dict:
    """
    Create a property with default information. Will return empty value as default value. 
    Returns a property instance.
    Arguments : 
        - companyId : REQUIRED : id of the company
        - name : REQUIRED : name of the property
        - platform : REQUIRED : default 'web', can be 'app'
        - return_class : REQUIRED : default True, will return an instance of property class. 
        If set to false, will just return the object created. 
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
        else:##if a string but only 1 domain
            domains = list(domains)
    obj['data']['attributes']['name'] = name
    obj['data']['attributes']['domains']=domains
    obj['data']['attributes']['platform']=platform
    obj['data']['attributes']['development']=development
    obj['data']['attributes']['undefined_vars_return_empty']=undefined_vars_return_empty
    obj['data']['type']='properties'
    new_property = _postData(_endpoint+_getProperties.format(_company_id=companyId),obj)
    if return_class:
        property_class = Property(new_property['data'])
        return property_class
    else:
        return new_property['data']


class Library:
    
    def __init__(self,data:dict):
        self.id = data['id']
        self.name = data['attributes']['name']
        self.state = data['attributes']['state']
        self.build_required = data['attributes']['build_required']
        self.builds = data['relationships']['builds']['links']['related']
        self._DataElements = _endpoint+'/libraries/'+data['id']+'/data_elements'
        self._Extensions = _endpoint+'/libraries/'+data['id']+'/extensions'
        self._Environment = _endpoint+'/libraries/'+data['id']+'/envrionment'
        self._Rules = _endpoint+'/libraries/'+data['id']+'/rules'
        self._Builds = _endpoint+'/libraries/'+data['id']+'/builds'
        self.builds = data['relationships']['builds']['links']['related']
        self.build_status = data['meta']['build_status']
        self.relationships = {}
        self._environments = {}
        self._dev_env = ''
          
    def getDataElements(self)->list:
        """
        retrieve the list of Data Elements attached to this library
        """
        dataElements = _getData(self._DataElements)
        data = dataElements.json()
        self.relationships['data_elements'] = data ## assign the list to its dict value
        return data
           
    def getExtensions(self)->list:
        """
        retrieve the list of Extensions attached to this library
        """
        extensions = _getData(self._Extensions)
        data = extensions.json()
        self.relationships['extensions'] = data
        return data
      
    def getRules(self)->list:
        """
        retrieve the list of rules attached to this library
        """
        rules = _getData(self._Rules)
        data = rules.json()
        self.relationships['rules'] = data
        return data
    
    def getFullLibrary(self)->dict:
        self.getDataElements()
        self.getRules()
        self.getExtensions()
        return self.relationships
    
    def addDataElements(self,data_element_ids:list)->object:
        """
        Take a list of data elements id and attach them to the library. 
        Arguments:
            data_element_ids: REQUIRED : list of data elements id
        """
        if self.state != 'development':
            print('State is not development, cannot add relationships')
            return None
        obj = {'data':[]}
        if type(data_element_ids) == str:
            data_element_ids = data_element_ids.split(' ')
        for ids in data_element_ids:
            obj['data'].append({"id": ids,"type": "data_elements","meta": {"action": "revise"}})
        url = _endpoint+'/libraries/'+self.id+'/relationships/data_elements'
        res = _postData(url,obj)
        return res
    
    def addRules(self,rules_ids:list)->object:
        """
        Take a list of rules id and attach them to the library. 
        Arguments:
            rules_ids: REQUIRED : list of rules id
        """
        if self.state != 'development':
            print('State is not development, cannot add relationships')
            return None
        obj = {'data':[]}
        if type(rules_ids) == str:
            rules_ids = rules_ids.split(' ')
        for ids in rules_ids:
            obj['data'].append({"id": ids,"type": "rules","meta": {"action": "revise"}})
        url = _endpoint+'/libraries/'+self.id+'/relationships/rules'
        res = _postData(url,obj)
        return res
    
    def addExtensions(self,extensions_ids:list)->object:
        """
        Take a list of extension id and attach them to the library. 
        Arguments:
            extensions_ids: REQUIRED : list of extension id
        """
        if self.state != 'development':
            print('State is not development, cannot add relationships')
            return None
        obj = {'data':[]}
        if type(extensions_ids) == str:
            extensions_ids = extensions_ids.split(' ')
        for ids in extensions_ids:
            obj['data'].append({"id": ids,"type": "extensions","meta": {"action": "revise"}})
        url = _endpoint+'/libraries/'+self.id+'/relationships/extensions'
        res = _postData(url,obj)
        return res
    
    def setEnvironments(self,environments_list:list,dev_name:str=None)->None:
        """
        Save the different environments ids available. 
        It is required to use the library class.
        Arguments : 
            environments_list : REQUIRED : list of environment retrieved by the getEnvironment method
            dev_name : OPTIONAL : Name of your dev environment. If not defined, will take the first dev environment
        """
        for env in environments_list:
            if env['attributes']['stage'] == 'production':
                self._environments['production'] = env['id']
            elif env['attributes']['stage'] == 'staging':
                self._environments['staging'] = env['id']
            elif env['attributes']['stage'] == 'development':
                devs = self._environments.get('developments',{})
                devs[env['attributes']['name']] = env['id']
                self._environments['developments'] = devs
        if dev_name != None: 
            self._dev_env = self._environments['developments'][dev_name]
        else:
            key1 = list(self._environments['developments'].keys())[0]
            self._dev_env = self._environments['developments'][key1]
            
    @_checkToken      
    def _setEnvironment(self,obj:dict)->None:
        new_env = _requests.patch(_endpoint+'/libraries/'+self.id+'/relationships/environment',headers=_header,data=_json.dumps(obj))
        res = new_env.json()
        return res
    
    @_checkToken
    def _removeEnvironment(self)->None:
        """
        Remove environment
        """
        new_env = _requests.get(_endpoint+'/libraries/'+self.id+'/relationships/environment',headers=_header)
        res = new_env.json()
        return res
    
    def build(self)->dict:
        """
        Build the library. 
        Part of the code takes care of assigning the right environement before building the library.
        Returns the build when it is completed (succeed or not).
        It will check every 15 seconds for the build status, making sure it is not "pending".
        """
        if self.build_required == False and self.state != 'approved':
            return 'build is not required'
        
        if self.state == 'development':
            env_id = self._dev_env
            obj={
              "data": {
                "id": env_id,
                "type": "environments"
              }
            }
            self._removeEnvironment()
            status = self._setEnvironment(obj)
        elif self.state == 'submitted':
            env = 'staging'
            obj={
              "data": {
                "id": self._environments[env],
                "type": "environments"
              }
            }
            self._removeEnvironment()
            status = self._setEnvironment(obj)
        elif self.state == 'approved':
            env = 'production'
            obj={
              "data": {
                "id": self._environments[env],
                "type": "environments"
              }
            }
            self._removeEnvironment()
            status = self._setEnvironment(obj)
        if 'error' in status.keys() :
            raise SystemExit('Issue setting environment')
        build = _requests.post(self._Builds,headers=_header)
        build_json = build.json()
        build_id = build_json['data']['id']
        build_status = build_json['data']['attributes']['status']
        while build_status == 'pending':
            print('pending...')
            _time.sleep(20)
            build = _getData(_endpoint+'/builds/'+str(build_id)) ## return the json directly
            build_status = build['data']['attributes']['status']
        if build['data']['attributes']['status']=='succeeded':
            self.build_required = False
            self.build_status = 'succeeded'
        else:
            self.build_required = True
            self.build_status = build['data']['attributes']['status']
        return build
        
    
    def transition(self,action:str=None,**kwargs)->object:
        """
        Move the library along the publishing funnel.
        If no action are provided, it would automatically go to the next state. 
        Arguments : 
            action : OPTIONAL : action to do on the library. Possible values: 
                - 'submit' : if state == development
                - 'approve' : if state == submitted
                - 'reject' : if state == submitted
        """
        if action== None: 
            if self.state == 'development':
                action = 'submit'
            elif self.state == 'submitted':
                action = 'approve'
        obj={"data": {
            "id": self.id,
            "type": "libraries",
            "meta": {
              "action": action
                  }
                }
            }
        transition = _patchData(_endpoint+'/libraries/'+self.id,obj)
        data = transition
        self.state = data['data']['attributes']['state']
        self.build_required = data['data']['attributes']['build_required']
        return data
            
    