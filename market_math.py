"""
Actual calculations
"""
import os
import sqlite3

import data

def arbitrage():
    """
    Calculates profits for buying outside Forge and reselling in Jita.
    """
    # Init
    cwd = os.getcwd()
    item_translation = data.translator_items()

    with open(cwd+"/data/k-spaceRegions.tsv", "r") as file:
        regions = file.read().strip().split("\n")
    
    # Jita prices for items
    forge_conn = sqlite3.connect(cwd+f"/market/prices/TheForge.db")
    forge_cur = forge_conn.cursor()
    forge_cur.execute("SELECT * FROM prices_system30000142")
    forge_data = forge_cur.fetchall()

    forge_price = {}
    for data_line in forge_data:
        forge_price[data_line[0]] = {"buy":data_line[1],
                                     "sell":data_line[2]}
    
    # Regional buy prices
    
    # Approved itemlist
    # Determine hauling cost
    # Rank items

arbitrage()
