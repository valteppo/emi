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

from data_handling import translator_location

def build_map():
    """
    Returns [list, dict]

    List is list of all systems.
    Dict links info to systems, regions and stations.
    
    { 
        system_id : {
                    constellation_id: 123123,
                    region_id: 123123,
                    security: 0.123123
                    station_id: [123, 124, 125, ...]
                    station_names: [name123, name124, name125, ...]
                    connection_id: [system_id1, system_id2, ...]
                }
        station_id : system_id where station is located
        constellation_id: [systems in constellation]
        region_id: [systems in region]
    }
    """
    cwd = os.getcwd()
    conn = sqlite3.connect(cwd+"/data/location.db")
    cur = conn.cursor()

    system_list = []
    nodes = {}

    # System info
    cur.execute("SELECT * FROM locations")
    locations_db = cur.fetchall()
    for line in locations_db:
        system_list.append(line[0])
        nodes[line[0]] = {
            "constellation_id":line[1],
            "region_id":line[2],
            "security":line[3]
        }

    # Stations
    cur.execute("SELECT * FROM stations")
    stations_db = cur.fetchall()
    for line in stations_db:
        if "station_id" not in nodes[line[0]]:
            nodes[line[0]]["station_id"] = [line[1]]
            nodes[line[0]]["station_name"] = [line[2]]
            nodes[line[1]] = line[0]
        else:
            nodes[line[0]]["station_id"].append(line[1])
            nodes[line[0]]["station_name"].append(line[2])
            nodes[line[1]] = line[0]
    
    # Jump gate connections
    cur.execute("SELECT * FROM connections")
    connections_db = cur.fetchall()
    conn.close()
    for line in connections_db:
        if "connection_id" not in nodes[line[0]]:
            nodes[line[0]]["connection_id"] = [line[1]]
        else:
            nodes[line[0]]["connection_id"].append(line[1])
    
    # Make regions and constellation searchable
    for system in system_list:
        constellation = nodes[system]["constellation_id"]
        region = nodes[system]["region_id"]

        if constellation not in nodes:
            nodes[constellation] = [system]
        else:
            nodes[constellation].append(system)
        
        if region not in nodes:
            nodes[region] = [system]
        else:
            nodes[region].append(system)
    
    return [system_list, nodes]

def download_kills():
    """
    Downloads the kills from esi. Stores with timestamp.
    """
    cwd = os.getcwd()
    conn = sqlite3.connect(cwd+"/data/kill.db")
    cur = conn.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS \
                kills (system_id int, npc_kills int, pod_kills int, ship_kills int, timestamp int)")
    cur.execute("SELECT strftime('%s', 'now') - timestamp FROM kills ORDER BY timestamp DESC LIMIT 1")
    last_query_since_seconds = cur.fetchone()
    if last_query_since_seconds != None:
        if last_query_since_seconds[0] < 60 * 60:
            conn.close()
            return

    r = requests.get(url="https://esi.evetech.net/latest/universe/system_kills/?datasource=tranquility", headers={"user-agent":"IG char: Great Artista"})    
    data = r.json()
    cmd = "INSERT INTO kills (system_id, npc_kills, pod_kills, ship_kills, timestamp)\
            VALUES (:system_id, :npc_kills, :pod_kills, :ship_kills, strftime('%s', 'now'))"
    cur.executemany(cmd, data)
    conn.commit()
    conn.close()
