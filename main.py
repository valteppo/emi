
""" 
Main used for scripts.
"""
import os
import requests
import datetime
import tarfile

cwd = os.getcwd()
yesterday = datetime.datetime.now() - datetime.timedelta(days=14)
print(yesterday)
files = os.listdir(cwd + "/data/")
for file in files:
    tokens = file.split(".")
    if tokens[-1] == "bz2":
        tar = tarfile.open(cwd + "/data/" + file)
        tar.extractall()
        tar.close()

# tar = tarfile.open(cwd+f"/data/")
# tar.extractall(filter='data')
# tar.close()


