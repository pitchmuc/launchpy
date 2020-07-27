token = ""
config = {
    "org_id": "",
    "api_key": "",
    "pathToKey": "",
    "secret": "",
}
header = {"Accept": "application/vnd.api+json;revision=1",
          "Content-Type": "application/vnd.api+json",
          "Authorization": "Bearer " + token,
          "X-Api-Key": config['api_key'],
          "X-Gw-Ims-Org-Id": config['org_id']
          }

date_limit = 0
endpoints = {
    "global": 'https://reactor.adobe.io/',
    "companies": '/companies',
    "profile": '/profile',
    "properties": '/companies/{_company_id}/properties',  # string format
    "auditEvents": '/audit_events'
}
