"""
Market data retrieval
"""

import aiohttp
import os
import sqlite3
import time

async def download_all_orders():
    cwd = os.getcwd()
    conn = sqlite3.connect(cwd+"/data/location.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM k_space_regions")
    regions = cur.fetchall()
    regions = [i[0] for i in regions]

    async with aiohttp.ClientSession() as session:
        for region in regions:
            orders = []
            conn = sqlite3.connect(cwd+f"/market/orders/{region}.db")
            cur = conn.cursor()

            url = "https://esi.evetech.net/latest/markets/"+str(region)+"/orders/"
            page = 1
            xpage = 0
            params = {"page":page}

            async with session.get(url=url, params=params, headers={"user-agent":"IG char: Great Artista"}) as resp:
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
