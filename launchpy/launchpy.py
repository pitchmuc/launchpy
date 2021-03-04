import time
import json
from collections import defaultdict
from concurrent import futures
from copy import deepcopy
import os
import datetime
# Non standard libraries
import pandas as pd
from pathlib import Path
from launchpy import config, connector

# Set up default values


def saveFile(data:str,filename:str=None,type:str='txt',encoding:str='utf-8')->None:
    """
    Save file to your system.
    Arguments:
        data : REQUIRED : data to be saved
        filename : REQUIRED : name of the file or the path
        type : OPTIONAL : Can be "txt", "json", "js"
            json
    """
    if type=="txt":
        if '.txt' not in filename:
            filename = f"{filename}.txt"
        with open(Path(filename),'w',encoding=encoding) as f:
            f.write(data)
    elif type == "js":
        if '.js' not in filename:
            filename = f"{filename}.js"
        with open(Path(filename),'w',encoding=encoding) as f:
            f.write(data)
    elif type=="json":
        if '.json' not in filename:
            filename = f"{filename}.json"
        with open(Path(filename),'w',encoding=encoding) as f:
            f.write(json.dumps(data,indent=4))


def createConfigFile(scope: bool = False, verbose: object = False)->None:
    """
    This function will create a 'config_admin.json' file where you can store your access data. 
    Arguments:
        scope: OPTIONAL : if you have problem with scope during API connection, you may need to update this.
            scope=""
    """
    json_data = {
        'org_id': '<orgID>',
        'api_key': "<APIkey>",
        'tech_id': "<something>@techacct.adobe.com",
        'secret': "<YourSecret>",
        'pathToKey': '<path/to/your/privatekey.key>',
        'scope': "https://ims-na1.adobelogin.com/s/ent_reactor_admin_sdk"
    }
    with open('config_admin.json', 'w') as cf:
        cf.write(json.dumps(json_data, indent=4))
    if verbose:
        print(
            f" file created at this location : {os.getcwd()}{os.sep}config_admin.json")


class Admin:

    def __init__(self,config_object:dict=config.config_object,header:dict=config.header):
        """
        Instantiate the connector for the Login class
        """
        self.connector = connector.AdobeRequest(
            config_object=config_object, header=header)
        self.header = self.connector.header
        self.COMPANY_ID = {}
        self.properties = []
        self.endpoint = config.endpoints['global']
        

    def getCompanyId(self)->object:
        """
        Retrieve the company id for later call for the properties
        """
        path =  "/companies"
        companies = self.connector.getData(self.endpoint + path)
        companyID = companies['data'][0]['id']
        self.COMPANY_ID = companyID
        return companyID


    def getProperties(self,companyID: str)->list:
        """
        Retrieve the different properties available for a specific company.
        Arguments :
            companyID : REQUIRED : Company from where you want the properties
        """
        path = f"/companies/{companyID}/properties"
        properties = self.connector.getData(self.endpoint + path)
        data = properties['data']  # properties information for page 1
        # searching if page 1 is enough
        pagination = properties['meta']['pagination']
        # requesting all the pages
        if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:
            # calculate how many page to download
            pages_left = pagination['total_pages'] - pagination['current_page']
            workers = min(pages_left, 5)  # max 5 threads
            list_page_number = [{
                'page[number]': str(x)} for x in range(2, pages_left+2)]  # starting page 2
            urls = [self.endpoint + path for x in range(2, pages_left+2)]
            with futures.ThreadPoolExecutor(workers) as executor:
                res = executor.map(lambda x, y: self.connector.getData(
                    x, params=y), urls, list_page_number)
            res = list(res)
            append_data = [val for sublist in [data['data'] for data in res]
                        for val in sublist]  # flatten list of list
            data = data + append_data
        self.properties = data
        return data


    def getAuditEvents(self, page_size: int = 50, nb_page: int = 10, **kwargs)->list:
        """
        Retrieve the different events that happened inside a Launch property.
        Arguments :
            page_size : OPTIONAL : How many result per page. (default 50 - max 100)
            nb_page : OPTIONAL : How many page to return. (default 10)
            type_of : OPTIONAL : event to look for.
            **kwargs option
            data : data being passed from one recursion to another.
            verbose : if want to follow up the completion (bool)
            end_date : the past date you want to stop iterating. Date to be in datetime isoformat.
        """
        params = {'include': 'property', 'page[size]': '50'}
        params['page[number]'] = kwargs.get('page_nb', 1)
        if page_size is not None:
            params['page[size]'] = page_size
        if kwargs.get('type_of',None) is not None:
            params['type_of'] = kwargs.get('type_of')
        path = '/audit_events'
        events = self.connector.getData(self.endpoint + path, params=params)
        data = events['data']
        last_date = datetime.datetime.fromisoformat(
            data[-1]['attributes']['updated_at'][:-1])
        curr_page = events['meta']['pagination']['current_page']
        if kwargs.get('end_date', False):
            date_check = datetime.datetime.fromisoformat(kwargs.get('end_date'))
        else:
            date_check = last_date  # ensure true in that condition if no date given
        if kwargs.get('verbose', False):
            if curr_page % 10 == 0 or curr_page == 1:
                print(f'current page {curr_page}')
            print(f'% completion : {curr_page / nb_page*100}%')
        # checking if we need to pursue iteration related to update date.
        if curr_page == nb_page and last_date > date_check:
            nb_page += 1
        if curr_page == 100:
            print('You have reach maximum limit of the API (100 pages of 100 results)')
            return data
        else:
            if (curr_page < events['meta']['pagination']['total_pages'] and curr_page < nb_page):
                data += self.getAuditEvents(page_size=page_size, nb_page=nb_page,
                                    page_nb=curr_page+1, verbose=kwargs.get('verbose', False), end_date=kwargs.get('end_date', False))
        return data
    
    def createProperty(self,companyId: str, name: str, platform: str = 'web', sequential: bool=True ,return_class: bool = True, **kwargs)->dict:
        """
        Create a property with default information. Will return empty value as default value. 
        Returns a property instance.
        Arguments : 
            - companyId : REQUIRED : id of the company
            - name : REQUIRED : name of the property
            - platform : OPTIONAL : default 'web', can be 'app'
            - sequential : OPTIONAL : enable Sequential Rule Component
            - return_class : OPTIONAL : default True, will return an instance of property class. (default True)
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
        obj['data']['attributes']['platform'] = platform
        if platform == "mobile":
            obj['data']['attributes']['ssl_enabled'] = kwargs.get(
                'ssl_enabled', True)
            obj['data']['attributes']['privacy'] = kwargs.get('privacy', 'optedin')
        elif platform == "web":
            obj['data']['attributes']['domains'] = domains
        obj['data']['attributes']['development'] = development
        obj['data']['attributes']['undefined_vars_return_empty'] = undefined_vars_return_empty
        obj['data']['attributes']['rule_component_sequencing_enabled'] = sequential
        obj['data']['type'] = 'properties'
        path = f"/companies/{companyId}/properties"
        new_property = self.connector.postData(self.endpoint +path, data=obj)
        if return_class:
            property_class = Property(new_property['data'])
            return property_class
        else:
            return new_property['data']


    def getExtensionsCatalogue(self, availability: str = None, name: str = None, platform: str = "web", save: bool = False)->list:
        """
        Return a list of the Extension Catalogue available for your organization
        Arguments: 
            availability : OPTIONAL : to filter for a specific type of extension. ("public" or "private")
            name : OPTIONAL : to filter for a specific extension name (contains method)
            platform : OPTIONAL : to filter for a specific platform (default "web", mobile possible)
            save : OPTIONAL : save the results in a txt file (packages.txt). Default False.
        """
        path = config.endpoints['global']+'/extension_packages'
        params = {'page[size]': '100'}
        if availability is not None:
            params["filter[availability]"] = f"EQ {availability}"
        if name is not None:
            params['filter[display_name]'] = f"CONTAINS {name}"
        if platform is not None:
            params['filter[platform]'] = f"EQ {platform}"
        extensions = self.connector.getData(path, params=params)
        data = extensions['data']  # properties information for page 1
        # searching if page 1 is enough
        pagination = extensions['meta']['pagination']
        # requesting all the pages
        if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:
            # calculate how many page to download
            pages_left = pagination['total_pages'] - pagination['current_page']
            workers = min(pages_left, 5)  # max 5 threads
            params = [{
                'page[number]': str(x), **params} for x in range(2, pages_left+2)]  # starting page 2
            urls = [path for x in range(2, pages_left+2)]
            with futures.ThreadPoolExecutor(workers) as executor:
                res = executor.map(lambda x, y: self.connector.getData(
                    x, params=y), urls, params)
            res = list(res)
            append_data = [val for sublist in [data['data'] for data in res]
                        for val in sublist]  # flatten list of list
            data = data + append_data
        if save:
                saveFile(data,'packages.txt',type='txt')
        return data
    
    def getRessource(self,res_url: str = None, params: dict = None):
        """
        Enable you to request a specific resource from Launch API.
        Arguments:
            res_url : REQUIRED : Resource URL to request
            params : OPTIONAL : If you want to pass any parameter.
        """
        if res_url is None:
            raise Exception("You must provide a resource url")
        res = self.connector.getData(res_url, params=params)
        return res


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

    def __init__(self, data: object,config_object:dict=config.config_object,header:dict=config.header) -> None:
        """
        Instanciate the class with the object retrieved by getProperties.
        Arguments : 
          data : REQUIRED : Object that has been retrieved on getProperties. Single property. 
          config : OPTIONAL : Configuration required to generate JWT token
          header : OPTIONAL : Header used for the requests
        """
        self.connector = connector.AdobeRequest(
            config_object=config_object, header=header)
        self.endpoint = config.endpoints['global']
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
            self.id + '/rule_components'
        self._Host = 'https://reactor.adobe.io//properties/' + \
            data['id']+'/hosts'
        self._Note = 'https://reactor.adobe.io/notes/'
        self._Environments = data['links']['environments']
        self._Libraries = data['relationships']['libraries']['links']['related']
        self.ruleComponents = {}
        self.header = deepcopy(config.header)

    def __repr__(self)-> dict:
        return json.dumps(self.dict, indent=4)

    def __str__(self)-> str:
        return str(json.dumps(self.dict, indent=4))
    

    def _getExtensionPackage(self, ext_name: str, platform: str = "web", verbose: bool = False)->dict:
        """
        Retrieve extension id of the catalog from an extension name.
        It will be used later on to check for available updates. 
        Arguments: 
            ext_name : REQUIRED : name of the extension to look for.
            platform : REQUIRED : if you want to look for specific platform.
            verbose : OPTIONAL : set to true to print statement along the way (default False)
        """
        path = '/extension_packages'
        params = {'filter[name]': 'EQ '+str(ext_name), 'platform': platform}
        res_ext = self.connector.getData(
            self.endpoint+path, params=params)
        data = res_ext['data'][0]
        extension_id = data['id']
        if verbose:
            print('extension name : ' + str(data['attributes']['name']))
            print('extension id : ' + str(data['id']))
        return extension_id

    def getRessource(self,res_url: str = None, params: dict = None):
        """
        Enable you to request a specific resource from Launch API.
        Arguments:
            res_url : REQUIRED : Resource URL to request
            params : OPTIONAL : If you want to pass any parameter.
        """
        if res_url is None:
            raise Exception("You must provide a resource url")
        res = self.connector.getData(res_url, params=params)
        return res

    def getEnvironments(self)->object:
        """
        Retrieve the environment sets for this property
        """
        env = self.connector.getData(self._Environments)
        data = env['data']  # skip meta for now
        return data

    def getHost(self)->object:
        """
        Retrieve the hosts sets for this property
        """
        host = self.connector.getData(self._Host, header=self.header)
        data = host['data']  # skip meta for now
        return data

    def getExtensions(self)-> object:
        """
        retrieve the different information from url retrieve in the properties
        """
        extensions = self.connector.getData(self._Extensions)
        try:
            pagination = extensions['meta']['pagination']
            data = extensions['data']  # keep only information on extensions
            # requesting all the pages
            if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:
                # calculate how many page to download
                pages_left = pagination['total_pages'] - \
                    pagination['current_page']
                workers = min(pages_left, 5)  # max 5 threads
                list_page_number = [
                    {'page[number]': str(x)} for x in range(2, pages_left+2)]
                urls = [self._Extensions for x in range(2, pages_left+2)]
                with futures.ThreadPoolExecutor(workers) as executor:
                    res = executor.map(lambda x, y: self.connector.getData(
                        x, params=y, header=self.header), urls, list_page_number)
                res = list(res)
                append_data = [val for sublist in [data['data'] for data in res]
                               for val in sublist]  # flatten list of list
                data = data + append_data
        except:
            data = extensions
        return data

    def checkExtensionUpdate(self, platform: str = "web", verbose: bool = False):
        """
        Returns a dictionary of extensions with their names, ids and if there is an update. 
        If there is an update available, the id returned is the latest id (to be used for installation). 
        It can be re-use for installation and for checking for update. 
        Arguments:
            platform : REQUIRED : if you need to look for extension on a specific platform (default web).
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
            new_id = self._getExtensionPackage(
                name, platform=platform, verbose=verbose)
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
        path = f"/extensions/{extension_id}"
        res = self.connector.patchData(
            self.endpoint+path, data=data)
        return res

    def getRules(self)->object:
        """
        Return the list of the rules data.
        On top, it fills the ruleComponents attribute with a dictionnary based on rule id and their rule name and the ruleComponent of each.
        """
        rules = self.connector.getData(self._Rules)
        try:
            data = rules['data']  # skip meta for now
            pagination = rules['meta']['pagination']
            # requesting all the pages
            if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:
                # calculate how many page to download
                pages_left = pagination['total_pages'] - \
                    pagination['current_page']
                workers = min(pages_left, 5)  # max 5 threads
                list_page_number = [
                    {'page[number]': str(x)} for x in range(2, pages_left+2)]
                urls = [self._Rules for x in range(2, pages_left+2)]
                headers = [self.header for x in range(2, pages_left+2)]
                with futures.ThreadPoolExecutor(workers) as executor:
                    res = executor.map(lambda x, y, z: self.connector.getData(
                        x, params=y, header=z), urls, list_page_number, headers)
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
        filters = {}
        if name != None:
            filters['filter[name]=CONTAINS '] = f"CONTAINS {name}"
        if dirty != None:
            filters['filter[dirty]'] = f"EQ {str(dirty).lower()}"
        if enabled != None:
            filters['filter[enabled]'] = f"EQ {str(enabled).lower()}"
        if published != None:
            filters['filter[published]'] = f"EQ {str(published).lower()}"
        if 'created_at' in kwargs:
            pass  # documentation unclear on how to handle it
        rules = self.connector.getData(self._Rules, params=filters)
        data = rules['data']  # skip meta for now
        pagination = rules['meta']['pagination']
        # requesting all the pages
        if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:
            # calculate how many page to download
            pages_left = pagination['total_pages'] - pagination['current_page']
            workers = min(pages_left, 5)  # max 5 threads
            list_parameters = [{'&page[number]':
                                str(x), **filters} for x in range(2, pages_left+2)]
            urls = [self._Rules for x in range(2, pages_left+2)]
            with futures.ThreadPoolExecutor(workers) as executor:
                res = executor.map(lambda x, y: self.connector.getData(
                    x, params=y, header=self.header), urls, list_parameters)
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

    def getRuleComponents(self, **kwargs)->dict:
        """
        Returns a list of all the ruleComponents gathered in the ruleComponents attributes.
        You must have retrieved the rules before using this method (getRules()), otherwise, the method will also realize it and it will take longer, without saving the rules.
        It will also enrich the RuleCompoment JSON data with the rule_name attached to it.
        Possible kwargs:
            rule_ids : list of rule ids to be used in order to retrieve ruleComponents
            rule_names : list of rule names to be used in order to retrieve ruleComponents
        """
        ruleComponents = self.ruleComponents
        if len(ruleComponents) == 0:
            rules = self.getRules()
            ruleComponents = self.ruleComponents
        if kwargs.get('rule_ids', False):
            if type(kwargs["rule_ids"]) == str:
                kwargs["rule_ids"] = list(kwargs["rule_ids"])
            ruleComponents = {rule: {'name': ruleComponents[rule]['name'],
                                     'url': ruleComponents[rule]['url']} for rule in ruleComponents if rule in kwargs["rule_ids"]}
        if kwargs.get('rule_names', False):
            if type(kwargs["rule_names"]) == str:
                kwargs["rule_names"] = list(kwargs["rule_names"])
            ruleComponents = {rule: {'name': ruleComponents[rule]['name'],
                                     'url': ruleComponents[rule]['url']} for rule in ruleComponents if ruleComponents[rule]['name'] in kwargs["rule_names"]}
        list_urls = [ruleComponents[_id]['url'] for _id in ruleComponents]
        names = [ruleComponents[_id]['name'] for _id in ruleComponents]
        ids = list(ruleComponents.keys())
        headers = [self.header for nb in range(len(list_urls))]
        workers = min((len(list_urls), 5))

        def request_data(url, header, name, ids):
            rule_component = self.connector.getData(url)
            data = rule_component['data']
            for element in data:
                element['rule_name'] = name
                element['rule_id'] = ids
            return data
        with futures.ThreadPoolExecutor(workers) as executor:
            res = executor.map(lambda x, y, z, a: request_data(
                x, header=y, name=z, ids=a), list_urls, headers, names, ids)
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
        dataElements = self.connector.getData(self._DataElement)
        try:
            data = dataElements['data']  # data for page 1
            pagination = dataElements['meta']['pagination']
            # requesting all the pages
            if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:
                # calculate how many page to download
                pages_left = pagination['total_pages'] - \
                    pagination['current_page']
                workers = min(pages_left, 5)  # max 5 threads
                list_page_number = [{'page[number]':
                                     str(x)} for x in range(2, pages_left+2)]
                urls = [self._DataElement for x in range(2, pages_left+2)]
                with futures.ThreadPoolExecutor(workers) as executor:
                    res = executor.map(lambda x, y: self.connector.getData(
                        x, params=y, header=self.header), urls, list_page_number)
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
        filters = {}
        if name != None:
            filters['filter[name]'] = f"CONTAINS {name}"
        if dirty != None:
            filters['filter[dirty]'] = f"EQ {str(dirty).lower()}"
        if enabled != None:
            filters['filter[enabled]'] = f"EQ {str(enabled).lower()}"
        if published != None:
            filters['filter[published]'] = f"EQ {str(published).lower()}"
        if 'created_at' in kwargs:
            pass  # documentation unclear on how to handle it
        parameters = {**filters}
        dataElements = self.connector.getData(self._DataElement, params=parameters)
        data = dataElements['data']  # skip meta for now
        pagination = dataElements['meta']['pagination']
        # requesting all the pages
        if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:
            # calculate how many page to download
            pages_left = pagination['total_pages'] - pagination['current_page']
            workers = min(pages_left, 5)  # max 5 threads
            list_parameters = [{'page[number]': str(
                x), **parameters} for x in range(2, pages_left+2)]
            urls = [self._Rules for x in range(2, pages_left+2)]
            with futures.ThreadPoolExecutor(workers) as executor:
                res = executor.map(lambda x, y: self.connector.getData(
                    x, params=y, header=self.header), urls, list_parameters)
            res = list(res)
            append_data = [val for sublist in [data['data']
                                               for data in res] for val in sublist]
            data = data + append_data
        return data

    def getLibraries(self, state: str = None)->object:
        """
        Retrieve libraries of the property.
        Returns a list.
        Arguments: 
            state : OPTIONAL : state of the library.
            Possible values:
                - development
                - submitted
                - approved
                - rejected
                - published
        """
        params = {}
        if state is not None:
            if state not in ['development', "submitted", "approved", "rejected", "published"]:
                raise KeyError("State provided didn't match possible state.")
            params['filter[state]'] = f"EQ {state}"
        libs = self.connector.getData(self._Libraries, params=params)
        data = libs['data']  # dat for page 1
        pagination = libs['meta']['pagination']
        # requesting all the pages
        if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:
            # calculate how many page to download
            pages_left = pagination['total_pages'] - pagination['current_page']
            workers = min(pages_left, 5)  # max 5 threads
            list_page_number = [
                {'page[number]': str(x), **params} for x in range(2, pages_left+2)]
            urls = [self._Libraries for x in range(2, pages_left+2)]
            with futures.ThreadPoolExecutor(workers) as executor:
                res = executor.map(lambda x, y: self.connector.getData(
                    x, params=y, header=self.header), urls, list_page_number)
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
        notes = self.connector.getData(url)
        data = notes['data']  # data for page 1
        pagination = notes['meta']['pagination']
        # requesting all the pages
        if pagination['current_page'] != pagination['total_pages'] and pagination['total_pages'] != 0:
            # calculate how many page to download
            pages_left = pagination['total_pages'] - pagination['current_page']
            workers = min(pages_left, 5)  # max 5 threads
            list_page_number = [
                {'page[number]': str(x)} for x in range(2, pages_left+2)]
            urls = [url for x in range(2, pages_left+2)]
            with futures.ThreadPoolExecutor(workers) as executor:
                res = executor.map(lambda x, y: self.connector.getData(
                    x, params=y, header=self.header), urls, list_page_number)
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
            settings : REQUIRED: string that define the setting to set in the extension. Usually, it can be empty.
            delegate_descriptor_id : REQUIRED : delegate descriptor id (set in name)
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
        extensions = self.connector.postData(self._Extensions, data=obj)
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
        rules = self.connector.postData(self._Rules, data=obj, header=self.header)
        try:
            data = rules['data']
            self.ruleComponents[data['id']] = {'name': data['attributes']['name'],
                                               'url': data['links']['rule_components']}
        except:
            data = rules
        return data

    def createRuleComponents(self, name: str, settings: str = None, descriptor: str = None, extension_infos: dict = None, rule_infos: dict = None, **kwargs)->object:
        """
        Create a ruleComponent by provided a rule name and descriptor (minimum). It returns an object.
        It takes additional information in order to link the ruleCompoment to a rule and with an Extension.
        Arguments: 
            name : REQUIRED : name of the rule component
            descriptor : REQUIRED : delegate_descriptor_id for the rule component
            extension_infos : REQUIRED : Extension used for that rule component (dictionary with "id" and "type")
            (can be found from translator)
            rule_infos : REQUIRED : rule information link to that rule component (dictionary with "data", "id" and "type")
            (can be found from translator)
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
                        "data": extension_infos
                    },
                    "rules": rule_infos
                },
                "type": "rule_components"
            }
        }
        if settings is not None:
            obj['data']['attributes']['settings'] = settings
        if 'order' in kwargs:
            obj['data']['attributes']['order'] = kwargs.get('order')
        rc = self.connector.postData(self._RuleComponents, data=obj, header=self.header)
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
        dataElements = self.connector.postData(self._DataElement, data=obj, header=self.header)
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
        env = self.connector.postData(self._Environments, data=obj, header=self.header)
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
        host = self.connector.postData(self._Host, data=obj, header=self.header)
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
        if name is None:
            raise Exception("Require a name")
        obj = {
            "data": {
                "attributes": {
                    "name": name
                },
                "type": "libraries"
            }
        }
        lib = self.connector.postData(self._Libraries, data=obj, header=self.header)
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
        path = f'/extensions/{extension_id}'
        extensions = self.connector.patchData(
            config.endpoints['global']+path, obj, header=self.header)
        data = extensions['data']
        return data

    def reviseRules(self, rule_id: str)->object:
        """
        Update the rule.
        arguments: 
            rule_id : REQUIRED : Rule ID
            attr_dict : REQUIRED : dictionary that will be passed to Launch for update
        """
        if rule_id is None:
            raise Exception("A rule ID is required")
        obj = {
            "data": {
                "meta": {
                    "action": "revise"
                },
                "id": rule_id,
                "type": "rules"
            }
        }
        path = f"/rules/{rule_id}"
        rules = self.connector.patchData(
            config.endpoints['global']+path, obj, header=self.header)
        data = rules
        return data
    
    def getRuleRevision(self,rule_id:str)->dict:
        """
        Retrieve the revisions of the specified Rule.
        Argument:
            rule_id : REQUIRED : Rule ID
        """
        if rule_id is None:
            raise Exception("A rule ID is required")
        path = f"/rules/{rule_id}/revisions"
        revisions = self.connector.getData(config.endpoints['global']+path,header=self.header)
        return revisions


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
        dataElements = self.connector.patchData(
            config.endpoints['global']+'/data_elements/'+dataElement_id, obj, header=self.header)
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
        rules = self.connector.patchData(
            config.endpoints['global']+'/rules/'+rule_id, obj, header=self.header)
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
        rc = self.connector.patchData(
            config.endpoints['global']+'/rule_components/'+rc_id, obj, header=self.header)
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
        dataElements = self.connector.patchData(
            config.endpoints['global']+'/data_elements/'+dataElement_id, obj, header=self.header)
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
        env = self.connector.patchData(
            config.endpoints['global']+'/environments/'+env_id, obj, header=self.header)
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
        extensions = self.connector.patchData(
            config.endpoints['global']+'/extensions/'+extension_id, obj, header=self.header)
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
        data = self.connector.deleteData(
            'https://reactor.adobe.io/extensions/'+extension_id, header=self.header)
        return data

    def deleteRule(self, rule_id: str)->str:
        """
        Delete the rule that you want. 
        Arguments: 
            rule_id : REQUIRED : Rule ID that needs to be deleted
        """
        data = self.connector.deleteData('https://reactor.adobe.io/rules/' +
                           rule_id, header=self.header)
        return data

    def deleteDataElement(self, dataElement_id: str)->str:
        """
        Delete a data element.  
        Arguments: 
            dataElement_id : REQUIRED : Data Element ID that needs to be deleted
        """
        data = self.connector.deleteData(
            'https://reactor.adobe.io/data_elements/'+dataElement_id, header=self.header)
        return data

    def deleteRuleComponent(self, rc_id: str)->str:
        """
        Delete the rule component that you have selected.  
        Arguments: 
            rc_id : REQUIRED : Rule Component ID that needs to be deleted
        """
        data = self.connector.deleteData(
            'https://reactor.adobe.io/rule_components/'+rc_id, header=self.header)
        return data

    def deleteEnvironments(self, env_id: str)->str:
        """
        Delete the environment based on the id.  
        Arguments: 
            env_id : REQUIRED : Environment ID that needs to be deleted
        """
        data = self.connector.deleteData(
            'https://reactor.adobe.io/environments/'+env_id, header=self.header)
        return data

    # Not supported for the moment
    # def extractAnalyticsConfig(self)->object:
    #     """
    #     Extract the analytics configuration that has been done in the Analytics Extensions and Rules.
    #     Return a dictionary of the different element in a dataframe
    #     """
    #     dict_eVars = defaultdict(list)
    #     dict_props = defaultdict(list)
    #     dict_events = defaultdict(list)
    #     dict_value_eVars = defaultdict(list)
    #     dict_value_props = defaultdict(list)
    #     p_rules = self.getRules()
    #     p_ext = self.getExtensions()
    #     p_rcs = self.getRuleComponents()
    #     analytics = [ext for ext in p_ext if ext['attributes']
    #                  ['name'] == 'adobe-analytics'][0]
    #     analytics_rcs = [rc for rc in p_rcs if rc['attributes']['delegate_descriptor_id'].find(
    #         'adobe-analytics::actions::set-variables') - 1]

    #     def searchSetupAnalytics(element: object, verbose: bool = False):
    #         """
    #         fills the different dictionaries with where informations are held.
    #         """
    #         if element['type'] == "rule_components":
    #             name = element['rule_name']
    #         elif element['type'] == "extensions":
    #             name = 'Analytics Extension'
    #         settings = json.loads(element['attributes']['settings'])
    #         if 'trackerProperties' in settings.keys():
    #             tracker_properties = settings['trackerProperties']
    #         else:
    #             tracker_properties = {}
    #         if verbose:
    #             print(name)
    #         if len(tracker_properties) > 0:
    #             if 'eVars' in tracker_properties.keys():
    #                 for v in tracker_properties['eVars']:
    #                     dict_eVars[v['name']].append(f'{name} - Interface')
    #                     dict_value_eVars[v['name']].append(v['value'])
    #             if 'props' in tracker_properties.keys():
    #                 for p in tracker_properties['props']:
    #                     dict_props[p['name']].append(f'{name} - Interface')
    #                     dict_value_props[p['name']].append(p['value'])
    #             if 'events' in tracker_properties.keys():
    #                 for e in tracker_properties['events']:
    #                     dict_events[e['name']].append(f'{name} - Interface')
    #         if 'customSetup' in settings.keys():
    #             code = settings['customSetup']['source']
    #             if len(code) > 0:
    #                 matchevents = re.findall('(event[0-9]+)', code)
    #                 matcheVars = re.findall('(eVar[0-9]+)\s*=', code)
    #                 matchprops = re.findall('(prop[0-9]+?)\s*=', code)
    #                 if matcheVars is not None:
    #                     for v in set(matcheVars):
    #                         value = f'{name} - Custom Code'
    #                         if value not in dict_eVars[v]:
    #                             dict_eVars[v].append(f'{name} - Custom Code')
    #                 if matchprops is not None:
    #                     for p in set(matchprops):
    #                         value = f'{name} - Custom Code'
    #                         if value not in dict_props[p]:
    #                             dict_props[p].append(f'{name} - Custom Code')
    #                 if matchevents is not None:
    #                     for e in set(matchevents):
    #                         value = f'{name} - Custom Code'
    #                         if value not in dict_events[e]:
    #                             dict_events[e].append(f'{name} - Custom Code')
    #     searchSetupAnalytics(analytics)
    #     for rc in analytics_rcs:
    #         searchSetupAnalytics(rc)
    #     df_eVars = pd.DataFrame(
    #         dict([(k, pd.Series(v)) for k, v in dict_eVars.items()])).T.fillna('')
    #     df_eVars.columns = ['location ' +
    #                         str(i) for i in range(1, len(df_eVars.columns)+1)]
    #     df_props = pd.DataFrame(
    #         dict([(k, pd.Series(v)) for k, v in dict_props.items()])).T.fillna('')
    #     df_props.columns = ['location ' +
    #                         str(i) for i in range(1, len(df_props.columns)+1)]
    #     df_events = pd.DataFrame(
    #         dict([(k, pd.Series(v)) for k, v in dict_events.items()])).T.fillna('')
    #     df_events.columns = ['location ' +
    #                          str(i) for i in range(1, len(df_events.columns)+1)]
    #     data = {'eVars': df_eVars, 'props': df_props, 'events': df_events}
    #     return data





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


def extractSettings(element: dict, analyticsCode:bool=True, save: bool = False)->dict:
    """
    Extract the settings from your element. For your custom code, it will extract the javaScript. 
    Arguments: 
        element : REQUIRED : element from which you would like to extract the setting from. 
        analyticsCode : OPTIONAL : if set to True (default), extract the Analytics code when there is one and not global setting.
        save : OPTIONAL : bool, if you want to save the setting in a JS or JSON file, set it to true (UTF-16). (default False)
    """
    element_type = element['type']
    if element_type == 'data_elements':
        if element['attributes']['delegate_descriptor_id'] == 'core::dataElements::custom-code':
            settings = element['attributes']['settings']
            code = json.loads(settings)['source']
            if save is True:
                name = f'DE - {str(element["attributes"]["name"])}.js'
                name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                saveFile(code,name,type='js',encoding='utf-16')
            return code
        else:
            settings = element['attributes']['settings']
            if save:
                name = f'DE - {str(element["attributes"]["name"])} - settings.json'
                name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                saveFile(settings,name,type='json',encoding='utf-16')
            return settings
    elif element_type == 'extensions':
        if element['attributes']['delegate_descriptor_id'] == "adobe-analytics::extensionConfiguration::config":
            settings = json.loads(element['attributes']['settings'])
            if save is True:
                name = f'EXT - {str(element["attributes"]["name"])}.json'
                name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                saveFile(settings,name,type='json',encoding='utf-16')
            return settings
        else:
            settings = element['attributes']['settings']
            if save:
                name = f'EXT - {str(element["attributes"]["name"])} - settings.json'
                name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                saveFile(settings,name,type='json',encoding='utf-16')
            return settings
    elif element_type == 'rule_components':
        rule_name = element['rule_name']
        element_place = element['attributes']['delegate_descriptor_id'].split('::')[
            1]
        if element['attributes']['delegate_descriptor_id'] == "core::conditions::custom-code":
            settings = element['attributes']['settings']
            code = json.loads(settings)['source']
            if save is True:
                name = f'RC - {rule_name} - {element_place} - {element["attributes"]["name"]}.js'
                name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                saveFile(code,name,type='js',encoding='utf-16')
            return code
        elif element['attributes']['delegate_descriptor_id'] == "core::events::custom-code":
            settings = element['attributes']['settings']
            code = json.loads(settings)['source']
            if save is True:
                name = f'RC - {rule_name} - {element_place} - {element["attributes"]["name"]}.js'
                name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                saveFile(code,name,type='js',encoding='utf-16')
            return code
        elif element['attributes']['delegate_descriptor_id'] == "core::actions::custom-code":
            settings = element['attributes']['settings']
            code = json.loads(settings)['source']
            if save is True:
                name = f'RC - {rule_name} - {element_place} - {element["attributes"]["name"]}.js'
                name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                saveFile(code,name,type='js',encoding='utf-16')
            return code
        else:
            settings = element['attributes']['settings']
            if 'customSetup' in json.loads(settings).keys() and analyticsCode:
                if 'source' in json.loads(settings)['customSetup']:
                    code = json.loads(settings)['customSetup'].get('source','')
                    if save:
                        name = f'RC - {rule_name} - {element_place} - {element["attributes"]["name"]} - code settings.js'
                        name = name.replace('"', "'").replace('|', '').replace('>', '').replace('<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                        saveFile(code,name,type='js',encoding='utf-16')
                    return code

            if save:
                name = f'RC - {rule_name} - {element_place} - {element["attributes"]["name"]} - settings.json'
                name = name.replace('"', "'").replace('|', '').replace('>', '').replace(
                    '<', '').replace('/', '').replace('\\', '').replace(':', ';').replace('?', '')
                saveFile(settings,name,type='json',encoding='utf-16')
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
        saveFile(attributes,name,type='json',encoding='utf-16')
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
        self.rules = pd.DataFrame()
        self.extensions = pd.DataFrame()

    def setBaseExtensions(self, base_property_extensions: object, property_name: str):
        """
        Pass all the extensions from the base property to start building the table. 
        Arguments: 
            base_property : REQUIRED : list of all extensions retrieve through getExtensions method
            property_name : REQUIRED : name of your base property.
        """
        df = pd.DataFrame(extensionsInfo(base_property_extensions)).T
        df = pd.DataFrame(df['id'])
        df.columns = [property_name]
        self.extensions = df

    def extendExtensions(self, new_property_extensions: object, new_prop_name: str)-> None:
        """
        Add the extensions id from a target property.
        Arguments: 
            new_property_extensions: REQUIRED : the extension list from your target property. 
            new_prop_name : REQUIRED : target property name. 
        """
        df = pd.DataFrame(extensionsInfo(new_property_extensions)).T
        df = pd.DataFrame(df['id'])
        self.extensions[new_prop_name] = df
        return self.extensions

    def setBaseRules(self, base_property_rules: object, property_name: str):
        """
        Pass all the rules from the base property to start building the table. 
        Arguments: 
            base_property : REQUIRED : list of all rules retrieve through getExtensions method
            property_name : REQUIRED : name of your base property.
        """
        df = pd.DataFrame(rulesInfo(base_property_rules)).T
        df = pd.DataFrame(df['id'])
        df.columns = [property_name]
        self.rules = df

    def extendRules(self, new_property_rules: object, new_prop_name: str):
        """
        Add the extensions id from a target property.
        Arguments: 
            new_property_rules: REQUIRED : the rules list from your target property. 
            new_prop_name : REQUIRED : target property name. 
        """
        df = pd.DataFrame(rulesInfo(new_property_rules)).T
        df = pd.DataFrame(df['id'])
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
            new_de = deepcopy(data_element)
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
            new_rc = deepcopy(rule_component)
            base_id = new_rc['extension']['id']
            row = self.extensions[self.extensions.eq(
                base_id).any(1)].index.values[0]
            new_value = self.extensions.loc[row, target_property]
            # print(f"name : {rule_component['rule_name']}")
            # print(f"old_id : {base_id}")
            # print(f"new_id : {new_value}")
            new_rc['extension']['id'] = new_value
            if self.rules.empty == False:
                new_rc['rule_setting'] = {
                    'data': [{
                        'id': self.rules.loc[rule_component['rule_name'], target_property],
                        'type':'rules'}
                    ]}
                new_rc['rule_id'] = self.rules.loc[rule_component['rule_name'],
                                                   target_property]
            else:
                print(
                    "You didn't load the rules. Please use setExtensions and setRules, and extendExtensions and extendRules")
                del new_rc['rules']
            return new_rc


def extractAnalyticsCode(rcSettings: str, save: bool = False, filename: str = None)->None:
    """
    Extract the custom code of the rule and save it in a file.
    Arguments:
        rcSettings: REQUIRED : it is the analytics rule component settings retrieved by the extractSettings method. 
        save : OPTIONAL : if you want to save the code as external js file. UTF-16. Default False. 
        filename : OPTIONAL : name of the file you want to use to save the code. 
    """
    json_data = json.loads(rcSettings)
    if 'customSetup' in json_data.keys():
        json_code = json_data['customSetup']['source']
        if filename is None:
            filename = 'code'
        filename = filename.replace('/', '_').replace('|', '_')
        if save:
            saveFile(json_code,filename,type='js',encoding='utf-16')
        return json_code


class Library:

    def __init__(self, data: dict,config_object:dict=config.config_object,header:dict=config.header):
        self.connector = connector.AdobeRequest(
            config_object=config_object, header=header)
        self.header = self.connector.header
        self.endpoint = config.endpoints['global']
        self.id = data['id']
        self.name = data['attributes']['name']
        self.state = data['attributes']['state']
        self.build_required = data['attributes']['build_required']
        self.builds = data['relationships']['builds']['links']['related']
        self._DataElements = config.endpoints['global'] + \
            '/libraries/'+data['id']+'/data_elements'
        self._Extensions = config.endpoints['global'] + \
            '/libraries/'+data['id']+'/extensions'
        self._Environment = config.endpoints['global'] + \
            '/libraries/'+data['id']+'/envrionment'
        self._Rules = config.endpoints['global'] + \
            '/libraries/'+data['id']+'/rules'
        self._Builds = config.endpoints['global'] + \
            '/libraries/'+data['id']+'/builds'
        self.build_status = data['meta']['build_status']
        self.relationships = {}
        self._environments = {}
        self._dev_env = ''

    def getDataElements(self)->list:
        """
        retrieve the list of Data Elements attached to this library
        """
        dataElements = self.connector.getData(self._DataElements)
        data = dataElements
        # assign the list to its dict value
        self.relationships['data_elements'] = data
        return data

    def getExtensions(self)->list:
        """
        retrieve the list of Extensions attached to this library
        """
        extensions = self.connector.getData(self._Extensions)
        data = extensions
        self.relationships['extensions'] = data
        return data

    def getRules(self)->list:
        """
        retrieve the list of rules attached to this library
        """
        rules = self.connector.getData(self._Rules)
        data = rules
        self.relationships['rules'] = data
        return data

    def getFullLibrary(self)->dict:
        self.getDataElements()
        self.getRules()
        self.getExtensions()
        return self.relationships

    def addDataElements(self, data_element_ids: list)->dict:
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
            obj['data'].append({"id": ids,
            "type": "data_elements", "meta": {"action": "revise"}})
        url =  f'/libraries/{self.id}/relationships/data_elements'
        res = self.connector.postData(self.endpoint +url, data=obj)
        return res
    
    def updateDataElement(self,data_element_ids:list)->dict:
        """
        Update the data element inside the library. (PATCH)
        Arguments:
            data_element_ids: REQUIRED : list of data elements id
        """
        if self.state != 'development':
            print('State is not development, cannot update relationships')
            return None
        obj = {'data': []}
        if type(data_element_ids) == str:
            data_element_ids = data_element_ids.split(' ')
        for ids in data_element_ids:
            obj['data'].append({"id": ids,
            "type": "data_elements", "meta": {"action": "revise"}})
        url =  f'/libraries/{self.id}/relationships/data_elements'
        res = self.connector.patchData(self.endpoint +url, data=obj)
        return res


    def addRules(self, rules_ids: list)->dict:
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
        url = f'/libraries/{self.id}/relationships/rules'
        res = self.connector.postData(self.endpoint + url, data=obj)
        return res
    
    def updateRules(self,rules_ids:list)->dict:
        """
        Replace all existing rules with the ones posted.
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
        url = f'/libraries/{self.id}/relationships/rules'
        res = self.connector.patchData(self.endpoint + url, data=obj)
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
            obj['data'].append({"id": ids, "type": "extensions", 
                                "meta": {"action": "revise"}})
        url = f'/libraries/{self.id}/relationships/extensions'
        res = self.connector.postData(self.endpoint+url, data=obj)
        return res
    
    def updateExtensions(self, extensions_ids: list)->object:
        """
        Replace all existing extensions into the library. 
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
            obj['data'].append({"id": ids, "type": "extensions", 
                                "meta": {"action": "revise"}})
        url = f'/libraries/{self.id}/relationships/extensions'
        res = self.connector.patchData(self.endpoint+url, data=obj)
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

    def _setEnvironment(self, obj: dict,verbose:bool=False)->None:
        path = f'/libraries/{self.id}/relationships/environment'
        new_env = self.connector.patchData(self.endpoint+path, data=obj,verbose=verbose)
        res = new_env
        return res

    def _removeEnvironment(self)->None:
        """
        Remove environment
        """
        path = f'/libraries/{self.id}/relationships/environment'
        new_env = self.connector.getData(self.endpoint+path) 
        return new_env

    def build(self,verbose:bool=False)->dict:
        """
        Build the library. 
        Part of the code takes care of assigning the right environement before building the library.
        Returns the build when it is completed (succeed or not).
        It will check every 15 seconds for the build status, making sure it is not "pending".
        """
        if self.build_required == False and self.state != 'approved':
            return 'build is not required'
        status = ""
        if self.state == 'development':
            env_id = self._dev_env
            obj = {
                "data": {
                    "id": env_id,
                    "type": "environments"
                }
            }
            self._removeEnvironment()
            status = self._setEnvironment(obj,verbose=verbose)
        elif self.state == 'submitted':
            env = 'staging'
            obj = {
                "data": {
                    "id": self._environments[env],
                    "type": "environments"
                }
            }
            self._removeEnvironment()
            status = self._setEnvironment(obj,verbose=verbose)
        elif self.state == 'approved':
            env = 'production'
            obj = {
                "data": {
                    "id": self._environments[env],
                    "type": "environments"
                }
            }
            self._removeEnvironment()
            status = self._setEnvironment(obj,verbose=verbose)
        if 'error' in status.keys():
            raise SystemExit('Issue setting environment')
        build = self.connector.postData(self._Builds)
        build_id = build['data']['id']
        build_status = build['data']['attributes']['status']
        while build_status == 'pending':
            print('pending...')
            time.sleep(20)
            # return the json directly
            build = self.connector.getData(
                config.endpoints['global']+'/builds/'+str(build_id))
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
        path = f'/libraries/{self.id}'
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
        transition = self.connector.patchData(self.endpoint+path, data=obj)
        data = transition
        self.state = data['data']['attributes']['state']
        self.build_required = data['data']['attributes']['build_required']
        return data
