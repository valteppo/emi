"""
Universe related functions
"""

import zipfile
import os
import yaml
from collections import deque
import json
import sqlite3
import requests
import copy
import time

from data import translator_location

def system_connections_builder():
    """
    Goes through the sde, lists in a dictionary what connections system has, saves to tsv with region and security.
    Format:
    [system name\tRegion\tSecurity\t[Connected system, ... , ...]]
    Takes time. Approx system count = 5200.
    """
    cwd = os.getcwd()

    jove = ["J7HZ-F", "A821-A", "UUA-F4"]
    system_gates = {}
    gates_systems = {}
    gate_gate = {}
    security = {}
    region = {}
    temp_counter = 0

    # Extract data
    with zipfile.ZipFile(cwd+"/data/sde.zip", "r") as openzip:
        for filename in openzip.namelist():
            tokens = filename.split("/")
            if len(tokens) > 6:
                if tokens[-5] == "eve" and tokens[-1] == "solarsystem.staticdata" and tokens[-4] not in jove:
                    with openzip.open(filename) as yaml_step:
                        system_data = yaml.safe_load(yaml_step)
                        system_name = tokens[-2]
                        region[system_name] = tokens[-4]
                        system_gates[system_name] = []
                        security[system_name] = system_data["security"]
                        for start_gate in system_data["stargates"]:
                            end_gate = system_data["stargates"][start_gate]["destination"]
                            gates_systems[start_gate] = system_name
                            gate_gate[start_gate] = end_gate
                            gate_gate[end_gate] = start_gate
                            system_gates[system_name].append(start_gate)
                        temp_counter += 1
                        if temp_counter % 10 == 0:
                            print("Systems handled",temp_counter,"/ 5210", end="\r")
    
    print("Translating and saving...", end="")
    # Translate
    named_connections = {}
    for system in system_gates:
        named_connections[system] = []
        for start_gate in system_gates[system]:
            end_gate = gate_gate[start_gate]
            named_connections[system].append(gates_systems[end_gate])
    
    # Save
    with open(cwd+"/data/system_connections.tsv", "w") as file:
        for system in named_connections:
            file.write(f"{system}\t{region[system]}\t{security[system]}\t{named_connections[system]}\n")
    print("done.")

def route(start, target, hisec_only = True, blocklist = []):
    """
    Finds a route to system. Supports hisec route only (on by default) and block list.
    Start and target parameters need to be folder-type exact names of systems.

    Returns [number of jumps, [Start system, ... , end system]] on success.
    Returns [0, [start system]] if start and end the same.
    Returns [0, []] if no route.
    """
    cwd = os.getcwd()
    with open(cwd+"/data/system_connections.tsv", "r") as file:
        data = file.read().strip().split("\n")
    
    connections = {}
    for line in data:
        system, region, security, gates = line.split("\t")
        gates = gates.replace('\'', '"')
        gates = json.loads(gates) # Shameful
        connections[system] = {"security":security,
                               "region":region,
                               "gates":gates}
    
    searcing = True
    systems_visited = []
    up_node = {} # Marks the route back.
    up_node[start] = ""
    queue = deque()
    queue.append(start)
    result = []
    while searcing:
        if len(queue) > 0: # Work the queue
            this_node = queue.popleft()
            if this_node not in systems_visited:
                systems_visited.append(this_node)
                if this_node != target: # Keep searching
                    connected_systems = connections[this_node]["gates"]
                    for system in connected_systems:
                        if hisec_only:
                            if float(connections[system]["security"]) > 0.45 and system not in systems_visited and system not in blocklist:
                                up_node[system] = this_node
                                queue.append(system)
                        else:
                            if system not in systems_visited and system not in blocklist:
                                up_node[system] = this_node
                                queue.append(system)
                else: # System found
                    queue = deque()
                    searcing = False
                    while this_node != "":
                        result.append(this_node)
                        this_node = up_node[this_node]
                    result.reverse()
        else: # Queue exhausted without results
            searcing = False

    return [len(result)-1, result]


def download_kills():
    """
    Downloads the kills from esi. Sums kills to kills table.
    No regards to rate, so useful as normalized output.
    """
    cwd = os.getcwd()
    conn = sqlite3.connect(cwd+"/data/kills.db")
    cur = conn.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS kills (npc_kills int, pod_kills int, ship_kills int, system_id int UNIQUE)")

    r = requests.get(url="https://esi.evetech.net/latest/universe/system_kills/?datasource=tranquility")    
    data = r.json()
    cmd = "INSERT INTO kills (npc_kills, pod_kills, ship_kills, system_id)\
            VALUES (:npc_kills, :pod_kills, :ship_kills, :system_id)\
            ON CONFLICT(system_id)\
            DO UPDATE SET   npc_kills = npc_kills + :npc_kills,\
                            pod_kills = pod_kills + :pod_kills,\
                            ship_kills = ship_kills + :ship_kills" # noice
    cur.executemany(cmd, data)
    conn.commit()
    conn.close()

def construct_systems_with_stations():
    """
    Saves a list of systems with stations.
    """
    location_translation = translator_location()
    cwd = os.getcwd()

    with zipfile.ZipFile(cwd+"/data/sde.zip", "r") as openzip:
        with openzip.open("sde/bsd/staStations.yaml", "r") as file:
            data = yaml.safe_load(file)
    
    systems = []
    for line in data:
        systems.append(location_translation[str(line["solarSystemID"])])
    
    with open(cwd+"/data/station_systems.tsv", "w") as file:
        for system in systems:
            file.write(f"{system}\n")

def systems_with_stations():
    """
    Returns a list of all systems that have stations.
    """

    with open(os.getcwd()+"/data/station_systems.tsv", "r") as file:
        data = file.read().strip().split("\n")
    return data

def construct_regional_npc_grinder_coverage(spots=1) -> dict:
    """
    Finds the best location(s) to place buy orders, and the optimal range for buy orders.
    Best meaning covers most unique systems with most npc kills, without touching lowsec systems.
    If multiple locations are requested, expand coverage as needed.

    !! Has off by one issues sometimes, so 1 lowsec can be on range because some systems can be
    be entered by 2 different routes, this confuses the algo.
    Buy order range is 0, 1, 2, 3, 4, 5, 10, 20, 30, 40, 100(=whole region).
    Saves {region:[[system, range] ... ]}
    """
    cwd = os.getcwd()
    buy_order_range = [0, 1, 2, 3, 4, 5, 10, 20, 30, 40, 100]

    # Translators
    location_translation = translator_location()

    # Systems that have stations
    station_systems = systems_with_stations()

    # Split data to dictionaries
    with open(cwd+"/data/system_connections.tsv", "r") as file:
        universe = file.read().strip().split("\n")
    universe_map = {}
    systems_in_region = {}
    hisec_systems_in_region = {}
    for system_connection in universe:
        system_name, system_region, system_security, system_connections = system_connection.split("\t")
        gates = json.loads(system_connections.replace('\'', '"'))
        # Map
        universe_map[system_name] = {  "region":system_region,
                                        "gates":gates,
                                        "npc_kills":0,
                                        "security":system_security}
        # Systems in region
        if system_region not in systems_in_region:
            systems_in_region[system_region] = [system_name]
        else:
            systems_in_region[system_region].append(system_name)
        if float(system_security) > 0.45:
            # Hisec systems in region
            if system_region not in hisec_systems_in_region:
                hisec_systems_in_region[system_region] = [system_name]
            else:
                hisec_systems_in_region[system_region].append(system_name)
    
    # Remove systems without station
    for region in hisec_systems_in_region:
        systems = hisec_systems_in_region[region]
        new_systems = []
        for system in systems:
            if system in station_systems:
                new_systems.append(system)
        hisec_systems_in_region[region] = new_systems

    # Require route to Jita
    regions_to_remove = []
    for region in hisec_systems_in_region:
        systems = hisec_systems_in_region[region]
        new_systems = []
        for system in systems:
            jita_route_results = route(start=system, target="Jita")
            if len(jita_route_results[1]) > 0:
                new_systems.append(system)
        hisec_systems_in_region[region] = new_systems
        if len(new_systems) == 0:
            regions_to_remove.append(region)
    for removal in regions_to_remove:
        del hisec_systems_in_region[removal]
    
    # Add npc_kills to system info
    conn = sqlite3.connect(cwd+"/data/kills.db")
    cur = conn.cursor()
    cur.execute("SELECT npc_kills, system_id FROM kills")
    kill_data = cur.fetchall()
    conn.close()
    for system in kill_data:
        npc_kills, system_id = system
        system_name = location_translation[str(system_id)]
        universe_map[system_name]["npc_kills"] = npc_kills
    
    def bfs_to_limit(system, 
                     universe_map, 
                     systems_in_region=systems_in_region, 
                     hisec_systems_in_region=hisec_systems_in_region):
        score = 0
        systems_visited = []
        this_node = system
        up_node = {}
        up_node[system] = "start"
        queue = deque()
        queue.append(this_node)
        searching = True
        universe_map_copy = copy.deepcopy(universe_map) # Don't change npc kills on the original
        depth = 0

        while searching:
            if len(queue) > 0:
                this_node = queue.popleft()
                # Determine depth
                depth = 0
                virtual_node = this_node
                while up_node[virtual_node] != "start":
                    depth += 1
                    virtual_node = up_node[virtual_node]
                if this_node not in systems_visited:
                    # Mark as visited
                    systems_visited.append(this_node)
                    # Mark the score and set score to 0
                    score += universe_map_copy[this_node]["npc_kills"]
                    universe_map_copy[this_node]["npc_kills"] = 0
                    # Get the connections and see if any are lowsec
                    gates = universe_map_copy[this_node]["gates"]
                    for gate in gates:
                        # If even one is to lowsec system of same region, the search is over
                        if universe_map_copy[gate]["region"] == universe_map_copy[system]["region"] and float(universe_map_copy[gate]["security"]) < 0.45:
                            searching = False
                        elif gate not in systems_visited and universe_map_copy[gate]["region"] == universe_map_copy[system]["region"]:
                            queue.append(gate)
                            up_node[gate] = this_node
                    if not searching:
                         queue = deque()
            else:
                searching = False
        
        return [system, depth, score, universe_map_copy] # Include the modified map for further searches.
        
    # Find the systems
    regional_winners = {}
    for region in hisec_systems_in_region:
        region_results = {}
        for hisec_system in hisec_systems_in_region[region]:
            system, depth, score, universe_map_copy = bfs_to_limit(hisec_system, universe_map=universe_map)
            region_results[score] = {"system":system,
                                     "depth":depth,
                                     "map":universe_map_copy}
        
        win_ranges = []
        for score in region_results:
            if region_results[score]["depth"] in buy_order_range:
                win_ranges.append(score)            
        win_ranges.sort()
        win_ranges.reverse()
        regional_winners[region] = [[region_results[win_ranges[0]]["system"], region_results[win_ranges[0]]["depth"]]]

        virtual_spots = spots
        if virtual_spots > 1: # If more spots needed
            winner_map = region_results[win_ranges[0]]["map"]
            winner_systems = []
            winner_systems.append(regional_winners[region][0][0])
            while virtual_spots > 1:
                temp_results = {0:{"system":0,
                                   "map":0,
                                   "depth":0}}
                for hisec_system  in hisec_systems_in_region[region]:
                    if hisec_system not in winner_systems:
                        system, depth, score, winner_map_copy = bfs_to_limit(hisec_system, universe_map=winner_map)
                        temp_results[score] ={"system":system,
                                            "depth":depth,
                                            "map":winner_map_copy}
                win_ranges = []
                for score in temp_results:
                    if temp_results[score]["depth"] in buy_order_range:
                        win_ranges.append(score)            
                win_ranges.sort()
                win_ranges.reverse()
                if win_ranges[0] > 0:
                    regional_winners[region].append([temp_results[win_ranges[0]]["system"], temp_results[win_ranges[0]]["depth"]])
                    winner_systems.append(temp_results[win_ranges[0]]["system"])
                    winner_map = temp_results[win_ranges[0]]["map"]
                virtual_spots -= 1
        print(region, regional_winners[region])
    
    # Save
    with open(cwd+"/data/system_cover.tsv", "w") as file:
        for region in regional_winners:
            s = f"{region}\t"
            winners = [i for i in regional_winners[region]]
            for win in winners:
                s += f"{win}\t"
            s = s[:-1]+"\n"
            file.write(s)
                



