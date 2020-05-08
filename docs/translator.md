# The Translator class in pylaunch

The translator class is not a required class or group of methods for the pylaunch module to work. You may want to rewrite some of the functionalities for your own use. However, as I was developing and using this wrapper, it became obvious that a method which will help me to translate the id of the extension or the rule from each individual property into other property extension id or rule id would be very helpful.
Nowadays the copy paste of element from one property is something that can be done in the UI so it doesn't require to go through all of this.

However, we can clearly imaigne that this methods can help you automate some copy paste.
Also it is possible to use it not only between 2 properties but between 2 Organizations.

## Starting with translator class

The instantiation of the translator class is very basic as you would just need to call for it.
What is really required is the base property extensions and rules. The id of the elements from your “mother” property.
This is an assumption that I have when I created this facilitator, you would have a blueprint that you will use to copy elements from.
The translator class provide 2 methods to add base rule and base extension ids:

* setBaseExtensions
* setBaseRules

Both elements are taking the 2 same arguments:

* base_property : list of all of the extensions or rules that you want to remember for matching.
* property_name : name to establish the matching.

## Set Target Rule and Extensions ids

Once you have loaded the base Extension and Rules ids, the method will start to expand the table into multiple columns for matching. Underlying is the use of pandas dataframe to realize that matching.
You will need to be consistent with the naming of your target in order for the method to work properly.
The methods that allow extension of your table are the following:

* extendExtensions:
  * new_property_extensions : REQUIRED : the extension list from your target property.
  * new_prop_name : REQUIRED : target property name.

* extendRules:
  * new_property_rules: REQUIRED : the rules list from your target property.
  * new_prop_name : REQUIRED : target property name.

## Translating elements

Every translator jobs is to translate, then the final method is actually the translate method.:)
You need to use either the data_element or the rule_component parameter when translating.

* translate:
  * target_property : REQUIRED : property that is targeted to translate the element to.
  * data_element : OPTIONAL : if the elements passed are data elements.
  * rule_component : OPTIONAL : if the elements passed are rule components

Code example:

``` python
## retrieve the properties of your base and target properties
## as base_prop and target_prop
## then create Property class from / for  them.
## set Property and Core components posts for more info

base_extensions = base_prop.getExtensions()
target_extensions = target_prop.getExtensions()

base_rules = base_prop.getRules()
target_rules = target_prop.getRules()

translator = pylaunch.Translator()
translator.setBaseExtensions(base_extensions,'base')
translator.extendExtensions(target_extensions,target_prop.name)

translator.setBaseRules(base_rules,'base')
translator.extendRules(target_rules,target_prop.name)

base_de = base_prop.getDataElements() ## get data elements

## trying to copy the setting from the base extension data element
new_de = []
for data_element in base_de:
    new_de.append(pylaunch.copySettings(data_element))

## problem is that the id are having relationship to wrong extension id.

new_de_translated = []
for de in new_de:
    new_de_translated.append(translator.translate(de))

## now you can use the information gathered in the new_de_translated list
##  to create Data Element in the target property.
```

[main documentation](./main.md)