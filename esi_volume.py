"""
Downloads the historical volume from ccp.
"""
import sqlite3
import os
import aiohttp
import asyncio
import time
import datetime

async def download_region_data(region):
    # Items to download
    cwd = os.getcwd()
    conn = sqlite3.connect(cwd+f"/market/orders/{region}.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC")
    tables = [i[0] for i in cur.fetchall()]
    latest = tables[0]
    cur.execute(f"SELECT DISTINCT type_id FROM {latest}")
    id_list = [i[0] for i in cur.fetchall()]
    conn.close()

    # Make insertion point
    conn = sqlite3.connect(cwd+f"/market/history/{region}.db")
    cur = conn.cursor()
    time_now = int(time.time())
    table = "unix"+str(time_now)
    cur.execute(f"CREATE TABLE {table} \
                (type_id int, date int, highest float, lowest float, average float, order_count int, volume int)")
    conn.close()

    # Launch queries, insert as each completes
    url = f"https://esi.evetech.net/latest/markets/{region}/history/?datasource=tranquility&type_id="
    async with aiohttp.ClientSession() as session:
        for type_id in id_list:
            async with session.get(url=url+str(type_id), headers={"user-agent":"IG char: Great Artista"}) as resp:
                type_data = await resp.json()
                if "error" not in type_data:
                    conn = sqlite3.connect(cwd+f"/market/history/{region}.db")
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
                    print("ID:",type_id,"done.")
