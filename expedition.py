"""
Buy day-to-day items in Jita, ship to periphery.
"""

import os
import requests
import datetime
import tarfile
import sqlite3
import json

import data_handling

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
    
    def flag_ok(flag) -> bool:
        if flag > 10 and flag < 35:
            return True
        elif flag > 91 and flag < 100:
            return True
        elif flag > 124 and flag < 133:
            return True
        elif flag == 177:
            return True
   
    data = {}
    for file in files:
        tokens = file.split(".")
        if tokens[-1] == "json":
            with open(cwd+f"/killmails/{file}", "r") as json_file:
                file_data = json.load(json_file)
            solarsystem_id = file_data["solar_system_id"]
            if "items" in file_data["victim"]:
                for item in file_data["victim"]["items"]:
                    if "quantity_destroyed" in item and flag_ok(item["flag"]):
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

def summarize_regions(minimum_volume = 0.2):
    """
    Goes through the collected killdata and saves a summary.
    """
    cwd = os.getcwd()
    # Cleanup old data
    old_txt = os.listdir(cwd+f"/output/expedition/")
    for file in old_txt:
        tokens = file.split(".")
        if tokens[-1] == "txt":
            os.remove(cwd+f"/output/expedition/{file}")

    # Filters and translators
    k_space_regions = data_handling.get_k_space_regions()
    vetted_groups = data_handling.get_vetted_groups()
    translate_typeID_groupID = data_handling.typeID_groupID_translator()
    item_translator = data_handling.translator_items()
    location_translator = data_handling.translator_location()

    conn = sqlite3.connect(cwd+f"/data/killmails.db")
    cur = conn.cursor()

    cur.execute("SELECT day FROM day_count")
    day = cur.fetchone()[0]

    cur.execute("SELECT DISTINCT region_id FROM killdata")
    regions = [i[0] for i in cur.fetchall()]
    
    summaries = {}
    for region in regions:
        cur.execute("SELECT * FROM killdata WHERE region_id = ?", (region,))
        region_data = cur.fetchall()
        
        region_summary = {}
        for line in region_data:
            region_id, system_id, security, type_id, destroyed = line
            if type_id not in region_summary:
                region_summary[type_id] = destroyed
            else:
                region_summary[type_id] += destroyed
        summaries[region] = region_summary
    conn.close()

    # Get prices
    jita_prices = data_handling.get_region_prices(10000002)
    
    # Save results to db for queries
    conn = sqlite3.connect(cwd+f"/data/killmails.db")
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS summary")
    cur.execute("CREATE TABLE summary (region_id int, type_id int, volume float, total_value float)")

    for region in summaries:
        if region not in k_space_regions:
            continue
        
        # Region prices & hubs
        region_prices = data_handling.get_region_prices(region)
        region_volume = data_handling.get_region_volumes(region)
        region_hubs = data_handling.get_region_main_hubs(region)
        if len(region_hubs) < 2:
            continue

        for type_id in summaries[region]:
            if type_id in jita_prices and type_id in region_prices and type_id in region_volume:
                # Check if it's worth buying directly from jita sell orders and ship to target region
                sell_price_difference = region_prices[type_id]["sell"] - jita_prices[type_id]["sell"] 
                cur.execute("INSERT INTO summary (region_id, type_id, volume, total_value) \
                            VALUES (?, ?, ?, ?)", (region, type_id, summaries[region][type_id] / day, (region_volume[type_id]["sell_vol"] * sell_price_difference)))
        conn.commit()
    
        # Query to form output
        cur.execute(f"SELECT type_id, volume, total_value FROM summary WHERE region_id = {region} AND volume > {minimum_volume} AND total_value > 0 ORDER BY total_value DESC")
        region_summary_data = cur.fetchall()
        if len(region_summary_data) == 0:
            continue

        quickbar = ""
        n = 1
        for line in region_summary_data:
            type_id, volume, total_value = line
            if type_id in item_translator and total_value > 1_000_000:
                if translate_typeID_groupID[type_id] in vetted_groups:
                    if n > 100:
                        break
                    quickbar += f"{item_translator[type_id]}\t{max(int(volume), 1)}\n"
                    n += 1
        
        if len(quickbar.split("\n")) > 5:
            with open(cwd+f"/output/expedition/{location_translator[region]} expedition multibuy.txt", "w") as file:
                file.write(quickbar)
    conn.close()

def refresh_n_days(n, m=1):
    """
    Removes and redownloads and calculates a "n" days of regional consumption of items as recorded by zkillboard.

    Costly long operation that destroys data.
    """

    cwd = os.getcwd()
    conn = sqlite3.connect(cwd+f"/data/killmails.db")
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS killdata")
    cur.execute("DROP TABLE IF EXISTS day_count")
    cur.execute("VACUUM")
    cur.execute("CREATE TABLE day_count (day int)")
    cur.execute("INSERT INTO day_count (day) VALUES (0)")
    conn.close()   

    for day in range(m, n+1):
        # Locks db if conn kept open.
        conn = sqlite3.connect(cwd+f"/data/killmails.db")
        cur = conn.cursor()
        cur.execute("UPDATE day_count SET day = day + 1")
        conn.commit()
        conn.close()

        download_extract_killmails(day)
        process_unpacked_killmail_jsons()
        print(day)

    summarize_regions()

def add_n_days(n=1):
    """
    Adds killboard data to killdata table without removing old data.
    Redoes buy lists. Buy lists indicate daily consumption.

    Intended as daily function.
    """
    cwd = os.getcwd()
    
    for day in range(1, n+1):
        # Locks db if conn kept open.
        conn = sqlite3.connect(cwd+f"/data/killmails.db")
        cur = conn.cursor()
        cur.execute("UPDATE day_count SET day = day + 1")
        conn.commit()
        conn.close()

        download_extract_killmails(day)
        process_unpacked_killmail_jsons()
    summarize_regions()

summarize_regions()