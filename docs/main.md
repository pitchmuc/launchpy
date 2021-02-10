# launchpy documentation

This documentation will give you a view on the main different methods available on the launchpy module.
You can have more detail on the [datanalyst.info website](https://www.datanalyst.info/category/python/launch-api/?camp=referral~github~launchpy-doc)
The launchpy wrapper is hosting several classes that helps you to manage Adobe Launch instances through API calls.

Here are the main ones:

* [Core compoment](##1.-Core-library-methods) : directly available through the launchpy module.
* [Property](##2.-Property-class) : methods available for a Launch property.
* [Library](##3.-Library-class) : methods to publish the changes
* [Translator](##4.-Translator-class) : methods that helps you to copy paste elements from one property to another. This has become less useful as the UI is now reflecting this possibility.

if you want to have quick view on how to get started: [Get Started documentation](./getstarted.md)

## Core library methods

The launchpy module comes with some methods directly available from the core library of that module.

### createConfigFile

This will create a json file that you will need to file with the different element requested to generate the token (API Key, Secret, Technical Account, Path to your private key, scope).

### importConfigFile

This is taking the name of your config file (or path to it) in order to open it and read it.
This will set the variable required to generate the token.

You can access the element imported by looking at the config element in launchpy.

```python
import launchpy

launchpy.importConfigFile('myConfig.json')

## Look at the configuration
launchpy.config.config_object
```

### Configure method

The configure method enables you to configure the `config_object` directly from the python console with environment.\
This is useful when you do not wish to import a config file.\
The method can be called with the following parameters:

```python
import launchpy as lp

lp.configure(
  org_id = 'ED48F97C5922D95E@AdobeOrg',
  tech_id = '310E95EE8@techacct.adobe.com',
  secret = 'c6854473-9731-ebd7e31e155f',
  client_id = 'df4b231cea4c6e90d91b10052',
  path_to_key ='./config/private.key',
  scope ="https://ims-na1.adobelogin.com/s/ent_reactor_admin_sdk",
)
```

## 1. The Admin class

The Admin methods helps your retrieving vital information to use the API later, such as the companyId.\
You can also realize several property agnostics methods directly from this instance.\
The Admin methods can be found on the linked documentation [here](./admin.md)

## 2. Property class

The Property methods enable you to manipulate and retrieve the different element of the Launch instance.
The Property methods can be found on the linked documentation [here](./property.md)

## 3. Library class

The library methods helps you to publish the different changes that you have made on your Launch instances.
You need to instanciate a class for managing the different state of your library process (Approve / Build / Reject).
Documentation can be found [here](./library.md)

## 4. Translator class

The translator class is helping to translate extension or rule ID from one property to another.
However, due to the possibility of Launch to realize this copy paste directly in the UI now, this class is less relevant.
You can still access documentation of this class methods [here](./translator.md).

## 5. Core module helper / facilitators

The core has some facilitators methods that should help you along the way of using this API. Those facilitators are the real bonus of this wrapper and I hope you will understand how to use them.

### The Info methods

There are 4 different methods that are actually giving you around the same information about the different component of Launch:

* extensionsInfo
* rulesInfo
* dataElementInfo
* ruleComponentInfo

Those 4 methods are taking their different elements lists, the ones returned by the getRules, getExtensions, etc… methods and they return a dictionary of name and their attributes. You can create a pandas dataframe from that dictionary and that can help you creating a report for your different elements.

The different attributes retrieve by these functions are :

* name
* data of the creation
* date of the update
* id
* delegate descriptor id (except for rules)
* Publish state
* Working state (dirty)
* review status
* revision number
* version
* settings (except for rules)
* id
* extension id (for Extension)
* rule order (for rule component)

### CopySettings

This method allows you to copy settings from one element (Data Element, Extension, Rules, Rule Component) and returns the settings required to create the element again.
One of my main use case would be to copy paste element from one property to another. Thanks to that function, the required elements can be easily catch in a loop on all of your elements.

***Note*** : Think that you don’t need to recreate a Core Extension because it created by default.

### extractSettings

This function let’s you extract the settings of your elements. It doesn’t work on rules because rules settings are actually set in the rule component elements.
So you can actually extract the settings for the Extensions, the data elements and the rule components.
It takes 2 arguments:

* element : REQUIRED : element from which you would like to extract the setting from.
* analyticsCode : OPTIONAL : if set to True (default), extract the Analytics code when there is one and not global setting. If you want to have everything (code + settings, set it to False)
* save : OPTIONAL : bool, if you want to save the setting in a JS or JSON file, set it to true. (default False)

***Note*** : for the Custom Code of the Core elements (Data Elements, Rule Component Condition, Rule Component Event, Rule Component Action) it will retrieve the code in a JS file.
For all of the other element type, it returns a JSON format of their settings.

### extractAttributes

The method Extract attributes will extract the overall attributes of your element (name, enabled or not, created at, published or not, etc…)
This method is quite interesting if you would like to change the one of the setting (it is a dictionary) and re-import it through an update method.
It takes 2 arguments:

* element : REQUIRED : element you want to get the attributes from
* save : OPTIONAL : bool, if you want to save the setting in a JS or JSON file, set it to true. (default False)

### duplicateAttributes

This method is copy pasting the setting of one element to another one. You need to provide the elements as a list (for the base element and the target elements).
However it can be a list of one element.
It will copy the base element setting and paste it to the target element. It can also do that for other attributes than settings. It is set through a kwargs.
It tales 2 arguments:

* base_elements : REQUIRED : list of elements you want to copy
* target_elements : REQUIRED : list of elements you want to change

Possible kwargs :

* key : OPTIONAL : the type of element you want to copy paste (settings, name,enabled ,etc…). default value for the key are “settings”.
* name_filter : OPTIONAL : Filter the elements to copy to only the ones containing the string in the filter.
* example : name_filter=’analytics’ will only copy the element that has analytics in their name
