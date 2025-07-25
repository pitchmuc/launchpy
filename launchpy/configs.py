import json, os
from pathlib import Path
from typing import Optional
from .config import config_object, header

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
        auth_type : OPTIONAL : The type of Oauth type you want to use for your config file. Possible value: "jwt" or "oauthV2"
    """
    json_data = {
        'org_id': '<orgID>',
        'client_id': "<client_id>",
        'secret': "<YourSecret>",
    }
    if auth_type == 'oauthV2':
        json_data['scopes'] = "<scopes>"
    elif auth_type == 'jwt':
        json_data["tech_id"] = "<something>@techacct.adobe.com"
        json_data["pathToKey"] = "<path/to/your/privatekey.key>"
        json_data['scope'] = scope
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
            elif 'tech_id' in provided_keys and "pathToKey" in provided_keys:
                auth_type = 'jwt'
        args = {
            "org_id" : provided_config['org_id'],
            "secret" : provided_config['secret'],
            "client_id" : client_id,
            "scope" : provided_config.get('scope')
        }
        if auth_type == 'oauthV2':
            args["scopes"] = provided_config["scopes"].replace(' ','')
        if auth_type == 'jwt':
            args["tech_id"] = provided_config["tech_id"]
            args["path_to_key"] = provided_config["pathToKey"]
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
              path_to_key: str=None,
              private_key: str = None,
              scopes : str= None,
              scope: str="https://ims-na1.adobelogin.com/s/ent_reactor_admin_sdk",
              ):
    """Performs programmatic configuration of the API using provided values.
    Arguments:
        org_id : REQUIRED : Organization ID
        tech_id : REQUIRED : Technical Account ID
        secret : REQUIRED : secret generated for your connection
        client_id : REQUIRED : The client_id (old api_key) provided by the JWT connection. 
        path_to_key : REQUIRED : If you have a file containing your private key value.
        private_key : REQUIRED : If you do not use a file but pass a variable directly.
        scope : OPTIONAL : Scope that is needed for JWT auth.
            Possible scope: https://www.adobe.io/authentication/auth-methods.html#!AdobeDocs/adobeio-auth/master/JWT/Scopes.md
    """
    if not org_id:
        raise ValueError("`org_id` must be specified in the configuration.")
    if not client_id:
        raise ValueError("`client_id` must be specified in the configuration.")
    if not tech_id and not scopes:
        raise ValueError("`tech_id` must be specified in the configuration.")
    if not secret:
        raise ValueError("`secret` must be specified in the configuration.")
    if not path_to_key and not private_key and not scopes:
        raise ValueError("`scopes` must be specified if Oauth setup.\n `pathToKey` or `private_key` must be specified in the configuration if JWT setup.")
    config_object["org_id"] = org_id
    header["x-gw-ims-org-id"] = org_id
    config_object["client_id"] = client_id
    header["x-api-key"] = client_id
    config_object["tech_id"] = tech_id
    config_object["secret"] = secret
    config_object["pathToKey"] = path_to_key
    config_object["private_key"] = private_key
    config_object["official_scope"] = scope
    config_object["scopes"] = scopes
    # ensure the reset of the state by overwriting possible values from previous import.
    config_object["date_limit"] = 0
    config_object["token"] = ""


def get_private_key_from_config(config: dict) -> str:
    """
    Returns the private key directly or read a file to return the private key.
    """
    private_key = config.get('private_key')
    if private_key is not None:
        return private_key
    private_key_path = find_path(config['pathToKey'])
    if private_key_path is None:
        raise FileNotFoundError(f'Unable to find the private key under path `{config["pathToKey"]}`.')
    with open(Path(private_key_path), 'r') as f:
        private_key = f.read()
    return private_key
