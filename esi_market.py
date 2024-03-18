import aiohttp
import asyncio
import os
import sqlite3
import time

import data

async def download_all_orders():
    time_start = time.time()
    translate = data.translator_location()
    with open(os.getcwd()+"/data/k-spaceRegions.tsv", "r") as file:
        regions = file.read().split("\n")

    async with aiohttp.ClientSession() as session:
        for region in regions:
            orders = []

            conn = sqlite3.connect(os.getcwd()+f"/market/orders/{region}.db")
            cur = conn.cursor()

            id = translate[region]
            url = "https://esi.evetech.net/latest/markets/"+id+"/orders/"
            page = 1
            xpage = 0
            params = {"page":page}

            async with session.get(url=url, params=params) as resp:
                headers = dict(resp.headers)
                xpage = int(headers["X-Pages"])
                page_orders = await resp.json()
                [orders.append(i) for i in page_orders]
            if xpage != page:
                for new_page in range(2, xpage+1):
                    params = {"page":new_page}
                    async with session.get(url=url, params=params) as resp:
                        page_orders = await resp.json()
                        [orders.append(i) for i in page_orders]
            print(region, len(orders))
            time_now = int(time.time())
            cur.execute(f"CREATE TABLE unix{time_now} \
                        (duration int, is_buy_order bool, issued text, location_id int,\
                         min_volume int, order_id int, price float, range text,\
                         system_id int, type_id int, volume_remain int, volume_total int)")
            
            cur.executemany(f"INSERT INTO unix{time_now} \
                            (duration, is_buy_order, issued, location_id, min_volume, order_id, \
                            price, range, system_id, type_id, volume_remain, volume_total)\
                            VALUES \
                            (:duration, :is_buy_order, :issued, :location_id, :min_volume, :order_id, \
                            :price, :range, :system_id, :type_id, :volume_remain, :volume_total)",\
                                orders)
            conn.commit()
            conn.close()
    print("Time elapsed: ", time.time() - time_start)

#asyncio.run(download_all_orders())

async def download_market_history(region = "TheForge"):
    """
    Download history for all items in market. Can take a while.
    """

    translate_location = data.translator_location()
    translate_item = data.translator_items()

    conn = sqlite3.Connection(os.getcwd()+f"/market/orders/{region}.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name ASC")
    latest = cur.fetchone()[0]
    cur.execute(f"SELECT DISTINCT type_id FROM {latest} WHERE duration < 300")
    item_ids = cur.fetchall()
    item_ids = [i[0] for i in item_ids]
    conn.close()

    region_id = translate_location[region]
    url = f"https://esi.evetech.net/latest/markets/{region_id}/history/"
    histories = {}
    async with aiohttp.ClientSession() as session:
        for item_id in item_ids:
            async with session.get(url=url, params={"type_id":str(item_id)}) as resp:
                try:
                    this_history = await resp.json()
                    histories[item_id] = this_history
                except:
                    continue
    
    conn = sqlite3.Connection(os.getcwd()+f"/market/history/{region}.db")
    cur = conn.cursor()
    exceptions = []
    for item_id in histories:
        try:
            cur.execute(f"CREATE TABLE item_id{str(item_id)} \
                        (average float, date text, highest float, lowest float, order_count int, volume int)")
            
            cur.executemany(f"INSERT INTO item_id{str(item_id)} \
                            (average, date, highest, lowest, order_count, volume) \
                            VALUES \
                            (:average, :date, :highest, :lowest, :order_count, :volume)",\
                                histories[item_id])
            conn.commit()
        except:
            exceptions.append((histories[item_id], item_id))
    conn.close()
    print("Region: ", region, "\titem histories: ",len(histories))
    print("exceptions: ", exceptions)

#asyncio.run(download_market_history())
