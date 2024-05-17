
""" 
Main used for scripts.
"""
import os
import requests
import datetime
import tarfile
import sqlite3
import json

def download_extract_killmails(from_n_days_ago = 1):
    """
    Downloads and extracts killmails from a day "n"-days ago
    """
    cwd = os.getcwd()
    target_date = datetime.datetime.now() - datetime.timedelta(days=from_n_days_ago)
    file_name = f"killmails-{target_date.year}-{str(target_date.month).rjust(2, '0')}-{str(target_date.day).rjust(2, '0')}.tar.bz2"
    url = f"https://data.everef.net/killmails/{target_date.year}/{file_name}"
    response = requests.get(url=url, headers={"user-agent":"vamteppo@protonmail.com", "Accept-Encoding":"gzip"})
    if response.status_code == 200:
        with open(file_name, "wb") as downloaded_file:
            downloaded_file.write(response.content)
        tar = tarfile.open(cwd+f"/{file_name}")
        tar.extractall()
        tar.close()
        os.remove(cwd+f"/{file_name}")

def process_unpacked_killmail_jsons():
    """
    Goes through the killmails folder and processes json files into database.
    Removes processed files.
    """
    cwd = os.getcwd()
    files = os.listdir(cwd+f"/killmails")
   
    data = {}
    for file in files:
        tokens = file.split(".")
        if tokens[-1] == "json":
            with open(cwd+f"/killmails/{file}", "r") as json_file:
                file_data = json.load(json_file)
            solarsystem_id = file_data["solar_system_id"]
            if "items" in file_data["victim"]:
                for item in file_data["victim"]["items"]:
                    if "quantity_destroyed" in item:
                        if solarsystem_id not in data:
                            data[solarsystem_id] = {item["item_type_id"]:item["quantity_destroyed"]}
                        else:
                            if item["item_type_id"] in data[solarsystem_id]:
                                data[solarsystem_id][item["item_type_id"]] += item["quantity_destroyed"]
                            else:
                                data[solarsystem_id][item["item_type_id"]] = item["quantity_destroyed"]
    
    # Build translator
    conn = sqlite3.connect(cwd+f"/data/location.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM locations")
    location_data = cur.fetchall()
    conn.close()

    region_solver = {}
    for line in location_data:
        system_id, constellation_id, region_id, security = line
        region_solver[system_id] = {"region":region_id,
                                    "security": security}

    # Insert results
    conn = sqlite3.connect(cwd+f"/data/killmails.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS killdata (region_id int, system_id int, security int, type_id int, destroyed int)")
    for system in data:
        for item in data[system]:
            cur.execute("INSERT INTO killdata (region_id, system_id, security, type_id, destroyed) \
                        VALUES (?, ?, ?, ? ,?)", 
                        (region_solver[system]["region"], system, region_solver[system]["security"], item, data[system][item]))
    conn.commit()
    conn.close()

    # Clean up killmails folder
    for file in files:        
        tokens = file.split(".")
        if tokens[-1] == "json":
            os.remove(cwd+f"/killmails/{file}")

def refresh_n_days(n, m=1):
    """
    Removes and redownloads and calculates a "n" days of regional consumption of items as recorded by zkillboard.
    """

    cwd = os.getcwd()
    conn = sqlite3.connect(cwd+f"/data/killmails.db")
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS killdata")
    cur.execute("VACUUM")
    conn.close()

    for day in range(m, n+1):
        download_extract_killmails(day)
        process_unpacked_killmail_jsons()
        print(day)

#refresh_n_days(30)