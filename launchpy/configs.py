import json, os
from pathlib import Path
from typing import Optional
from launchpy.config import config_object, header

def find_path(path: str) -> Optional[Path]:
    """Checks if the file denoted by the specified `path` exists and returns the Path object
    for the file.

    If the file under the `path` does not exist and the path denotes an absolute path, tries
    to find the file by converting the absolute path to a relative path.

    If the file does not exist with either the absolute and the relative path, returns `None`.
    """
    if Path(path).exists():
        return Path(path)
    elif path.startswith('/') and Path('.' + path).exists():
        return Path('.' + path)
    elif path.startswith('\\') and Path('.' + path).exists():
        return Path('.' + path)
    else:
        return None


def createConfigFile(filename:str='config_launch',auth_type: str = "oauthV2", scope: str = "https://ims-na1.adobelogin.com/s/ent_reactor_admin_sdk", verbose: object = False)->None:
    """
    This function will create a 'config_launch_admin.json' file where you can store your access data. 
    Arguments:
        scope: OPTIONAL : if you have problem with scope during API connection, you may need to update this.
            scope="https://ims-na1.adobelogin.com/s/ent_reactor_admin_sdk"
            or 
            scope="https://ims-na1.adobelogin.com/s/ent_reactor_sdk"
        auth_type : OPTIONAL : The type of Oauth type you want to use for your config file. Possible value: "oauthV2"
    """
    json_data = {
        'org_id': '<orgID>',
        'client_id': "<client_id>",
        'secret': "<YourSecret>",
    }
    if auth_type == 'oauthV2':
        json_data['scopes'] = "<scopes>"
    if '.json' not in filename:
        filename = f"{filename}.json"
    with open(filename, 'w') as cf:
        cf.write(json.dumps(json_data, indent=4))
    if verbose:
        print(
            f" file created at this location : {os.getcwd()}{os.sep}{filename}")

def importConfigFile(path: str = None,auth_type:str=None) -> None:
    """Reads the file denoted by the supplied `path` and retrieves the configuration information
    from it.

    Arguments:
        path: REQUIRED : path to the configuration file. Can be either a fully-qualified or relative.
        auth_type : OPTIONAL : The type of Auth to be used by default. Detected if none is passed, OauthV2 takes precedence.
                        Possible values: "jwt" or "oauthV2"
    Example of path value.
    "config.json"
    "./config.json"
    "/my-folder/config.json"
    """
    if path is None:
        raise ValueError("a path must be provided")
    config_file_path: Optional[Path] = find_path(path)
    if config_file_path is None:
        raise FileNotFoundError(
            f"Unable to find the configuration file under path `{path}`."
        )
    with open(config_file_path, 'r') as file:
        provided_config = json.load(file)
        provided_keys = provided_config.keys()
        if 'api_key' in provided_keys:
            ## old naming for client_id
            client_id = provided_config['api_key']
        elif 'client_id' in provided_keys:
            client_id = provided_config['client_id']
        else:
            raise RuntimeError(f"Either an `api_key` or a `client_id` should be provided.")
        if auth_type is None:
            if 'scopes' in provided_keys:
                auth_type = 'oauthV2'
        args = {
            "org_id" : provided_config['org_id'],
            "secret" : provided_config['secret'],
            "client_id" : client_id,
            "scope" : provided_config.get('scope')
        }
        if auth_type == 'oauthV2':
            args["scopes"] = provided_config["scopes"].replace(' ','')
        configure(**args)


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

def configure(org_id: str = None,
              tech_id: str = None,
              secret: str = None,
              client_id: str = None,
              scopes : str= None,
              scope: str="https://ims-na1.adobelogin.com/s/ent_reactor_admin_sdk",
              **kwargs
              ):
    """Performs programmatic configuration of the API using provided values.
    Arguments:
        org_id : REQUIRED : Organization ID
        tech_id : REQUIRED : Technical Account ID
        secret : REQUIRED : secret generated for your connection
        client_id : REQUIRED : The client_id (old api_key) provided by the Adobe Project. 
        scopes : REQUIRED : The scopes required for the Oauth connection
        scope : OPTIONAL : Scope that is needed for JWT auth.
            Possible scope: https://www.adobe.io/authentication/auth-methods.html#!AdobeDocs/adobeio-auth/master/JWT/Scopes.md
    """
    if not org_id:
        raise ValueError("`org_id` must be specified in the configuration.")
    if not client_id:
        raise ValueError("`client_id` must be specified in the configuration.")
    if not scopes:
        raise ValueError("`scopes` must be specified in the configuration.")
    if not secret:
        raise ValueError("`secret` must be specified in the configuration.")
    config_object["org_id"] = org_id
    header["x-gw-ims-org-id"] = org_id
    config_object["client_id"] = client_id
    header["x-api-key"] = client_id
    config_object["tech_id"] = tech_id
    config_object["secret"] = secret
    config_object["official_scope"] = scope
    config_object["scopes"] = scopes
    # ensure the reset of the state by overwriting possible values from previous import.
    config_object["date_limit"] = 0
    config_object["token"] = ""
