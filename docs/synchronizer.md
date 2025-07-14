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

There is a possibility to setup some rules so you can filter when migrating from one property to another. See [dynamic Filtering](#dynamic-component-filter)

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

Check if the component,from the base property, is synced to the different target properties.
It can also check for the Extensions.\
It will return a dictionary with the key being the target property and the value being the result of the evaluation, such as {targetProperty: 'similar'} when component have same settings or {targetPropery : '<difference>'} when component do not have same settings.\
See below for differences.\
Arguments:
* componentName : REQUIRED : the name of the component to compare
* componentID : REQUIRED : the id of the component to compare
* publishedVersion : OPTIONAL : if you want to compare to the version that has been published in your base vs the published version of your target.
possible kwargs:
* action_setting_path : [str,list] : The dot notation of the paths you want to verify for the settings object. ex: ["code","customAttributes"]. If not provided, the complete settings are compared.
* condition_setting_path : [str,list] : The dot notation of the paths you want to verify for the setting object . ex: ["id",""]. If not provided, the complete settings are compared
* event_setting_path : [str,list] : The dot notation of the paths you want to verify for the setting object . ex: ["id",""]. If not provided, the complete settings are compared

### Check realised for component

The script will provide these evaluations:
For Extensions: 
* It will check if the extension is also present in that property. (returns the following sentence `f'Extension "{extension_name}" is not present'` if not the case )
* It will check if the same version of the extension is used (return the following sentence  `f'Extension version is different: {version_base} vs {version_target}` in case different versions)
* It will check if the same settings has been applied (return `'Extension settings are different'` if not the same)

For Rules:
* It will check if the rule exist in the target property (if not, returning `"Rule does not exist in Target"`)
* It will check if the rules contain the same number of ruleComponents (return `"The rule does not have the same number of components"` in case different numbers)
* It will check if the enabled state is the same than your base (if not, returning `"Rule enabled status is different"`)
* It will check if the published state is the same than your base (if not, returning `"Rule published status is different"`)
* It will check each ruleComponent if it can be found (based on name) and generate a list of differences based on each component check:
  * If the ruleComponent name cannot be found in the target property : return `f'component {rule-component-name} does not exist in Target'`
  * If the ruleComponent is an event it will check if the order of the event is different. If different, it will return: `rule_order is different`
  * If the ruleComponent is an condition or an action it will check if the tiemout is different. If different, it will return: `f"condition|action {rule-component-name} timeout is different"`
  * If the ruleComponent cannot be found in the target rule, it will add the following elements: `'component {rule-component-name} does not exist in Target'`
  * If the ruleComponent name is found and the settings are different : return `f'<componentType> {rule-component-name} has different settings'`.\
  ComponentType can be: `event, condition, action`\
  The settings can be check globally or you can specify a specific part of the setting to be checked (see `possible kwargs`)
  * If the ruleComponent are all similar, then the result will be `Similar` 


For Data Elements:
* It will check if the Data Element name can be found : return `f'Data Element "{data-element-name}" does not exist in Target'` if not found
* If Data Element (based on name) is found and settings are the same : return `"Similar"`, else return `"Data Element settings are different"`

#### Additional elements
On top of the different properties check, additional information will be provided for the base component: 
* `base-publihsed`: If the current component check is published.\
  **IMPORTANT NOTE**: When you using the `publishedVersion` parameter set to True, most of the element will be set to Published. In reverse, it is not because the component current version is not published that it has never been published. Use the `publishedVersion` to ensure this.
* `base-enabled`: If the current component check is enabled. 
* `base-state`: 
  * `Latest`: If the component retrieved is the latest latest version
  * `Unknown`: If the component retrieved cannot be evaluated to know if it is the latest.
  * `Draft` : If the component retrieved is not the latest and it has not yet been published
  * `Edited`: If the component retrieved is not the latest and has been published before.

#### Similar vs Same
The idea of checking the similarity of 2 components is partially done as not everything can be tested during the check.\
For that reason, the wording `Similar` is used and not `Same` as they are not technically the same. (different ids, different things.)

#### publishedVersion for checking
In the case that you want to compare the published versions, 2 similar problems could occure: 
- **The base component is not published**. The result of that would be the **failing of the comparison** (an exception will be thrown) because you need to have your base clean to start a comparison with a published version.
- **One or all the Targets properties do not have the component published**. In that case, I tried to handle that nicely and then try to default to the latest version for comparison. In the result, the following parenthesis would be added `(draft)`

Therefore, the `(draft)` is always referring to the target property.

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

### Dynamic Component Filtering options

#### Data Elements

You can pass a Data Element name during the instanciation of the `Synchronizer`. This data element needs to resides in the base property and it will contain a **valid** JSON that will describe the different rules that will apply during the synchronization.\
The format of the JSON representation for the data element is [explained above](#dynamic-component-filter)\
The data element name needs to be passed in the `dynamicRuleComponent` parameter.

Hence the code would look like this for instantiation:
```python

import launchpy as lp

lp.importConfigFile('config.json')
synchronizor = lp.Synchronizer(base='Prop1',targets=['Prop2'],dynamicRuleComponent='dataElementName')

```

#### Code

You can also provide the JSON representation of the filter used for synchronization via a dictionary, directly in your notebook.\
A method called `dynamicFiltering` allows you to load a dynamic filter directly within the python application and do not require the creation of data element for it.

So after instantiation, you can now pass the rule such as: 

```python
import launchpy as lp

lp.importConfigFile('config.json')
synchronizor = lp.Synchronizer(base='Prop1',targets=['Prop2'])
myRules = [
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

synchronizor.dynamicFiltering(myRules)

```


### Dynamic Component filter check

Once you have loaded your dynamic component rules in your Synchronizer class, you can access 2 attributes to verify the correct setup.

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

### Regular expression in Python

One common issue seeing the pattern used in Regular Expression is the use of the quantifier `*` without any character before.\
This can lead to some errors when using the following regular expression: `*some pattern*`\
This type of pattern needs to be replaced by `.*some pattern.*`\

The `*` is a quantifier that needs to have a character before it so it can know which character or pattern to repeat (or not).