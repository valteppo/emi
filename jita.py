"""
Jita station trader
"""
import os
import sqlite3
import time

import data_handling

def jita_esi_trader(volume_day_history=15, min_eff_vol=0.5, tax_buffer=1.07):
    """
    Uses esi data to find trades.
    """

    cwd = os.getcwd()

    # Fetch vetted groups
    conn = sqlite3.connect(os.getcwd()+"/data/item.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM vetted_groups")
    vetted_groups = [i[0] for i in cur.fetchall()]
    
    # Link type_id to group
    cur.execute("SELECT * FROM typeID_group")
    group_linking_data = cur.fetchall()
    translate_typeID_groupID = {}
    for line in group_linking_data:
        type_id, group_id = line
        translate_typeID_groupID[type_id] = group_id
    conn.close()

    # Copy orders
    conn = sqlite3.connect(cwd+"/market/orders/10000002.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC")
    tables = [i[0] for i in cur.fetchall()]
    latest = tables[0]
    cur.execute(f"SELECT * FROM {latest}")
    order_data = cur.fetchall()
    conn.close()

    # Copy volume
    conn = sqlite3.connect(cwd+"/market/history/10000002.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC")
    tables = [i[0] for i in cur.fetchall()]
    latest = tables[0]
    cur.execute(f"SELECT * FROM {latest}")
    volume_data = cur.fetchall()
    conn.close()

    # At trade db
    conn = sqlite3.connect(cwd+"/market/trade/jita.db")
    cur = conn.cursor()
    # Insert orders
    cur.execute("DROP TABLE IF EXISTS orders")
    cur.execute(f"CREATE TABLE orders \
                        (duration int, is_buy_order bool, issued text, location_id int,\
                         min_volume int, order_id int, price float, range text,\
                         system_id int, type_id int, volume_remain int, volume_total int)")
    cur.executemany(f"INSERT INTO orders \
                    (duration, is_buy_order, issued, location_id, min_volume, order_id, \
                    price, range, system_id, type_id, volume_remain, volume_total) \
                    VALUES \
                    (?, ?, ?, ?, ?, ?, \
                        ?, ?, ?, ?, ?, ?)",
                    order_data)
    conn.commit()
    # Insert volume
    cur.execute("DROP TABLE IF EXISTS volume")
    cur.execute("CREATE TABLE volume \
                (type_id int, date int, highest float, lowest float, average float, order_count int, volume int)")
    cur.executemany(f"INSERT INTO volume \
                (type_id, date, highest, lowest, average, order_count, volume) \
                VALUES \
                (?, ?, ?, ?, ?, ?, ?)",
                volume_data)
    conn.commit()

    # find buy and sell prices
    """SELECT buy.type_id as type_id, buy.buy_price as buy_price, sell.sell_price as sell_price FROM 
            (SELECT type_id, MAX(price) AS buy_price FROM orders WHERE system_id = 30000142 AND is_buy_order = 1 GROUP BY type_id) AS buy
            JOIN 
            (SELECT type_id, MIN(price) AS sell_price FROM orders WHERE system_id = 30000142 AND is_buy_order = 0 GROUP BY type_id) AS sell
            ON buy.type_id = sell.type_id 
        GROUP BY buy.type_id;"""
    
    # find effective tradeable volume
    f""" SELECT 
            type_id, 
            SUM(eff_vol)/{volume_day_history}
        FROM (
            SELECT
                type_id, lowest, average, highest, volume,
                ((CASE WHEN average-lowest < highest-average THEN average-lowest ELSE highest-average END) / average) * volume AS eff_vol
            FROM volume 
            WHERE strftime('%s', 'now') - date < 60*60*24*{volume_day_history}
        )
        GROUP BY type_id;"""
    
    # combine
    cmd = f"""
    SELECT type_id, buy_price, sell_price, eff_vol,
            (sell_price - (buy_price * {tax_buffer})) * eff_vol AS profit
    FROM
        (SELECT * FROM
            ((SELECT buy.type_id as type_id, buy.buy_price as buy_price, sell.sell_price as sell_price FROM 
                (SELECT type_id, MAX(price) AS buy_price FROM orders WHERE (system_id = 30000142 OR system_id = 30000144) AND is_buy_order = 1 GROUP BY type_id) AS buy
                JOIN 
                (SELECT type_id, MIN(price) AS sell_price FROM orders WHERE (system_id = 30000142 OR system_id = 30000144) AND is_buy_order = 0 GROUP BY type_id) AS sell
                ON buy.type_id = sell.type_id 
            GROUP BY buy.type_id) AS a
            JOIN
            (SELECT 
                type_id, 
                SUM(eff_vol) as eff_vol
            FROM (
                SELECT
                    type_id, lowest, average, highest, volume,
                    ((CASE WHEN average-lowest < highest-average THEN average-lowest ELSE highest-average END) / average) * (volume / 2) AS eff_vol
                FROM volume 
                WHERE strftime('%s', 'now') - date < 60*60*24*{volume_day_history}
            )
            GROUP BY type_id) AS b
            ON a.type_id = b.type_id)
        GROUP BY a.type_id)
    WHERE profit > 5000000 AND eff_vol > {min_eff_vol}
    GROUP BY type_id
    ORDER BY profit DESC;
    """

    cur.execute(cmd)
    results = cur.fetchall()

    item_translator = data_handling.translator_items()
    with open("/output/jita_station_trade.tsv", "w") as file:
        for item in results:
            type_id, buy_price, sell_price, eff_volume, profit = item
            if type_id in item_translator:
                item_name = item_translator[type_id]
                if translate_typeID_groupID[type_id] in vetted_groups:
                    file.write(f"{item_name}\t{int(profit):,}\t{eff_volume}\n")


jita_esi_trader() # keep here, used in rasp trade generation