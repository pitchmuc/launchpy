# The Property class in launchpy

The launchpy property class helds most of the methods that are being display in the Launch API documentation ().\
The name of the class and instanciation method implies that these methods works on one property at a time.\
You can have several insances of property to apply changes to multiple properties.\
As usual more information can be found here : [datanalyst.info website](https://www.datanalyst.info/category/python/launch-api/?camp=referral~github~launchpy-doc)

The class is divided 4 types of methods:

* get methods
* create methods
* delete methods
* update methods

Here are shortlinks to the different methods explanation.

- [Get methods](#get-methods)
- [Create methods](#create-methods)
- [Delete methods](#delete-methods)
- [Update methods](#update-methods)
- [Helper methods](#helper-methods)

## Get methods

When you have your property instance created, the methods that you may want to call first are the get methods. They never take any argument, they don’t actually need any argument.
The only thing important to know is that you must run the getRules() method before the getRuleComponents() method.

The different get methods are the following :

* **getRessource** : Enable you to request a specific resource from Launch API via GET method.\
  Arguments:
  * res_url : REQUIRED : Resource URL to request
  * params : OPTIONAL : If you want to pass any parameter.

* **getEnvironments** : Retrieve the environment sets for this property

* **getHost** : Retrieve the hosts sets for this property

* **getExtensions** : retrieve the different information from url retrieve in the properties

* **getProfile** : Returns the information about a profile

* **getRules** : Return the list of the rules data.\
    On top, it fills the ruleComponents attribute with a dictionnary based on rule id and their rule name and the ruleComponent of each.

* **getRule** : Update the rule based on elements passed in attr_dict.\
  arguments: 
  * rule_id : REQUIRED : Rule ID
  * attr_dict : REQUIRED : dictionary that will be passed to Launch for update
  documentation : https://developer.adobelaunch.com/api/reference/1.0/rules/update/

* **getRuleComponents** : Returns a list of all the ruleComponents gathered in the ruleComponents attributes.
  You must have retrieved the rules before using this method (getRules()), otherwise, the method will also realize it and it will take longer, without saving the rules.\
  It will also enrich the RuleCompoment JSON data with the rule_name attached to it.\
  Possible kwargs:
  * rule_ids : list of rule ids to be used in order to retrieve ruleComponents
  * rule_names : list of rule names to be used in order to retrieve ruleComponents

* **getRuleComponent** : Return a ruleComponent information\
  Argument:
  * rc_id : REQUIRED : Rule Component ID

* **getDataElements** : Retrieve data elements of that property. Returns a list.

* **getDataElement** : Retrieve a specific data elements based on its ID.\
  Argument:
  * dataElementId : REQUIRED : a Data Element ID

* **getLibraries** : Retrieve libraries of the property.\
  Returns a list.\
  Arguments: 
  * state : OPTIONAL : state of the library.
    Possible values:
        - development
        - submitted
        - approved
        - rejected
        - published
  possible kwargs: 
    - published_at : it will be greater that this date ('2022-12-12T10:19:20.867Z')
    - name : it will be matching the name as equals
    - created_at : it will be greater that this date ('2022-12-12T10:19:20.867Z')
    - updated_at : it will be greater that this date ('2022-12-12T10:19:20.867Z')

* **getNotes** : Retrieve the note associated with the object pass to the method. Returns list.
  Arguments:
  * data: OPTIONAL : object that is associated with a Note (rule, data element, etc...)

* **getRuleRevision** : Retrieve the revisions of the specified Rule.
  Argument:
  * rule_id : REQUIRED : Rule ID

* **getRevisions** : Get the revisions of an element.
  Arguments:
  * element : REQUIRED : the element definition dictionary


## Create methods

The same way than you can get the elements, you can create different elements.\
You can create only one element at a time.\
The different elements that can be created :

* **createExtension** : Create an extension in your property. Your extension_id argument should be the latest one extension id available.\
  Arguments : 
  * extension_id : REQUIRED : ID for the extension to be created
  * settings : REQUIRED: string that define the setting to set in the extension. Usually, it can be empty.
  * delegate_descriptor_id : REQUIRED : delegate descriptor id (set in name)

* **createRule**: Create a rule by provided a rule name.\
  Arguments:
  * name : REQUIRED : name of your rule.

* **createRuleComponent** : Create a ruleComponent by provided a rule name and descriptor (minimum). It returns an object.\
  It takes additional information in order to link the ruleCompoment to a rule and with an Extension.\
  Arguments: 
  * name : REQUIRED : name of the rule component
  * descriptor : REQUIRED : delegate_descriptor_id for the rule component
  * extension_infos : REQUIRED : Extension used for that rule component (dictionary with "id" and "type")
    (can be found from translator)
  * rule_infos : REQUIRED : rule information link to that rule component (dictionary with "data", "id" and "type")
    (can be found from translator)
  * settings : OPTIONAL : settings for that rule component\
  possible kwargs:
  * order : the order of the rule component
  * negate : if the component is a negation
  * rule_order : the priority of the rule
  * timeout : the associated timeout with the rule component
  *  delay_next : if we should delay the next action

* **createDataElement** : Create Data Elements following the usage of required arguments.\
  Arguments: 
  * name : REQUIRED : name of the data element
  * descriptor : REQUIRED : delegate_descriptor_id for the data element
  * extension : REQUIRED : extension id used for the data element. (dictionary)
  * settings : OPTIONAL : settings for the data element\
  possible kwargs:\
    any attributes key you want to set.

* **createEnvironment** : Create an environment. Note that you cannot create more than 1 environment for Staging and Production stage.\
  Arguments: 
  * name : REQUIRED : name of your environment
  * host_id : REQUIRED : The host id that you would need to connect to the correct host. 
  * stage : OPTIONAL : Default Development. can be staging, production as well.\
documentation : https://developer.adobelaunch.com/api/reference/1.0/environments/create/

* **createHost** : Create a host in that property. By default Akamai host.\
  Arguments: 
  * name : REQUIRED : name of the host
  * host_type : OPTIONAL : type of host. 'akamai' or 'sftp'. Default 'akamai'
  If the host type is sftp, additional info can be enter as kwargs:
  * username : REQUIRED : str : username of the sftp
  * encrypted_private_key : REQUIRED : str : private key for the sftp as string
  * server : REQUIRED : str : server for the sftp.
  * path : REQUIRED : str : path of the sftp
  * port : REQUIRED : int : port to use\
documentation : https://developer.adobelaunch.com/api/reference/1.0/hosts/create/

* **createLibrary** : Create a library with the name provided. Returns an instance of the Library class or the response from the API (object).\
  Arguments:
  * name : REQUIRED : name of the library
  * return_class : OPTIONAL : Bool. will return a instance of the Library class if True.



the createLibrary can return an instance of the library class. More details [here](./library.md) about that.

## Delete methods

The delete methods delete the resources from the Launch instance.\
You can delete only one element at a time.\
The different delete methods are:

* **deleteEnvironment** : Delete the environment based on the id.  
  Argument: 
  * env_id : REQUIRED : Environment ID that needs to be deleted

* **deleteExtension** : Delete the extension that you want.  
  Arguments: 
  * extension_id : REQUIRED : Rule ID that needs to be deleted

* **deleteRule** : Delete the rule that you want. 
  Arguments: 
  * rule_id : REQUIRED : Rule ID that needs to be deleted

* **deleteRuleComponent** : Delete a rule component based on its ID.  
  Arguments: 
  * rc_id : REQUIRED : Rule Component ID that needs to be deleted

* **deleteDataElement** : Delete a data element.  
  Arguments: 
  * dataElement_id : REQUIRED : Data Element ID that needs to be deleted

## Update methods

As you can imagine the update methods enable you to update the different elements.\
Here is the list of the update methods available.

* **updateRule** : Update the rule based on elements passed in attr_dict.\
  arguments: 
  * rule_id : REQUIRED : Rule ID
  * attr_dict : REQUIRED : dictionary that will be passed to Launch for update\
  documentation : https://developer.adobelaunch.com/api/reference/1.0/rules/update/

* **updateRuleComponent** : Update the ruleComponents based on the information provided.\
  arguments: 
  * rc_id : REQUIRED : Rule Component ID
  * attr_dict : REQUIRED : dictionary that will be passed to Launch for update

* **updateDataElement** : Update the data element information based on the information provided.\
  arguments: 
  * dataElement_id : REQUIRED : Data Element ID
  * attr_dict : REQUIRED : dictionary that will be passed to Launch for update

* **updateEnvironment** : Update an environment. Note :only support name change.
  Arguments:
  * name : REQUIRED : name of your environment
  * env_id : REQUIRED : The environement id.\
  documentation : https://developer.adobelaunch.com/api/reference/1.0/environments/create/

* **updateExtension** : update the extension with the information provided in the argument.
  argument: 
  * extension_id : REQUIRED : the extension id
  * attr_dict : REQUIRED : dictionary that will be passed to Launch for update


## Helper methods

Here you can find methods that are here to help you work with the Launch property.\
They are not propertly defined by the Launch API, they have some business logic that I include to make my (and maybe your) like easier.

* **checkExtensionUpdate** : Returns a dictionary of extensions with their names, ids and if there is an update. 
  If there is an update available, the id returned is the latest id (to be used for installation).
  It can be re-use for installation and for checking for update. 
  Arguments:
  * platform : REQUIRED : if you need to look for extension on a specific platform (default web).
  * verbose: OPTIONAL : if set to True, will print the different name and id of the extensions checked.
  Output
    Dictionary example: 
    {'adobe-mcid':
        {'id':'XXXXX',
        'update':False
        }
    }

* **upgradeExtension** : Upgrade the extension with the new package id (EP...). \
  Returns the extension data.\
  Arguments:
  * extension_id : REQUIRED : Your internal ID for this extension in your property (EX....)
  * package_id : REQUIRED : new extension id for the extension (EP...)

* **searchRules** : Returns the rules searched through the different operator. One argument is required in order to return a result.\
  Arguments:
  * name : OPTIONAL : string of what is searched (used as "EQUALS")
  * name_contains : OPTIONAL : string of what is searched (used as "CONTAINS")
  * enabled : OPTIONAL : boolean if search for enabled rules or not
  * published : OPTIONAL : boolean if search for published rules or not
  * dirty : OPTIONAL : boolean if search for dirty rules or not

* **searchDataElements** : Returns the rules searched through the different operator. One argument is required in order to return a result.\
  Arguments: 
  * name : OPTIONAL : string of what is searched (used as "contains")
  * enabled : OPTIONAL : boolean if search for enabled rules or not
  * published : OPTIONAL : boolean if search for published rules or not
  * dirty : OPTIONAL : boolean if search for dirty rules or not

* **reviseExtension** : update the extension with the information provided in the argument.\
  argument: 
  * attr_dict : REQUIRED : attributes dictionary/object that will be passed to Launch for update

* **reviseRule** : Update the rule.\
  arguments: 
  * rule_id : REQUIRED : Rule ID
  * attr_dict : REQUIRED : dictionary that will be passed to Launch for update

* **reviseDataElement** : Update the data element information based on the information provided.\
  arguments: 
  * dataElement_id : REQUIRED : Data Element ID
  * attr_dict : REQUIRED : attributes dictionary/object that will be passed to Launch for update

* **getLatestPublishedVersion** : Find the latest published version of a component based on the list of revisions retrieved via getRevisions methods.\
  Arguments:
  * revisions : REQUIRED : list of revisions

* **updateCustomCode** : Update the custom code of a component (analytics action or core action or data element).\
  Arguments:
  * comp_id : REQUIRED : Component ID
  * customCode : REQUIRED : code to be updated in the component.2 options:
        javaScript file; example : "myCode.js" -> ".js" suffix is required.
        string; the code you want to write as a string.
  * encoding: OPTIONAL : encoding to read the JS file. Default (utf-8)

* **extensionsInfo** : Return a dictionary from the list provided from the extensions request.\
  Arguments: 
  * data : REQUIRED : list information returned by the getExtension method.

* **rulesInfo** : Return a dictionary from the list provided from the rules request.\
  Arguments : 
  * data : REQUIRED : list information returned by the getRules method.

* **ruleComponentInfo** : Return a dictionary from the list provided from the rules component request.\
  Arguments : 
  * data : REQUIRED : list information returned by the getRuleComponent method. 

* **dataElementInfo** : return information about data elements as dictionary.\
  Arguments : 
  * data : list return by the getDataElement value

* **extractSettings** : Extract the settings from your element. For your custom code, it will extract the javaScript. 
  Arguments: 
  * element : REQUIRED : element from which you would like to extract the setting from. 
  * analyticsCode : OPTIONAL : if set to True (default), extract the Analytics code when there is one and not global setting.
  * save : OPTIONAL : bool, if you want to save the setting in a JS or JSON file, set it to true. (default False)
  * encoding : OPTIONAL : encoding to be used for saving the file.

* **findRuleComponentSettingsFileName** : Return the filename use to save your custom code of your ruleComponent in a file using the extractSettings method.\
  Returns None when this is not a Custom code from CORE or Adobe Analytics. \
  Argument:
  * rc : REQUIRED : rule component object you want to retrieve the filename for.

* **extractAttributes** : Extract the attributes of your element. You can save it in a file as well.\
  Arguments:
  * element : REQUIRED : element you want to get the attributes from 
  * save : OPTIONAL : do you want to save it in a JSON file.
  * encoding : OPTIONAL : encoding to be used for saving the file.

* **duplicateAttributes** : Take a list of element and copy their settings (default) to another list of element.\
  returns a new list of the elements attributes.\
  Arguments:
  * base_elements : REQUIRED : list of elements you want to copy
  * target_elements : REQUIRED : list of elements you want to change\
  Possible kwargs : 
  * key : OPTIONAL : the type of element you want to copy paste (settings, name,enabled ,etc...)
  * default value for the key is "settings".
  * name_filter : OPTIONAL : Filter the elements to copy to only the ones containing the string in the filter.
  * example : name_filter='analytics' will only copy the element that has analytics in their name

* **copySettings** : copy the settings from an element and returns an object with required information
  Returns an object with the information required to create copy this element.  
  Arguments:
  * data : REQUIRED : Single Element Object that you want to copy (not a list of elements)

[main documentation](./main.md)
