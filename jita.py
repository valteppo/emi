"""
Jita station trader
"""
import os
import sqlite3
import time

import data_handling

def items_h(h=24):
    """
    Gets the items that made the most money in the last {h} hours.

    Output saved in /market/product/interaction.db "jita"
    """

    cwd = os.getcwd()
    conn = sqlite3.connect(cwd+"/market/volume/10000002.db")
    cur = conn.cursor()

    cmd = f"""
    SELECT 
        type_id,
        eff_volume,
        (av_sell-(av_buy * 1.08)) * eff_volume as profit        
    FROM (
        SELECT
            type_id,
            sum(sell_value)/sum(sell_volume) as av_sell,
            sum(buy_value)/sum(buy_volume) as av_buy,
            (CASE WHEN sum(sell_volume) > sum(buy_volume) THEN sum(buy_volume) ELSE sum(sell_volume) END) as eff_volume
        FROM events
        WHERE   system_id = 30000142 AND
                strftime('%s') - timestamp < {h}*60*60
        GROUP BY type_id
    ) AS temp
    GROUP BY type_id 
    ORDER BY profit DESC;
    """
    cur.execute(cmd)
    res = cur.fetchall()
    conn.close()

    conn = sqlite3.connect(cwd+"/market/product/interaction.db")
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS jita")
    cur.execute("CREATE TABLE jita (type_id int, eff_vol int, profit int)")
    cmd = "INSERT INTO jita (type_id, eff_vol, profit) VALUES (?, ?, ?)"
    cur.executemany(cmd, res)
    conn.commit()
    conn.close()    

def jita_esi_trader():
    """
    Uses esi data to find trades.
    """

    cwd = os.getcwd()

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
    """ SELECT 
            type_id, 
            SUM(eff_vol)/8
        FROM (
            SELECT
                type_id, lowest, average, highest, volume,
                ((CASE WHEN average-lowest < highest-average THEN average-lowest ELSE highest-average END) / average) * volume AS eff_vol
            FROM volume 
            WHERE strftime('%s', 'now') - date < 60*60*24*8
        )
        GROUP BY type_id;"""
    
    # combine
    cmd = """
    SELECT type_id, buy_price, sell_price, eff_vol,
            (sell_price - (buy_price * 1.08)) * eff_vol AS profit
    FROM
        (SELECT * FROM
            ((SELECT buy.type_id as type_id, buy.buy_price as buy_price, sell.sell_price as sell_price FROM 
                (SELECT type_id, MAX(price) AS buy_price FROM orders WHERE system_id = 30000142 AND is_buy_order = 1 GROUP BY type_id) AS buy
                JOIN 
                (SELECT type_id, MIN(price) AS sell_price FROM orders WHERE system_id = 30000142 AND is_buy_order = 0 GROUP BY type_id) AS sell
                ON buy.type_id = sell.type_id 
            GROUP BY buy.type_id) AS a
            JOIN
            (SELECT 
                type_id, 
                SUM(eff_vol)/8 as eff_vol
            FROM (
                SELECT
                    type_id, lowest, average, highest, volume,
                    ((CASE WHEN average-lowest < highest-average THEN average-lowest ELSE highest-average END) / average) * volume AS eff_vol
                FROM volume 
                WHERE strftime('%s', 'now') - date < 60*60*24*8
            )
            GROUP BY type_id) AS b
            ON a.type_id = b.type_id)
        GROUP BY a.type_id)
    WHERE profit > 10000000 AND eff_vol > 1
    GROUP BY type_id
    ORDER BY profit DESC;
    """

    cur.execute(cmd)
    results = cur.fetchall()

    item_translator = data_handling.translator_items()
    items = 50
    i = 0
    while i < items or i >= len(results):
        type_id, buy_price, sell_price, eff_vol, profit = results[i]
        if type_id in item_translator:
            print(item_translator[type_id], profit)
        i+=1

jita_esi_trader()