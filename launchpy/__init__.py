# -*- coding: utf-8 -*-
"""
May  15 12:04:49 2019
@author: Julien Piccini
"""
__version__ = "0.0.7"
import time as _time
import json as _json
from collections import defaultdict as _defaultdict
from concurrent import futures as _futures
from copy import deepcopy as _deepcopy
import re
import os
# Non standard libraries
import pandas as _pd
import requests as _requests
import jwt as _jwt
from pathlib import Path


# Set up default values
_org_id, _api_key, _tech_id, _pathToKey, _secret = "", "", "", "", "",
_TokenEndpoint = "https://ims-na1.adobelogin.com/ims/exchange/jwt"
_orga_admin = {'_org_admin', '_deployment_admin', '_support_admin'}
_date_limit = 0
_token = ''
_header = {}


def createConfigFile(verbose: object = False)->None:
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
        print(
            f" file created at this location : {os.getcwd()}{os.sep}config_admin.json")


def importConfigFile(file: str)-> None:
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


# Launch API Endpoint
_endpoint = 'https://reactor.adobe.io/'


def retrieveToken(verbose: bool = False, save: bool = False)->str:
    """ Retrieve the token by using the information provided by the user during the import importConfigFile function. 

    Argument : 
        verbose : OPTIONAL : Default False. If set to True, print information.
    """
    global _token
    global _pathToKey
    if _pathToKey.startswith('/'):
        _pathToKey = "."+_pathToKey
    with open(Path(_pathToKey), 'r') as f:
        private_key_unencrypted = f.read()
        header_jwt = {'cache-control': 'no-cache',
                      'content-type': 'application/x-www-form-urlencoded'}
    jwtPayload = {
        # Expiration set to 24 hours
        "exp": round(24*60*60 + int(_time.time())),
        "iss": _org_id,  # org_id
        "sub": _tech_id,  # technical_account_id
        "https://ims-na1.adobelogin.com/s/ent_reactor_admin_sdk": True,
        "aud": "https://ims-na1.adobelogin.com/c/"+_api_key
    }
    encoded_jwt = _jwt.encode(
        jwtPayload, private_key_unencrypted, algorithm='RS256')  # working algorithm
    payload = {
        "client_id": _api_key,
        "client_secret": _secret,
        "jwt_token": encoded_jwt.decode("utf-8")
    }
    response = _requests.post(_TokenEndpoint, headers=header_jwt, data=payload)
    json_response = response.json()
    token = json_response['access_token']
    _updateHeader(token)
    expire = json_response['expires_in']
    global _date_limit  # getting the scope right
    _date_limit = _time.time() + expire/1000 - 500  # end of time for the token
    if save:
        with open('token.txt', 'w') as f:  # save the token
            f.write(token)
    if verbose == True:
        print('token valid till : ' + _time.ctime(_time.time() + expire/1000))
        print(f"token has been saved here : {os.getcwd()}{os.sep}token.txt")
    return token


def _checkToken(func):
    """    decorator that checks that the token is valid before calling the API    """
    def checking(*args, **kwargs):  # if function is not wrapped, will fire
        global _date_limit
        now = _time.time()
        if now > _date_limit - 1000:
            global _token
            _token = retrieveToken(*args, **kwargs)
            return func(*args, **kwargs)
        else:  # need to return the function for decorator to return something
            return func(*args, **kwargs)
    return checking  # return the function as object

###


def _updateHeader(token: str)->None:
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


# Endpoint
_getCompanies = '/companies'
_getProfile = '/profile'
_getProperties = '/companies/{_company_id}/properties'  # string format
_getAuditEvents = '/audit_events'


@_checkToken
def _getData(url: str, params: dict = None, *args: str)->object:
    try:  # try to set pagination if exists
        url = url + args[0]
    except:
        url = url
    res = _requests.get(url, headers=_header, params=params)
    try:
        infos = res.json()
    except:
        infos = res.text
    return infos


@_checkToken
def _postData(url: str, obj: dict, **kwargs)->object:
    res = _requests.post(url, headers=_header, data=_json.dumps(obj))
    if kwargs.get('print') == True:
        print(res.text)
    try:
        infos = res.json()
    except:
        infos = res.text
    return infos


@_checkToken
def _patchData(url: str, obj: dict, **kwargs)->object:
    res = _requests.patch(url, headers=_header, data=_json.dumps(obj))
    if kwargs.get('print') == True:
        print(res.text)
    try:
        infos = res.json()
    except:
        infos = res.text
    return infos


@_checkToken
def _putData(url: str, obj: dict, **kwargs)->object:
    res = _requests.put(url, headers=_header, data=_json.dumps(obj))
    if kwargs.get('print') == True:
        print(res.text)
    try:
        infos = res.json()
    except:
        infos = res.text
    return infos


@_checkToken
def _deleteData(url: str, **kwargs)->object:
    res = _requests.delete(url, headers=_header)
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
    companies = _requests.get(_endpoint+_getCompanies, headers=_header)
    companyID = companies.json()['data'][0]['id']
    return companyID


def getProperties(companyID: str)->object:
    """
    Retrieve the different properties available for a specific company.
    Arguments :
        companyID : REQUIRED : Company from where you want the properties
    """
    req_properties = _getData(
        _endpoint+_getProperties.format(_company_id=companyID))
    properties = req_properties
    data = properties['data']  # properties information for page 1
    # searching if page 1 is enough
    pagination = properties['meta']['pagination']
    # requesting all the pages
    if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:
        # calculate how many page to download
        pages_left = pagination['total_pages'] - pagination['current_page']
        workers = min(pages_left, 5)  # max 5 threads
        list_page_number = [
            '?page%5Bnumber%5D='+str(x) for x in range(2, pages_left+2)]  # starting page 2
        urls = [_endpoint+_getProperties.format(_company_id=companyID)
                for x in range(2, pages_left+2)]
        with _futures.ThreadPoolExecutor(workers) as executor:
            res = executor.map(_getData, urls, list_page_number)
        res = list(res)
        append_data = [val for sublist in [data['data'] for data in res]
                       for val in sublist]  # flatten list of list
        data = data + append_data
    return data


def getAuditEvents(page_size: int = 50, nb_page: int = 10, **kwargs)->list:
    """
    Retrieve the different events that happened inside a Launch property.
    Arguments :
        page_size : OPTIONAL : How many result per page. (default 50)
        nb_page : OPTIONAL : How many page to return. (default 10)
        type_of : OPTIONAL : event to look for.
        **kwargs option
        data : data being passed from one recursion to another. 
        verbose : if want to follow up the completion (bool)

    """
    params = {'include': 'property', 'page[size]': '50'}
    params['page[number]'] = kwargs.get('page_nb', 1)
    if page_size is not None:
        params['page[size]'] = page_size
    events = _getData(_endpoint+_getAuditEvents, params=params)
    data = events['data']
    curr_page = events['meta']['pagination']['current_page']
    if kwargs.get('verbose', False):
        if curr_page % 10 == 0 or curr_page == 1:
            print(f'current page {curr_page}')
        print(f'% completion : {curr_page / nb_page*100}%')
    if curr_page < events['meta']['pagination']['total_pages'] and curr_page < nb_page:
        data += getAuditEvents(page_size=page_size, nb_page=nb_page,
                               page_nb=curr_page+1, data=data, verbose=kwargs.get('verbose', False))
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

    def __init__(self, data: object) -> None:
        """
        Instanciate the class with the object retrieved by getProperties.
        Attributes : 
          data : Object that has been retrieved on getProperties. Single property. 
        """
        self.dict = data
        self.name = data['attributes']['name']
        self.id = data['id']
        self.platform = data['attributes']['platform']
        self.development = data['attributes']['development']
        if data['attributes']['platform'] == "web":
            self.domains = data['attributes']['domains']
        if data['attributes']['platform'] == "mobile":
            self.ssl_enabled = data['attributes']['ssl_enabled']
            self.privacy = data['attributes']['privacy']
        self._DataElement = data['links']['data_elements']
        self._Extensions = data['links']['extensions']
        self._Rules = data['links']['rules']
        self._RuleComponents = 'https://reactor.adobe.io/properties/' + \
            data['id']+'/rule_components'
        self._Host = 'https://reactor.adobe.io//properties/' + \
            data['id']+'/hosts'
        self._Note = 'https://reactor.adobe.io/notes/'
        self._Environments = data['links']['environments']
        self._Libraries = data['relationships']['libraries']['links']['related']
        self.ruleComponents = {}

    def __repr__(self)-> dict:
        return _json.dumps(self.dict, indent=4)

    def __str__(self)-> str:
        return str(_json.dumps(self.dict, indent=4))

    def _getExtensionPackage(self, ext_name: str, verbose: bool = False)->dict:
        """
        Retrieve extension id of the catalog from an extension name.
        It will be used later on to check for available updates. 
        """
        uri = '/extension_packages'
        params = {'filter[name]': 'EQ '+str(ext_name)}
        res_ext = _requests.get(_endpoint+uri, params=params, headers=_header)
        data = res_ext.json()['data'][0]
        extension_id = data['id']
        if verbose:
            print('extension name : ' + str(data['attributes']['name']))
            print('extension id : ' + str(data['id']))
        return extension_id

    def getEnvironments(self)->object:
        """
        Retrieve the environment sets for this property
        """
        env = _getData(self._Environments)
        data = env['data']  # skip meta for now
        return data

    def getHost(self)->object:
        """
        Retrieve the hosts sets for this property
        """
        host = _getData(self._Host)
        data = host['data']  # skip meta for now
        return data

    def getExtensions(self)-> object:
        """
        retrieve the different information from url retrieve in the properties
        """
        extensions = _getData(self._Extensions)
        try:
            pagination = extensions['meta']['pagination']
            data = extensions['data']  # keep only information on extensions
            # requesting all the pages
            if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:
                # calculate how many page to download
                pages_left = pagination['total_pages'] - \
                    pagination['current_page']
                workers = min(pages_left, 5)  # max 5 threads
                list_page_number = ['?page%5Bnumber%5D=' +
                                    str(x) for x in range(2, pages_left+2)]
                urls = [self._Extensions for x in range(2, pages_left+2)]
                with _futures.ThreadPoolExecutor(workers) as executor:
                    res = executor.map(_getData, urls, list_page_number)
                res = list(res)
                append_data = [val for sublist in [data['data'] for data in res]
                               for val in sublist]  # flatten list of list
                data = data + append_data
        except:
            data = extensions
        return data

    def checkExtensionUpdate(self, verbose: bool = False):
        """
        Returns a dictionary of extensions with their names, ids and if there is an update. 
        If there is an update available, the id returned is the latest id (to be used for installation). 
        It can be re-use for installation and for checking for update. 
        Arguments:
            verbose: OPTIONAL : if set to True, will print the different name and id of the extensions checked.

        Dictionary example: 
        {'adobe-mcid':
            {'id':'XXXXX',
            'update':False
            }
        }

        """
        extensions = self.getExtensions()
        dict_extensions = {ext['attributes']['name']: {'package_id': ext['relationships']['extension_package']['data']['id'],
                                                       'update': False,
                                                       'internal_id': ext['id']
                                                       } for ext in extensions}
        for name in dict_extensions:
            new_id = self._getExtensionPackage(name, verbose)
            if new_id != dict_extensions[name]['package_id']:
                dict_extensions[name]['package_id'] = new_id
                dict_extensions[name]['update'] = True
        return dict_extensions

    def upgradeExtension(self, extension_id: str, package_id: str, **kwargs)-> object:
        """
        Upgrade the extension with the new package id (EP...). 
        Returns the extension data. 
        Arguments:
            extension_id : REQUIRED : Your internal ID for this extension in your property (EX....)
            package_id : REQUIRED : new extension id for the extension (EP...)
        """
        data = {'data': {
            'id': extension_id,
                "type": "extensions",
                "relationships": {"extension_package": {
                    "links": {
                        "related": "https://reactor.adobe.io/extensions/"+extension_id+"/extension_package"
                    },
                    "data": {
                        "id": package_id,
                        "type": "extension_packages"
                    }
                }
                },
                'meta': {
                    'upgrade_extension_package_id': package_id
                }
                }
                }
        res = _requests.patch(
            _endpoint+'/extensions/'+str(extension_id), headers=_header, data=_json.dumps(data))
        upgrade = res.json()
        return upgrade

    def getRules(self)->object:
        """
        Return the list of the rules data.
        On top, it fills the ruleComponents attribute with a dictionnary based on rule id and their rule name and the ruleComponent of each.
        """
        rules = _getData(self._Rules)
        try:
            data = rules['data']  # skip meta for now
            pagination = rules['meta']['pagination']
            # requesting all the pages
            if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:
                # calculate how many page to download
                pages_left = pagination['total_pages'] - \
                    pagination['current_page']
                workers = min(pages_left, 5)  # max 5 threads
                list_page_number = ['?page%5Bnumber%5D=' +
                                    str(x) for x in range(2, pages_left+2)]
                urls = [self._Rules for x in range(2, pages_left+2)]
                with _futures.ThreadPoolExecutor(workers) as executor:
                    res = executor.map(_getData, urls, list_page_number)
                res = list(res)
                append_data = [val for sublist in [data['data']
                                                   for data in res] for val in sublist]
                data = data + append_data
            for rule in data:
                self.ruleComponents[rule['id']] = {
                    'name': rule['attributes']['name'],
                    'url': rule['links']['rule_components']
                }
        except:
            data = rules
        return data

    def searchRules(self, name: str = None, enabled: bool = None, published: bool = None, dirty: bool = None, **kwargs)->object:
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
            filters.append('filter%5Bpublished%5D=EQ%20' +
                           str(published).lower())
        if 'created_at' in kwargs:
            pass  # documentation unclear on how to handle it
        parameters = '?'+'&'.join(filters)
        rules = _getData(self._Rules, parameters)
        data = rules['data']  # skip meta for now
        pagination = rules['meta']['pagination']
        # requesting all the pages
        if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:
            # calculate how many page to download
            pages_left = pagination['total_pages'] - pagination['current_page']
            workers = min(pages_left, 5)  # max 5 threads
            list_parameters = [parameters+'&page%5Bnumber%5D=' +
                               str(x) for x in range(2, pages_left+2)]
            urls = [self._Rules for x in range(2, pages_left+2)]
            with _futures.ThreadPoolExecutor(workers) as executor:
                res = executor.map(_getData, urls, list_parameters)
            res = list(res)
            append_data = [val for sublist in [data['data']
                                               for data in res] for val in sublist]
            data = data + append_data
        for rule in data:
            self.ruleComponents[rule['id']] = {
                'name': rule['attributes']['name'],
                'url': rule['links']['rule_components']
            }
        return data

    @_checkToken
    def getRuleComponents(self)->dict:
        """
        Returns a list of all the ruleComponents gathered in the ruleComponents attributes.
        You must have retrieved the rules before using this method (getRules()).
        It will also enrich the RuleCompoment JSON data with the rule_name attached to it. 
        """
        ruleComponents = self.ruleComponents
        if len(ruleComponents) == 0:
            raise AttributeError(
                'Rules should have been retrieved in order to retrieve Rule Component.\n {}.ruleComponent is empty'.format(self.name))
        list_urls = [ruleComponents[_id]['url'] for _id in ruleComponents]
        names = [ruleComponents[_id]['name'] for _id in ruleComponents]
        ids = list(ruleComponents.keys())
        headers = [_header for nb in range(len(list_urls))]
        workers = min((len(list_urls), 5))

        def request_data(url, header, name, ids):
            rule_component = _requests.get(url, headers=_header)
            data = rule_component.json()['data']
            for element in data:
                element['rule_name'] = name
                element['rule_id'] = ids
            return data
        with _futures.ThreadPoolExecutor(workers) as executor:
            res = executor.map(request_data, list_urls, headers, names, ids)
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
        try:
            data = dataElements['data']  # data for page 1
            pagination = dataElements['meta']['pagination']
            # requesting all the pages
            if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:
                # calculate how many page to download
                pages_left = pagination['total_pages'] - \
                    pagination['current_page']
                workers = min(pages_left, 5)  # max 5 threads
                list_page_number = ['?page%5Bnumber%5D=' +
                                    str(x) for x in range(2, pages_left+2)]
                urls = [self._DataElement for x in range(2, pages_left+2)]
                with _futures.ThreadPoolExecutor(workers) as executor:
                    res = executor.map(_getData, urls, list_page_number)
                res = list(res)
                append_data = [val for sublist in [data['data']
                                                   for data in res] for val in sublist]
                data = data + append_data
        except:
            data = dataElements
        return data

    def searchDataElements(self, name: str = None, enabled: bool = None, published: bool = None, dirty: bool = None, **kwargs)->object:
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
            filters.append('filter%5Bpublished%5D=EQ%20' +
                           str(published).lower())
        if 'created_at' in kwargs:
            pass  # documentation unclear on how to handle it
        parameters = '?'+'&'.join(filters)
        dataElements = _getData(self._DataElement, parameters)
        data = dataElements['data']  # skip meta for now
        pagination = dataElements['meta']['pagination']
        # requesting all the pages
        if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:
            # calculate how many page to download
            pages_left = pagination['total_pages'] - pagination['current_page']
            workers = min(pages_left, 5)  # max 5 threads
            list_parameters = [parameters+'&page%5Bnumber%5D=' +
                               str(x) for x in range(2, pages_left+2)]
            urls = [self._Rules for x in range(2, pages_left+2)]
            with _futures.ThreadPoolExecutor(workers) as executor:
                res = executor.map(_getData, urls, list_parameters)
            res = list(res)
            append_data = [val for sublist in [data['data']
                                               for data in res] for val in sublist]
            data = data + append_data
        return data

    def getLibraries(self)->object:
        """
        Retrieve libraries of the property.
        Returns a list.
        """
        libs = _getData(self._Libraries)
        data = libs['data']  # dat for page 1
        pagination = libs['meta']['pagination']
        # requesting all the pages
        if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:
            # calculate how many page to download
            pages_left = pagination['total_pages'] - pagination['current_page']
            workers = min(pages_left, 5)  # max 5 threads
            list_page_number = ['?page%5Bnumber%5D=' +
                                str(x) for x in range(2, pages_left+2)]
            urls = [self._Rules for x in range(2, pages_left+2)]
            with _futures.ThreadPoolExecutor(workers) as executor:
                res = executor.map(_getData, urls, list_page_number)
            res = list(res)
            append_data = [val for sublist in [data['data']
                                               for data in res] for val in sublist]
            data = data + append_data
        return data

    def getNotes(self, data: object)->list:
        """
        Retrieve the note associated with the object pass to the method. Returns list.
        Arguments:
            data: OPTIONAL : object that is associated with a Note (rule, data element, etc...)
        """
        supported_objects = "libraries data_elements rules rule_components extensions"
        if data is not None and data['type'] not in supported_objects.split():
            raise ReferenceError('Data passed are not supported for notes.')

        if data is None:
            url = self.dict['relationships']['notes']['links']['related']
        else:
            url = data['relationships']['notes']['links']['related']
        notes = _getData(url)
        data = notes['data']  # data for page 1
        pagination = notes['meta']['pagination']
        # requesting all the pages
        if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:
            # calculate how many page to download
            pages_left = pagination['total_pages'] - pagination['current_page']
            workers = min(pages_left, 5)  # max 5 threads
            list_page_number = ['?page%5Bnumber%5D=' +
                                str(x) for x in range(2, pages_left+2)]
            urls = [url for x in range(2, pages_left+2)]
            with _futures.ThreadPoolExecutor(workers) as executor:
                res = executor.map(_getData, urls, list_page_number)
            res = list(res)
            append_data = [val for sublist in [data['data']
                                               for data in res] for val in sublist]
            data = data + append_data
        return data

    def createExtensions(self, extension_id: str, settings: str = None, descriptor: str = None, **kwargs)-> object:
        """
        Create an extension in your property. Your extension_id argument should be the latest one extension id available.
        Arguments : 
            extension_id : REQUIRED : ID for the extension to be created
            settings : OPTIONAL: setting to set in the extension
            delegate_descriptor_id : OPTIONAL : delegate descriptor id
        """
        obj = {
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
        if settings is not None and descriptor is not None:
            obj['data']['attributes']['settings'] = str(settings)
            obj['data']['attributes']['delegate_descriptor_id'] = descriptor
        extensions = _postData(self._Extensions, obj)
        try:
            data = extensions['data']
        except:
            data = extensions
        return data

    def createRules(self, name: str)->object:
        """
        Create a rule by provided a rule name.
        Arguments:
            name : REQUIRED : name of your rule. 
        """

        obj = {
            "data": {
                "attributes": {
                    "name": name
                },
                "type": "rules"
            }
        }
        rules = _postData(self._Rules, obj)
        try:
            data = rules['data']
            self.ruleComponents[data['id']] = {'name': data['attributes']['name'],
                                               'url': data['links']['rule_components']}
        except:
            data = rules
        return data

    def createRuleComponents(self, name: str, settings: str = None, descriptor: str = None, extension_id: dict = None, rule_id: dict = None, **kwargs)->object:
        """
        Create a ruleComponent by provided a rule name and descriptor (minimum). It returns an object.
        It takes additional information in order to link the ruleCompoment to a rule and with an Extension.
        Arguments: 
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
                    "delegate_descriptor_id": descriptor
                },
                "relationships": {
                    "extension": {
                        "data": extension_id
                    },
                    "rules": rule_id
                },
                "type": "rule_components"
            }
        }
        if settings is not None:
            obj['data']['attributes']['settings'] = settings
        if 'order' in kwargs:
            obj['data']['attributes']['order'] = kwargs.get('order')
        rc = _postData(self._RuleComponents, obj)
        try:
            data = rc['data']
        except:
            data = rc
        return data

    def createDataElements(self, name: str, settings: str = None, descriptor: str = None, extension: dict = None, **kwargs: dict)->object:
        """
        Create Data Elements following the usage of required arguments. 
        Arguments: 
            name : REQUIRED : name of the data element
            descriptor : REQUIRED : delegate_descriptor_id for the data element
            extension : REQUIRED : extension id used for the data element. (dictionary)
            settings : OPTIONAL : settings for the data element
        """
        obj = {
            "data": {
                "attributes": {
                    "name": name,
                    "delegate_descriptor_id": descriptor,
                },
                "relationships": {
                    "extension": {
                        "data": extension
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
        dataElements = _postData(self._DataElement, obj)
        try:
            data = dataElements['data']
        except:
            data = dataElements
        return data

    def createEnvironment(self, name: str, host_id: str, stage: str = 'development', **kwargs)->object:
        """
        Create an environment. Note that you cannot create more than 1 environment for Staging and Production stage. 
        Arguments: 
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
        env = _postData(self._Environments, obj)
        data = env['data']
        return data

    def createHost(self, name: str, host_type: str = 'akamai', **kwargs):
        """
        Create a host in that property. By default Akamai host. 
        Arguments: 
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
                    "type_of": host_type
                },
                "type": "hosts"
            }
        }
        if host_type == 'sftp':
            if 'encrypted_private_key' not in kwargs:
                raise KeyError('missing the encrypted_private_key key')
            else:
                obj['data']['attributes']['username'] = kwargs.get('username')
                obj['data']['attributes']['encrypted_private_key'] = kwargs.get(
                    'encrypted_private_key')
                obj['data']['attributes']['server'] = kwargs.get('server')
                obj['data']['attributes']['path'] = kwargs.get('path', '/')
                obj['data']['attributes']['port'] = kwargs.get('port', 22)
        host = _postData(self._Host, obj)
        try:
            data = host['data']
        except:
            data = host
        return data

    def createLibrary(self, name: str, return_class: bool = True)->object:
        """
        Create a library with the name provided. Returns an instance of the Library class or the response from the API (object).
        Arguments:
            name : REQUIRED : name of the library
            return_class : OPTIONAL : Bool. will return a instance of the Library class if True.
        """
        obj = {
            "data": {
                "attributes": {
                    "name": name
                },
                "type": "libraries"
            }
        }
        lib = _postData(self._Libraries, obj)
        try:
            data = lib['data']
            if return_class:
                new_instance = Library(data)
                return new_instance
            else:
                return data
        except:
            return lib

    def reviseExtensions(self, extension_id, attr_dict: dict, **kwargs)-> object:
        """
        update the extension with the information provided in the argument.
        argument: 
            attr_dict : REQUIRED : dictionary that will be passed to Launch for update
        """
        obj = {
            "data": {
                "attributes": attr_dict,
                "meta": {
                    "action": "revise"
                },
                "id": extension_id,
                "type": "extensions"
            }
        }
        extensions = _patchData(_endpoint+'/extensions/'+extension_id, obj)
        data = extensions['data']
        return data

    def reviseRules(self, rule_id: str)->object:
        """
        Update the rule.
        arguments: 
            rule_id : REQUIRED : Rule ID
            attr_dict : REQUIRED : dictionary that will be passed to Launch for update
        """
        obj = {
            "data": {
                "meta": {
                    "action": "revise"
                },
                "id": rule_id,
                "type": "rules"
            }
        }
        rules = _patchData(_endpoint+'/rules/'+rule_id, obj)
        data = rules
        return data

    def reviseDataElements(self, dataElement_id: str)->object:
        """
        Update the data element information based on the information provided.
        arguments: 
            dataElement_id : REQUIRED : Data Element ID
            attr_dict : REQUIRED : dictionary that will be passed to Launch for update
        """
        obj = {
            "data": {
                "type": "data_elements",
                "id": dataElement_id,
                "meta": {
                    "action": "revise"
                }
            }
        }
        dataElements = _patchData(
            _endpoint+'/data_elements/'+dataElement_id, obj)
        data = dataElements
        return data

    def updateRules(self, rule_id: str, attr_dict: object)->object:
        """
        Update the rule based on elements passed in attr_dict. 
        arguments: 
            rule_id : REQUIRED : Rule ID
            attr_dict : REQUIRED : dictionary that will be passed to Launch for update

        documentation : https://developer.adobelaunch.com/api/reference/1.0/rules/update/
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
        rules = _patchData(_endpoint+'/rules/'+rule_id, obj)
        try:
            data = rules['data']
        except:
            data = rules
        return data

    def updateRuleComponents(self, rc_id: str, attr_dict: object, **kwargs)->object:
        """
        Update the ruleComponents based on the information provided.
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
        rc = _patchData(_endpoint+'/rule_components/'+rc_id, obj)
        try:
            data = rc['data']
        except:
            data = rc
        return data

    def updateDataElements(self, dataElement_id: str, attr_dict: object, **kwargs)->object:
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
        dataElements = _patchData(
            _endpoint+'/data_elements/'+dataElement_id, obj)
        try:
            data = dataElements['data']
        except:
            data = dataElements
        return data

    def updateEnvironment(self, name: str, env_id: str, **kwargs)->object:
        """
        Update an environment. Note :only support name change.
        Arguments:
            name : REQUIRED : name of your environment
            env_id : REQUIRED : The environement id.

        documentation : https://developer.adobelaunch.com/api/reference/1.0/environments/create/
        """
        obj = {
            "data": {
                "attributes": {
                    "name": name
                },
                'id': env_id,
                "type": "environments"
            }
        }
        env = _patchData(_endpoint+'/environments/'+env_id, obj)
        try:
            data = env['data']
        except:
            data = env
        return data

    def updateExtensions(self, extension_id, attr_dict: dict, **kwargs)-> object:
        """
        update the extension with the information provided in the argument.
        argument: 
            extension_id : REQUIRED : the extension id
            attr_dict : REQUIRED : dictionary that will be passed to Launch for update
        """
        obj = {
            "data": {
                "attributes": attr_dict,
                "id": extension_id,
                "type": "extensions"
            }
        }
        extensions = _patchData(_endpoint+'/extensions/'+extension_id, obj)
        try:
            data = extensions['data']
        except:
            data = extensions
        return data

    def deleteExtension(self, extension_id: str)->str:
        """
        Delete the extension that you want.  
        Arguments: 
            extension_id : REQUIRED : Rule ID that needs to be deleted
        """
        data = _deleteData('https://reactor.adobe.io/extensions/'+extension_id)
        return data

    def deleteRule(self, rule_id: str)->str:
        """
        Delete the rule that you want. 
        Arguments: 
            rule_id : REQUIRED : Rule ID that needs to be deleted
        """
        data = _deleteData('https://reactor.adobe.io/rules/'+rule_id)
        return data

    def deleteDataElement(self, dataElement_id: str)->str:
        """
        Delete a data element.  
        Arguments: 
            dataElement_id : REQUIRED : Data Element ID that needs to be deleted
        """
        data = _deleteData(
            'https://reactor.adobe.io/data_elements/'+dataElement_id)
        return data

    def deleteRuleComponent(self, rc_id: str)->str:
        """
        Delete the rule component that you have selected.  
        Arguments: 
            rc_id : REQUIRED : Rule Component ID that needs to be deleted
        """
        data = _deleteData('https://reactor.adobe.io/rule_components/'+rc_id)
        return data

    def deleteEnvironments(self, env_id: str)->str:
        """
        Delete the environment based on the id.  
        Arguments: 
            env_id : REQUIRED : Environment ID that needs to be deleted
        """
        data = _deleteData('https://reactor.adobe.io/environments/'+env_id)
        return data

    def extractAnalyticsConfig(self)->object:
        """
        Extract the analytics configuration that has been done in the Analytics Extensions and Rules.
        Return a dictionary of the different element in a dataframe
        """
        dict_eVars = _defaultdict(list)
        dict_props = _defaultdict(list)
        dict_events = _defaultdict(list)
        dict_value_eVars = _defaultdict(list)
        dict_value_props = _defaultdict(list)
        p_rules = self.getRules()
        p_ext = self.getExtensions()
        p_rcs = self.getRuleComponents()
        analytics = [ext for ext in p_ext if ext['attributes']
                     ['name'] == 'adobe-analytics'][0]
        analytics_rcs = [rc for rc in p_rcs if rc['attributes']['delegate_descriptor_id'].find(
            'adobe-analytics::actions::set-variables') - 1]

        def searchSetupAnalytics(element: object, verbose: bool = False):
            """
            fills the different dictionaries with where informations are held. 
            """
#            global dict_eVars
#            global dict_props
#            global dict_events
#            global dict_value_eVars
#            global dict_value_props
            if element['type'] == "rule_components":
                name = element['rule_name']
            elif element['type'] == "extensions":
                name = 'Analytics Extension'
            settings = _json.loads(element['attributes']['settings'])
            if 'trackerProperties' in settings.keys():
                tracker_properties = settings['trackerProperties']
            else:
                tracker_properties = {}
            if verbose:
                print(name)
            if len(tracker_properties) > 0:
                if 'eVars' in tracker_properties.keys():
                    for v in tracker_properties['eVars']:
                        dict_eVars[v['name']].append(f'{name} - Interface')
                        dict_value_eVars[v['name']].append(v['value'])
                if 'props' in tracker_properties.keys():
                    for p in tracker_properties['props']:
                        dict_props[p['name']].append(f'{name} - Interface')
                        dict_value_props[p['name']].append(p['value'])
                if 'events' in tracker_properties.keys():
                    for e in tracker_properties['events']:
                        dict_events[e['name']].append(f'{name} - Interface')
            if 'customSetup' in settings.keys():
                code = settings['customSetup']['source']
                if len(code) > 0:
                    matchevents = re.findall('(event[0-9]+)', code)
                    matcheVars = re.findall('(eVar[0-9]+)\s*=', code)
                    matchprops = re.findall('(prop[0-9]+?)\s*=', code)
                    if matcheVars is not None:
                        for v in set(matcheVars):
                            value = f'{name} - Custom Code'
                            if value not in dict_eVars[v]:
                                dict_eVars[v].append(f'{name} - Custom Code')
                    if matchprops is not None:
                        for p in set(matchprops):
                            value = f'{name} - Custom Code'
                            if value not in dict_props[p]:
                                dict_props[p].append(f'{name} - Custom Code')
                    if matchevents is not None:
                        for e in set(matchevents):
                            value = f'{name} - Custom Code'
                            if value not in dict_events[e]:
                                dict_events[e].append(f'{name} - Custom Code')
        searchSetupAnalytics(analytics)
        for rc in analytics_rcs:
            searchSetupAnalytics(rc)
        df_eVars = _pd.DataFrame(
            dict([(k, _pd.Series(v)) for k, v in dict_eVars.items()])).T.fillna('')
        df_eVars.columns = ['location ' +
                            str(i) for i in range(1, len(df_eVars.columns)+1)]
        df_props = _pd.DataFrame(
            dict([(k, _pd.Series(v)) for k, v in dict_props.items()])).T.fillna('')
        df_props.columns = ['location ' +
                            str(i) for i in range(1, len(df_props.columns)+1)]
        df_events = _pd.DataFrame(
            dict([(k, _pd.Series(v)) for k, v in dict_events.items()])).T.fillna('')
        df_events.columns = ['location ' +
                             str(i) for i in range(1, len(df_events.columns)+1)]
        data = {'eVars': df_eVars, 'props': df_props, 'events': df_events}
        return data


def createProperty(companyId: str, name: str, platform: str = 'web', return_class: bool = True, **kwargs)->dict:
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
    obj['data'] = {}
    obj['data']['attributes'] = {}
    # in case some optional value are filled in
    undefined_vars_return_empty = kwargs.get(
        'undefined_vars_return_empty', True)
    development = kwargs.get('development', False)
    domains = kwargs.get('domains', ['example.com'])
    if type(domains) == str:  # change the domains to list as required
        if ',' in domains:
            domains = domains.split(',')
        else:  # if a string but only 1 domain
            domains = list(domains)
    obj['data']['attributes']['name'] = name
    obj['data']['attributes']['domains'] = domains
    obj['data']['attributes']['platform'] = platform
    obj['data']['attributes']['development'] = development
    obj['data']['attributes']['undefined_vars_return_empty'] = undefined_vars_return_empty
    obj['data']['type'] = 'properties'
    new_property = _postData(
        _endpoint+_getProperties.format(_company_id=companyId), obj)
    if return_class:
        property_class = Property(new_property['data'])
        return property_class
    else:
        return new_property['data']


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
    rules = _defaultdict(None)
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
    elements = _defaultdict(None)
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


def extractSettings(element: dict, save: bool = False)->dict:
    """
    Extract the settings from your element. For your custom code, it will extract the javaScript. 
    Arguments: 
        element : REQUIRED : element from which you would like to extract the setting from. 
        save : OPTIONAL : bool, if you want to save the setting in a JS or JSON file, set it to true. (default False)
    """
    element_type = element['type']
    if element_type == 'data_elements':
        if element['attributes']['delegate_descriptor_id'] == 'core::dataElements::custom-code':
            settings = element['attributes']['settings']
            code = _json.loads(settings)['source']
            if save is True:
                name = f'DE - {str(element["attributes"]["name"])}.js'
                name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                with open(name, 'w') as f:
                    f.write(code)
            return code
        else:
            settings = element['attributes']['settings']
            if save:
                name = f'DE - {str(element["attributes"]["name"])} - settings.json'
                name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                with open(name, 'w') as f:
                    f.write(settings)
            return settings
    elif element_type == 'extensions':
        if element['attributes']['delegate_descriptor_id'] == "adobe-analytics::extensionConfiguration::config":
            settings = _json.loads(element['attributes']['settings'])
            if save is True:
                name = f'EXT - {str(element["attributes"]["name"])}.json'
                name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                with open(name, 'w') as f:
                    f.write(_json.dumps(settings, indent=4))
            return settings
        else:
            settings = element['attributes']['settings']
            if save:
                name = f'EXT - {str(element["attributes"]["name"])} - settings.json'
                name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                with open(name, 'w') as f:
                    f.write(settings)
            return settings
    elif element_type == 'rule_components':
        rule_name = element['rule_name']
        element_place = element['attributes']['delegate_descriptor_id'].split('::')[
            1]
        if element['attributes']['delegate_descriptor_id'] == "core::conditions::custom-code":
            settings = element['attributes']['settings']
            code = _json.loads(settings)['source']
            if save is True:
                name = f'RC - {rule_name} - {element_place} - {element["attributes"]["name"]}.js'
                name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                with open(f'{name}', 'w') as f:
                    f.write(code)
            return code
        elif element['attributes']['delegate_descriptor_id'] == "core::events::custom-code":
            settings = element['attributes']['settings']
            code = _json.loads(settings)['source']
            if save is True:
                name = f'RC - {rule_name} - {element_place} - {element["attributes"]["name"]}.js'
                name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                with open(f'{name}', 'w') as f:
                    f.write(code)
            return code
        elif element['attributes']['delegate_descriptor_id'] == "core::actions::custom-code":
            settings = element['attributes']['settings']
            code = _json.loads(settings)['source']
            if save is True:
                name = f'RC - {rule_name} - {element_place} - {element["attributes"]["name"]}.js'
                name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                with open(f'{name}', 'w') as f:
                    f.write(code)
            return code
        else:
            settings = element['attributes']['settings']
            if save:
                name = f'RC - {rule_name} - {element_place} - {element["attributes"]["name"]} - settings.json'
                name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                with open(name, 'w') as f:
                    f.write(_json.dumps(settings, indent=4))
            return settings


def extractAttributes(element: dict, save: bool = False)->dict:
    """
    Extract the attributes of your element. You can save it in a file as well. 
    Arguments:
        element : REQUIRED : element you want to get the attributes from 
        save : OPTIONAL : do you want to save it in a JSON file.
    """
    attributes = element['attributes']
    el_name = element['attributes']['name']
    element_type = element['type']
    if save:
        name = f'{element_type} - {el_name} - attributes.json'
        name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
            '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
        with open(name, 'w') as f:
            f.write(_json.dumps(attributes, indent=4))
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
            copy_target = _deepcopy(target_elements[index[check_name]])
            copy_target_attr = copy_target['attributes']
            copy_target_attr[key] = base_setting
            new_list.append(copy_target_attr)
    return new_list


def copySettings(data: object)->object:
    """
    copy the settings from an element and returns an object with required information
    Returns an object with the information required to create copy this element.  
    Arguments:
        data : REQUIRED : Single Element Object that you want to copy (not a list of elements)
    """
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
    elif data['type'] == 'rules':
        obj['name'] = data['attributes']['name']
    elif data['type'] == 'rule_components':
        obj['name'] = data['attributes']['name']
        obj['order'] = data['attributes']['order']
        obj['descriptor'] = data['attributes']['delegate_descriptor_id']
        obj['negate'] = data['attributes']['negate']
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
        self.rules = _pd.DataFrame()
        self.extensions = _pd.DataFrame()

    def setBaseExtensions(self, base_property_extensions: object, property_name: str):
        """
        Pass all the extensions from the base property to start building the table. 
        Arguments: 
            base_property : REQUIRED : list of all extensions retrieve through getExtensions method
            property_name : REQUIRED : name of your base property.
        """
        df = _pd.DataFrame(extensionsInfo(base_property_extensions)).T
        df = _pd.DataFrame(df['id'])
        df.columns = [property_name]
        self.extensions = df

    def extendExtensions(self, new_property_extensions: object, new_prop_name: str)-> None:
        """
        Add the extensions id from a target property.
        Arguments: 
            new_property_extensions: REQUIRED : the extension list from your target property. 
            new_prop_name : REQUIRED : target property name. 
        """
        df = _pd.DataFrame(extensionsInfo(new_property_extensions)).T
        df = _pd.DataFrame(df['id'])
        self.extensions[new_prop_name] = df
        return self.extensions

    def setBaseRules(self, base_property_rules: object, property_name: str):
        """
        Pass all the rules from the base property to start building the table. 
        Arguments: 
            base_property : REQUIRED : list of all rules retrieve through getExtensions method
            property_name : REQUIRED : name of your base property.
        """
        df = _pd.DataFrame(rulesInfo(base_property_rules)).T
        df = _pd.DataFrame(df['id'])
        df.columns = [property_name]
        self.rules = df

    def extendRules(self, new_property_rules: object, new_prop_name: str):
        """
        Add the extensions id from a target property.
        Arguments: 
            new_property_rules: REQUIRED : the rules list from your target property. 
            new_prop_name : REQUIRED : target property name. 
        """
        df = _pd.DataFrame(rulesInfo(new_property_rules)).T
        df = _pd.DataFrame(df['id'])
        self.rules[new_prop_name] = df
        return self.rules

    def translate(self, target_property: str, data_element: dict = None, rule_component: dict = None)->dict:
        """
        change the id from the base element to the new property. 
        Pre checked should be done beforehands (updating Extension & Rules elements)
        Arguments: 
            target_property : REQUIRED : property that is targeted to translate the element to
            data_element : OPTIONAL : if the elements passed are data elements
            rule_component : OPTIONAL : if the elements passed are rule components
        """
        if self.extensions.empty == True:
            raise AttributeError(
                "You didn't import the base extensions or the target extensions")
        if data_element is not None:
            new_de = _deepcopy(data_element)
            base_id = new_de['extension']['id']
            row = self.extensions[self.extensions.iloc[:, 0]
                                  == base_id].index.values[0]
            new_value = self.extensions.loc[row, target_property]
            new_de['extension']['id'] = new_value
            return new_de
        elif rule_component is not None:
            if self.rules.empty == True:
                print(
                    "The rules have not been imported, the rule id needs to be changed")
            new_rc = _deepcopy(rule_component)
            base_id = new_rc['extension']['id']
            row = self.extensions[self.extensions.eq(
                base_id).any(1)].index.values[0]
            new_value = self.extensions.loc[row, target_property]
            new_rc['extension']['id'] = new_value
            if self.rules.empty == False:
                new_rc['rule_setting'] = {
                    'data': [{
                        'id': self.rules.loc[rule_component['rule_name'], target_property],
                        'type':'rules'}
                    ]}
            else:
                del new_rc['rules']
            return new_rc


def extractAnalyticsCode(rcSettings: str, save: bool = False, filename: str = None)->None:
    """
    Extract the custom code of the rule and save it in a file.
    Arguments:
        rcSettings: REQUIRED : it is the analytics rule component settings retrieved by the extractSettings method. 
        save : OPTIONAL : if you want to save the code as external js file. 
        filename : OPTIONAL : name of the file you want to use to save the code. 
    """
    json_data = _json.loads(rcSettings)
    if 'customSetup' in json_data.keys():
        json_code = json_data['customSetup']['source']
        if filename is None:
            filename = 'code'
        filename = filename.replace('/', '_').replace('|', '_')
        if save:
            with open(f'{filename}.js', 'w') as f:
                f.write(json_code)
        return json_code


class Library:

    def __init__(self, data: dict):
        self.id = data['id']
        self.name = data['attributes']['name']
        self.state = data['attributes']['state']
        self.build_required = data['attributes']['build_required']
        self.builds = data['relationships']['builds']['links']['related']
        self._DataElements = _endpoint + \
            '/libraries/'+data['id']+'/data_elements'
        self._Extensions = _endpoint+'/libraries/'+data['id']+'/extensions'
        self._Environment = _endpoint+'/libraries/'+data['id']+'/envrionment'
        self._Rules = _endpoint+'/libraries/'+data['id']+'/rules'
        self._Builds = _endpoint+'/libraries/'+data['id']+'/builds'
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
        # assign the list to its dict value
        self.relationships['data_elements'] = data
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

    def addDataElements(self, data_element_ids: list)->object:
        """
        Take a list of data elements id and attach them to the library. 
        Arguments:
            data_element_ids: REQUIRED : list of data elements id
        """
        if self.state != 'development':
            print('State is not development, cannot add relationships')
            return None
        obj = {'data': []}
        if type(data_element_ids) == str:
            data_element_ids = data_element_ids.split(' ')
        for ids in data_element_ids:
            obj['data'].append(
                {"id": ids, "type": "data_elements", "meta": {"action": "revise"}})
        url = _endpoint+'/libraries/'+self.id+'/relationships/data_elements'
        res = _postData(url, obj)
        return res

    def addRules(self, rules_ids: list)->object:
        """
        Take a list of rules id and attach them to the library. 
        Arguments:
            rules_ids: REQUIRED : list of rules id
        """
        if self.state != 'development':
            print('State is not development, cannot add relationships')
            return None
        obj = {'data': []}
        if type(rules_ids) == str:
            rules_ids = rules_ids.split(' ')
        for ids in rules_ids:
            obj['data'].append({"id": ids, "type": "rules",
                                "meta": {"action": "revise"}})
        url = _endpoint+'/libraries/'+self.id+'/relationships/rules'
        res = _postData(url, obj)
        return res

    def addExtensions(self, extensions_ids: list)->object:
        """
        Take a list of extension id and attach them to the library. 
        Arguments:
            extensions_ids: REQUIRED : list of extension id
        """
        if self.state != 'development':
            print('State is not development, cannot add relationships')
            return None
        obj = {'data': []}
        if type(extensions_ids) == str:
            extensions_ids = extensions_ids.split(' ')
        for ids in extensions_ids:
            obj['data'].append(
                {"id": ids, "type": "extensions", "meta": {"action": "revise"}})
        url = _endpoint+'/libraries/'+self.id+'/relationships/extensions'
        res = _postData(url, obj)
        return res

    def setEnvironments(self, environments_list: list, dev_name: str = None)->None:
        """
        Save the different environments ids available. 
        It is required to use the library class.
        Arguments : 
            environments_list : REQUIRED : list of environment retrieved by the getEnvironment method
            dev_name : OPTIONAL : Name of your dev environment. If not defined, will take the first dev environment.
        """
        for env in environments_list:
            if env['attributes']['stage'] == 'production':
                self._environments['production'] = env['id']
            elif env['attributes']['stage'] == 'staging':
                self._environments['staging'] = env['id']
            elif env['attributes']['stage'] == 'development':
                devs = self._environments.get('developments', {})
                devs[env['attributes']['name']] = env['id']
                self._environments['developments'] = devs
        if dev_name != None:
            self._dev_env = self._environments['developments'][dev_name]
        else:
            key1 = list(self._environments['developments'].keys())[0]
            self._dev_env = self._environments['developments'][key1]

    @_checkToken
    def _setEnvironment(self, obj: dict)->None:
        new_env = _requests.patch(_endpoint+'/libraries/'+self.id +
                                  '/relationships/environment', headers=_header, data=_json.dumps(obj))
        res = new_env.json()
        return res

    @_checkToken
    def _removeEnvironment(self)->None:
        """
        Remove environment
        """
        new_env = _requests.get(
            _endpoint+'/libraries/'+self.id+'/relationships/environment', headers=_header)
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
            obj = {
                "data": {
                    "id": env_id,
                    "type": "environments"
                }
            }
            self._removeEnvironment()
            status = self._setEnvironment(obj)
        elif self.state == 'submitted':
            env = 'staging'
            obj = {
                "data": {
                    "id": self._environments[env],
                    "type": "environments"
                }
            }
            self._removeEnvironment()
            status = self._setEnvironment(obj)
        elif self.state == 'approved':
            env = 'production'
            obj = {
                "data": {
                    "id": self._environments[env],
                    "type": "environments"
                }
            }
            self._removeEnvironment()
            status = self._setEnvironment(obj)
        if 'error' in status.keys():
            raise SystemExit('Issue setting environment')
        build = _requests.post(self._Builds, headers=_header)
        build_json = build.json()
        build_id = build_json['data']['id']
        build_status = build_json['data']['attributes']['status']
        while build_status == 'pending':
            print('pending...')
            _time.sleep(20)
            # return the json directly
            build = _getData(_endpoint+'/builds/'+str(build_id))
            build_status = build['data']['attributes']['status']
        if build['data']['attributes']['status'] == 'succeeded':
            self.build_required = False
            self.build_status = 'succeeded'
        else:
            self.build_required = True
            self.build_status = build['data']['attributes']['status']
        return build

    def transition(self, action: str = None, **kwargs)->object:
        """
        Move the library along the publishing funnel.
        If no action is provided, it would automatically go to the next state. 
        Arguments : 
            action : OPTIONAL : action to do on the library. Possible values: 
                - 'submit' : if state == development
                - 'approve' : if state == submitted
                - 'reject' : if state == submitted
        """
        if action == None:
            if self.state == 'development':
                action = 'submit'
            elif self.state == 'submitted':
                action = 'approve'
        obj = {"data": {
            "id": self.id,
            "type": "libraries",
            "meta": {
                "action": action
            }
        }
        }
        transition = _patchData(_endpoint+'/libraries/'+self.id, obj)
        data = transition
        self.state = data['data']['attributes']['state']
        self.build_required = data['data']['attributes']['build_required']
        return data
