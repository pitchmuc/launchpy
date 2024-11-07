# Release for launchpy

This page gathered the changes made between version of the launchpy module.\
This has been started after the 0.3.0 release.\

## 0.4.4
* adding a `getBuilds` method on the `Library` class instance
* extend support for pagination on `getEnvironments`
* adding `getProductionEndpoint` and `getStagingEndpoint` to retrieve the URL to use on websites
* support the instantiation of the `Library` class via a single libraryId string. 

## 0.4.3
* Refactor `Translator` class for removing `pandas` dependency\
Patch:
* Fix an issue with dependency on `target_configs` attribute in synchronizor.

## 0.4.2
* Supporting the Oauth Token V2 authentication

### 0.4.1
* single component methods (getDataElement, getRule) will now return the definition directly and avoid that you need to access the `data` attibute.
* introducing the `updateDataElementCode` method that update directly the code from a custom code data element based on the stringify code passed.
* provide a possible configuration for Synchronizer via a Data Element name. (Link)[./synchronizer.md#dynamic-component-filter]

## 0.4.0
* Improve `getLatestPublishedVersion` as API response may not be consistent.
* Extending the `Translator` class with 
  * `extendBaseRules` & `extendTargetRules` for adding new rules in the mapping table.
* Fixing issue when synchronizing properties and creating a new rule that is not enabled.
* Taking care of `default_value` parameter for Data Element in synchronizer
* Adding the `renameComponent` method in the `Synchronizer`\
Patch:
* adding support for additional parameter for `getLibraries` method.
* supporting when synchronizer is used as duplicator 
* changing methods name from `updateEnvironments` to `updateEnvironment` and `createExtensions` to `createExtension`\
Patch: 
* change the build required setup after `transition` as the response from Launch API is incorrect.
* removing the `builds` attribute.

## 0.3.9

* adding a `syncComponents` method in `Synchronizer` class
* adding a `createTargetsLibrary` method `Synchronizer` class
* improving the `Library` class for fetching libraries with pagination.
* update name of method `updateDataElement` to `updateDataElements` as it takes a list of data element ids
* adding the `getLatestPublishedVersion` method in `Property` class to find the latest published version of a component
* adding "enabled" attribute in rule `copySetting` method\
Patch:
* adding the copySetting `enabled` attribute 
* adding `negate`, `delay_next` and `timeout` in copySetting method.
* Published version edge-case & typo fix issue.

## 0.3.8

* Cleaning methods and code to improve performance and load size
* Adding and fixing typing for methods
* Adding the `Synchronizer` class
* change `createDataElements` to `createDataElement` as only a single data element is created each time.
* change `updateDataElements` to `updateDataElement` for same reason
* change `createRuleComponents` to `createRuleComponent` for same reason
* change `createRules` to `createRule` for same reason
* rename `extractAnalyticsCode` to `extractAnalyticsCustomCode` for clarity\
Patch
* reverse the creation of ruleComponent in order to preserve the order.

## 0.3.7
* Fix issue with the Property class not present in last build.
* adding the `getRule` and `getDataElement` methods
* adding the `getRevisions` method to fetch the last revision of the element.\
Patch
* Fixing Revision typo
* Adding delete property + update documentation.

## 0.3.6

* adding `getProfile` method
* adding verbose parameters

Path

* add edge methods
* upgrade getRuleComponents method with `ruleInfo` paramater
* refine architecture with a `property.py` file
* change default filename for save of the extration to use the `id` of the element

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
