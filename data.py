"""
Maintains data.
"""

import os
import urllib.request
import zipfile
import yaml

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

def id_translation_files() -> None:
    """
    Saves regionID and solarsystemID csv files for decoding region/system names to IDs.
    Additionally saves csv file for all k-space regions.
    """

    regions = {}
    solar_systems = {}
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
                        regions[tokens[4]] = region_id
                if tokens[3] == "eve" and tokens[-1] == "region.staticdata":
                    kspace.append(tokens[4])
        
            # Solarsystems
            if len(tokens) == 8 and tokens[-1] == "solarsystem.staticdata": 
                with openzip.open(filename) as file:
                    data = file.read().decode()
                    index_str = "solarSystemID: "
                    solar_system_ID = data[data.find(index_str):data.find("\n", data.find(index_str)+len(index_str))].split(" ")[1]
                    solar_systems[tokens[-2]] = solar_system_ID
        # Exit for loop and handle item IDs:
        # TODO
            

    with open(os.getcwd()+"/data/regionID.csv", "w") as csvout:
        for region in regions:
            csvout.write(f"{region},{regions[region]}\n")

    with open(os.getcwd()+"/data/solarsystemID.csv", "w") as csvout:
        for system in solar_systems:
            csvout.write(f"{system},{solar_systems[system]}\n")
    
    with open(os.getcwd()+"/data/k-spaceRegions.csv", "w") as csvout:
        csvout.write("\n".join(kspace))

id_translation_files()