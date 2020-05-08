# Getting Started with the python wrapper for Launch API

On this page, an intro on how to start with the wrapper for Launch.

## 1. Create an Adobe IO console account

First you should create an Adobe IO account and connect to a Product Profile.
You can also create an Adobe IO account and then go to the product Profile in Adobe Admin Console to contect to your Adobe IO account.
When you create your Adobe IO account, you need to set a certificate, keep the key nearby because you will need it.
You can follow this [tutorial](https://www.datanalyst.info/python/adobe-io-user-management/adobe-io-jwt-authentication-with-python/)

## 2. Download the library

You can download the library from [here](https://github.com/pitchmuc/launchpy.git) and install it directly in your python3X/Lib.
or by doing the following command line: pip install launchpy

## 3. Setup a JSON with your information

Starting with the wrapper, you can import it and create a template for the JSON file that will store your credential to your Adobe IO account.

```python
import launchpy as lp
lp.createConfigFile()
```

This will create a JSON and you will need to fill it with the information available in your adobe io account.

## 4. Import the configuration file

Once this is done, you can import the configuration file.
I would recommend to store the config file and the key in the folder that you are using, however, the element will work if you are using correct path.

```python
lp.importConfigFile('myconfig.json')
```

## 5. Get Company ID(s) & retrieve properties

Once all of these setup steps are completed, you can start using the methods attached to launchpy module.
The first method is the _getCompanyId_, that will return you the company ID that is attached to your Adobe IO account.
you will use the *company* to retrieve the different properties.

```python
import launchpy as lp
lp.importConfigFile('myconfig.json')
cid = lp.getCompanyId()
properties = lp.getProperties(cid)
```

This will return you a list of properties.

## 6. Instanciate your Property class

You can use one of your element of the list return to instantiate the work on a property.
I usually select the property by name by doing the following :

```python
myProperty = [prop for prop in properties if prop['attributes']['name'] == "mypropertyName"][0]
mypropertyName = lp.Property(myProperty) ## here instanciation
```

## 7. Use the property methods or Library methods

When you have instanciate the property, you can start using the different methods hosted in the property class.
Example:

```python
dataelements = mypropertyName.getDataElements()
```

You can have a more complete view of the methods on the [property documentation](./property.md)

you can also use the libray class to publish the changes, more details on the [library class](./library.md)

Global documentation link [launchpy starting page](./main.md).
