"""
Get market data from raspberry pi.
"""
import os
import subprocess
import pyperclip

def get_orders_volumes():
    """
    Replaces local volume and orders with ones stored in raspi.
    """
    cwd = os.getcwd()

    # Remove old
    old_vols = os.listdir(cwd+"/market/history")
    for vol in old_vols:
        os.remove(cwd+"\\market\\history\\"+vol)

    old_ord = os.listdir(cwd+"/market/orders")
    for ord in old_ord:
        os.remove(cwd+"\\market\\orders\\"+ord)
    # Load to transfer folder
    subprocess.run(["scp","-r", "user@pi:/home/user/emi/transfer", cwd])
    # Relocate if ok
    for db in os.listdir(cwd+"/transfer/market/history"):
        os.replace(cwd+"\\transfer\\market\\history\\"+db , cwd+"\\market\\history\\"+db)
    for db in os.listdir(cwd+"/transfer/market/orders"):
        os.replace(cwd+"\\transfer\\market\\orders\\"+db , cwd+"\\market\\orders\\"+db)

def get_trades():
    """
    Download the generated trade opportunities from raspberry
    """
    cwd = os.getcwd()
    subprocess.run(["scp","-r", "user@pi:/home/user/emi/output/", cwd])

get_trades()