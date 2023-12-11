# Synchronizer

This page will provide information about the `Synchronizer` class available in launchpy module.\
The synchronizer module and class is built around existing methods and class available in the launchpy module.\
You can recreate a (more advanced) version that supports additional methods or extend this class if wishes, the current state is the one that is a minimal viable feature in my use-case.

The Synchronizer will allow you to specify a template property and target property **within the same organization** in order to sync these properties rules and data elements.



## PRE REQUISITE

This class is currently requiring the following elements on your side:

* You have imported the config file (via `importConfigFile`) or configure your module via `configure` method.
* Your template property and target properties are located in the same organization
* You have unique name for your rule and data elements
* You have the same extension installed in both the template and target properties.\
  The Synchronizer will not sync the extensions configuration.

If a rule and a data element have the same name, by passing that name in the `syncComponent` method, you will only sync the rule.

## Instantiation

In order to instantiate the `Synchronizer` class, you will need to provide 2 elements:

* The name of the base property (as string)
* The names of the target properties (as a list of strings)

Example:

```python

import launchpy as lp

lp.importConfigFile('config.json')
synchronizor = lp.Synchronizer(base='Prop1',targets=['Prop2'])

```

## SyncComponent Method

The `syncComponent` method can take 3 arguments.
Arguments:
 * componentName : The name of the component to sync between template and target properties
 * componentId : The id of the component to sync
 * publishedVersion : Set to `False` by default. If set to True, takes the latest published version of the component.

Either of these 2 can be used, but in the end, the name of the component is used to do the matching between properties.
A component is either a Data Element or a Rule.

Example:
```python

synchronizor.syncComponent('my Component Name')
## or
synchronizor.syncComponent(componentId='myComponentId')
## or for publishedVersion
synchronizor.syncComponent('my Component Name',publishedVersion=True)

```
### syncComponent behavior

#### Data Elements
The method will replace the existing configuration of a data element by the template configuration.\
Completely overriding the existing element configuration in the target properties.

#### Rules
The method will delete all rule components existing in the Target property for that rule.\
It will then copy all template rule component existing in that base property to the target properties.\
No history is saved from the existing rule component, which will make revision check very hard.

## SyncComponents Method

You can pass down a list of component names or componentIds.\
It takes 3 arguments:\
Arguments:
* componentsName : REQUIRED : The list of component names to sync
* componentsId : REQUIRED : The list of component ID to sync*
* publishedVersion : OPTIONAL : if you want to take the version that has been published

## createTargetsLibrary

The synchronizer will automatically track the component that has been updated via the module.\
When you are done synchronizing your components, you can run this method to create a library, that will contain all of your elements you synchronized.\
The library will be available within all of your synch properties.

You can pass a name to define the library name that is created.\
The name is then used to match if a library already exist with that name, in the case it exists, it will use this library name.\
Note that the match looked for is using regular expression (`re.search`) to find a match in the existing libraries name.\
Arguments:
* name : REQUIRED : Name of the library to create or to use.

## renameComponent

You can use the `renameComponent` method before you synchronize a renamed component in the base property.\ This way the name will be equals in all of the properties and the synchronization can happen.\
The Synchronizer can only use the name as common key between properties, therefore, if you need to change the name of a component in the base property, you would need to change that name as well in all of the target properties as well before doing the sync.
Otherwise, the component will not be recognized and the sync will not happen.
Arguments:
* old_name : REQUIRED : The name you want to replace.
* new_name : REQUIRED : The new name to be given to that component.

## checkComponentSync

This method will allow you to check if a component is the same in the target properties, when compare to the base.
It works on Rules, Data Elements, Extensions, with their name or ID.
It is returning a dictionary with the name of the target properties as keys and `True` when the component is the same, `False` when the component is **not** the same.
Arguments:
* componentName : REQUIRED : The name of the component to compare (can be replaced by componentId)
* componentId : OPTIONAL : The ID of the component to compare
* publishedVersion : OPTIONAL : if you want to compare to the version that has been published in your base to your target latest version.

### Check realised for component

The script will provide these evaluations:
For Extensions: 
* It will check if the same version of the extension is used (return `False` in case different versions)
* It will check if the same settings has been applied (return `False` else `True`)

For Rules:
* It will check if the rules contain the same number of ruleComponents (return `False` in case different numbers)
* It will check each ruleComponent if it can be found (based on Name)
  * If the ruleComponent name cannot be found in the target property : return `False`
  * If the ruleComponent name is found and the settings are different : return `False`
  * If all ruleComponent names have been found and their settings are identical : 
    * If ruleComponent is an event :
      * If the rule_order attribute is the same return `True` else return `False`
    * If the ruleComponent is an action : 
      * If the timeout attribute is the same return `True` else return `False`
    * neither an action or event ruleComponent : return `True` as settings are identical.

For Data Elements:
* It will check if the Data Element name can be found : return `False` if not found
* If component Name is found and settings are the same : return `True`, else return `False`

## Dynamic Component filter

You could use a data element to store some rule on how the synchronization can be done. This can serve as a configuration file for your synchronization.This Data Element is expected to follow a particular data structure.

The data element is an array of objects, each object should contain these keys: 

* name : name of the rule
* targetProperties : string (can be a **VALID** regular expression) that will look at the target property. _It must be unique_.
* exclComponents : the list of component to exclude during the sync (can be empty, can use regular expression)
* inclComponents : the list of components to include (can be empty, can use regular expression)
                  If the list is not empty, then the list is the only source of truth for syncing the component.
                  If the list is empty, everything that is not in the exclComponent list will be synced

If a component is not found in any of these rules, it will be automatically mapped in all of the properties you want to sync.
An example on how the data element looks like:

```JS
[
  {
    'name':'myName',
    'targetProperties':'.+ some condition .+ ',
    'exclComponents':[
        'DE - My Data Element',
        'RL - My Rule'
      ],
    'inclComponents':[
        'somecomponent name'
      ]
  }
]
```
**NOTE** : The JSON representation should be flawless and the regular expression used as well, otherwise the script can break trying to decrypting it. 

### Usage of Dynamic Component filter

You would use that data element name during the instantiation of the synchronizer such as: 

```python 
synchronizor = lp.Synchronizer(base='BaseProperty',targets=['Target Property 1',
                                                         'Target Property 2',
                                                         'Target Property  3'],
                               dynamicRuleComponent='syncFilter')
```
In this example above, `syncFilter` is the name of the data element containing that configuration.\
Once your Synchronizer class has been instanciated, you can access 2 attributes in it to verify the correct setup.

* `dict_config` 
The `dict_config` attribute will be a copy of your data element setup, but a dictionary instead of an array where all of the target properties rule will be a key.\
These keys containing the include and exclude components to be deal with. 

* `target_configs`
The `target_configs` attribute will show you how the configuration you have passed is being applied to each of the target properties you want to sync to.
It basically merge all rules and components depending on the targetProperties rules or name you have passed.

### Logic of that Dynamic Component filter

The logic that will be applied during the sync is the following:

* IF there is a `target_configs` setup, we will use it to verify that the component can be sync.
* IF the Target property that is currently being sync is in the list:
  * IF the component is in the `exclComponents` list: It will **not** be synced
  * IF there is a list of `inclComponents` for that target property (and not empty)
    * IF the component name is in that list, **and not** in the `exclComponents` list, it will be sync
    * IF the component name is in that list **and** in the `exclComponents` list, it will **NOT** be sync
  * IF there is no list of `inclComponents` for that target property (or empty list), **and not** in the `exclComponents` list, the component will be synced
* ELSE: it will be sync