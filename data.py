"""
Maintains data.
"""

import os
import urllib.request
import zipfile
import yaml
import re

def maintain_sde()-> None:
    """
    Assures up-to-date SDE. Does nothing if everything up to date.
    """
    dir = os.getcwd()
    try:
        os.mkdir(dir+"\\data")
    except FileExistsError:
        pass
    datadir = dir + "\\data\\"
    checksum = ""

    # if no files, download
    if not os.path.exists(datadir+"sde.zip"):
        urllib.request.urlretrieve("https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/sde.zip", datadir+"\\sde.zip")
    if not os.path.exists(datadir+"checksum"):
        urllib.request.urlretrieve("https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/checksum", datadir+"\\checksum")

    # verify checksum validity
    modified_since_seconds = os.path.getmtime(datadir+"checksum")
    if modified_since_seconds > 60*60*24: # only once a day
        checksum = open(datadir+"checksum").read()
        urllib.request.urlretrieve("https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/checksum", datadir+"\\new_checksum")
        new_checksum = open(datadir+"\\new_checksum").read()
        if checksum != new_checksum:
            urllib.request.urlretrieve("https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/sde.zip", datadir+"\\sde.zip")
        os.remove(datadir+"\\checksum")
        os.rename(datadir+"\\new_checksum", datadir+"\\checksum")

def id_translator_constructor() -> None:
    """
    Saves typeID to item name translations in form
    {typeID}\t{item name}\n
    to translator.tsv file.

    Additionally saves list of k-space regions in form
    {region name}\n
    to k-spaceRegions.tsv file.
    """
    translator_location = {}
    translator_items = {}
    kspace = []

    maintain_sde() # assure

    with zipfile.ZipFile(os.getcwd()+"/data/sde.zip", "r") as openzip:
        for filename in openzip.namelist():
            tokens = filename.split("/")

            # Regions
            if len(tokens) >= 4: 
                if tokens[2] == "universe" and tokens[-1] == "region.staticdata":
                    with openzip.open(filename) as file:
                        data = file.read().decode()
                        index_str = "regionID: "
                        region_id = data[data.find(index_str):data.find("\n", data.find(index_str)+len(index_str))].split(" ")[1]
                        translator_location[region_id] = tokens[4]
                if tokens[3] == "eve" and tokens[-1] == "region.staticdata":
                    kspace.append(tokens[4])
        
            # Solarsystems
            if len(tokens) == 8 and tokens[-1] == "solarsystem.staticdata": 
                with openzip.open(filename) as file:
                    data = file.read().decode()
                    index_str = "solarSystemID: "
                    solar_system_ID = data[data.find(index_str):data.find("\n", data.find(index_str)+len(index_str))].split(" ")[1]
                    translator_location[solar_system_ID] = tokens[-2]

        # Exit for loop and handle item IDs:
        with openzip.open("sde/fsd/categoryIDs.yaml", "r") as raw_yaml:
            category_IDs = yaml.safe_load(raw_yaml)
        with openzip.open("sde/fsd/groupIDs.yaml", "r") as raw_yaml:
            group_IDs = yaml.safe_load(raw_yaml)
        with openzip.open("sde/fsd/typeIDs.yaml", "r") as raw_yaml:
            type_IDs = yaml.safe_load(raw_yaml)

    # Approve marketable items only.
    approved_categories = []
    for category in category_IDs:
        if category_IDs[category]["published"] == True and category >= 4:
            approved_categories.append(category)

    approved_groups = []
    for group in group_IDs:
        this_group = group_IDs[group]
        if this_group["categoryID"] in approved_categories and this_group["published"] == True:
            approved_groups.append(group)

    for typeID in type_IDs:
        this_typeID = type_IDs[typeID]
        if this_typeID["groupID"] in approved_groups and this_typeID["published"] == True:
            translator_items[typeID] = this_typeID["name"]["en"]

    with open(os.getcwd()+"/data/translator_location.tsv", "w") as csvout:
        for key in translator_location:
            csvout.write(f"{key}\t{translator_location[key]}\n")

    with open(os.getcwd()+"/data/translator_items.tsv", "w") as csvout:
        for key in translator_items:
            csvout.write(f"{key}\t{translator_items[key]}\n")
            
    with open(os.getcwd()+"/data/k-spaceRegions.tsv", "w") as csvout:
        csvout.write("\n".join(kspace))

def translator_location() -> dict:
    """
    Returns translator dict for locations. 
    If given typeID, outputs system/region name. 
    If given system/region name (accurate), outputs typeID.
    {string : string}
    """
    translator = {}
    with open(os.getcwd()+"/data/translator_location.tsv", "r") as file:
        data = file.read().strip().split("\n")

    for line in data:
        typeID, item_name = line.split("\t")
        translator[typeID] = item_name
        translator[item_name] = typeID
    return translator

def translator_items() -> dict:
    """
    Returns translator dict for market items. 
    If given typeID, outputs item name. 
    If given item name (accurate), outputs typeID.
    {string : string}
    """
    translator = {}
    with open(os.getcwd()+"/data/translator_items.tsv", "r") as file:
        data = file.read().strip().split("\n")

    for line in data:
        typeID, item_name = line.split("\t")
        translator[typeID] = item_name
        translator[item_name] = typeID
    return translator
