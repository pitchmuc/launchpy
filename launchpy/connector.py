import os
import json
import time
from typing import Dict, Union
from copy import deepcopy
# Non standard libraries
import jwt
import requests
from launchpy import config, configs

class AdobeRequest:
    """
    Handle request to Audience Manager and taking care that the request have a valid token set each time.
    """

    def __init__(self,
                 config_object: dict = config.config_object,
                 header: dict = config.header,
                 verbose: bool = False,
                 retry: int = 0
                ) -> None:
        """
        Set the connector to be used for handling request to AAM
        Arguments:
            config_object : OPTIONAL : Require the importConfig file to have been used.
            header : OPTIONAL : header of the config modules
            verbose : OPTIONAL : display comment on the request.
            retry : OPTIONAL : If you wish to retry failed GET requests
        """
        if config_object['org_id'] == '':
            raise Exception(
                'You have to upload the configuration file with importConfigFile method.')
        self.config = deepcopy(config_object)
        self.header = header
        self.retry = retry
        if self.config['token'] == '' or time.time() > self.config['date_limit']:
            if 'scopes' in self.config.keys() and self.config.get('scopes',None) is not None:
                self.connectionType = 'oauthV2'
                token_and_expiry = self.get_oauth_token_and_expiry_for_config(config=self.config, verbose=verbose)
            elif self.config.get("private_key",None) is not None or self.config.get("pathToKey",None) is not None:
                self.connectionType = 'jwt'
                token_and_expiry = self.get_jwt_token_and_expiry_for_config(config=self.config, verbose=verbose)
            token = token_and_expiry['token']
            expiry = token_and_expiry['expiry']
            self.token = token
            self.config['token'] = token
            self.config['date_limit'] = time.time() + expiry - 500
            self.header.update({'Authorization': f'Bearer {token}'})

    def get_jwt_token_and_expiry_for_config(self,config: dict, verbose: bool = False, save: bool = False, *args, **kwargs) -> Dict[str, str]:
        """
        Retrieve the token by using the information provided by the user during the import importConfigFile function.
        Arguments :
            config : REQUIRED : config object to passs for information
            verbose : OPTIONAL : Default False. If set to True, print information.
            save : OPTIONAL : Default False. If set to True, save the toke in the .
        """
        private_key = configs.get_private_key_from_config(config)
        header_jwt = {
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded'
        }
        now_plus_24h = int(time.time()) + 24 * 60 * 60
        jwtPayload_default = {
        # Expiration set to 24 hours
        "exp": now_plus_24h,
        "iss": config['org_id'],
        "sub": config['tech_id'],
        config["official_scope"] : True,
        "aud": "https://ims-na1.adobelogin.com/c/"+config["client_id"]
        }
        jwtPayload_dev = {
            # Expiration set to 24 hours
            "exp": now_plus_24h,
            "iss": config['org_id'],
            "sub": config['tech_id'],
            config['scope_dev']: True,
            "aud": "https://ims-na1.adobelogin.com/c/"+config["client_id"]
        }
        encoded_jwt_admin = self._get_jwt(payload=jwtPayload_default, private_key=private_key)
        encoded_jwt_dev = self._get_jwt(payload=jwtPayload_dev, private_key=private_key)
        payload_admin = {
            'client_id': config['client_id'],
            'client_secret': config['secret'],
            'jwt_token': encoded_jwt_admin
        }
        payload_dev = {
            'client_id': config['client_id'],
            'client_secret': config['secret'],
            'jwt_token': encoded_jwt_dev
        }
        response = requests.post(config['jwtTokenEndpoint'], headers=header_jwt, data=payload_admin)
        json_response = response.json()
        if 'error' in json_response.keys():
            if json_response['error'] == "invalid_scope":
                try:
                    response = requests.post(config['jwtTokenEndpoint'], headers=header_jwt, data=payload_dev)
                    json_response = response.json()
                except Exception as e:
                    print(json.dumps(json_response, indent=4))
                    raise Exception(e)
        try:
            token = json_response['access_token']
        except KeyError:
            print('Issue retrieving token')
            print(json_response)
        expiry = json_response['expires_in'] / 1000
        if save:
            with open('token.txt', 'w') as f:
                f.write(token)
            print(f'token has been saved here: {os.getcwd()}{os.sep}token.txt')
        if verbose:
            print('token valid till : ' + time.ctime(time.time() + expiry / 1000))
        return {'token': token, 'expiry': expiry}
    
    def get_oauth_token_and_expiry_for_config(self,config:dict,verbose:bool=False,save:bool=False)->Dict[str,str]:
        """
        Retrieve the access token by using the OAuth information provided by the user
        during the import importConfigFile function.
        Arguments :
            config : REQUIRED : Configuration object.
            verbose : OPTIONAL : Default False. If set to True, print information.
            save : OPTIONAL : Default False. If set to True, save the toke in the .
        """
        if config is None:
            raise ValueError("config dictionary is required")
        oauth_payload = {
            "grant_type": "client_credentials",
            "client_id": config["client_id"],
            "client_secret": config["secret"],
            "scope": config["scopes"]
        }
        response = requests.post(
            config["oauthTokenEndpointV2"], data=oauth_payload)
        json_response = response.json()
        if 'access_token' in json_response.keys():
            token = json_response['access_token']
            expiry = json_response["expires_in"]
        else:
            return json.dumps(json_response,indent=2)
        if save:
            with open('token.txt', 'w') as f:
                f.write(token)
        if verbose:
            print('token valid till : ' + time.ctime(time.time() + expiry))
        return {'token': token, 'expiry': expiry}


    def _get_jwt(self,payload: dict, private_key: str) -> str:
        """
        Ensure that jwt enconding return the same type (str) as versions < 2.0.0 returned bytes and >2.0.0 return strings. 
        """
        token: Union[str, bytes] = jwt.encode(payload, private_key, algorithm='RS256')
        if isinstance(token, bytes):
            return token.decode('utf-8')
        return token

    def _checkingDate(self) -> None:
        """
        Checking if the token is still valid
        """
        now = time.time()
        if now > self.config['date_limit']:
            if self.connectionType =='oauthV2':
                token_and_expiry = self.get_oauth_token_and_expiry_for_config(config=self.config)
            elif self.connectionType == 'jwt':
                token_and_expiry = self.get_jwt_token_and_expiry_for_config(config=self.config)
            token = token_and_expiry['token']
            self.config['token'] = token
            self.config['date_limit'] = time.time() + token_and_expiry['expiry'] - 500
            self.header.update({'Authorization': f'Bearer {token}'})

    def getData(self, endpoint: str, params: dict = None, data: dict = None, headers: dict = None, *args, **kwargs):
        """
        Abstraction for getting data
        """
        internRetry = self.retry - kwargs.get("retry", 0)
        self._checkingDate()
        if headers is None:
            headers = self.header
        if params is None and data is None:
            res = requests.get(
                endpoint, headers=headers)
        elif params is not None and data is None:
            res = requests.get(
                endpoint, headers=headers, params=params)
        elif params is None and data is not None:
            res = requests.get(
                endpoint, headers=headers, data=data)
        elif params is not None and data is not None:
            res = requests.get(endpoint, headers=headers, params=params, data=data)
        if kwargs.get("verbose", False):
            print(f"request URL : {res.request.url}")
            print(f"statut_code : {res.status_code}")
        try:
            if res.status_code == 429:
                if kwargs.get("verbose", False):
                    print(f'Too many requests')
                time.sleep(45)
                res_json = self.getData(endpoint, params=params, data=data, headers=headers, retry=internRetry, **kwargs)
                return res_json
            res_json = res.json()
        except:
            res_json = {'error': 'Request Error'}
            while internRetry > 0:
                internRetry -= 1
                if kwargs.get("verbose", False):
                    print('Retry parameter activated')
                    print(f'{internRetry} retry left')
                if 'error' in res_json.keys():
                    time.sleep(30)
                    res_json = self.getData(endpoint, params=params, data=data, headers=headers, retry=internRetry, **kwargs)
                    return res_json
        return res_json

    def postData(self, endpoint: str, params: dict = None, data: dict = None, headers: dict = None, *args, **kwargs):
        """
        Abstraction for posting data
        """
        self._checkingDate()
        if headers is None:
            headers = self.header
        if params is None and data is None:
            res = requests.post(endpoint, headers=headers)
        elif params is not None and data is None:
            res = requests.post(endpoint, headers=headers, params=params)
        elif params is None and data is not None:
            res = requests.post(endpoint, headers=headers, data=json.dumps(data))
        elif params is not None and data is not None:
            res = requests.post(endpoint, headers=headers, params=params, data=json.dumps(data))
        try:
            res_json = res.json()
            if res.status_code == 429 or res_json.get('error_code', None) == "429050":
                time.sleep(45)
                res_json = self.postData(endpoint, params=params, data=data, headers=headers, **kwargs)
                return res_json
        except:
            if kwargs.get("verbose", False):
                print("status_code: {res.status_code}")
                print(res.text)
            res_json = {'error': 'Request Error'}
        return res_json

    def patchData(self, endpoint: str, params: dict = None, data=None, headers: dict = None, *args, **kwargs):
        """
        Abstraction for deleting data
        """
        self._checkingDate()
        if headers is None:
            headers = self.header
        if params is not None and data is None:
            res = requests.patch(endpoint, headers=headers, params=params)
        elif params is None and data is not None:
            res = requests.patch(endpoint, headers=headers, data=json.dumps(data))
        elif params is not None and data is not None:
            res = requests.patch(endpoint, headers=headers, params=params, data=json.dumps(data))
        try:
            status_code = res.json()
        except:
            if kwargs.get("verbose", False):
                print(res.text)
            status_code = {'error': 'Request Error'}
        return status_code

    def putData(self, endpoint: str, params: dict = None, data=None, headers: dict = None, *args, **kwargs):
        """
        Abstraction for deleting data
        """
        self._checkingDate()
        if headers is None:
            headers = self.header
        if params is not None and data is None:
            res = requests.put(endpoint, headers=headers, params=params)
        elif params is None and data is not None:
            res = requests.put(endpoint, headers=headers, data=json.dumps(data))
        elif params is not None and data is not None:
            res = requests.put(endpoint, headers=headers, params=params, data=json.dumps(data))
        try:
            status_code = res.json()
        except:
            if kwargs.get("verbose", False):
                print(res.text)
            status_code = {'error': 'Request Error'}
        return status_code

    def deleteData(self, endpoint: str, params: dict = None, headers: dict = None, *args, **kwargs):
        """
        Abstraction for deleting data
        """
        self._checkingDate()
        if headers is None:
            headers = self.header
        if params is None:
            res = requests.delete(endpoint, headers=headers)
        elif params is not None:
            res = requests.delete(endpoint, headers=headers, params=params)
        try:
            status_code = res.status_code
        except:
            status_code = {'error': 'Request Error'}
        return status_code
