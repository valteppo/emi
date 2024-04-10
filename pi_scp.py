"""
Get market data from raspberry pi.
"""
import os
import subprocess

def get():
    """
    Replaces local volume and orders with ones stored in raspi.
    """
    cwd = os.getcwd()

    # Remove old
    old_vols = os.listdir(cwd+"/market/volume")
    for vol in old_vols:
        os.remove(cwd+"\\market\\volume\\"+vol)

    old_ord = os.listdir(cwd+"/market/orders")
    for ord in old_ord:
        os.remove(cwd+"\\market\\orders\\"+ord)
    # Load to transfer folder
    subprocess.run(["scp","-r", "user@pi:/home/user/emi/transfer", cwd])
    # Relocate if ok
    for db in os.listdir(cwd+"/transfer/market/volume"):
        os.replace(cwd+"\\transfer\\market\\volume\\"+db , cwd+"\\market\\volume\\"+db)
    for db in os.listdir(cwd+"/transfer/market/orders"):
        os.replace(cwd+"\\transfer\\market\\orders\\"+db , cwd+"\\market\\orders\\"+db)

get()