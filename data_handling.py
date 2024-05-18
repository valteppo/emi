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
    Saves translations:

    type_id, type_name
        /data/item.db
            table: item_translation

    location_id, location_name
        /data/location.db
            table: location_translation

    Saves k-space regions to:
            /data/location.db
                table: k_space_regions

    Also saves item sizes to:
        /data/item.db
            table: size
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

    size = {}
    for typeID in type_IDs:
        this_typeID = type_IDs[typeID]
        if this_typeID["published"] == True:
            translator_items[typeID] = this_typeID["name"]["en"]
            if "volume" in this_typeID:
                size[typeID] = this_typeID["volume"]

    # Save items:
    cwd = os.getcwd()
    conn = sqlite3.connect(cwd+"/data/item.db")
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS item_translation")
    cur.execute("CREATE TABLE item_translation (type_id int, type_name text)")
    for key in translator_items:
        cur.execute("INSERT INTO item_translation (type_id, type_name) VALUES \
                    (?, ?)", (key, translator_items[key]))
    conn.commit()

    # Save sizes
    cur.execute("DROP TABLE IF EXISTS size")
    cur.execute("CREATE TABLE size (type_id int, size float)")
    for key in size:
        cur.execute("INSERT INTO size (type_id, size) VALUES \
                    (?, ?)", (key, size[key]))
    conn.commit()
    conn.close()

    # Save locations:
    conn = sqlite3.connect(cwd+"/data/location.db")
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS location_translation")
    cur.execute("CREATE TABLE location_translation (location_id int, location_name text)")
    for key in translator_location:
        cur.execute("INSERT INTO location_translation (location_id, location_name) VALUES \
                    (?, ?)", (key, translator_location[key]))
    conn.commit()

    # Save k-space region list:
    cur.execute("DROP TABLE IF EXISTS k_space_regions")
    cur.execute("CREATE TABLE k_space_regions (region_id int)")
    for region in kspace:
        cur.execute("INSERT INTO k_space_regions (region_id) VALUES \
                    (?)", (region, ))
    conn.commit()
    conn.close()


def translator_location() -> dict:
    """
    Returns translator dict for locations. 
    If given typeID, outputs system/region name. 
    If given system/region name (accurate), outputs typeID.
    {string : string}
    """
    translator = {}
    conn = sqlite3.connect(os.getcwd()+"/data/location.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM location_translation")
    data = cur.fetchall()
    conn.close()

    for line in data:
        typeID, item_name = line
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
    conn = sqlite3.connect(os.getcwd()+"/data/item.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM item_translation")
    data = cur.fetchall()
    conn.close()

    for line in data:
        typeID, item_name = line
        translator[typeID] = item_name
        translator[item_name] = typeID
    return translator

def get_size():
    """
    Dictionary gives sizes to items.
    Returns a dictionary that:

    Given typeID, outputs size in m^3.
    """
    size = {}
    conn = sqlite3.connect(os.getcwd()+"/data/item.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM size")
    data = cur.fetchall()
    conn.close()

    for line in data:
        typeID, item_size = line
        size[typeID] = item_size
    return size


def vetted_groups_construction():
    """
    Save market groups that make sense.
    """
    with zipfile.ZipFile(os.getcwd()+"/data/sde.zip") as openzip:
        with openzip.open("sde/fsd/groupIDs.yaml") as file:
            data = yaml.safe_load(file.read())
    
    my_catIDs = [4, 6, 7, 8, 17, 18, 20, 22, 25, 32, 34, 35, 41, 42, 43, 46, 65, 66, 87]
    my_groups = []
    for line in data:
        if data[line]["categoryID"] in my_catIDs and data[line]["published"]:
            my_groups.append(line)
    
    conn = sqlite3.connect(os.getcwd()+"/data/item.db")
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS vetted_groups")
    cur.execute("CREATE TABLE vetted_groups (group_id int)")
    for group in my_groups:
        cur.execute("INSERT INTO vetted_groups (group_id) VALUES \
                    (?)", (group, ))
    conn.commit()
    conn.close()


def link_typeID_group():
    """
    Links typeID to groupID.

    type_id, group_id
        /data/item.db
            table: typeID_group
    """
    linked = {}
    with zipfile.ZipFile(os.getcwd()+"/data/sde.zip", "r") as openzip:
        with openzip.open("sde/fsd/typeIDs.yaml", "r") as raw_yaml:
                type_IDs = yaml.safe_load(raw_yaml)

    for typeID in type_IDs:
        this_typeID = type_IDs[typeID]
        if this_typeID["published"] == True:
            linked[typeID] = type_IDs[typeID]["groupID"]
    
    conn = sqlite3.connect(os.getcwd()+"/data/item.db")
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS typeID_group")
    cur.execute("CREATE TABLE typeID_group (type_id int, group_id int)")
    
    for typeID in linked:
        cur.execute("INSERT INTO typeID_group (type_id, group_id) VALUES \
                    (?, ?)", (typeID, linked[typeID]))
    conn.commit()
    conn.close()


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

def orders_clean_up():
    """
    Removes old order tables from regional databases. Leaves only the freshest.
    """
    cwd = os.getcwd()
    order_databases = os.listdir(cwd+"/market/orders/")
    for database in order_databases:
        conn = sqlite3.connect(cwd+"/market/orders/"+database)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC")
        tables = [i[0] for i in cur.fetchall()]
        if len(tables)>1:
            for i in range(1, len(tables)):
                cur.execute(f"DROP TABLE {tables[i]}")
        cur.execute("VACUUM")
        conn.close()

def history_clean_up():
    """
    Removes old volume tables from volume histories. Leaves only the freshest.
    """
    cwd = os.getcwd()
    history_databases = os.listdir(cwd+"/market/history/")
    for database in history_databases:
        conn = sqlite3.connect(cwd+"/market/history/"+database)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC")
        tables = [i[0] for i in cur.fetchall()]
        if len(tables)>1:
            for i in range(1, len(tables)):
                cur.execute(f"DROP TABLE {tables[i]}")
        cur.execute("VACUUM")
        conn.close()

def get_k_space_regions():
    """
    Returns the list of k-space regions.
    """
    conn = sqlite3.connect(os.getcwd()+"/data/location.db")
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM k_space_regions")
    k_space_regions = [i[0] for i in cur.fetchall()]
    conn.close()
    return k_space_regions

def get_vetted_groups():
    """
    Returns a list of items ok for trading.
    """
    conn = sqlite3.connect(os.getcwd()+"/data/item.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM vetted_groups")
    vetted_groups = [i[0] for i in cur.fetchall()]
    conn.close()
    return vetted_groups

def typeID_groupID_translator():
    """
    Returns a dict that translates type_id to group_id.
    """
    conn = sqlite3.connect(os.getcwd()+"/data/item.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM typeID_group")
    group_linking_data = cur.fetchall()
    translate_typeID_groupID = {}
    for line in group_linking_data:
        type_id, group_id = line
        translate_typeID_groupID[type_id] = group_id
    conn.close()
    return translate_typeID_groupID

def get_region_prices(region_id):
    """
    Returns a dictionary that has regional sell and buy prices for items.
    """
    cwd = os.getcwd()
    conn = sqlite3.connect(cwd+f"/market/orders/{region_id}.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC")
    tables = [i[0] for i in cur.fetchall()]
    latest = tables[0]
    if len(latest) == 0:
        return {}
    
    cmd = f"""SELECT buy.type_id as type_id, buy.buy_price as buy_price, sell.sell_price as sell_price FROM 
                (SELECT type_id, MAX(price) AS buy_price FROM {latest} WHERE is_buy_order = 1 GROUP BY type_id) AS buy
            JOIN 
                (SELECT type_id, MIN(price) AS sell_price FROM {latest} WHERE is_buy_order = 0 GROUP BY type_id) AS sell
            ON buy.type_id = sell.type_id 
            GROUP BY buy.type_id;"""
    cur.execute(cmd)
    data = cur.fetchall()
    conn.close()

    results = {}
    for line in data:
        type_id, buy_price, sell_price = line
        results[type_id] = {"buy":buy_price,
                            "sell":sell_price}
    return results

def get_region_main_hubs(region_id):
    """
    Returns an ordered list of systems with the most player orders.
    """
    cwd = os.getcwd()
    conn = sqlite3.connect(cwd+f"/market/orders/{region_id}.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC")
    tables = [i[0] for i in cur.fetchall()]
    latest = tables[0]
    if len(latest) == 0:
        return []
    cmd =   f"""SELECT system_id FROM (
                        SELECT 
                            system_id, 
                            COUNT(order_id) as order_count 
                        FROM {latest}
                        WHERE duration < 91
                        GROUP BY system_id 
                        ORDER BY order_count DESC
                        )"""
    cur.execute(cmd)
    res = [i[0] for i in cur.fetchall()]
    conn.close()
    return res

def get_region_volumes(region_id, volume_day_history=15):
    """
    Fetches regional buy and sell volumes.
    """
    cwd = os.getcwd()
    conn = sqlite3.connect(cwd+f"/market/history/{region_id}.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC")
    tables = [i[0] for i in cur.fetchall()]
    latest = tables[0]
    cur.execute(f"""SELECT
                        buy_data.type_id,
                        buy_data.buy,
                        sell_data.sell
                    FROM (
                            (SELECT 
                                type_id, 
                                SUM(eff_vol)/{volume_day_history} as buy
                            FROM (
                                SELECT
                                    type_id, lowest, average, highest, volume,
                                    ((average-lowest) / average) * ({latest}.volume / 2) AS eff_vol
                                FROM {latest} 
                                WHERE strftime('%s', 'now') - date < 60*60*24*{volume_day_history}
                            )
                            GROUP BY type_id) AS buy_data
                        JOIN
                            (SELECT 
                                type_id, 
                                SUM(eff_vol)/{volume_day_history} as sell
                            FROM (
                                SELECT
                                    type_id, lowest, average, highest, volume,
                                    ((highest-average) / average) * ({latest}.volume / 2) AS eff_vol
                                FROM {latest} 
                                WHERE strftime('%s', 'now') - date < 60*60*24*{volume_day_history}
                            )
                            GROUP BY type_id) AS sell_data
                        ON buy_data.type_id = sell_data.type_id
                    )
                    """)
    volume_data = cur.fetchall()
    volume = {}
    for line in volume_data:
        type_id, buy_volume, sell_volume = line
        volume[type_id] =   {"buy_vol":buy_volume,
                            "sell_vol":sell_volume}
    conn.close()
    return volume