# Library class

The Library class will enable you to manage your Library workflow through python directly. You will be able to add elements to the library, build the library, attach environment or reject the library workflow.

By default the library instance is always going to move forward except if you set the require element.
The Library instance has several attributes that should help you understand at which state the library is actually at.

## Create a Library Instance

There are 2 methods to create a library instance :

1. You can create a library instance by using the Library class method from launchpy, this method requires that you take one of the element returned by the getLibraries method.
2. You can just create a library from scratch and, by default, the createLibrary method will return you an instance of the Library method.

Code example:

```python
import launchpy
### get a property instance as myProperty

## 1st method - from createLibrary method.
myLib = myProperty.createLibrary('myLib') ## will return a Library instance

## 2nd method
all_libs = myProperty.getLibraries() ## will return a list
myLib2 = launchpy.Library(all_libs[0]) ## take the first one as example.
```

## Library attributes

The instance you have created possess several attributes that can give you interesting information.
The different attributes are the following:

* id : id of the library
* name : name of the library
* state : is it “development”, “staging” or “production” environment
* build_required : is a build required or not (Boolean)
* builds : The build attache to this library
* buid_status : Is the last build has been “successful” ?
* relationships : the different element attached to this Library
* _environments = a dictionary of the different environment possible.

## The get methods

The get methods will enable you to retrieve the elements that have been attached to this library.
The different get methods are the followings:

* getDataElements
* getExtensions
* getRules
* getFullLibrary : It is a combinaison of all of the 3 above.

## Adding element to a library

As you can imagine, the add methods will permit to add elements to the Library itself.
The add methods takes a list of ids as arguments.
They are the following:

* addDataElements
* addRules
* addExtensions

## Environments settings

Before you can actually start building the library and pass it from one state to another (“development” -> “staging”). You would need to set the different environments.

The method used for that is : setEnvironments().
It takes 2 arguments:

* environments_list : REQUIRED : list of environment retrieved by the getEnvironment method
* dev_name : OPTIONAL : Name of your dev environment. If not defined, will take the first dev environment.

Example:

```python
envs = myProperty.getEnvironments() ## retrieve the environment list
myLib.setEnvironments(envs) ## set the environments
```

## Building the library

This one is pretty easy as it comes with the build() method.

```python
myLib.build() # require that you have set your environment.
```

## Transition your library

As it is your goal to publish your library, you want to transition it from the dev to the staging environment and so forth.
In order to do that, you can use the transition() method.
***Note*** : You would need to build your library between 2 transition.
At the end of the funnel, you just need to build your library when you are in the “approved” state.
The transition method takes 1 argument:

* action : it can be either
  * submit
  * approve
  * reject

[main documentation](./main.md)
