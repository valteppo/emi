"""
Find items worth courier contracting to and from. Destination/origin Jita.
"""
import os
import sqlite3

import data_handling

def determine_region_info(region_id):
    """
    Returns tradehubs and shipping costs.
    Returns dictionary if successful, None if not.
    """
    hubs = {}
    if region_id == 10000043: # Domain
        hubs["primary_system"] = 30002187 # Amarr
        hubs["secondary_system"] = 30003491 # Ashab
        hubs["cost_of_dst"] = 33_000_000
        return hubs
    
    if region_id == 10000032: # Sinq Laison
        hubs["primary_system"] = 30002659 # Dodixie
        hubs["secondary_system"] = 30002661 # Botane
        hubs["cost_of_dst"] = 15_000_000
        return hubs
    
    if region_id == 10000042: # Metropolis
        hubs["primary_system"] = 30002053 # Hek
        hubs["secondary_system"] = 30002068 # Nakugard, some neighbour
        hubs["cost_of_dst"] = 20_000_000
        return hubs
    
    if region_id == 10000030: # Heimatar
        hubs["primary_system"] = 30002543 # Eystur
        hubs["secondary_system"] = 30002568 # Onga, some neighbour
        hubs["cost_of_dst"] = 20_000_000
        return hubs
    
    if region_id == 10000048: # Placid
        hubs["primary_system"] = 30003794 # Stacmon
        hubs["secondary_system"] = 30003794 # Stacmon, replicate
        hubs["cost_of_dst"] = 20_000_000
        return hubs
    
    if region_id == 10000033: # The Citadel
        hubs["primary_system"] = 30002768 # Uedama
        hubs["secondary_system"] = 30002764 # Hatakani
        hubs["cost_of_dst"] = 15_000_000
        return hubs
    
    if region_id == 10000068: # Verge Vendor
        hubs["primary_system"] = 30005304 # Alentene
        hubs["secondary_system"] = 30005305 # Cistuvaert
        hubs["cost_of_dst"] = 16_000_000
        return hubs
    
    if region_id == 10000069: # Black Rise
        hubs["primary_system"] = 30045324 # Onnamon
        hubs["secondary_system"] = 30045324 # Onnamon, replicate
        hubs["cost_of_dst"] = 13_000_000
        return hubs
    
    else:
        return None
    
    

def regional_imports_exports(periphery_region_id, volume_day_history=15, min_eff_vol=0.5, tax_buffer=1.07):
    """
    Major tradehub in another region <--> Jita
    Minimum effective volume is not active.
    """
    cost_of_dst = 30_000_000

    jita_id = 30000142
    perimeter_id = 30000144
    forge_id = 10000002

    if periphery_region_id == forge_id:
        return

    size = data_handling.get_size()
    item_translator = data_handling.translator_items()
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

    
    conn = sqlite3.connect(cwd+f"/market/orders/{periphery_region_id}.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC")
    tables = [i[0] for i in cur.fetchall()]
    latest = tables[0]

    # Get periphery main hubs
    cur.execute(f"""SELECT system_id, COUNT(system_id) as order_count FROM {latest} WHERE duration < 91 GROUP BY system_id ORDER BY order_count DESC""")
    system_order_ranking = cur.fetchall()
    if len(system_order_ranking) < 2:
        return # No two hubs
    
    periphery_primary_hub = system_order_ranking[0][0]
    periphery_secondary_hub = system_order_ranking[1][0]


    # Get periphery prices
    cur.execute(f"""SELECT buy.type_id as type_id, buy.buy_price as buy_price, sell.sell_price as sell_price FROM 
                        (SELECT type_id, MAX(price) AS buy_price FROM {latest} WHERE (system_id = {periphery_primary_hub} OR system_id = {periphery_secondary_hub}) AND is_buy_order = 1 GROUP BY type_id) AS buy
                    JOIN 
                        (SELECT type_id, MIN(price) AS sell_price FROM {latest} WHERE (system_id = {periphery_primary_hub} OR system_id = {periphery_secondary_hub}) AND is_buy_order = 0 GROUP BY type_id) AS sell
                    ON buy.type_id = sell.type_id 
                    GROUP BY buy.type_id;""")
    periphery_price_data = cur.fetchall()
    periphery_price = {}
    for line in periphery_price_data:
        type_id, buy_price, sell_price = line
        periphery_price[type_id] = {"buy_price":buy_price,
                                "sell_price":sell_price}
    conn.close()

    # Get Forge prices
    conn = sqlite3.connect(cwd+f"/market/orders/{forge_id}.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC")
    tables = [i[0] for i in cur.fetchall()]
    latest = tables[0]
    cur.execute(f"""SELECT buy.type_id as type_id, buy.buy_price as buy_price, sell.sell_price as sell_price FROM 
                        (SELECT type_id, MAX(price) AS buy_price FROM {latest} WHERE (system_id = {jita_id} OR system_id = {perimeter_id}) AND is_buy_order = 1 GROUP BY type_id) AS buy
                    JOIN 
                        (SELECT type_id, MIN(price) AS sell_price FROM {latest} WHERE (system_id = {jita_id} OR system_id = {perimeter_id}) AND is_buy_order = 0 GROUP BY type_id) AS sell
                    ON buy.type_id = sell.type_id 
                    GROUP BY buy.type_id;""")
    forge_price_data = cur.fetchall()
    forge_price = {}
    for line in forge_price_data:
        type_id, buy_price, sell_price = line
        forge_price[type_id] = {"buy_price":buy_price,
                                "sell_price":sell_price}
    conn.close()

    # Fetch periphery volume
    conn = sqlite3.connect(cwd+f"/market/history/{periphery_region_id}.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC")
    tables = [i[0] for i in cur.fetchall()]
    latest = tables[0]
    cur.execute(f"""SELECT
                        buy_data.type_id,
                        buy_data.buy,
                        sell_data.sell
                    FROM (
                            (SELECT 
                                type_id, 
                                SUM(eff_vol)/{volume_day_history} as buy
                            FROM (
                                SELECT
                                    type_id, lowest, average, highest, volume,
                                    ((average-lowest) / average) * ({latest}.volume / 2) AS eff_vol
                                FROM {latest} 
                                WHERE strftime('%s', 'now') - date < 60*60*24*{volume_day_history}
                            )
                            GROUP BY type_id) AS buy_data
                        JOIN
                            (SELECT 
                                type_id, 
                                SUM(eff_vol)/{volume_day_history} as sell
                            FROM (
                                SELECT
                                    type_id, lowest, average, highest, volume,
                                    ((highest-average) / average) * ({latest}.volume / 2) AS eff_vol
                                FROM {latest} 
                                WHERE strftime('%s', 'now') - date < 60*60*24*{volume_day_history}
                            )
                            GROUP BY type_id) AS sell_data
                        ON buy_data.type_id = sell_data.type_id
                    )
                    """)
    periphery_volume_data = cur.fetchall()
    periphery_volume = {}
    for line in periphery_volume_data:
        type_id, buy_volume, sell_volume = line
        periphery_volume[type_id] = {"buy_vol":buy_volume,
                                  "sell_vol":sell_volume}
    conn.close()

    # Fetch Forge volume
    conn = sqlite3.connect(cwd+f"/market/history/{forge_id}.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC")
    tables = [i[0] for i in cur.fetchall()]
    latest = tables[0]
    cur.execute(f"""SELECT
                        buy_data.type_id,
                        buy_data.buy,
                        sell_data.sell
                    FROM (
                            (SELECT 
                                type_id, 
                                SUM(eff_vol)/{volume_day_history} as buy
                            FROM (
                                SELECT
                                    type_id, lowest, average, highest, volume,
                                    ((average-lowest) / average) * ({latest}.volume / 2) AS eff_vol
                                FROM {latest} 
                                WHERE strftime('%s', 'now') - date < 60*60*24*{volume_day_history}
                            )
                            GROUP BY type_id) AS buy_data
                        JOIN
                            (SELECT 
                                type_id, 
                                SUM(eff_vol)/{volume_day_history} as sell
                            FROM (
                                SELECT
                                    type_id, lowest, average, highest, volume,
                                    ((highest-average) / average) * ({latest}.volume / 2) AS eff_vol
                                FROM {latest} 
                                WHERE strftime('%s', 'now') - date < 60*60*24*{volume_day_history}
                            )
                            GROUP BY type_id) AS sell_data
                        ON buy_data.type_id = sell_data.type_id
                    )
                    """)
    forge_volume_data = cur.fetchall()
    forge_volume = {}
    for line in forge_volume_data:
        type_id, buy_volume, sell_volume = line
        forge_volume[type_id] = {"buy_vol":buy_volume,
                                  "sell_vol":sell_volume}
    conn.close()

    # Find arbitrage using the periphery region
    per_cube_cost = cost_of_dst / 50_000
    exports = {}
    imports = {}
    for type_id in periphery_price:
        if type_id not in periphery_volume or type_id not in forge_price or type_id not in forge_volume or type_id not in size:
            continue # No sufficient data

        if translate_typeID_groupID[type_id] not in vetted_groups:
            continue # Skip unwanted market groups

        # Find it
        if periphery_price[type_id]["sell_price"] > forge_price[type_id]["buy_price"] * tax_buffer: # Eligible for export
            effective_volume = min(periphery_volume[type_id]["sell_vol"], forge_volume[type_id]["buy_vol"])
            profit = (periphery_price[type_id]["sell_price"] - (forge_price[type_id]["buy_price"] * tax_buffer)) * effective_volume
            profit_per_cube = (profit / size[type_id]) - per_cube_cost
            exports[type_id] = {"profit":profit,
                                "profit_per_cube":profit_per_cube,
                                "trade_volume": effective_volume}

        elif forge_price[type_id]["sell_price"] > periphery_price[type_id]["buy_price"] * tax_buffer: # Eligible for import
            effective_volume = min(forge_volume[type_id]["sell_vol"], periphery_volume[type_id]["buy_vol"])
            profit = (forge_price[type_id]["sell_price"] - (periphery_price[type_id]["buy_price"] * tax_buffer)) * effective_volume
            profit_per_cube = (profit / size[type_id]) - per_cube_cost
            imports[type_id] = {"profit":profit,
                                "profit_per_cube":profit_per_cube,
                                "trade_volume": effective_volume}

        else:
            continue
    
    # Insert into courier db
    conn = sqlite3.connect(cwd+f"/output/courier.db")
    cur = conn.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS courier (is_export int, region int, type_id int, name text, profit float, profit_per_cube float, trade_volume float)")
    
    for type_id in exports:
        if exports[type_id]["profit"] > 0 and exports[type_id]["profit_per_cube"] > 0:
            cur.execute(f"INSERT INTO courier (is_export, region, type_id, name, profit, profit_per_cube, trade_volume) \
                        VALUES \
                        (?, ?, ?, ?, ?, ?, ?)", (1, periphery_region_id, type_id, item_translator[type_id], exports[type_id]["profit"], exports[type_id]["profit_per_cube"], exports[type_id]["trade_volume"]))
    conn.commit()

    for type_id in imports:
        if imports[type_id]["profit"] > 0 and imports[type_id]["profit_per_cube"] > 0:
            cur.execute(f"INSERT INTO courier (is_export, region, type_id, name, profit, profit_per_cube, trade_volume) \
                        VALUES \
                        (?, ?, ?, ?, ?, ?, ?)", (0, periphery_region_id, type_id, item_translator[type_id], imports[type_id]["profit"], imports[type_id]["profit_per_cube"], imports[type_id]["trade_volume"]))
    conn.commit()

    # Mark the hubs
    cur.execute(f"CREATE TABLE IF NOT EXISTS hubs (region int UNIQUE, primary_hub int, secondary_hub int)")
    cur.execute(f"""INSERT INTO hubs (region, primary_hub, secondary_hub) VALUES (?, ?, ?) 
                    ON CONFLICT (region) DO UPDATE SET primary_hub = ?, secondary_hub = ? """, 
                    (periphery_region_id, periphery_primary_hub, periphery_secondary_hub, periphery_primary_hub, periphery_secondary_hub))
    conn.commit()
    conn.close()

def make_ie_readable():
    """
    Transforms the data to market quickbar form.
    """
    cwd = os.getcwd()
    translate_location = data_handling.translator_location()

    conn = sqlite3.connect(cwd+f"/output/courier.db")
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT region FROM courier")
    regions = [i[0] for i in cur.fetchall()]
    
    for region in regions:
        if region == 10000002:
            continue # Forge itself

        cur.execute(f"""SELECT primary_hub, secondary_hub FROM hubs WHERE region = {region}""")
        hubs = cur.fetchall()
        main_hub, secondary_hub = hubs[0]

        # Export
        cur.execute(f"SELECT * FROM courier WHERE region = {region} AND is_export = 1 ORDER BY profit DESC")
        data = cur.fetchall()

        quickbar = ""
        count_len = len(str(len(data)))
        count = 0
        current_count_len = len(str(count))
        zerobuffer = "".join("0"* ((count_len - current_count_len)+1))
        quickbar += f"+ {zerobuffer} {translate_location[region]} region EXPORT. Buy in Jita. Ship towards {translate_location[main_hub]}.\n"
        count +=1
        for line in data:
            is_export, this_region, type_id, name, profit, profit_per_cube, trade_volume = line
            current_count_len = len(str(count))
            zerobuffer = "".join("0"* (count_len - current_count_len))
            quickbar += f"+ {zerobuffer}{count} {name} [{int(profit):,} ISK] [{int(profit_per_cube):,} ISK/m3]\n- {name} [{trade_volume}]\n"
            count += 1

        with open(cwd+f"/output/{translate_location[region]} export.txt", "w") as file:
            file.write(quickbar)

        # Import
        cur.execute(f"SELECT * FROM courier WHERE region = {region} AND is_export = 0 ORDER BY profit DESC")
        data = cur.fetchall()

        quickbar = ""
        count_len = len(str(len(data)))
        count = 0
        current_count_len = len(str(count))
        zerobuffer = "".join("0"* ((count_len - current_count_len)+1))
        quickbar += f"+ {zerobuffer} {translate_location[region]} region IMPORT. Buy in {translate_location[main_hub]}. Ship towards Jita.\n"
        count +=1
        for line in data:
            is_export, this_region, type_id, name, profit, profit_per_cube, trade_volume = line
            current_count_len = len(str(count))
            zerobuffer = "".join("0"* (count_len - current_count_len))
            quickbar += f"+ {zerobuffer}{count} {name} [{int(profit):,} ISK] [{int(profit_per_cube):,} ISK/m3]\n- {name} [{trade_volume}]\n"
            count += 1

        with open(cwd+f"/output/{translate_location[region]} import.txt", "w") as file:
            file.write(quickbar)

def make_exports_imports():
    """
    Use this, calculates imports and exports for all defined regions.
    """
    cwd = os.getcwd()
    conn = sqlite3.connect(cwd+"/data/location.db")
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM k_space_regions")
    regions = [i[0] for i in cur.fetchall()]
    conn.close()

    # Clean up
    conn = sqlite3.connect(cwd+f"/output/courier.db")
    cur = conn.cursor()
    cur.execute(f"DROP TABLE IF EXISTS courier")
    cur.execute(f"DROP TABLE IF EXISTS hubs")
    cur.execute("VACUUM")    
    conn.close()

    for region in regions:
        regional_imports_exports(region) # Calculations
    make_ie_readable() # Make market quickbar

make_exports_imports() # keep here, used in rasp trade generation
