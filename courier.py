"""
Find items worth courier contracting to and from. Destination/origin Jita.
"""
import os
import sqlite3
import data_handling
 
def regional_imports_exports(periphery_region_id, volume_day_history=15, min_eff_vol=0.5, tax_buffer=1.07):
    """
    Major tradehub in another region <--> Jita
    Minimum effective volume is not active.
    """
    cost_of_dst = 30_000_000
    forge_id = 10000002

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
            effective_volume = min(periphery_volume[type_id]["sell_vol"], forge_volume[type_id]["buy_vol"])
            profit = (periphery_price[type_id]["sell"] - (forge_price[type_id]["sell"] * tax_buffer)) * effective_volume
            profit_per_cube = (profit / size[type_id]) - per_cube_cost
            exports[type_id] = {"profit":profit,
                                "profit_per_cube":profit_per_cube,
                                "trade_volume": effective_volume}

        elif forge_price[type_id]["sell"] > periphery_price[type_id]["buy"] * tax_buffer: # Eligible for import, buy with long-term buy orders from region
            effective_volume = min(forge_volume[type_id]["sell_vol"], periphery_volume[type_id]["buy_vol"])
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

    conn = sqlite3.connect(cwd+f"/output/courier/courier.db")
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

        with open(cwd+f"/output/courier/{translate_location[region]} export.txt", "w") as file:
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

        with open(cwd+f"/output/courier/{translate_location[region]} import.txt", "w") as file:
            file.write(quickbar)

def make_exports_imports():
    """
    Use this, calculates imports and exports for all defined regions.
    """
    cwd = os.getcwd()
    regions = data_handling.get_k_space_regions()

    # Clean up
    conn = sqlite3.connect(cwd+f"/output/courier/courier.db")
    cur = conn.cursor()
    cur.execute(f"DROP TABLE IF EXISTS courier")
    cur.execute(f"DROP TABLE IF EXISTS hubs")
    cur.execute("VACUUM")    
    conn.close()

    for region in regions:
        regional_imports_exports(region) # Calculations
    make_ie_readable() # Make market quickbar

make_exports_imports() # keep here, used in rasp trade generation
