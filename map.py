"""
Universe related functions
"""

import zipfile
import os
import yaml
from collections import deque
import json
import sqlite3
import time
import requests

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

    Returns [  
                number of jumps,
                [Start system, ... , end system]
            ]
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
    up_node = {}
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
        else:
            searcing = False

    return [len(result)-1, result]


def download_kills():
    """
    Downloads the kills from esi.
    """
    cwd = os.getcwd()
    conn = sqlite3.connect(cwd+"/data/kills.db")
    cur = conn.cursor()
    time_now = str(int(time.time()))
    cur.execute(f"CREATE TABLE IF NOT EXISTS kills{time_now} (npc_kills int, pod_kills int, ship_kills int, system_id int)")

    r = requests.get(url="https://esi.evetech.net/latest/universe/system_kills/?datasource=tranquility")    
    data = r.json()
    cmd = f"INSERT INTO kills{time_now} (npc_kills, pod_kills, ship_kills, system_id) VALUES (:npc_kills, :pod_kills, :ship_kills, :system_id)"
    cur.executemany(cmd, data)
    conn.commit()
    conn.close()


