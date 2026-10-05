import os
import json
import logging
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Union
from copy import deepcopy
# Non standard libraries
import requests
from launchpy import config, configs

class AdobeRequest:
    """
    Handle request to Audience Manager and taking care that the request have a valid token set each time.
    """

    def __init__(self,
                 config_objects: dict = config.config_objects,
                 headers: dict = config.headers,
                 org_name: str = None,
                 verbose: bool = False,
                 retry: int = 0
                ) -> None:
        """
        Set the connector to be used for handling request to AAM
        Arguments:
            config_objects : OPTIONAL : Require the importConfig file to have been used.
            headers : OPTIONAL : header of the config modules
            verbose : OPTIONAL : display comment on the request.
            retry : OPTIONAL : Number of additional attempts for GET responses
                that cannot be decoded as JSON. Default: 0.
                Rate-limited requests always retry and do not consume this budget.
        """
        if org_name is None:
            if len(config_objects) >= 1:
                self.config_key = list(config_objects.keys())[0]
                config_object = config_objects[self.config_key]
        else:
            if org_name in config_objects.keys():
                self.config_key = org_name
                config_object = config_objects[self.config_key]
            else:
                raise ValueError(f"Configuration for org_name '{org_name}' not found.")
        if config_object['org_id'] == '':
            raise Exception(
                'You have to upload the configuration file with importConfigFile method.')
        self.config = {self.config_key: deepcopy(config_object)}
        header = headers[self.config_key]
        self.header = deepcopy(header)
        self.retry = retry
        if self.config[self.config_key].get('token', '') == '' or time.time() > self.config[self.config_key].get('date_limit', 0):
            if 'scopes' in self.config[self.config_key].keys() and self.config[self.config_key].get('scopes',None) is not None:
                self.connectionType = 'oauthV2'
                token_and_expiry = self.get_oauth_token_and_expiry_for_config(config=self.config[self.config_key], verbose=verbose)
            else:
                raise ValueError("Invalid configuration: missing 'scopes' for OAuth V2 authentication.")
            token = token_and_expiry['token']
            expiry = token_and_expiry['expiry']
            self.token = deepcopy(token)
            self.config[self.config_key]['token'] = deepcopy(token)
            self.config[self.config_key]['date_limit'] = deepcopy(time.time() + expiry - 500)
            self.header.update({'Authorization': f'Bearer {token}'})
    
    def get_oauth_token_and_expiry_for_config(self,config:dict,verbose:bool=False,save:bool=False)->Dict[str,str]:
        """
        Retrieve the access token by using the OAuth information provided by the user
        during the import importConfigFile function.
        Arguments :
            config : REQUIRED : Configuration object.
            verbose : OPTIONAL : Default False. If set to True, print information.
            save : OPTIONAL : Default False. If set to True, save the token in the 'token.txt' file.
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

    def _checkingDate(self) -> None:
        """
        Checking if the token is still valid
        """
        now = time.time()
        if now > self.config[self.config_key]['date_limit']:
            if self.connectionType =='oauthV2':
                token_and_expiry = self.get_oauth_token_and_expiry_for_config(config=self.config[self.config_key], verbose=False)
            token = token_and_expiry['token']
            self.config[self.config_key]['token'] = deepcopy(token)
            self.config[self.config_key]['date_limit'] = deepcopy(time.time() + token_and_expiry['expiry'] - 500)
            self.header.update({'Authorization': f'Bearer {token}'})

    @staticmethod
    def _retry_delay(response: requests.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                seconds = int(retry_after)
                if seconds >= 0:
                    return float(seconds)
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(retry_after)
                    return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
                except (TypeError, ValueError, OverflowError):
                    pass
        return min(45 * 2 ** min(attempt, 3), 300)

    def _request(self, method: str, endpoint: str, params: dict | None = None,
                 data: Any = None, headers: dict | None = None, *,
                 retry: int | None = None, verbose: bool = False) -> Any:
        retries = self.retry if retry is None else retry
        if isinstance(retries, bool) or not isinstance(retries, int) or retries < 0:
            raise ValueError("retry must be a non-negative integer")
        request_kwargs: dict[str, Any] = {}
        if params is not None:
            request_kwargs["params"] = params
        if data is not None:
            request_kwargs["data"] = data if method == "get" else json.dumps(data)
        attempt = 0
        rate_limit_attempt = 0
        while True:
            self._checkingDate()
            response = getattr(requests, method)(
                endpoint, headers=self.header if headers is None else headers, **request_kwargs)
            if verbose:
                print(f"request URL : {response.request.url}")
                print(f"status_code : {response.status_code}")
            rate_limited = response.status_code == 429
            if not rate_limited:
                if method == "delete":
                    return response.status_code
                try:
                    result = response.json()
                except ValueError:
                    if method == "get" and attempt < retries:
                        time.sleep(30)
                        attempt += 1
                        continue
                    logging.getLogger(__name__).warning(
                        "%s request returned invalid JSON (HTTP %s)",
                        method.upper(), response.status_code)
                    return {"error": "Request Error"}
                rate_limited = isinstance(result, dict) and result.get("error_code") == "429050"
                if not rate_limited:
                    return result
            delay = self._retry_delay(response, rate_limit_attempt)
            if verbose:
                print(f"Rate limited; retrying in {delay:g} seconds")
            time.sleep(delay)
            rate_limit_attempt += 1

    def getData(self, endpoint: str, params: dict = None, data: dict = None, headers: dict = None, *args, **kwargs):
        """Get JSON data, always retrying rate limits independently of retry."""
        return self._request("get", endpoint, params, data, headers,
                             retry=kwargs.get("retry"), verbose=kwargs.get("verbose", False))

    def postData(self, endpoint: str, params: dict = None, data: dict = None, headers: dict = None, *args, **kwargs):
        """Post JSON data, always retrying rate limits."""
        return self._request("post", endpoint, params, data, headers,
                             retry=kwargs.get("retry"), verbose=kwargs.get("verbose", False))

    def patchData(self, endpoint: str, params: dict = None, data=None, headers: dict = None, *args, **kwargs):
        """Patch JSON data, always retrying rate limits."""
        return self._request("patch", endpoint, params, data, headers,
                             retry=kwargs.get("retry"), verbose=kwargs.get("verbose", False))

    def putData(self, endpoint: str, params: dict = None, data=None, headers: dict = None, *args, **kwargs):
        """Put JSON data, always retrying rate limits."""
        return self._request("put", endpoint, params, data, headers,
                             retry=kwargs.get("retry"), verbose=kwargs.get("verbose", False))

    def deleteData(self, endpoint: str, params: dict = None, data=None, headers: dict = None, *args, **kwargs):
        """Delete data and return the HTTP status, always retrying rate limits."""
        return self._request("delete", endpoint, params, data, headers,
                             retry=kwargs.get("retry"), verbose=kwargs.get("verbose", False))
