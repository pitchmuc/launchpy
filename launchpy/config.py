
token = ""
config_object = {
    "org_id": "",
    "api_key": "",
    "pathToKey": "",
    "secret": "",
    "tokenEndpoint" : "https://ims-na1.adobelogin.com/ims/exchange/jwt",
    "date_limit" : 0,
    "scope_admin" : "https://ims-na1.adobelogin.com/s/ent_reactor_admin_sdk",
    "scope_dev" : "https://ims-na1.adobelogin.com/s/ent_reactor_sdk",
    "official_scope" :  ""
}

header = {"Accept": "application/vnd.api+json;revision=1",
          "Content-Type": "application/vnd.api+json",
          "Authorization": "Bearer " + token,
          "X-Api-Key": config_object['api_key'],
          "X-Gw-Ims-Org-Id": config_object['org_id']
          }

endpoints = {
    "global": 'https://reactor.adobe.io',
    "profile": '/profile'
}
