"""
Cross regional trade.
"""

import os
import sqlite3

def jita_freight(h=24):
    """
    Find trade items in other regions to sell in jita.
    Or buy items in jita to sell else-where.
    Results from the last {h} hours.

    Output saved in /market/product/interaction.db "freight"
    """
    cwd = os.getcwd()
    region_dbs = os.listdir(cwd+"/market/volume")
    data = {}
    for db in region_dbs:
        region_id = int(db.split(".")[0])

        # Volume and isk spent, by system, by type
        conn = sqlite3.connect(cwd+"/market/volume/"+db)
        cur = conn.cursor()
        cmd  = f"""
        SELECT
            system_id,
            type_id,
            sum(buy_volume) as buy_volume,
            sum(sell_volume) as sell_volume,
            sum(buy_value) / sum(buy_volume) as av_buy,
            sum(sell_value) / sum(sell_volume) as av_sell
        FROM events
        WHERE strftime('%s') - timestamp < {h}*60*60
        GROUP BY system_id, type_id;
        """
        cur.execute(cmd)
        region_volume = cur.fetchall()
        conn.close()

        data[region_id] = {}
        for line in region_volume:
            system_id, type_id, buy_volume, sell_volume, av_buy, av_sell = line
            if system_id not in data[region_id]:
                data[region_id][system_id] = {}
            data[region_id][system_id][type_id] = {
                "buy_volume":buy_volume,
                "sell_volume":sell_volume,
                "av_buy":av_buy,
                "av_sell":av_sell
            }
    
    # Find demand
    jita_export = {}
    jita_import = {}
    errors = []
    for region in data:
        if region == 10000002: # Only look from outside to jita.
            continue
        for system in data[region]:
            for type_id in data[region][system]:
                try:
                    system_buy_vol = data[region][system][type_id]["buy_volume"]
                    system_sell_vol = data[region][system][type_id]["sell_volume"]
                    system_buy_price = data[region][system][type_id]["av_buy"]
                    system_sell_price = data[region][system][type_id]["av_sell"]

                    jita_buy_vol = data[10000002][30000142][type_id]["buy_volume"]
                    jita_sell_vol = data[10000002][30000142][type_id]["sell_volume"]
                    jita_buy_price = data[10000002][30000142][type_id]["av_buy"]
                    jita_sell_price = data[10000002][30000142][type_id]["av_sell"]
                    
                    # If export possible
                    if type(system_sell_price) == float and type(jita_buy_price) == float:
                        if system_sell_price > jita_buy_price * 1.08:
                            if system not in jita_export:
                                jita_export[system] = {}
                                jita_export[system][type_id] = {
                                    "jita_price":jita_buy_price,
                                    "system_price":system_sell_price,
                                    "eff_vol":min(jita_buy_vol, system_sell_vol),
                                    "profit":(system_sell_price - (jita_buy_price*1.08)) * min(jita_buy_vol, system_sell_vol) 
                            }
                            else:
                                jita_export[system][type_id] = {
                                    "jita_price":jita_buy_price,
                                    "system_price":system_sell_price,
                                    "eff_vol":min(jita_buy_vol, system_sell_vol),
                                    "profit":(system_sell_price - (jita_buy_price*1.08)) * min(jita_buy_vol, system_sell_vol) 
                            }
                    
                    # If import possible
                    if type(system_buy_price) == float and type(jita_sell_price) == float:
                        if jita_sell_price > system_buy_price * 1.08:
                            if system not in jita_import:
                                jita_import[system] = {}
                                jita_import[system][type_id] = {
                                    "jita_price":jita_sell_price,
                                    "system_price":system_buy_price,
                                    "eff_vol":min(system_buy_vol, jita_sell_vol),
                                    "profit":(jita_sell_price - (system_buy_price*1.08)) * min(system_buy_vol, jita_sell_vol)
                            }
                            else:
                                jita_import[system][type_id] = {
                                    "jita_price":jita_sell_price,
                                    "system_price":system_buy_price,
                                    "eff_vol":min(system_buy_vol, jita_sell_vol),
                                    "profit":(jita_sell_price - (system_buy_price*1.08)) * min(system_buy_vol, jita_sell_vol)
                            }
                except:
                    errors.append(["err",region, system, type_id]) # mostly errors out on bizarre items not found on jita market
 
    conn = sqlite3.connect(cwd+"/market/product/interaction.db")
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS freight")
    cur.execute("CREATE TABLE freight (to_jita int, system_id int, type_id int, volume int, profit float)")
    for system in jita_export:
        for type_id in jita_export[system]:
            line = (0, system, type_id, jita_export[system][type_id]["eff_vol"], jita_export[system][type_id]["profit"])
            cur.execute(f"INSERT INTO freight (to_jita, system_id, type_id, volume, profit)\
                        VALUES \
                        (?, ?, ?, ?, ?)", line)
    conn.commit()
    for system in jita_import:
        for type_id in jita_import[system]:
            line = (1, system, type_id, jita_import[system][type_id]["eff_vol"], jita_import[system][type_id]["profit"])
            cur.execute(f"INSERT INTO freight (to_jita, system_id, type_id, volume, profit)\
                        VALUES \
                        (?, ?, ?, ?, ?)", line)
    conn.commit()
    conn.close()
