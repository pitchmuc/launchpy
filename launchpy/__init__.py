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
import re
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

def extractProperty(property: dict | Property):
    if property is None:
        raise ValueError("Property is None")
    elif type(property) is not Property and type(property) is dict:
        if 'attributes' in property.keys() and 'id' in property.keys() and 'relationships' in property.keys():
            property = Property(property)
        else:
            raise ValueError("Property is not of type Property")
    folder = __safe_name__(property.name)
    Path(folder).mkdir(parents=True, exist_ok=True)
    rules = property.getRules()
    asyncio.run(process_all_rules(rules, folder, property.header))