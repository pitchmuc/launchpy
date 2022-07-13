from launchpy import config, connector
from concurrent import futures
import datetime
from .launchpy import saveFile
from .property import Property

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
    
    def updateProperty(self,propertyId:str=None,attributes:dict=None)->dict:
        """
        Update a property based on the information passed in the attributes.
        Arguments:
            propertyId : REQUIRED : The property ID to be updated
            attributes : REQUIRED : the dictionary containing the attributes to be updated
                more info here https://developer.adobelaunch.com/api/reference/1.0/properties/update/
        """
        if propertyId is None:
            raise ValueError('Require a property ID')
        if attributes is None:
            raise ValueError('require a dictionary with the data')
        attributes = {**attributes}
        obj = {"data": {
                "attributes": attributes,
                "id": propertyId,
                "type": "properties"
            }
        }
        path = f"/properties/{propertyId}"
        res:dict = self.connector.patchData(self.endpoint+path,data=obj)
        return res
    
    def deleteProperty(self,propertyId:str=None)->dict:
        """
        Delete a property based on the information passed in the attributes.
        Arguments:
            propertyId : REQUIRED : The property ID to be deleted
        """
        if propertyId is None:
            raise ValueError('Require a property ID')
        path = f"/properties/{propertyId}"
        res:dict = self.connector.deleteData(self.endpoint+path)
        return res

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
    
    def getEdgeConfigs(self)->dict:
        """
        Returns the edge configs, using a different endpoints.
        """
        url = "https://edge.adobe.io/configs/user/edge"
        res = self.connector.getData(url,headers=self.header)
        return res
    
    def getEdgeConfig(self,configId:str=None,env:str="prod")->dict:
        """
        Returns a specific config ID.
        Arguments:
            configId : REQUIRED : the configId to be retrived.
            env : OPTIONAL : default prod. Other env possible are "dev" or "stage"
        """
        if configId is None:
            raise ValueError("A configId is required")
        url = f"https://edge.adobe.io/configs/user/edge/{configId}/environments/{env}"
        res = self.connector.getData(url,headers=self.header)
        return res
    
    def updateEdgeConfig(self,configId:str=None,data:dict=None,env:str="prod")->dict:
        """
        Update the edge configuration with the value pass in data. (PUT method)
        Arguments:
            configId : REQUIRED : the configId to be updated.
            data : REQUIRED : Data to be passed for updating the configuration
            env : OPTIONAL : default prod. Other env possible are "dev" or "stage"
        """
        if configId is None:
            raise ValueError("A configId is required")
        if data is None:
            raise ValueError("Data needs to be passed for updating the config")
        url = f"https://edge.adobe.io/configs/user/edge/{configId}/environments/{env}"
        res = self.connector.putData(url,data=data,headers=self.header)
        return res

    
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