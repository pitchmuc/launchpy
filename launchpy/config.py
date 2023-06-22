
token = ""
config_object = {
    "org_id": "",
    "api_key": "",
    "pathToKey": "",
    "secret": "",
    "jwtTokenEndpoint" : "https://ims-na1.adobelogin.com/ims/exchange/jwt",
    "oauthTokenEndpointV2" : "https://ims-na1.adobelogin.com/ims/token/v2",
    "date_limit" : 0,
    "scope_admin" : "https://ims-na1.adobelogin.com/s/ent_reactor_admin_sdk",
    "scope_dev" : "https://ims-na1.adobelogin.com/s/ent_reactor_sdk",
    "official_scope" :  "",
    "scopes":""
}

header = {"Accept": "application/vnd.api+json;revision=1",
          "Content-Type": "application/vnd.api+json",
          "Authorization": "Bearer " + token,
          "x-gw-ims-org-id": config_object['org_id']
          }

endpoints = {
    "global": 'https://reactor.adobe.io',
    "profile": '/profile'
}
