import aiohttp
import asyncio
import os
import sqlite3
import time
import itertools
import requests
import concurrent.futures

import data

async def download_all_orders():
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

def construct_prices():
    """
    Construct regional buy & sell prices in major hubs from order data.
    """
    cwd = os.getcwd()

    with open(cwd+"/data/k-spaceRegions.tsv", "r") as file:
        regions = file.read().strip().split("\n")
    for region in regions:
        order_conn = sqlite3.Connection(cwd+f"/market/orders/{region}.db")
        order_cur = order_conn.cursor()
        order_cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name ASC")
        latest_order_table = order_cur.fetchone()[0]

        order_cur.execute(f"SELECT * FROM {latest_order_table} WHERE duration < 365")
        orders = order_cur.fetchall()
        # (duration, is_buy_order, issued, location_id, min_volume, order_id, \
        # price, range, system_id, type_id, volume_remain, volume_total)\
        system_split = {}
        for order in orders:
            if order[8] in system_split: #order[8] is system_id
                system_split[order[8]].append(order)
            else:
                system_split[order[8]] = [order]
        
        # Determine the biggest hub
        count = 0
        leader = 0
        for system in system_split:
            if len(system_split[system]) > count:
                count = len(system_split[system])
                leader = system
        
        # If there is a hub, determine prices.
        if leader > 0:
            # Split orders to items.
            items= {}
            for order in system_split[leader]:
                if order[9] in items:
                    if order[1] == 1:
                        if items[order[9]]["buy"] < order[6]:
                            items[order[9]]["buy"] = order[6]
                    else:
                        if items[order[9]]["sell"] < order[6]:
                            items[order[9]]["sell"] = order[6]
                else:
                    items[order[9]] = {"buy":0,
                                       "sell":0}
                    if order[1] == 1:
                        if items[order[9]]["buy"] < order[6]:
                            items[order[9]]["buy"] = order[6]
                    else:
                        if items[order[9]]["sell"] < order[6]:
                            items[order[9]]["sell"] = order[6]
            
            # Remove duds (only items that are available/being bought at regional center)
            deletion_list = []
            for item in items:
                if items[item]["buy"] == 0 and items[item]["sell"] == 0:
                    deletion_list.append(item)
            for item in deletion_list:
                del items[item]
            
            # Save regional prices
            try:
                os.remove(cwd+f"/market/prices/{region}.db")
            except:
                pass
            summation_conn = sqlite3.Connection(cwd+f"/market/prices/{region}.db")
            summation_cur = summation_conn.cursor()
            summation_cur.execute(f"CREATE TABLE prices_system{str(leader)} \
                                (type_id int, buy float, sell float)")
            for item in items:
                summation_cur.execute(f"INSERT INTO prices_system{str(leader)} \
                                    (type_id, buy, sell) \
                                    VALUES \
                                    (?, ?, ?)", (item, items[item]["buy"], items[item]["sell"]))
            summation_conn.commit()
            summation_conn.close()

def construct_region_range_buy_orders():
    """
    Saves the region-wide buy orders in a region, to gauge where remote buy's can be effective.
    """
    cwd = os.getcwd()

    with open(cwd+"/data/k-spaceRegions.tsv", "r") as file:
        regions = file.read().strip().split("\n")

    for region in regions:
        order_conn = sqlite3.Connection(cwd+f"/market/orders/{region}.db")
        order_cur = order_conn.cursor()
        order_cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name ASC")
        latest_order_table = order_cur.fetchone()[0]

        order_cur.execute(f"SELECT * FROM {latest_order_table} WHERE duration < 365 AND is_buy_order = 1 AND range = 'region' OR range = '40' AND min_volume = 1")
        orders = order_cur.fetchall()
        if len(orders) == 0:
            continue
        items = {}
        for order in orders:
            if order[9] not in items:
                items[order[9]] = order
            else:
                current_leader = items[order[9]]
                if order[6] > current_leader[6]:
                    items[order[9]] = order
        

        # (duration, is_buy_order, issued, location_id, min_volume, order_id, \
        # price, range, system_id, type_id, volume_remain, volume_total)\
            
        # Save regional prices

        summation_conn = sqlite3.Connection(cwd+f"/market/prices/{region}.db")
        summation_cur = summation_conn.cursor()
        summation_cur.execute(f"CREATE TABLE IF NOT EXISTS regional_buy \
                            (type_id int, buy float, volume int)")
        summation_cur.execute("DELETE FROM regional_buy")
        for item in items:
            summation_cur.execute(f"INSERT INTO regional_buy \
                                (type_id, buy, volume) \
                                VALUES \
                                (?, ?, ?)", (items[item][9], items[item][6], items[item][10]))
        summation_conn.commit()
        summation_conn.close()

construct_region_range_buy_orders()

def construct_volume():
    """
    Construct regional buy & sell volumes.
    Average from history data. Since history data takes so long to compile,
    volume is averaged over the whole maximum data, normally year.
    """
    cwd = os.getcwd()
    pass

