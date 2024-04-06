"""
Maintain data and repo.
"""
import os

import data_handling

def run_set_up():
    check_folders_exist()
    data_handling.maintain_sde()
    data_handling.id_translator_constructor()
    data_handling.vetted_groups_construction()
    data_handling.link_typeID_group()
    data_handling.build_location_info_db()

def check_folders_exist():
    def make (folder_name):
        os.mkdir(folder_name)
    
    directories = {
        "market":["history", "orders", "prices", "test"],
        "data":None
    }
    for directory in directories:
        if not os.path.isdir(directory):
            make(directory)
        if directories[directory] != None:
            for subdir in directories[directory]:
                if not os.path.isdir(directory+"/"+subdir):
                    make(directory+"/"+subdir)

