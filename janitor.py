"""
Maintain data and repo.
"""
import os
import asyncio

import data_handling
import esi_market
import eve_map

def set_up():
    check_folders_exist()
    data_handling.maintain_sde()
    data_handling.id_translator_constructor()
    data_handling.vetted_groups_construction()
    data_handling.link_typeID_group()
    data_handling.build_location_info_db()

def update_esi_data():
    asyncio.run(esi_market.download_all_orders())
    eve_map.download_kills()
    

def check_folders_exist():
    def make (folder_name):
        os.mkdir(folder_name)
    
    directories = {
        "market":["history", "orders", "prices", "volume"],
        "data":None
    }
    for directory in directories:
        if not os.path.isdir(directory):
            make(directory)
        if directories[directory] != None:
            for subdir in directories[directory]:
                if not os.path.isdir(directory+"/"+subdir):
                    make(directory+"/"+subdir)

