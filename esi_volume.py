"""
Downloads the historical volume from ccp.
"""
import sqlite3
import os
import requests
import time
import datetime
from concurrent.futures import ThreadPoolExecutor

def download_region_data(region):
    # Items to download
    cwd = os.getcwd()
    conn = sqlite3.connect(cwd+f"/market/orders/{str(region)}.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC")
    tables = [i[0] for i in cur.fetchall()]

    if len(tables) == 0: # Breakpoint
        return
    
    latest = tables[0]
    cur.execute(f"SELECT DISTINCT type_id FROM {latest}")
    id_list = [i[0] for i in cur.fetchall()]
    conn.close()

    # Make insertion point
    conn = sqlite3.connect(cwd+f"/market/history/{str(region)}.db")
    cur = conn.cursor()
    time_now = int(time.time())
    table = "unix"+str(time_now)
    cur.execute(f"CREATE TABLE {table} \
                (type_id int, date int, highest float, lowest float, average float, order_count int, volume int)")
    conn.close()

    # Launch queries, insert as each completes
    url = f"https://esi.evetech.net/latest/markets/{str(region)}/history/?datasource=tranquility&type_id="
    urls = [(url+str(id), id) for id in id_list]

    def get(url_id):
        url, type_id = url_id
        type_data = requests.get(url=url, headers={"user-agent":"IG char: Great Artista"}).json()
        if "error" not in type_data:
            conn = sqlite3.connect(cwd+f"/market/history/{str(region)}.db")
            cur = conn.cursor()
            for line in type_data:
                year, month, day = line["date"].split("-")
                date = datetime.date(year=int(year), month=int(month), day=int(day))
                date_unix = int(time.mktime(date.timetuple()))
                cur.execute(f"INSERT INTO {table} \
                                (type_id, date, highest, lowest, average, order_count, volume) \
                                VALUES \
                                (?, ?, ?, ?, ?, ?, ?)", 
                                (type_id, date_unix, line["highest"], line["lowest"], line["average"], line["order_count"], line["volume"])
                            )
            conn.commit()
            conn.close()
    
    with ThreadPoolExecutor(max_workers=16) as executor:
        executor.map(get, urls)

def download_all_regions():
    cwd = os.getcwd()
    conn = sqlite3.connect(cwd + f"/data/location.db")
    cur = conn.cursor()

    # regions
    cur.execute(f"SELECT * FROM k_space_regions")
    regions = cur.fetchall()
    conn.close()

    # Volumes
    for region in regions:
        download_region_data(region=region[0])


def history_transfer():
    """
    Moves the order folder to transfer folder.
    """
    cwd = os.getcwd()
    try:
        os.mkdir(cwd+"/transfer/market/history/")
    except:
        pass
    for file in os.listdir(cwd+"/market/history"):
        os.popen(f'cp {cwd+"/market/history/"+file} {cwd+"/transfer/market/history/"+file}') 