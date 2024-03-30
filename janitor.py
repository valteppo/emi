"""
Maintain data and repo.
"""
import os

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
