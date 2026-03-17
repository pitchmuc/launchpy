from rich import rule
import launchpy
import argparse, cmd, shlex, json
from functools import wraps
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
from typing import Any, Concatenate, ParamSpec, ParamSpecKwargs
from collections.abc import Callable

P = ParamSpec("P")

def property_required(f:Callable[Concatenate["PropertyCLI", P], None]) -> Callable[Concatenate["PropertyCLI", P], None]:
    """Decorator to block commands if not logged in."""
    @wraps(f)
    def wrapper(self:"PropertyCLI", *args:P.args, **kwargs:P.kwargs) -> None:
        if not hasattr(self, 'property') or self.property is None:
            print("(!) Access Denied: You must setup a property first.")
            return
        return f(self, *args, **kwargs)
    return wrapper

def login_required(f:Callable[Concatenate["MainShell", P], None]) -> Callable[Concatenate["MainShell", P], None]:
    """Decorator to block commands if not logged in."""
    @wraps(f)
    def wrapper(self:"MainShell", *args:P.args, **kwargs:P.kwargs) -> None:
        if (not hasattr(self, 'cid') or self.cid is None):
            print("(!) Access Denied: You must configure your connection first.")
            return
        return f(self, *args, **kwargs)
    return wrapper

console = Console()

class PropertyCLI(cmd.Cmd):
    def __init__(self, property: launchpy.Property):
        super().__init__()
        self.prompt = f"{property.name}> "
        self.property = property
        self.data_elements = None
        self.rules_components = None
        self.rules = None
    
    @property_required
    def do_get_extensions(self, arg):
        """Get all extensions in the property and list them."""
        parser = argparse.ArgumentParser(prog='get_extensions', add_help=True)
        parser.add_argument("-s", "--save", help="Boolean. Save extensions to a CSV file. Default False. Possible values: True, False", type=bool, default=False)
        try:
            args = parser.parse_args(shlex.split(arg))
            extensions = self.property.getExtensions()
            table = Table(title=f"Extensions for {self.property.name}")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name", style="magenta")
            table.add_column("Version", style="green")
            table.add_column("Published", style="yellow")
            for ext in extensions:
                ext_id = ext['id']
                ext_name = ext['attributes']['name']
                ext_version = ext['attributes']['version']
                ext_published = str(ext['attributes']['published'])
                table.add_row(ext_id, ext_name, ext_version, ext_published)
            console.print(table)
            if args.save:
                df = pd.DataFrame([{
                    "id": ext['id'],
                    "name": ext['attributes']['name'],
                    "version": ext['attributes']['version'],
                    "published": ext['attributes']['published']
                } for ext in extensions])
                df.to_csv(f"{(self.property.name)}_extensions.csv", index=False)
                console.print(f"Extensions saved to {(self.property.name)}_extensions.csv", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return

    def do_get_extension(self,args:Any):
        """Get details for a specific extension by name."""
        parser = argparse.ArgumentParser(prog='get_extension', add_help=True)
        parser.add_argument("name", help="Name of the extension to get details for", type=str)
        parser.add_argument("-s", "--save", help="Boolean. Save extension details to a JSON file. Default False. Possible values: True, False", type=bool, default=False)
        try:
            args = parser.parse_args(shlex.split(args))
            extensions = self.property.getExtensions()
            matching_exts = [ext for ext in extensions if ext['attributes']['name'] == args.name]
            if not matching_exts:
                console.print(f"Extension '{args.name}' not found in this property.", style="red")
                return
            ext = matching_exts[0]
            console.print_json(json.dumps(ext, indent=4))
            if args.save:
                with open(f"{args.name}_extension.json", "w") as f:
                    json.dump(ext, f, indent=4)
                console.print(f"Extension details saved to {args.name}_extension.json", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return

    @property_required
    def do_get_rules(self, arg):
        """Get all rules for the property."""
        parser = argparse.ArgumentParser(prog='get_rules', add_help=True)
        parser.add_argument("-n", "--name", help="Filter rules by name (partial match, non-case sensitive)", type=str, default=None)
        parser.add_argument("-s", "--save", help="Boolean. Save rules to a CSV file. Default False. Possible values: True, False", type=bool, default=False)
        try:
            args = parser.parse_args(shlex.split(arg))
            rules = self.property.getRules()
            self.rules = rules
            if args.name:
                rules = [rule for rule in rules if args.name.lower() in rule['attributes']['name'].lower()]
            table = Table(title=f"Rules for {self.property.name}")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Current Published State", style="yellow")
            for rule in rules:
                rule_id = rule['id']
                rule_name = rule['attributes']['name']
                rule_published = str(rule['attributes']['published'])
                table.add_row(rule_id, rule_name, rule_published)
            console.print(table)
            if args.save:
                df = pd.DataFrame([{
                    "id": rule['id'],
                    "name": rule['attributes']['name'],
                    "current_published_state": str(rule['attributes']['published'])
                } for rule in rules])
                df.to_csv(f"{(self.property.name)}_rules.csv", index=False)
                console.print(f"Rules saved to {(self.property.name)}_rules.csv", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
    
    def do_get_rule(self, arg):
        """Get details for a specific rule by name."""
        parser = argparse.ArgumentParser(prog='get_rule', add_help=True)
        parser.add_argument("-n", "--name", help="Name of the rule to get details for", type=str)
        parser.add_argument("-id", "--id", help="ID of the rule to get details for (overrides name if both provided)", type=str)
        parser.add_argument("-s", "--save", help="Boolean. Save rule details to a JSON file. Default False. Possible values: True, False", type=bool, default=False)
        try:
            args = parser.parse_args(shlex.split(arg))
            if self.rules is None:
                rules = self.property.getRules()
                self.rules = rules
            else:
                rules = self.rules
            if args.id:
                matching_rules = [rule for rule in rules if rule['id'] == args.id]
            elif args.name:
                matching_rules = [rule for rule in rules if rule['attributes']['name'] == args.name]
            else:
                console.print("(!) Please provide either a rule name using the -n or --name option, or a rule ID using the -id or --id option.", style="red")
                return
            if not matching_rules:
                console.print(f"Rule '{args.name or args.id}' not found in this property.", style="red")
                return
            rule = matching_rules[0]
            console.print_json(json.dumps(rule, indent=4))
            if args.save:
                filename = f"rule_{launchpy.__safe_name__(args.name or args.id)}.json"
                with open(filename, "w") as f:
                    json.dump(rule, f, indent=4)
                console.print(f"Rule details saved to {filename}", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
    
    @property_required
    def do_get_rules_components(self, arg):
        """Get all components, possibly for a given rule, and save them to a CSV file if specified."""
        parser = argparse.ArgumentParser(prog='get_rules_components', add_help=True)
        parser.add_argument("-rn", "--rule_name", help="(Partial) Name of the rule to get components for", type=str,default=None)
        parser.add_argument("-rid", "--rule_id", help="ID of the rule to get components for (overrides rule_name if both provided)", type=str, default=None)
        parser.add_argument("-s", "--save", help="Boolean. Save components to a CSV file. Default False. Possible values: True, False", type=bool, default=False)
        try:
            args = parser.parse_args(shlex.split(arg))
            if self.rules_components is None:
                rcs = self.property.getRulesComponents()
                self.rules_components = rcs
            else:
                rcs = self.rules_components
            if args.rule_id is not None:
                rcs = [rc for rc in rcs if rc['rule_id'] == args.rule_id]
                if not rcs:
                    console.print(f"Rule with ID '{args.rule_id}' not found in this property.", style="red")
                    return
            elif args.rule_name is not None:
                rcs = [rc for rc in rcs if args.rule_name.lower() in rc['rule_name'].lower()]
                if not rcs:
                    console.print(f"Rule '{args.rule_name or args.rule_id}' not found in this property.", style="red")
                    return
            title_suffix = f" for rule '{args.rule_name or args.rule_id}'" if args.rule_name or args.rule_id else ""
            table = Table(title=f"Components{title_suffix}")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Type", style="green")
            table.add_column("Rule Name", style="yellow")
            for component in rcs:
                component_id = component['id']
                component_name = component['attributes']['name']
                component_type = component['attributes']['delegate_descriptor_id'].split("::")[1]
                component_rule_name = component['rule_name']
                table.add_row(component_id, component_name, component_type, component_rule_name)
            console.print(table)
            if args.save:
                if args.rule_name:
                    folder = f"{launchpy.__safe_name__(args.rule_name)}"
                    Path(folder).mkdir(parents=True, exist_ok=True)
                    for comp in rcs:
                        component_id = launchpy.__safe_name__(comp['id'])
                        file_path = Path(folder) / f"{component_id}.json"
                        with open(file_path, "w") as f:
                            json.dump(comp, f, indent=4)
                    console.print(f"Components saved to folder '{folder}'", style="green")
                else:
                    df = pd.DataFrame([{
                        "id": comp['id'],
                        "name": comp['attributes']['name'],
                        "order": comp['attributes']['order'],
                        "rule_order": comp['attributes']['rule_order'],
                        "timeout": comp['attributes']['timeout'],
                        "current_published_state": comp['attributes']['published'],
                        'rule_name': comp['rule_name']
                    } for comp in rcs])
                    df.to_csv(f"{(self.property.name)}_components.csv", index=False)
                    console.print(f"Components saved to {(self.property.name)}_components.csv", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
        
    def do_get_rule_components(self, arg:Any):
        """Get all components for a specific rule by name or ID."""
        parser = argparse.ArgumentParser(prog='get_rule_components', add_help=True)
        parser.add_argument("-rn", "--rule_name", help="(Partial) Name of the rule to get components for", type=str, default=None)
        parser.add_argument("-rid", "--rule_id", help="ID of the rule to get components for (overrides rule_name if both provided)", type=str, default=None)
        parser.add_argument("-s", "--save", help="Boolean. Save components to a JSON file. Default False. Possible values: True, False", type=bool, default=False)
        try:
            args = parser.parse_args(shlex.split(arg))
            rule = None ## fallback
            if self.rules is None:
                rules = self.property.getRules()
                self.rules = rules
            else:
                rules = self.rules
            if args.rule_id is not None:
                rule = [rc for rc in rules if rc['id'] == args.rule_id]
                if len(rule) == 0:
                    console.print(f"Rule with ID '{args.rule_id}' not found in this property.", style="red")
                    return
            elif args.rule_name is not None:
                rule = [rc for rc in rules if args.rule_name.lower() in rc['attributes']['name'].lower()]
                if len(rule) == 0:
                    console.print(f"Rule '{args.rule_name or args.rule_id}' not found in this property.", style="red")
                    return
            if rule is None: ## in case mixed up between get_rules_components and get_rule_components 
                return self.do_get_rules_components(arg)
            else:
                rcs = self.property.getRuleComponents(rule=rule[0])
            for rc in rcs:
                rc['attributes']['settings'] = json.loads(rc['attributes']['settings']) if rc['attributes']['settings'] else {}
            console.print_json(json.dumps(rcs, indent=4))
            if args.save:
                filename = f"components_{launchpy.__safe_name__(args.rule_name or args.rule_id)}.json"
                with open(filename, "w") as f:
                    json.dump(rcs, f, indent=4)
                console.print(f"Components saved to {filename}", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
        
    def do_get_data_elements(self,args:Any):
        """Get all data elements, or only the ones matching a name filter, for the property. Can save them in CSV file."""
        parser = argparse.ArgumentParser(prog='get_data_elements', add_help=True)
        parser.add_argument("-n", "--name", help="Filter data elements by name (partial match, non-case sensitive)", type=str, default=None)
        parser.add_argument("-s", "--save", help="Boolean. Save data elements to a CSV file. Default False. Possible values: True, False", type=bool, default=False)
        try:
            args = parser.parse_args(shlex.split(args))
            des = self.property.getDataElements()
            if args.name:
                des = [de for de in des if args.name.lower() in de['attributes']['name'].lower()]
            self.data_elements = des
            table = Table(title=f"Data Elements for {self.property.name}")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Current Published State", style="green")
            for de in des:
                de_id = de['id']
                de_name = de['attributes']['name']
                de_published = str(de['attributes']['published'])
                table.add_row(de_id, de_name, de_published)
            console.print(table)
            if args.save:
                df = pd.DataFrame([{
                    "id": de['id'],
                    "name": de['attributes']['name'],
                    "current_published_state": de['attributes']['published']
                } for de in des])
                df.to_csv(f"{(self.property.name)}_data_elements.csv", index=False)
                console.print(f"Data elements saved to {(self.property.name)}_data_elements.csv", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
    
    def do_get_data_element(self, args:Any):
        """Get details for a specific data element by name."""
        parser = argparse.ArgumentParser(prog='get_data_element', add_help=True)
        parser.add_argument("name", help="Name of the data element to get details for", type=str)
        parser.add_argument("-s", "--save", help="Boolean. Save data element details to a JSON file. Default False. Possible values: True, False", type=bool, default=False)
        try:
            args = parser.parse_args(shlex.split(args))
            if self.data_elements is None:
                des = self.property.getDataElements()
                self.data_elements = des
            matching_des = [de for de in self.data_elements if de['attributes']['name'] == args.name]
            if not matching_des:
                console.print(f"Data element '{args.name}' not found in this property.", style="red")
                return
            de = matching_des[0]
            console.print_json(json.dumps(de, indent=4))
            if args.save:
                filename = f"data_element_{launchpy.__safe_name__(args.name)}.json"
                with open(filename, "w") as f:
                    json.dump(de, f, indent=4)
                console.print(f"Data element details saved to {filename}", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
        
    @property_required
    def do_get_latest_published_version(self, arg):
        """Get the latest published version for the component."""
        parser = argparse.ArgumentParser(prog='get_latest_published_version', add_help=True)
        parser.add_argument("-n", "--name", help="Name of the component to get the latest published version for", type=str, default=None)
        parser.add_argument("-t", "--type", help="Type of the component (e.g. 'rule', 'data_element', 'extension') to get the latest published version for. Default None", type=str, default=None)
        parser.add_argument("-s", "--save", help="Boolean. Save the latest published version details to a JSON file. Default False. Possible values: True, False", type=bool, default=False)
        try:
            args = parser.parse_args(shlex.split(arg))
            if args.type and args.name is None:
                console.print("(!) Please provide a component name using the -n or --name option when using the -t or --type option.", style="red")
                return
            if args.type == "rule":
                if self.rules is None:
                    rules = self.property.getRules()
                    self.rules = rules
                element = [rule for rule in self.rules if rule['attributes']['name'] == args.name]
                if not element:
                    console.print(f"Rule '{args.name}' not found in this property.", style="red")
                    return
            if args.type == "data_element":
                if self.data_elements is None:
                    des = self.property.getDataElements()
                    self.data_elements = des
                element = [de for de in self.data_elements if de['attributes']['name'] == args.name]
                if not element:
                    console.print(f"Data element '{args.name}' not found in this property.", style="red")
                    return
            if args.type == "extension":
                exts = self.property.getExtensions()
                element = [ext for ext in exts if ext['attributes']['name'] == args.name]
                if not element:
                    console.print(f"Extension '{args.name}' not found in this property.", style="red")
                    return
            curr_version = element[0]
            revisions = self.property.getRevisions(element=curr_version)
            try:
                latest_version = self.property.getLatestPublishedVersion(revisions)
                if args.type == 'rule':
                    rcs = self.property.getOneRuleComponents(rule=latest_version)
                    folder = launchpy.__safe_name__(args.name)
                    Path(folder).mkdir(parents=True, exist_ok=True)
                    for el in rcs:
                        component_id = launchpy.__safe_name__(el['id'])
                        file_path = Path(folder) / f"{component_id}.json"
                        with open(file_path, "w") as f:
                            json.dump(el, f, indent=4)
                    rule_path = Path(folder) / f"{launchpy.__safe_name__(args.name)}_rule.json"
                    with open(rule_path, "w") as f:
                        json.dump(latest_version, f, indent=4)
                    console.print(f"Latest published version of rule '{args.name}' and its components saved to folder '{folder}'", style="green")
                else:
                    with open(f"{launchpy.__safe_name__(args.name)}_latest_version.json", "w") as f:
                        json.dump(latest_version, f, indent=4)
                    console.print(f"Latest published version of {args.type} '{args.name}' saved to {launchpy.__safe_name__(args.name)}_latest_version.json", style="green")
                if latest_version['id'] == curr_version['id']:
                    console.print(f"The latest published version of {args.type} '{args.name}' is the same as the current version.", style="green")
                else:
                    console.print(f"The latest published version of {args.type} '{args.name}' is different from the current version.", style="yellow")
            except IndexError:
                console.print(f"Rule '{args.name}' has no published versions.", style="yellow")
                return
            console.print_json(json.dumps(latest_version, indent=4))
            if args.save:
                filename = f"{launchpy.__safe_name__(args.name)}_latest_published_version.json"
                with open(filename, "w") as f:
                    json.dump(latest_version, f, indent=4)
                console.print(f"Latest published version details saved to {filename}", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
    
    @property_required
    def do_get_libraries(self, arg: Any):
        """Get all libraries for the property."""
        parser = argparse.ArgumentParser(prog='get_libraries', add_help=True)
        parser.add_argument("-s", "--save", help="Boolean. Save libraries to a CSV file. Default False. Possible values: True, False", type=bool, default=False)
        parser.add_argument("-st", "--state", help="Filter by library state. Possible values: 'development' (default), 'submitted', 'approved', 'rejected', 'published'", type=str, default="development")
        try:
            args = parser.parse_args(shlex.split(arg))
            libraries = self.property.getLibraries(state=args.state)
            table = Table(title=f"Libraries for {self.property.name}")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Build Required", style="green")
            for lib in libraries:
                lib_id = lib['id']
                lib_name = lib['attributes']['name']
                lib_build_required = str(lib['attributes']['build_required'])
                table.add_row(lib_id, lib_name, lib_build_required)
            console.print(table)
            if args.save:
                df = pd.DataFrame([{
                    "id": lib['id'],
                    "name": lib['attributes']['name'],
                    "buildRequired": lib['attributes']['build_required']
                } for lib in libraries])
                df.to_csv(f"{(self.property.name)}_libraries.csv", index=False)
                console.print(f"Libraries saved to {(self.property.name)}_libraries.csv", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
    
    @property_required
    def do_delete_library(self, arg):
        """Delete a library by name."""
        parser = argparse.ArgumentParser(prog='delete_library', add_help=True)
        parser.add_argument("name", help="Name of the library to delete", type=str)
        try:
            args = parser.parse_args(shlex.split(arg))
            libraries = self.property.getLibraries()
            matching_libs = [lib for lib in libraries if lib['attributes']['name'] == args.name]
            if not matching_libs:
                console.print(f"Library '{args.name}' not found in this property.", style="red")
                return
            lib_id = matching_libs[0]['id']
            self.property.deleteLibrary(lib_id)
            console.print(f"Library '{args.name}' deleted successfully.", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
    
    @property_required
    def do_delete_library_components(self,args:Any):
        """Delete all components in a library by library name."""
        parser = argparse.ArgumentParser(prog='delete_library_components', add_help=True)
        parser.add_argument("name", help="Name of the library to delete components from", type=str)
        try:
            args = parser.parse_args(shlex.split(args))
            libraries = self.property.getLibraries()
            matching_libs = [lib for lib in libraries if lib['attributes']['name'] == args.name]
            if not matching_libs:
                console.print(f"Library '{args.name}' not found in this property.", style="red")
                return
            lib_id = matching_libs[0]['id']
            self.property.deleteLibrary(lib_id,components=True)
            console.print(f"Components in library '{args.name}' deleted successfully.", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
    
    @property_required
    def do_create_env(self,args:Any):
        """Create a new environment based on Adobe host."""
        parser = argparse.ArgumentParser(prog='create_env', add_help=True)
        parser.add_argument("name", help="Name of the new environment", type=str)
        parser.add_argument("-sg", "--stage", help="Stage of the environment. Default 'development'. Possible values: 'development', 'staging', 'production'", type=str, default="development")
        try:
            args = parser.parse_args(shlex.split(args))
            host = self.property.getHost()
            host_id = [h['id'] for h in host if h['attributes']['name'] == 'Managed by Adobe'][0]
            self.property.createEnvironment(name=args.name,stage=args.stage,host_id=host_id)
            console.print(f"Environment '{args.name}' created successfully.", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    def do_exit(self, arg):
        """Return to the main menu."""
        console.print(Panel("Returning to main menu..."),style="blue")
        return True  # Returning True breaks the cmdloop

    def do_EOF(self, args:Any) -> None:
        """Handle Ctrl+D"""
        console.print(Panel("Exiting...", style="blue"))
        return True

class SynchronizerCLI(cmd.Cmd):
    """Interactive shell for managing launchpy synchronizers."""
    def __init__(self, synchronizer: launchpy.Synchronizer):
        super().__init__()
        self.synchronizer = synchronizer
        self.prompt = f"synchronizer:{self.synchronizer.base['name']}> "

    def do_check_component(self,ars:Any):
        """Check if a specific component is in sync between source and destination properties."""
        parser = argparse.ArgumentParser(prog='check_component', add_help=True)
        parser.add_argument("-n", "--name", help="Name of the component to check", type=str)
        parser.add_argument("-id", "--id", help="ID of the component to check (overrides name if both provided)", type=str)
        parser.add_argument("-p", "--published", help="Boolean. Check the latest published version of the component instead of the current version. Default False. Possible values: True, False", type=bool, default=False)
        try:
            args = parser.parse_args(shlex.split(ars))
            if args.id is not None:
                result = self.synchronizer.checkComponentSync(componentId=args.id, publishedVersion=args.published)
            else:
                result = self.synchronizer.checkComponentSync(componentName=args.name, publishedVersion=args.published)
            console.print_json(json.dumps(result, indent=4))
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
    
    def do_sync(self,args:Any):
        """Sync a specific component between source and destination properties."""
        parser = argparse.ArgumentParser(prog='sync', add_help=True)
        parser.add_argument("-n", "--name", help="Name of the component to sync", type=str)
        parser.add_argument("-id", "--id", help="ID of the component to sync (overrides name if both provided)", type=str)
        parser.add_argument("-p", "--published", help="Boolean. Sync the latest published version of the component instead of the current version. Default False. Possible values: True, False", type=bool, default=False)
        parser.add_argument("-f", "--force", help="Boolean. Create the component if it does not exist. Default True. Possible values: True, False", type=bool, default=True)
        try:
            args = parser.parse_args(shlex.split(args))
            if args.id is not None:
                result = self.synchronizer.syncComponent(componentId=args.id, publishedVersion=args.published, forceCreation=args.force)
            else:
                result = self.synchronizer.syncComponent(componentName=args.name, publishedVersion=args.published, forceCreation=args.force)
            console.print(f"Component '{args.name or args.id}' synced successfully.", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
        
    def do_rename_component(self,args:Any):
        """Rename a component in the destination property."""
        parser = argparse.ArgumentParser(prog='rename_component', add_help=True)
        parser.add_argument("current_name", help="Current name of the component to rename", type=str)
        parser.add_argument("new_name", help="New name for the component", type=str)
        try:
            args = parser.parse_args(shlex.split(args))
            self.synchronizer.renameComponent(old_name=args.current_name, new_name=args.new_name)
            console.print(f"Component '{args.current_name}' renamed to '{args.new_name}' successfully.", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
        
    def do_get_targets(self, args:Any):
        """Get the target properties for this synchronizer."""
        try:
            targets = self.synchronizer.targets.keys()
            console.print_json(json.dumps(list(targets), indent=4))
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
    
    def do_upgrade_extension(self,args:Any):
        """Upgrade an extension in the destination property to the latest version available in the source property."""
        parser = argparse.ArgumentParser(prog='upgrade_extension', add_help=True)
        parser.add_argument("name", help="Name of the extension to upgrade", type=str)
        parser.add_argument("-p", "--platform", help="Platform to be used for extension upgrade. default 'web'. Possible values: web, app", type=str, default="web")
        try:
            args = parser.parse_args(shlex.split(args))
            self.synchronizer.upgradeTargetExtension(extensionName=args.name, platform=args.platform)
            console.print(f"Extension '{args.name}' upgraded successfully.", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
    
    def do_get_base_rules(self,args:Any):
        """Get the base rules that are available for synchronization."""
        parser = argparse.ArgumentParser(prog='get_base_rules', add_help=True)
        parser.add_argument("-n", "--name", help="Filter base rules by name (partial match, non-case sensitive)", type=str, default=None)
        try:
            args = parser.parse_args(shlex.split(args))
            base_rules = self.synchronizer.base['rules']
            if args.name:
                base_rules = [rule for rule in base_rules if args.name.lower() in rule['attributes']['name'].lower()]
            table = Table(title=f"Rules for {self.synchronizer.base['name']}")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            for rule in base_rules:
                rule_id = rule['id']
                rule_name = rule['attributes']['name']
                table.add_row(rule_id, rule_name)
            console.print(table)
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return

    def do_get_base_data_elements(self,args:Any):
        """Get the base data elements that are being synchronized."""
        parser = argparse.ArgumentParser(prog='get_base_data_elements', add_help=True)
        parser.add_argument("-n", "--name", help="Filter base data elements by name (partial match, non-case sensitive)", type=str, default=None)
        try:
            args = parser.parse_args(shlex.split(args))
            base_des = self.synchronizer.base['dataElements']
            if args.name:
                base_des = [de for de in base_des if args.name.lower() in de['attributes']['name'].lower()]
            table = Table(title=f"Data Elements for {self.synchronizer.base['name']}")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            for de in base_des:
                de_id = de['id']
                de_name = de['attributes']['name']
                table.add_row(de_id, de_name)
            console.print(table)
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
        
    def do_get_base_extensions(self,args:Any):
        """Get the base extensions that are being synchronized."""
        parser = argparse.ArgumentParser(prog='get_base_extensions', add_help=True)
        parser.add_argument("-n", "--name", help="Filter base extensions by name (partial match, non-case sensitive)", type=str, default=None)
        try:
            args = parser.parse_args(shlex.split(args))
            base_exts = self.synchronizer.base['extensions']
            if args.name:
                base_exts = [ext for ext in base_exts if args.name.lower() in ext['attributes']['name'].lower()]
            table = Table(title=f"Extensions for {self.synchronizer.base['name']}")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            for ext in base_exts:
                ext_id = ext['id']
                ext_name = ext['attributes']['name']
                table.add_row(ext_id, ext_name)
            console.print(table)
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
    
    def do_get_base_libraries(self,args:Any):
        """Get the base libraries that are being synchronized."""
        parser = argparse.ArgumentParser(prog='get_base_libraries', add_help=True)
        parser.add_argument('-s', '--state', help="Filter by library state. Possible values: 'published'(default),'development' , 'submitted', 'approved', 'rejected', ", type=str, default="published")
        parser.add_argument("-n", "--name", help="Filter base libraries by name (partial match, non-case sensitive)", type=str, default=None)
        parser.add_argument("-d", "--days", help="Filter libraries that have been updated in the last X days", type=int, default=None)
        try:
            args = parser.parse_args(shlex.split(args))
            base_libs = self.synchronizer.base["api"].getLibraries(state=args.state)
            if args.name:
                base_libs = [lib for lib in base_libs if args.name.lower() in lib['attributes']['name'].lower()]
            if args.days is not None:
                cutoff_date = datetime.now() - timedelta(days=args.days)
                base_libs = [lib for lib in base_libs if 'updated_at' in lib['attributes'] and datetime.strptime(lib['attributes']['updated_at'], "%Y-%m-%dT%H:%M:%S.%fZ") >= cutoff_date]
            table = Table(title=f"Libraries for {self.synchronizer.base['name']}")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("State", style="green")
            table.add_column("Published", style="yellow")
            for lib in base_libs:
                lib_id = lib['id']
                lib_name = lib['attributes']['name']
                lib_state = lib['attributes']['state']
                lib_published = lib['attributes'].get('published_at', 'N/A')
                table.add_row(lib_id, lib_name, lib_state, lib_published)
            console.print(table)
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
    
    def do_get_base_library(self,args:Any):
        """ Return the components that are in the base library specified (rules, data elements, extensions)"""
        parser = argparse.ArgumentParser(prog='get_base_library', add_help=True)
        parser.add_argument("-n", "--name", help="Name of the library to get details for", type=str)
        parser.add_argument("-id", "--id", help="ID of the library to get details for (overrides name if both provided)", type=str)
        try:
            args = parser.parse_args(shlex.split(args))
            if args.id is not None:
                lib = self.synchronizer.base["api"].getLibrary(args.id, return_class=True)
            else:
                libs = self.synchronizer.base["api"].getLibraries()
                matching_libs = [lib for lib in libs if lib['attributes']['name'] == args.name]
                if not matching_libs:
                    console.print(f"Library '{args.name}' not found in this property.", style="red")
                    return
                lib = self.synchronizer.base["api"].getLibrary(matching_libs[0]['id'], return_class=True)
            rules = lib.getRules()
            data_elements = lib.getDataElements()
            extensions = lib.getExtensions()
            data = {
                "rules": [],
                "dataElements": [],
                "extensions": []
            }
            if len(rules) > 0:
                data['rules'] = [r['attributes']['name'] for r in rules]
            if len(data_elements) > 0:
                data['dataElements'] = [de['attributes']['name'] for de in data_elements]
            if len(extensions) > 0:
                data['extensions'] = [ext['attributes']['name'] for ext in extensions]
            console.print_json(json.dumps(data, indent=4))
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return

    def do_sync_from_library(self,args:Any):
        """Sync all components from a base library in the source property to the destination properties. Rules and data elements will be the latest published one"""
        parser = argparse.ArgumentParser(prog='sync_from_library', add_help=True)
        parser.add_argument("-n", "--name", help="Name of the library to sync from", type=str)
        parser.add_argument("-id", "--id", help="ID of the library to sync from (overrides name if both provided)", type=str)
        try:
            args = parser.parse_args(shlex.split(args))
            if args.id is not None:
                lib = self.synchronizer.base["api"].getLibrary(args.id, return_class=True)
            else:
                libs = self.synchronizer.base["api"].getLibraries()
                matching_libs = [lib for lib in libs if lib['attributes']['name'] == args.name]
                if not matching_libs:
                    console.print(f"Library '{args.name}' not found in this property.", style="red")
                    return
                lib = self.synchronizer.base["api"].getLibrary(matching_libs[0]['id'], return_class=True)
            rules = lib.getRules()
            dataelements = lib.getDataElements()
            extensions = lib.getExtensions()
            if len(extensions)>0:
                console.print(f"Upgrading {len(extensions)} extension{'s' if len(extensions) > 1 else ''} from library '{lib.name}'...", style="blue")
                for ext in extensions:
                    try:
                        self.synchronizer.upgradeTargetExtension(extensionName=ext['attributes']['name'])
                        console.print(f"Extension '{ext['attributes']['name']}' upgraded successfully.", style="green")
                    except Exception as e:
                        console.print(f"(!) Error upgrading extension '{ext['attributes']['name']}': {str(e)}", style="red")
            if len(rules)>0:
                console.print(f"Syncing {len(rules)} rule{'s' if len(rules) > 1 else ''} from library '{lib.name}'...", style="blue")
                for rule in rules:
                    try:
                        self.synchronizer.syncComponent(componentId=rule['id'], publishedVersion=True, forceCreation=True)
                        console.print(f"Rule '{rule['attributes']['name']}' synced successfully.", style="green")
                    except Exception as e:
                        console.print(f"(!) Error syncing rule '{rule['attributes']['name']}': {str(e)}", style="red")
            if len(dataelements)>0:
                console.print(f"Syncing {len(dataelements)} data element{'s' if len(dataelements) > 1 else ''} from library '{lib.name}'...", style="blue")
                for de in dataelements:
                    try:
                        self.synchronizer.syncComponent(componentId=de['id'], publishedVersion=True, forceCreation=True)
                        console.print(f"Data element '{de['attributes']['name']}' synced successfully.", style="green")
                    except Exception as e:
                        console.print(f"(!) Error syncing data element '{de['attributes']['name']}': {str(e)}", style="red")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
    
    def do_create_libraries(self,args:Any):
        """Create libraries in the destination property based on the libraries in the source property that are selected for synchronization."""
        parser = argparse.ArgumentParser(prog='create_libraries', add_help=True)
        parser.add_argument("name",help="Name for the new library to be created in the destination properties", type=str)
        parser.add_argument("-env",'--environment',help='Boolean. try to find an empty environment to build the library. Default False.',type=bool,default=False)
        try:
            args = parser.parse_args(shlex.split(args))
            res = self.synchronizer.createTargetsLibrary(name=args.name,assignEnv=args.environment)
            console.print_json(json.dumps(res, indent=4))
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return

    def do_exit(self, arg):
        """Return to the main menu."""
        console.print(Panel("Returning to main menu...", style="blue"))
        return True  # Returning True breaks the cmdloop

    def do_EOF(self, args:Any) -> None:
        """Handle Ctrl+D"""
        console.print(Panel("Exiting...", style="blue"))
        return True
        

# --- 2. The Main Interactive Shell ---
class MainShell(cmd.Cmd):
    """Interactive shell for managing Adobe Launch properties."""

    def __init__(self, **kwargs:ParamSpecKwargs) -> None:
        super().__init__()
        self.admin = None
        self.cid = None
        self.properties = None
        if kwargs.get("config_file") is not None:
            config_path = Path(kwargs.get("config_file"))
            if not config_path.is_absolute():
                config_path = Path.cwd() / config_path
            with open(config_path, "rb") as f:
                dict_config = json.load(f)
            self.secret = dict_config.get("secret", kwargs.get("secret"))
            self.org_id = dict_config.get("org_id", kwargs.get("org_id"))
            self.client_id = dict_config.get("client_id", dict_config.get("api_key", kwargs.get("client_id", kwargs.get("api_key"))))
            self.scopes = dict_config.get("scopes", kwargs.get("scopes"))
        else:
            self.secret:str|None = kwargs.get("secret")
            self.org_id:str|None = kwargs.get("org_id")
            self.client_id:str|None = kwargs.get("client_id",kwargs.get("api_key"))
            self.scopes:str|None = kwargs.get("scopes")
        if self.secret is not None and self.org_id is not None and self.client_id is not None and self.scopes is not None:
            console.print("Configuring connection...", style="blue")
            self._configure_connection()
            if kwargs.get("property") is not None:
                console.print(f"Auto-loading property '{kwargs.get('property')}'...", style="blue")
                try:
                    property_name = kwargs.get("property")
                    cid = self.admin.getCompanyId()
                    properties = self.admin.getProperties(cid)
                    if property_name in [prop['attributes']['name'] for prop in properties]:
                        prop_def = [prop for prop in properties if prop['attributes']['name'] == property_name][0]
                        myproperty = launchpy.Property(prop_def)
                        property_shell = PropertyCLI(myproperty)
                        property_shell.cmdloop()
                    else:
                        console.print(f"property '{property_name}' cannot be found.", style="red")
                        return
                except Exception as e:
                    console.print(f"(!) Error loading property: {str(e)}", style="red")
            console.print(Panel(f"Connected to [bold green]launchpy[/bold green]", style="blue"))

    def _configure_connection(self) -> None:
        self.config = launchpy.configure(
            secret=self.secret,
            org_id=self.org_id,
            client_id=self.client_id,
            scopes=self.scopes
        )
        self.admin = launchpy.Admin()
        self.cid = self.admin.getCompanyId()
        self.prompt = "launchpy> "

    def do_create_config_file(self, arg:Any) -> None:
        """Create a configuration file for storing your AEP API connection details."""

        parser = argparse.ArgumentParser(prog='create_config_file', add_help=True)
        parser.add_argument("-fn", "--file_name", help="file name for your config file", default="launchpy_config.json",type=str)
        try:
            args = parser.parse_args(shlex.split(arg))
            filename = args.file_name
            launchpy.createConfigFile(filename=filename)
            filename_json = filename + ".json" if not filename.endswith(".json") else filename
            console.print(f"Configuration file created at {Path.cwd() / Path(filename_json)}", style="green")
            return
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return

    # # --- Commands ---
    def do_config(self, arg:Any) -> None:
        """Pass the different configuration parameters to connect to an AEP instance. Either individually or through a config file with the --config_file option."""
        parser = argparse.ArgumentParser(prog='config', add_help=True)
        parser.add_argument("-s", "--secret", help="Secret")
        parser.add_argument("-o", "--org_id", help="IMS org ID")
        parser.add_argument("-sc", "--scopes", help="Scopes")
        parser.add_argument("-cid", "--client_id", help="client ID")
        parser.add_argument("-cf", "--config_file", help="Path to config file", default=None)
        parser.add_argument("-p", "--property", help="Property Name to auto-load on startup", default=None)
        try:
            args = parser.parse_args(shlex.split(arg))
            if args.config_file is not None:
                config_path = Path(args.config_file)
                if not config_path.is_absolute():
                    config_path = Path.cwd() / config_path
                with open(config_path, "rb") as f:
                    dict_config = json.load(f)
                self.secret = dict_config.get("secret", args.secret)
                self.org_id = dict_config.get("org_id", args.org_id)
                self.client_id = dict_config.get("client_id", dict_config.get("api_key", args.client_id))
                self.scopes = dict_config.get("scopes", args.scopes)
            else:
                if args.secret: self.secret = str(args.secret)
                if args.org_id: self.org_id = str(args.org_id)
                if args.scopes: self.scopes = str(args.scopes)
                if args.client_id: self.client_id = str(args.client_id)

            missing = [
                key for key, value in {
                    "secret": self.secret,
                    "org_id": self.org_id,
                    "client_id": self.client_id,
                    "scopes": self.scopes,
                }.items() if value is None
            ]
            if missing:
                console.print(
                    f"(!) Missing required config values: {', '.join(missing)}",
                    style="red"
                )
                self.config = None
                self.admin = None
                self.cid = None
                return
            console.print("Configuring connection...", style="blue")
            self._configure_connection()
            console.print(Panel(f"Connected to [bold green]launchpy[/bold green]", style="blue"))
            if args.property is not None:
                console.print(f"Auto-loading property '{args.property}'...", style="blue")
                try:
                    property_name = args.property
                    cid = self.admin.getCompanyId()
                    properties = self.admin.getProperties(cid)
                    if property_name in [prop['attributes']['name'] for prop in properties]:
                        prop_def = [prop for prop in properties if prop['attributes']['name'] == property_name][0]
                        myproperty = launchpy.Property(prop_def)
                        property_shell = PropertyCLI(myproperty)
                        property_shell.cmdloop()
                    else:
                        console.print(f"property '{property_name}' cannot be found.", style="red")
                        return
                except Exception as e:
                    console.print(f"(!) Error loading property: {str(e)}", style="red")
            return
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
        
    @login_required
    def do_get_properties(self, arg:Any) -> None:
        """List all properties available in the connected AEP instance."""
        parser = argparse.ArgumentParser(prog='get_properties', add_help=True)
        parser.add_argument("-n", "--name", help="Filter properties by name (partial match, non-case sensitive)", type=str, default=None)
        parser.add_argument("-s", "--save", help="Boolean. Save properties to a CSV file. Default False. Possible values: True, False", type=bool, default=False)
        try:
            args = parser.parse_args(shlex.split(arg))
            properties = self.admin.getProperties(self.cid)
            if args.name:
                properties = [prop for prop in properties if args.name.lower() in prop['attributes']['name'].lower()]
            self.properties = properties
            if len(properties) == 0:
                console.print("No properties found in this instance.", style="yellow")
                return
            table = Table(title="Available Properties")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name", style="magenta")
            for prop in properties:
                prop_id = prop['id']
                prop_name = prop['attributes']['name']
                table.add_row(prop_id, prop_name)
            console.print(table)
            if args.save:
                df = pd.DataFrame([{
                    "id": prop['id'],
                    "name": prop['attributes']['name']
                } for prop in properties])
                df.to_csv("properties.csv", index=False)
                console.print(f"Properties saved to properties.csv", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
    
    @login_required
    def create_property(self, arg:Any) -> None:
        """
        Create a new property in the organization. 
        """
        parser = argparse.ArgumentParser(prog='create_property', add_help=True)
        parser.add_argument("name", help="Name of the new property", type=str)
        parser.add_argument("-d", "--description", help="Description of the new property", type=str, default="")
        parser.add_argument("-p", "--platform", help="Platform of the new property. Default 'web', possible values: 'web', 'mobile'", type=str, default="web")
        try:
            args = parser.parse_args(shlex.split(arg))
            if str(args.name).strip() == "" or args.name is None:
                console.print("(!) Property name cannot be empty.", style="red")
                return
            new_property = self.admin.createProperty(companyId=self.cid, name=args.name, description=args.description,platform=args.platform)
            console.print(f"Property '{args.name}' created with ID: {new_property.id}", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
    
    @login_required
    def do_load_property(self, arg:Any) -> None:
        """Load a property CLI to manage its rules and components."""
        parser = argparse.ArgumentParser(prog='load_property', add_help=True)
        parser.add_argument("name", help="Name of the property to load", type=str)
        try:
            args = parser.parse_args(shlex.split(arg))
            if self.properties is None:
                properties = self.admin.getProperties(self.cid)
                self.properties = properties
            matching_props = [prop for prop in self.properties if prop['attributes']['name'] == args.name]
            if not matching_props:
                console.print(f"Property '{args.name}' not found in this instance.", style="red")
                return
            prop_def = matching_props[0]
            myproperty = launchpy.Property(prop_def)
            property_shell = PropertyCLI(myproperty)
            property_shell.cmdloop()
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
    
    @login_required
    def do_extract_property(self, arg:Any) -> None:
        """Extract all rules and components for a given property into folder."""
        parser = argparse.ArgumentParser(prog='extract_property', add_help=True)
        parser.add_argument("name", help="Name of the property to extract", type=str)
        try:
            args = parser.parse_args(shlex.split(arg))
            if self.properties is None:
                properties = self.admin.getProperties(self.cid)
                self.properties = properties
            matching_props = [prop for prop in self.properties if prop['attributes']['name'] == args.name]
            if not matching_props:
                console.print(f"Property '{args.name}' not found in this instance.", style="red")
                return
            prop_def = matching_props[0]
            myproperty = launchpy.Property(prop_def)
            console.print(f"Extracting property '{args.name}'...", style="blue")
            launchpy.extractProperty(myproperty)
            console.print(f"Extraction completed for property '{args.name}'. Check the folder '{launchpy.__safe_name__(args.name)}' for the output files.", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
    
    @login_required
    def do_delete_property(self, arg:Any) -> None:
        """Delete a property by name."""
        parser = argparse.ArgumentParser(prog='delete_property', add_help=True)
        parser.add_argument("name", help="Name of the property to delete", type=str)
        try:
            args = parser.parse_args(shlex.split(arg))
            if self.properties is None:
                properties = self.admin.getProperties(self.cid)
                self.properties = properties
            matching_props = [prop for prop in self.properties if prop['attributes']['name'] == args.name]
            if not matching_props:
                console.print(f"Property '{args.name}' not found in this instance.", style="red")
                return
            prop_id = matching_props[0]['id']
            self.admin.deleteProperty(prop_id)
            console.print(f"Property '{args.name}' deleted successfully.", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
    
    @login_required
    def do_get_extensions(self, arg:Any) -> None:
        """List all available extensions in the connected Adobe Launch organization."""
        parser = argparse.ArgumentParser(prog='get_extensions', add_help=True)
        parser.add_argument("-s", "--save", help="Boolean. Save extensions to a JSON file. Default False. Possible values: True, False", type=bool, default=False)
        try:
            args = parser.parse_args(shlex.split(arg))
            extensions = self.admin.getExtensionsCatalogue()
            if len(extensions) == 0:
                console.print("No extensions found in this instance.", style="yellow")
                return
            table = Table(title="Available Extensions")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name", style="magenta")
            table.add_column("Version", style="green")
            table.add_column("Current Published State", style="yellow")
            for ext in extensions:
                ext_id = ext['id']
                ext_name = ext['attributes']['name']
                ext_version = ext['attributes']['version']
                ext_current_published_state = str(ext['attributes']['published'])
                table.add_row(ext_id, ext_name, ext_version, ext_current_published_state)
            console.print(table)
            if args.save:
                with open("extensions.json", "w") as f:
                    json.dump(extensions, f, indent=4)
                console.print(f"Extensions saved to extensions.json", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return
    
    @login_required
    def do_load_synchronizer(self, arg:Any) -> None:
        """Load a synchronizer to manage synchronization between different properties."""
        parser = argparse.ArgumentParser(prog='load_synchronizer', add_help=True)
        parser.add_argument("base_name", help="Name of the Launch Property to use as base", type=str)
        parser.add_argument("-t", "--targets", help="list of target property names for synchronization", nargs='+', type=str, default=None)
        parser.add_argument("-dy","--dynamic_component", help="Name of the Data Element that would contain dynamic component rules", type=str, default=None)
        try:
            args = parser.parse_args(shlex.split(arg))
            if args.targets is None:
                console.print("(!) Please provide at least one target property name using the -t or --targets option.", style="red")
                return
            synchronizer = launchpy.Synchronizer(base=args.base_name, targets=args.targets, dynamicRuleComponent=args.dynamic_component)
            synchronizer_shell = SynchronizerCLI(synchronizer)
            synchronizer_shell.cmdloop()
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
            return
        except SystemExit:
            return

    def do_exit(self, arg:Any) -> bool:
        """Exit the application."""
        console.print(Panel("Exiting...", style="blue"))
        return True  # Returning True breaks the cmdloop
    
    def do_EOF(self, args:Any) -> None:
        """Handle Ctrl+D"""
        console.print(Panel("Exiting...", style="blue"))
        return True

def main():
    # ARGPARSE: Handles the initial setup flags
    parser = argparse.ArgumentParser(description="Interactive Client Tool",add_help=True)
    
    # Optional: Allow passing user/pass via flags to skip the interactive login step
    parser.add_argument("-s", "--secret", help="Secret")
    parser.add_argument("-o", "--org_id", help="Auto-login org ID")
    parser.add_argument("-sc", "--scopes", help="Scopes")
    parser.add_argument("-cid", "--client_id", help="Auto-login client ID")
    parser.add_argument("-cf", "--config_file", help="Path to config file", default=None)
    parser.add_argument("-p", "--property", help="Property Name to auto-load on startup", default=None)
    args = parser.parse_args() 
    shell = MainShell(**vars(args))
    try:
        shell.cmdloop()
    except KeyboardInterrupt:
        console.print(Panel("\nForce closing...", style="red"))

if __name__ == "__main__":
    main()