# Release for launchpy

This page gathered the changes made between version of the launchpy module.\
This has been started after the 0.3.0 release.

## 0.3.6

* adding `getProfile` method
* adding verbose parameters

## 0.3.5

* cleaning glbal variables
* separating admin code.

## 0.3.4

* Adding a `getRuleComponent` method to retrieve singleComponent
* Adding a `updateCustomCode` method to upload custom code directly to Launch
* Adding a `updateProperty` method to update the property settings
* separate `Library` class to its own submodule
* cleaning code in launchpy core library
* small fix `createConfigFile` method.
*Patch*
* adding encoding option and default to utf-8. `ENCODING` is now an attribute to launchpy 

## 0.3.3

* fixing the build method for library that didn't account for new optimized call with new architecture.
-- patch 0.3.3-1
fixed methods that didn't account for new architecture.

## 0.3.2

* adding a `getResources` method on `Admin` class.

## 0.3.1

* adding *analyticsCode* parameter for `extractSettings`. See documentation on [extractSettings in main documentation](main.md)

## 0.3.0

* Major change in architecture with addition of *configs* and *connector* submodules.
* Adding the `Admin` class to retrieve the CompanyId.
* Adding the `configure` method for server usage of the API
* Update documentation to reflect changes in the module.
* add update for Data Element, Rules, Extension for library management.
