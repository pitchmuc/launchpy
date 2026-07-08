# -*- coding: utf-8 -*-
"""
May  15 12:04:49 2019
@author: Julien Piccini
"""
from launchpy.__version__ import __version__
from launchpy.configs import *
from launchpy.library import Library
from launchpy.admin import Admin
from launchpy.property import Property
from launchpy.synchronizer import Synchronizer
import re,json
from pathlib import Path
import httpx, asyncio


def __safe_name__(name: str):
    if name is None:
        raise ValueError("Name is None")
    elif type(name) is not str:
        raise ValueError("Name is not of type str")
    valid_chars = "[^a-zA-Z0-9_\n\\.]"
    text = re.sub(valid_chars, "_", name)
    return text.strip().lower()

# 1. Make the function 'async'
async def __extractRuleComponents__(rule: dict, client: httpx.AsyncClient, folder: str, header: dict):
    rule_url = rule['relationships']['rule_components']['links']['related']
    rule_name = __safe_name__(rule['attributes']['name'])
    rule_folder = Path(folder) / rule_name
    rule_folder.mkdir(parents=True, exist_ok=True)
    # 2. Use 'await' with the shared client
    response = await client.get(rule_url, headers=header,timeout=httpx.Timeout(60.0, pool=None))
    if response.status_code == 200:
        components = response.json().get('data', [])
        for component in components:
            component_name = __safe_name__(component['attributes']['name'])
            file_path = rule_folder / f"{component_name}.json"
            # Note: For massive scale, look into 'aiofiles' for async writing, 
            # but standard open() is usually fine for small JSON files.
            with open(file_path, "w") as f:
                json.dump(component, f, indent=4)

# 3. Use an orchestrator instead of ThreadPoolExecutor
async def process_all_rules(rules_list, folder, header):
    timeout = httpx.Timeout(10.0, read=120.0)
    limits = httpx.Limits(max_connections=100, max_keepalive_connections=50)
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        # Create a list of "tasks" to run
        tasks = [__extractRuleComponents__(rule, client, folder, header) for rule in rules_list]
        # 'gather' runs them all concurrently
        await asyncio.gather(*tasks)


async def write_all_data_elements(data_elements_list, folder, header):
    for data_element in data_elements_list:
        data_element_name = __safe_name__(data_element['attributes']['name'])
        file_path = Path(folder) / f"{data_element_name}.json"
        with open(file_path, "w") as f:
            json.dump(data_element, f, indent=4)


def extractProperty(property: dict | Property, publishedVersion: bool = False,folder: str = None):
    """
    Extract the rules, Data Elements and Extensions configuration for a given property and save them in a folder named after the property.
    Arguments:
        property: dict | Property: The property to extract. Can be a Property object or a dictionary containing the property data.
        publishedVersion: bool: If True, only the latest published version of each rule will be extracted. If False, all rules as latest state will be extracted.
            For rules that are not yet published, the latest state will be extracted regardless of the value of this parameter.
        folder : str: The folder where the property will be extracted. If None, a folder named after the property will be created in the current working directory.
    """
    if property is None:
        raise ValueError("Property is None")
    elif type(property) is not Property and type(property) is dict:
        if 'attributes' in property.keys() and 'id' in property.keys() and 'relationships' in property.keys():
            property = Property(property)
        else:
            raise ValueError("Property is not of type Property")
    if folder is None:
        folder = __safe_name__(property.name)
    Path(folder).mkdir(parents=True, exist_ok=True)
    rules = property.getRules()
    if publishedVersion:
        published_rules = []
        for rule in rules:
            revisions = property.getRevisions(rule)
            try:
                publishedRule = property.getLatestPublishedVersion(revisions)
                published_rules.append(publishedRule)
            except Exception as e:
                published_rules.append(rule)
        rules = published_rules
    asyncio.run(process_all_rules(rules, folder, property.header))
    dataElements = property.getDataElements()
    if publishedVersion:
        published_data_elements = []
        for data_element in dataElements:
            revisions = property.getRevisions(data_element)
            try:
                publishedDataElement = property.getLatestPublishedVersion(revisions)
                published_data_elements.append(publishedDataElement)
            except Exception as e:
                published_data_elements.append(data_element)
        dataElements = published_data_elements
    dataElements_folder = Path(folder) / "data_elements"
    Path(dataElements_folder).mkdir(parents=True, exist_ok=True)
    asyncio.run(write_all_data_elements(dataElements, dataElements_folder, property.header))
    extension_folder = Path(folder) / "extensions"
    extension_folder.mkdir(parents=True, exist_ok=True)
    extensions = property.getExtensions()
    if publishedVersion:
        published_extensions = []
        for extension in extensions:
            revisions = property.getRevisions(extension)
            try:
                publishedExtension = property.getLatestPublishedVersion(revisions)
                published_extensions.append(publishedExtension)
            except Exception as e:
                published_extensions.append(extension)
        extensions = published_extensions
    for extension in extensions:
        extension_name = __safe_name__(extension['attributes']['name'])
        file_path = extension_folder / f"{extension_name}.json"
        with open(file_path, "w") as f:
            json.dump(extension, f, indent=4)