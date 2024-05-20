"""
Find items worth courier contracting to and from. Destination/origin Jita.
"""
import os
import sqlite3
import math

import data_handling
 
def regional_imports_exports(periphery_region_id, volume_day_history=15, min_exp_vol=2, min_imp_vol=0.5, tax_buffer=1.07):
    """
    Major tradehub in another region <--> Jita
    """
    forge_id = 10000002
    jita_id = 30000142

    if periphery_region_id == forge_id:
        return
    
    cwd = os.getcwd()

    # Filters and translators
    size = data_handling.get_size()
    item_translator = data_handling.translator_items()
    vetted_groups = data_handling.get_vetted_groups()
    translate_typeID_groupID = data_handling.typeID_groupID_translator()
    
    # Hubs
    system_order_ranking = data_handling.get_region_main_hubs(periphery_region_id)
    if len(system_order_ranking) < 2:
        return
    periphery_primary_hub = system_order_ranking[0]
    periphery_secondary_hub = system_order_ranking[1]

    # Route
    route_systems_primary = data_handling.get_route(jita_id, periphery_primary_hub)
    if route_systems_primary == None:
        return
    route_lenght_primary = len(route_systems_primary)-1
    
    # Cost of dst
    cost_of_dst = 6_000_000 + (route_lenght_primary * 613_000)
    
    # Stack size max, only take piles that are worth transporting as piles smaller than
    stack_cubic_vol_max = 4000

    # Price
    periphery_price = data_handling.get_region_prices(periphery_region_id)
    forge_price = data_handling.get_region_prices(forge_id)
    
    # Volume
    periphery_volume = data_handling.get_region_volumes(periphery_region_id)
    forge_volume = data_handling.get_region_volumes(forge_id)

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
        if periphery_price[type_id]["sell"] > forge_price[type_id]["sell"] * tax_buffer: # Eligible for export, buy from Jita sell orders
            effective_volume_market = periphery_volume[type_id]["sell_vol"] + periphery_volume[type_id]["buy_vol"] * 0.9 # Assume in periphery that items are sold 90% from sell orders
            volume_throttle = math.ceil(stack_cubic_vol_max / size[type_id])
            effective_volume = min(effective_volume_market, volume_throttle)
            if effective_volume > min_exp_vol:
                profit = (periphery_price[type_id]["sell"] - (forge_price[type_id]["sell"] * tax_buffer)) * effective_volume
                profit_per_cube = (profit / size[type_id]) - per_cube_cost
                exports[type_id] = {"profit":profit,
                                    "profit_per_cube":profit_per_cube,
                                    "trade_volume": effective_volume}

        elif forge_price[type_id]["sell"] > periphery_price[type_id]["buy"] * tax_buffer: # Eligible for import, buy with long-term buy orders from region
            effective_volume_market = min(forge_volume[type_id]["sell_vol"], periphery_volume[type_id]["buy_vol"])
            volume_throttle = math.ceil(stack_cubic_vol_max / size[type_id])
            effective_volume = min(effective_volume_market, volume_throttle)
            if effective_volume > min_imp_vol:
                profit = (forge_price[type_id]["sell"] - (periphery_price[type_id]["buy"] * tax_buffer)) * effective_volume
                profit_per_cube = (profit / size[type_id]) - per_cube_cost
                imports[type_id] = {"profit":profit,
                                    "profit_per_cube":profit_per_cube,
                                    "trade_volume": effective_volume}

        else:
            continue
    
    # Insert into courier db
    conn = sqlite3.connect(cwd+f"/output/courier/courier.db")
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
    cur.execute(f"CREATE TABLE IF NOT EXISTS hubs (region int UNIQUE, primary_hub int, secondary_hub int, hauling_cost float)")
    cur.execute(f"""INSERT INTO hubs (region, primary_hub, secondary_hub, hauling_cost) VALUES (?, ?, ?, ?) 
                    ON CONFLICT (region) DO UPDATE SET primary_hub = ?, secondary_hub = ?, hauling_cost = ? """, 
                    (periphery_region_id, periphery_primary_hub, periphery_secondary_hub, cost_of_dst, periphery_primary_hub, periphery_secondary_hub, cost_of_dst))
    conn.commit()
    conn.close()

def make_ie_readable():
    """
    Transforms the data to market quickbar form.
    """
    cwd = os.getcwd()
    translate_location = data_handling.translator_location()

    conn = sqlite3.connect(cwd+f"/output/courier/courier.db")
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT region FROM courier")
    regions = [i[0] for i in cur.fetchall()]

    # Clean up
    files = os.listdir(cwd+f"/output/courier/")
    for file in files:
        tokens = file.split(".")
        if tokens[-1] == "txt":
            os.remove(cwd+f"/output/courier/{file}")
    
    for region in regions:
        if region == 10000002:
            continue # Forge itself

        cur.execute(f"""SELECT primary_hub, hauling_cost FROM hubs WHERE region = {region}""")
        hubs = cur.fetchall()
        main_hub, cost_of_dst = hubs[0]

        # Export
        cur.execute(f"SELECT * FROM courier WHERE region = {region} AND profit > 500000 AND is_export = 1 ORDER BY profit DESC")
        data = cur.fetchall()
        
        quickbar = ""
        count = 1
        for line in data:
            is_export, this_region, type_id, name, profit, profit_per_cube, trade_volume = line
            if count > 100:
                break
            quickbar += f"{name}\t{max(int(trade_volume),1)}\n"
            count += 1

        with open(cwd+f"/output/courier/EXPORT {translate_location[region]} Jita to {translate_location[main_hub]}.txt", "w") as file:
            file.write(quickbar)

        # Import
        cur.execute(f"SELECT * FROM courier WHERE region = {region} AND profit > 500000 AND is_export = 0 ORDER BY profit DESC")
        data = cur.fetchall()

        quickbar = ""
        count_len = len(str(len(data)))
        count = 1
        for line in data:
            is_export, this_region, type_id, name, profit, profit_per_cube, trade_volume = line
            current_count_len = len(str(count))
            zerobuffer = "".join("0"* (count_len - current_count_len))
            quickbar += f"+ {zerobuffer}{count} {name} [{int(profit):,} ISK]\n- {name} [{trade_volume}]\n"
            count += 1
            if count > 100:
                break

        with open(cwd+f"/output/courier/IMPORT {translate_location[region]} {translate_location[main_hub]} to Jita.txt", "w") as file:
            file.write(quickbar)

def make_exports_imports():
    """
    Use this, calculates imports and exports for all defined regions.
    """
    cwd = os.getcwd()
    regions = data_handling.get_k_space_regions()

    # Clean up of database
    conn = sqlite3.connect(cwd+f"/output/courier/courier.db")
    cur = conn.cursor()
    cur.execute(f"DROP TABLE IF EXISTS courier")
    cur.execute(f"DROP TABLE IF EXISTS hubs")
    cur.execute("VACUUM")    
    conn.close()

    # Clean up of txt files
    files = os.listdir(cwd+f"/output/courier/")
    for file in files:        
        tokens = file.split(".")
        if tokens[-1] == "txt":
            os.remove(cwd+f"/output/courier/{file}")

    for region in regions:
        regional_imports_exports(region) # Calculations
    make_ie_readable() # Make market quickbar

make_exports_imports() # keep here, used in rasp trade generation
