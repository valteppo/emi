"""
Maintain data and repo.
"""
import os
import asyncio

import data_handling
import esi_market
import esi_volume

def set_up():
    check_folders_exist()
    data_handling.maintain_sde()
    data_handling.id_translator_constructor()
    data_handling.vetted_groups_construction()
    data_handling.link_typeID_group()
    data_handling.build_location_info_db()

def update_orders_data():
    data_handling.orders_clean_up()
    asyncio.run(esi_market.download_all_orders())
    esi_market.order_transfer()

def download_volume_histories():
    data_handling.history_clean_up()
    esi_volume.download_all_regions()
    esi_volume.history_transfer()
    

def check_folders_exist():
    def make (folder_name):
        os.mkdir(folder_name)
    
    directories = {
        "transfer":["orders", "volume"],
        "market":["orders", "product", "history", "trade"],
        "data":None
    }
    for directory in directories:
        if not os.path.isdir(directory):
            make(directory)
        if directories[directory] != None:
            for subdir in directories[directory]:
                if not os.path.isdir(directory+"/"+subdir):
                    make(directory+"/"+subdir)

