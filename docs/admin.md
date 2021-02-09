# Admin class for launchpy

The Admin class is the first class that you would like to instantiate in order to retrieve useful information for further usage of the launchpy module.\
This class enables you to realize actions that are within administrative panel.

You can instantiate the Admin class once you have imported the information  

## getCompanyId

The most important method to use is the `getCompanyId` method that will return the company ID from your adobe IO connector.\
You can access your company ID by doing the following code:

```python
import launchpy as lp

lp.importConfigFile('myconfig.json')

admin = lp.Admin()
myCid = admin.getCompanyId()

## can be access via your variable
myCid
## or saved attribute
admin.COMPANY_ID

```

As you may have noted the result is automatically stored in the `COMPANY_ID` attribute of your instance.

### getProperties

This method takes one argument (the company id) and it will return a list of property that you will be able to feed the Property class.\
Following the previous example:

```python
myProperties = admin.getProperties(myCid)

## can be access via your variable
myProperties
## or saved attribute
admin.properties

```

### getAuditEvents

You can request Audit Events directly from the Admin instance.\
These events will give you information about what has happened on your different properties so it is property agnostic.\
The method takes those arguments:
* 

You can request the audit events by using the following method:



### createProperty

It takes several arguments:

* the company id
* a name
* the platform (by default it is web)
* return_class : a Boolean if you want to return an instance of the Property class.

It returns either the instance of the Property class or the object returned by the API.


### Extension Packages

When creating a new property, you may want to see the possible packages that you can install. There is a method available in the core components to access the available module.

* getExtensionsCatalogue: returns a list of the extension available for your company.
  Arguments:
  * availability : OPTIONAL : to filter for a specific type of extension. ("public" or "private")
  * name : OPTIONAL : to filter for a specific extension name (contains method)
  * platform : OPTIONAL : to filter for a specific platform (default "web", mobile possible)
  * save : OPTIONAL : save the results in a txt file (packages.txt). Default False.

You will need to use the name, the display name and 