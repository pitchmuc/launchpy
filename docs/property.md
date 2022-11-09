# The Property class in launchpy

The launchpy property class helds most of the methods that are being display in the Launch API documentation ().
The name of the class and instanciation method implies that these methods works on one property at a time.
You can have several insances of property to apply changes to multiple properties.
As usual more information can be found here : [datanalyst.info website](https://www.datanalyst.info/category/python/launch-api/?camp=referral~github~launchpy-doc)

The class is divided 4 types of methods:

* get methods
* create methods
* delete methods
* update methods

## Get methods

When you have your property instance created, the methods that you may want to call first are the get methods. They never take any argument, they don’t actually need any argument.
The only thing important to know is that you must run the getRules() method before the getRuleComponents() method.

The different get methods are the following :

* getEnvironments
* getHost
* getExtensions
* getRules
* getRuleComponents
* getDataElements
* getLibraries

## Create methods

The same way than you can get the elements, you can create different elements.
You can create only one element at a time.
The different elements that can be created :

* createExtensions
* createRules
* createRuleComponent
* createDataElement
* createEnvironment
* createHost
* createLibrary

the createLibrary can return an instance of the library class. More details [here](./library.md) about that.

## Delete methods

The delete methods delete the resources from the Launch instance.
You can delete only one element at a time.
The different delete methods are:

* deleteEnvironments
* deleteExtension
* deleteRule
* deleteRuleComponent
* deleteDataElement

## Update methods

As you can imagine the update methods enable you to update the different elements.
Here is the list of the update methods available.

* updateRuleComponents
* updateDataElements
* updateEnvironment
* updateExtension
* updateCustomCode

[main documentation](./main.md)
