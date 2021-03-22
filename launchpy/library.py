import time
# Non standard libraries
from launchpy import config, connector

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