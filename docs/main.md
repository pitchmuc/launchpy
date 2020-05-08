# Pylaunch documentation

This documentation will give you a view on the main different methods available on the pylaunch module.
You can have more detail on the [datanalyst.info website](https://www.datanalyst.info/category/python/launch-api/?camp=referral~github~pylaunch-doc)
The pylaunch wrapper is hosting several classes that helps you to manage Adobe Launch instances through API calls.

Here are the main ones:

* [Core compoment](##1.-Core-library-methods) : directly available through the pylaunch module.
* [Property](##2.-Property-class) : methods available for a Launch property.
* [Library](##3.-Library-class) : methods to publish the changes
* [Translator](##4.-Translator-class) : methods that helps you to copy paste elements from one property to another. This has become less useful as the UI is not reflecting this possibility.

## 1. Core library methods

The pylaunch module comes with some methods directly available from the core library of that module.

### createConfigFile

This will create a json file that you will need to file with the different element requested to generate the token (API Key, Secret, Technical Account, Path to your private key).
Once you have set up this configuration, you can actually call the 2nd method.

### importConfigFile

This is taking the name of your config file (or path to it) in order to open it and read it.
This will set the variable required to generate the token.

### retrieveToken

This method is actually generating a token. It can be used once you have actually set up your config file and import it into your environment.
However, this method is not required. If you try to retrieve a company id without a token, a token will automatically be generated for you.

### getCompanyId

This method will return the company ID from your adobe IO connector. Your token are usually generated for only one company and this is returning which company you are allowed to look for.

### getProperties

This method takes one argument (the company id) and it will return a list of property that you will be able to feed the Property class.

### createProperty

It takes several arguments:

* the company id
* a name
* the platform (by default it is web)
* return_class : a Boolean if you want to return an instance of the Property class.

It returns either the instance of the Property class or the object returned by the API.

## Core module helper / facilitators

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

## 2. Property class

The property methods enable you to manipulate and retrieve the different element of the Launch instance.
The property methods can be found on the linked documentation [here](./property.md)

## 3. Library class

The library methods helps you to publish the different changes that you have made on your Launch instances.


## 4. Translator class