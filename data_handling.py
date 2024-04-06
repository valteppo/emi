"""
Maintains data.
"""

import os
import urllib.request
import sqlite3
import zipfile
import yaml
import json

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
        # Unique region and system name dict formation
        with openzip.open("sde/bsd/invUniqueNames.yaml") as unique_names:
            location_name_data = yaml.safe_load(unique_names)
        location_names = {}
        for dataline in location_name_data:
            location_names[dataline["itemID"]] = dataline["itemName"]

        # Main operation
        for filename in openzip.namelist():
            tokens = filename.split("/")
            # Regions
            if len(tokens) >= 4: 
                if tokens[2] == "universe" and tokens[-1] == "region.staticdata":
                    with openzip.open(filename) as file:
                        data = file.read().decode()
                        index_str = "regionID: "
                        region_id = int(data[data.find(index_str):data.find("\n", data.find(index_str)+len(index_str))].split(" ")[1])
                        translator_location[region_id] = location_names[region_id]
                if tokens[3] == "eve" and tokens[-1] == "region.staticdata":
                    kspace.append(region_id)
        
            # Solarsystems
            if len(tokens) == 8 and tokens[-1] == "solarsystem.staticdata": 
                with openzip.open(filename) as file:
                    data = file.read().decode()
                    index_str = "solarSystemID: "
                    solar_system_ID = int(data[data.find(index_str):data.find("\n", data.find(index_str)+len(index_str))].split(" ")[1])
                    translator_location[solar_system_ID] = location_names[solar_system_ID]

        # Exit for loop and handle item IDs:
        with openzip.open("sde/fsd/typeIDs.yaml", "r") as raw_yaml:
            type_IDs = yaml.safe_load(raw_yaml)

    for typeID in type_IDs:
        this_typeID = type_IDs[typeID]
        if this_typeID["published"] == True:
            translator_items[typeID] = this_typeID["name"]["en"]

    with open(os.getcwd()+"/data/translator_location.tsv", "w") as csvout:
        for key in translator_location:
            csvout.write(f"{str(key)}\t{translator_location[key]}\n")

    with open(os.getcwd()+"/data/translator_items.tsv", "w") as csvout:
        for key in translator_items:
            csvout.write(f"{str(key)}\t{translator_items[key]}\n")
            
    with open(os.getcwd()+"/data/k-spaceRegions.tsv", "w") as csvout:
        for region in kspace:
            csvout.write(f"{str(region)}\t{location_names[region]}\n")

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

def market_groups():
    """
    Retrieves marketgroups from esi.
    """
    req = urllib.request.Request(url="https://esi.evetech.net/latest/markets/groups/?datasource=tranquility", method="GET")
    res = json.load(urllib.request.urlopen(req))
    return res

def vetted_groups():
    """
    Market groups that make sense.
    """
    with open(os.getcwd()+"/data/groupIDs.yaml", "r", encoding="utf8") as file:
        data = yaml.safe_load(file.read())
    
    my_catIDs = [4, 6, 7, 8, 17, 18, 20, 22, 25, 32, 34, 35, 41, 42, 43, 46, 65, 66, 87]
    my_groups = []
    for line in data:
        if data[line]["categoryID"] in my_catIDs and data[line]["published"]:
            my_groups.append(line)
    return my_groups

def link_typeID_group():
    """
    Links typeID to groupID. Saves as tsv.
    """
    linked = {}
    with zipfile.ZipFile(os.getcwd()+"/data/sde.zip", "r") as openzip:
        with openzip.open("sde/fsd/typeIDs.yaml", "r") as raw_yaml:
                type_IDs = yaml.safe_load(raw_yaml)

    for typeID in type_IDs:
        this_typeID = type_IDs[typeID]
        if this_typeID["published"] == True:
            linked[typeID] = type_IDs[typeID]["groupID"]
    
    with open(os.getcwd()+"/data/typeID_groupID.tsv", "w") as file:
        for typeID in linked:
            file.write(f"{str(typeID)}\t{str(linked[typeID])}\n")

def build_location_info_db():
    """
    Makes database for info searching.
        INFO:
        - System ID
        - Constellation ID
        - Region ID
        - Security Status
        - Connections (system ID)
        - Station IDs

    Split to tables locations, connections, stations
    """
    cwd = os.getcwd()
    try:
        os.remove(cwd+"\data\location.db") # refresh
    except:
        pass
    conn = sqlite3.connect(cwd+"/data/location.db")
    cur = conn.cursor()
    # Location table
    cmd =   "CREATE TABLE IF NOT EXISTS \
            locations (system_id int, constellation_id int, region_id int, security float)"
    cur.execute(cmd)
    # Connections
    cmd =   "CREATE TABLE IF NOT EXISTS \
            connections (system_id int, connection_id int)"
    cur.execute(cmd)
    # Stations
    cmd =   "CREATE TABLE IF NOT EXISTS \
            stations (system_id int, station_id int, station_name text)"
    cur.execute(cmd)

    regions_data = {}
    constellations_data = {}
    systems = {}
    gate_connections = []

    with zipfile.ZipFile(cwd+"/data/sde.zip") as openzip:
        for filename in openzip.namelist():
            tokens = filename.split("/")
            # Systems
            if len(tokens) == 8 and tokens[-1] == "solarsystem.staticdata":
                # Register regions in order not to reopen files constantly
                if tokens[-4] not in regions_data:
                    file_path = "/".join(tokens[:5])+"/region.staticdata"
                    with openzip.open(file_path) as region_raw:
                        this_region_data = region_raw.read().decode()
                    index_str = "regionID: "
                    region_id = int(this_region_data[this_region_data.find(index_str):this_region_data.find("\n", this_region_data.find(index_str)+len(index_str))].split(" ")[1])
                    regions_data[tokens[-4]] = region_id
                
                # Also register constellations
                if tokens[-3] not in constellations_data:
                    file_path = "/".join(tokens[:6])+"/constellation.staticdata"
                    with openzip.open(file_path) as constellation_raw:
                        this_constellation_data = constellation_raw.read().decode()
                    index_str = "constellationID: "
                    constellation_id = int(this_constellation_data[this_constellation_data.find(index_str):this_constellation_data.find("\n", this_constellation_data.find(index_str)+len(index_str))].split(" ")[1])
                    constellations_data[tokens[-3]] = constellation_id

                # Process system file
                with openzip.open(filename) as file:
                    system_data = yaml.safe_load(file)
                system_id = int(system_data["solarSystemID"])
                constellation_id = constellations_data[tokens[-3]]
                region_id = regions_data[tokens[-4]]
                security = float(system_data["security"])

                # Form system data
                systems[system_id] = {
                    "constellation_id":constellation_id,
                    "region_id":region_id,
                    "security":security
                }

                # Form connection data and gate-system translation table
                for gate in system_data["stargates"]:
                    gate_connections.append([system_id, int(gate), int(system_data["stargates"][gate]["destination"])])
                    

        # Stations
        stations = []
        with openzip.open("sde/bsd/staStations.yaml") as station_file:
            station_data = yaml.safe_load(station_file)
        for station in station_data:
            station_id = int(station["stationID"])
            system_id = int(station["solarSystemID"])
            station_name = station["stationName"]
            stations.append({ "system_id":system_id,
                              "station_id":station_id,
                              "station_name":station_name})
    
    # Submit location data
    for system in systems:
        cur.execute("INSERT INTO locations (system_id, constellation_id, region_id, security) \
                    VALUES \
                    (?, ?, ?, ?)", \
                        (system, 
                        systems[system]["constellation_id"],
                        systems[system]["region_id"],
                        systems[system]["security"]))
    conn.commit()

    # Connection finalization
    gate_system_translation = {}
    for connection_line in gate_connections:
        gate_system_translation[connection_line[1]] = connection_line[0]

    # Submit connections
    for connection_line in gate_connections:
        cur.execute("INSERT INTO connections (system_id, connection_id) \
                            VALUES \
                            (?, ?)", (connection_line[0], gate_system_translation[connection_line[2]]))
    conn.commit()

    # Submit stations
    for station in stations:
        cur.execute("INSERT INTO stations (system_id, station_id, station_name) \
                    VALUES \
                    (?, ?, ?)", (station["system_id"],
                                 station["station_id"],
                                 station["station_name"]))
    conn.commit()
    conn.close()
