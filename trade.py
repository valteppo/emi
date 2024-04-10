"""
Parses data trade orders.
"""
import os
import sqlite3

import jita
import import_export
import data_handling

def jita_station_trades(history_heure = 48):
    jita.items_h(history_heure)
    item_translator = data_handling.translator_items()
    cwd = os.getcwd()
    conn = sqlite3.connect(cwd+"/market/product/interaction.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM jita WHERE eff_vol > 0 and profit > 0 ORDER BY profit DESC")
    items = cur.fetchall()
    conn.close()

    # type_id, eff_vol, profit
    translated = []
    for item in items:
        type_id, eff_vol, profit = item
        try:
            translated.append([item_translator[type_id], eff_vol, profit])
        except:
            pass # some new items might be missing from translator
    return translated

def preliminary_jita_import_export(history_heure = 48):
    """
    Items need a better price check and verification, but does return interesting things.

    Low hours (2-6) seem more reasonable than longer ones.
    """

    import_export.jita_freight(history_heure)
    location_translator = data_handling.translator_location()
    item_translator = data_handling.translator_items()
    cwd = os.getcwd()
    conn = sqlite3.connect(cwd+"/market/product/interaction.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM freight ORDER BY profit DESC")
    items = cur.fetchall()
    conn.close()

    # to_jita, system_id, type_id, volume, profit
    translated_import = []
    translated_export = []
    for item in items:
        to_jita, system_id, type_id, volume, profit = item
        if to_jita:
            try:
                translated_import.append([location_translator[system_id], item_translator[type_id], volume, profit])
            except:
                pass
        else:
            try:
                translated_export.append([location_translator[system_id], item_translator[type_id], volume, profit])
            except:
                pass
    
    pr = 0
    for item in translated_import:
        if item[0] == "Amarr" and item[3] > 10_000_000:
            pr += item[3]

    print("import profit:",pr)
    pr = 0
    for item in translated_export:
        if item[0] == "Amarr" and item[3] > 10_000_000:
            pr += item[3]
    print("export profit:", pr)

    # TODO continue
    # Maybe simplify this to old system

print(jita_station_trades(12))
