# Command Line Interface for launchpy

This document provides an overview of the command line interface (CLI) for `launchpy`, a tool designed to facilitate the launching of applications and services. The CLI allows users to interact with `launchpy` directly from the terminal, providing a convenient way to manage and execute tasks.

**Table of Contents**:
- [Command Line Interface for launchpy](#command-line-interface-for-launchpy)
  - [Prequisites](#prequisites)
  - [Installation](#installation)
  - [Usage](#usage)
    - [Instantiation](#instantiation)
      - [create\_config\_file](#create_config_file)
      - [config](#config)
      - [get\_properties](#get_properties)
      - [create\_property](#create_property)
      - [delete\_property](#delete_property)
      - [extract\_property](#extract_property)
      - [load\_property](#load_property)
      - [get\_extensions](#get_extensions)
      - [load\_extension](#load_extension)
    - [Property Layer Commands](#property-layer-commands)
      - [get\_extensions](#get_extensions-1)
      - [get\_extension](#get_extension)
      - [get\_rules](#get_rules)
      - [get\_rule](#get_rule)
      - [get\_rules\_components](#get_rules_components)
      - [get\_rule\_components](#get_rule_components)
      - [get\_data\_elements](#get_data_elements)
      - [get\_data\_element](#get_data_element)
      - [get\_latest\_published\_version](#get_latest_published_version)
      - [get\_libraries](#get_libraries)
      - [delete\_library](#delete_library)
      - [delete\_library\_components](#delete_library_components)
      - [create\_env](#create_env)
    - [Synchronizer Layer Commands](#synchronizer-layer-commands)
      - [check\_component](#check_component)
      - [sync](#sync)
      - [rename\_component](#rename_component)
      - [get\_targets](#get_targets)
      - [upgrade\_extension](#upgrade_extension)
      - [get\_base\_rules](#get_base_rules)
      - [get\_base\_data\_elements](#get_base_data_elements)
      - [get\_base\_extensions](#get_base_extensions)
      - [get\_base\_libraries](#get_base_libraries)
      - [get\_base\_library](#get_base_library)
      - [sync\_from\_library](#sync_from_library)
      - [create\_libraries](#create_libraries)



## Prequisites
Before using the `launchpy` CLI, ensure that you have the following prerequisites:
- Python 3.10 or higher installed on your system.
- Access to a terminal or command prompt.
- An active internet connection to install `launchpy` and its dependencies.
- An Adobe Developer Project that is connected to your Adobe Launch / Adobe Experience Platform Data Collection Tags. This would provide the information required (`client_id`, `secret`, `org_id`, `scopes`) to use the CLI to launch your applications and services.

## Installation
You would need to have Python installed on your system to use `launchpy`. The recommended version is Python 3.10 or higher. You can check your Python version by running:

```bash
python --version
```

In order to use the CLI, you would need to have at least the version `0.4.7` of `launchpy`.
To install `launchpy`, you can use pip:

```bash
pip install launchpy
```

to upgrade to the latest version, you can run:

```bash
pip install --upgrade launchpy
```

## Usage
Once installed, you can access the `launchpy` CLI by running the following command in your terminal:

```bash
python -m launchpy.cli
```

launchpy CLI provides various commands nested in different layer: 
- **Main Layer** : This is the top layer of the CLI where you can access the main functionalities such as creating a config file and setting up the configuration for API connection. It can be recognized by the `(Cmd)` or `launchpy>` (once config has been ran) prompt.
- **Property Layer**: This layer allows you to access information about a specific Launch property and perform actions related to that property. It can be recognized by the `property_name>` prompt, where `property_name` is replaced by the name of your property. You can directly access this layer by providing the property name in the `config` command in the main layer.
- **Synchronizer Layer**: This layer is focused on synchronizing Launch properties. It provides commands to check for updates and synchronize your property. It can be recognized by the `synchronizer:base_property>` prompt, where `base_property` will be replaced by the name of your base property.

All layers contains the following common commands:
- `help` : Display the help message with a list of available commands and their descriptions.
- `exit` : Exit the CLI.


### Instantiation

Once you have started the CLI, you can either create a config file if needed, or load the config file in the `config` method. 
The config method also take individual parameters as arguments, which would override the values in the config file. 

#### create_config_file
Create a config file to store your credentials and other necessary information for using `launchpy`. This is a one-time setup step that allows you to save your configuration for future use.\
Arguments
`-fn`, `--file_name`: The name of the config file to be created. If not provided, it defaults to `launchpy_config.json`.\

You can create a config file by running the following command:

```bash
python -m launchpy.cli
(Cmd) create_config_file
```


#### config
Setup the API connection to use the full capacity of the CLI. 
Arguments
`-cid`,`--client_id`: The client ID for your Adobe Developer Project. This is a required parameter.
`-s`,`--secret`: The secret key for your Adobe Developer Project. This is a required parameter.
`-o`,`--org_id`: The organization ID associated with your Adobe Developer Project. This is a required parameter.
`-sc`,`--scopes`: The scopes that define the permissions for your API connection. This is a required parameter.
`-cf`,`--config_file`: The path to the config file that contains your credentials and other necessary information.
`-p`,`--property` : The property name to be used and directly instantiated the property layer. This is an optional parameter.

Example via parameters:
```bash
python -m launchpy.cli
(Cmd) config --client_id <your_client_id> --secret <your_secret> --org_id <your_org_id> --scopes <your_scopes>
```

Example via config file:
```bash
python -m launchpy.cli
(Cmd) config --config_file <path_to_your_config_file>
```
Example with direct access to property layer:
```bash
python -m launchpy.cli
(Cmd) config --config_file <path_to_your_config_file> --property <your_property_name>
```

**TIP**
When you are instantiating the CLI, you can directly pass the credentials information:

```bash
python -m launchpy.cli --client_id <your_client_id> --secret <your_secret> --org_id <your_org_id> --scopes <your_scopes>
```

or 

```bash
python -m launchpy.cli --config_file <path_to_your_config_file>
```

It also supports direct access to the property layer by providing the property name in the parameters:

```bash 
python -m launchpy.cli --config_file <path_to_your_config_file> --property <your_property_name>
```


#### get_properties
Retrieve a list of properties associated with your Adobe Developer Project. This command allows you to view the properties that you have access to and can manage using `launchpy`.\
Arguments: 
`-n`,`--name`: The name of the property to filter the results (partial match, non-case sensitive). This is an optional parameter.
`-s`,`--save`: Boolean. Save properties to a CSV file. Default False. Possible values: `True`, `False`

```bash
python -m launchpy.cli -cf <path_to_your_config_file>
launchpy> get_properties -n <property_name> -s True
```

#### create_property
Create a new property in your Adobe Launch account. This command allows you to set up a new property that you can manage and synchronize using `launchpy`.\
Arguments:
`name` : The name of the new property to be created. This is a required parameter.
`-d`,`--description`: The description of the new property. This is an optional parameter.
`-p`,`--platform`: The platform for the new property. Default 'web', possible values: 'web', 'mobile'. This is an optional parameter.

Example: 
```bash
python -m launchpy.cli -cf <path_to_your_config_file>
launchpy> create_property "New Property" --description "This is a new property"
```

#### delete_property
Delete an existing property from your Adobe Launch account. This command allows you to remove a property that you no longer need or want to manage using `launchpy`.\
Arguments:
`name`: The name of the property to be deleted. This is a required parameter.

```bash
python -m launchpy.cli -cf <path_to_your_config_file>
launchpy> delete_property "Property Name"
```


#### extract_property
This method allows you to extract the details of a specific property and save them to a folder.\
The folder name would be the name of the property, it will contains sub folders for each rules.\
Arguments:
`name`: The name of the property to extract. This is a required parameter.

This can be useful for searching code or for backup purposes. 

```bash

python -m launchpy.cli -cf <path_to_your_config_file>
launchpy> extract_property "Property Name"
```


#### load_property
This method load the property layer for a specific property, allowing you to access and manage that property directly.
Arguments:
`name`: The name of the property to load. This is a required parameter.

```bash
python -m launchpy.cli -cf <path_to_your_config_file>
launchpy> load_property "Property Name"
property_name>
```

#### get_extensions
List all available extensions in the connected Adobe Launch organization.
Arguments:
`-s`, `--save`: Boolean. Save extensions to a JSON file. Default False. Possible values: `True`, `False`

```bash
python -m launchpy.cli -cf <path_to_your_config_file>
launchpy> get_extensions -s True
```

#### load_extension
Load a the synchronizer layer, allowing you to manage and synchronize properties with rules and data elements.\
Arguments:
`base_name`: Name of the Launch Property to use as base.
`-t`, `--targets`: list of target property names for synchronization. This is a required parameter.
`-dy`, `--dynamic_component`: Name of the Data Element that would contain dynamic component rules. This is an optional parameter, if not provided, it would not use dynamic component rules.

```bash
python -m launchpy.cli -cf <path_to_your_config_file>
launchpy> load_synchronizer "Base Property Name" -t "Target Property 1" "Target Property 2" -dy "Dynamic Component Data Element Name"
synchronizer:Base_Property_Name>
```

### Property Layer Commands

Once you have instantiated the property layer for a specific property, you can access various commands to manage that property. These commands allow you to perform actions such as viewing and editing rules, data elements, and other configurations related to that property.

#### get_extensions
Get all extensions in the property and list them.\
Arguments:
`-s`, `--save`: Boolean. Save extensions to a CSV file. Default False. Possible values: `True`, `False`

```bash
property_name> get_extensions -s True
```

#### get_extension
Get details of a specific extension in the property.\
Arguments:
`name`: The name of the extension to retrieve details for. This is a required parameter.
`-s`, `--save`: Boolean. Save the extension details to a JSON file. Default False. Possible values: `True`, `False`

```bash
property_name> get_extension "Extension Name" -s True
```

#### get_rules
Get all rules in the property and list them.\
Arguments:
`-n`, `--name`: The name of the rule to filter the results (partial match, non-case sensitive). This is an optional parameter.
`-s`, `--save`: Boolean. Save rules to a CSV file. Default False. Possible values: `True`, `False`

```bash
property_name> get_rules -n "Rule Name" -s True
```

#### get_rule
Get details of a specific rule in the property.\
Arguments:
`name`: The name of the rule to retrieve details for. This is a required parameter.
`-s`, `--save`: Boolean. Save the rule details to a JSON file. Default False. Possible values: `True`, `False`

```bash
property_name> get_rule "Rule Name" -s True
```

#### get_rules_components
Get all rule components, and save them to a CSV file if specified. Intended to be used for all components, but can be filtering.\
Arguments:
`-s`, `--save`: Boolean. Save rules components to a CSV file. Default False. Possible values: `True`, `False`
`-rn`, `--rule_name`: (Partial) Name of the rule to get components for. This is an optional parameter.
`-rid`, `--rule_id`: ID of the rule to get components for. This is an optional parameter, if both `rule_name` and `rule_id` are provided, it will use `rule_id`.

```bash
property_name> get_rules_components -s True
```

#### get_rule_components
Get all components for a specific rule by name or ID. Way more effective than the other methods and provide more details.\
Arguments:
`-s`, `--save`: Boolean. Save the rule components to a JSON file. Default False. Possible values: `True`, `False`
`-rn`, `--rule_name`: (Partial) Name of the rule to get components for. This is an optional parameter.
`-rid`, `--rule_id`: ID of the rule to get components for. This is an optional parameter, if both `rule_name` and `rule_id` are provided, it will use `rule_id`.

```bash
property_name> get_rule_components -rn "Rule Name" -s True
```

#### get_data_elements
Get all data elements in the property and list them.\
Arguments:
`-n`, `--name`: The name of the data element to filter the results (partial match, non-case sensitive). This is an optional parameter.
`-s`, `--save`: Boolean. Save data elements to a CSV file. Default False. Possible values: `True`, `False`

```bash
property_name> get_data_elements -n "Data Element Name" -s True
```

#### get_data_element
Get details of a specific data element in the property.\
Arguments:
`name`: The name of the data element to retrieve details for. This is a required parameter.
`-s`, `--save`: Boolean. Save the data element details to a JSON file. Default False. Possible values: `True`, `False`

```bash
property_name> get_data_element "Data Element Name" -s True
```

#### get_latest_published_version
Get the latest published version of a specific component in the property.\
Arguments:
`-n`, `--name`: The name of the component to get the latest published version for. This is a required parameter.
`-t`, `--type`: The type of the component (e.g. 'rule', 'data_element', 'extension') to get the latest published version for. This is a required parameter.
`-s`, `--save`: Boolean. Save the latest published version details to a JSON file. Default False. Possible values: `True`, `False`

```bash
property_name> get_latest_published_version -n "Component Name" -t "rule" -s True
```

#### get_libraries
Get all libraries in the property and list them.\
Arguments:
`-s`, `--save`: Boolean. Save libraries to a CSV file. Default False. Possible values: `True`, `False`
`-st`, `--state`: Filter by library state. Possible values: 'development' (default), 'submitted', 'approved', 'rejected', 'published'. This is an optional parameter.

```bash
property_name> get_libraries -s True -st "development"
```

#### delete_library
Delete a library from the property.\
Arguments:
`name`: The name of the library to delete. This is a required parameter.

```bash
property_name> delete_library "Library Name"
```

#### delete_library_components
Delete components from a library.\
Arguments:
`name`: The name of the library to delete components from. This is a required parameter.

```bash
property_name> delete_library_components "Library Name"
```

#### create_env
Create a new environment based on Adobe host in the property.\
Arguments:
`name`: The name of the environment to create. This is a required parameter.

```bash
property_name> create_env "Environment Name"
```

### Synchronizer Layer Commands
Once you have loaded the synchronizer layer for a specific base property, you can access commands to manage and synchronize that property with target properties. These commands allow you to perform actions such as checking for updates, synchronizing properties, and managing dynamic component rules.

#### check_component
Check if a specific component is in sync between the base property and target properties.\
Arguments:
`-n`, `--name`: The name of the component to check for synchronization. This is a required parameter.
`-id`, `--id`: ID of the component to check (overrides name if both provided)
`-p`, `--published` : Boolean. Check the synchronization based on the latest published version of the component. Default False. Possible values: `True`, `False`

```bash
synchronizer:Base_Property_Name> check_component -n "Component Name" -p True
```

#### sync
Synchronize a specific component between the base property and target properties.\
Arguments:
`-n`, `--name`: The name of the component to synchronize. This is a required parameter.
`-id`, `--id`: ID of the component to synchronize (overrides name if both provided)
`-p`, `--published` : Boolean. Synchronize the latest published version of the component. Default `False`. Possible values: `True`, `False`
`-f`, `--force` : Boolean. Create the component if it does not exist. Default `True`. Possible values: `True`, `False`

```bash
synchronizer:Base_Property_Name> sync -n "Component Name" -p True -f True
```

#### rename_component
Rename a component in the destination property.
Arguments:
`current_name` : The current name of the component to rename. This is a required parameter.
`new_name`: The new name for the component. This is a required parameter.

```bash
synchronizer:Base_Property_Name> rename_component "Current Component Name" "New Component Name"
```

#### get_targets
Get the target properties for synchronization. This command allows you to view the properties that are set as targets for synchronization with the base property.

```bash
synchronizer:Base_Property_Name> get_targets
```

#### upgrade_extension
Upgrade an extension in the destination property to the latest version available in the base property.
Arguments:
`name`: The name of the extension to upgrade. This is a required parameter.
`-p`, `--platform`: The platform of the extension to upgrade (e.g. 'web', 'app'). This is an optional parameter. Default `web`.

```bash
synchronizer:Base_Property_Name> upgrade_extension "Extension Name"
```

#### get_base_rules
This command allows you to view the rules that are availble in the base property for synchronization with the target properties.\
Arguments:
`-n`, `--name`: The name of the rule to filter the results (partial match, non-case sensitive). This is an optional parameter.


```bash
synchronizer:Base_Property_Name> get_base_rules -n "Rule Name"
```

#### get_base_data_elements
This command allows you to view the data elements that are availble in the base property for synchronization with the target properties.\
Arguments:
`-n`, `--name`: The name of the data element to filter the results (partial match, non-case sensitive). This is an optional parameter.

```bash
synchronizer:Base_Property_Name> get_base_data_elements -n "Data Element Name"
```

#### get_base_extensions
This command allows you to view the extensions that are availble in the base property for synchronization with the target properties.\
Arguments:
`-n`, `--name`: The name of the extension to filter the results (partial match, non-case sensitive). This is an optional parameter.

```bash
synchronizer:Base_Property_Name> get_base_extensions -n "Extension Name"
```

#### get_base_libraries
This command allows you to view the libraries that are availble in the base property for synchronization with the target properties.\
Arguments:
`-s`, `--state`: Filter by library state. Possible values: 'published'(default),'development' , 'submitted', 'approved', 'rejected'. This is an optional parameter.
`-n`, `--name`: Filter base libraries by name (partial match, non-case sensitive). This is an optional parameter.
`-d`, `--days`: Filter libraries that have been updated in the last X days. This is an optional parameter.

```bash
synchronizer:Base_Property_Name> get_base_libraries -s "published" -n "Library Name" -d 30
```

#### get_base_library
This command allows you to view the details of a specific library that is availble in the base property for synchronization with the target properties.\
It returns the rule, data elements and extensions that are part of the library, as well as the details of the library itself.\
Arguments:
`-n`, `--name`: The name of the library to get details for. This is a required parameter.
`-id`, `--id`: The ID of the library to get details for (overrides name if both provided). This is an optional parameter.

```bash
synchronizer:Base_Property_Name> get_base_library -n "Library Name"
```

#### sync_from_library
This command allows you to synchronize a library from the base property to the target properties.\
**IMPORTANT**:By default it will use the published version of the elements that are part of the library. 
`-n`, `--name`: The name of the library to sync from. This is a required parameter.
`-id`, `--id`: The ID of the library to sync from (overrides name if both provided). This is an optional parameter.

```bash
synchronizer:Base_Property_Name> sync_from_library -n "Library Name"
```

#### create_libraries
This command allows you to create a library in the destination properties with the elements you have sync.\
Arguments:
`name`: Name for the new library to be created in the destination properties. This is a required parameter.
`-env`, `--environment`: Boolean. Try to find an empty environment to build the library. Default False. Possible values: `True`, `False`

```bash
synchronizer:Base_Property_Name> create_library "Library Name" -env True
```
        