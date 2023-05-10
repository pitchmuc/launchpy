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
* old_name : REQUIRED :The name you want to replace.
* new_name : REQUIRED : The new name to be given to that component.

## Dynamic Component filter

You could use a data element to store some rule on how the synchronization can be done. This can serve as a configuration file for your synchronization. 
This Data Element is expected to follow a particular data structure.

The data element is an array of objects, each object should contain these keys: 

The elements you can use are:

* name : name of the rule
* targetProperties : string (can be a VALID regular expression) that wil look at the target property
* exclComponents : the list of component to exclude during the sync (can be empty)
* inclComponents : the list of components to include (can be empty)
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
