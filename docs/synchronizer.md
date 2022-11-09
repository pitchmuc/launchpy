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

The `syncComponent` method can take 2 arguments.
Arguments:
 * componentName : The name of the component to sync between template and target properties
 * componentId : The id of the component to sync

Either of these 2 can be used, but in the end, the name of the component is used to do the matching between properties.
A component is either a Data Element or a Rule.

Example:
```python

synchronizor.syncComponent('my Component Name')
## or
synchronizor.syncComponent(componentId='myComponentId')

```
### syncComponent behavior

#### Data Elements
The method will replace the existing configuration of a data element by the template configuration.\
Completely overriding the existing element configuration in the target properties.

#### Rules
The method will delete all rule components existing in the Target property for that rule.\
It will then copy all template rule component existing in that base property to the target properties.\
No history is saved from the existing rule component, which will make revision check very hard.


