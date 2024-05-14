"""
Get market data from raspberry pi.
"""
import os
import subprocess
from tkinter import Tk

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

def get_jita_trades():
    """
    Download the generated trade.tsv from raspberry
    """
    cwd = os.getcwd()
    subprocess.run(["scp","-r", "user@pi:/home/user/emi/trade.tsv", cwd+"/jita_trades.tsv"])
    with open("jita_trades.tsv", "r") as file:
        data = file.readlines()[:-1]
    
    quickbar = ""
    count_len = len(str(len(data)))
    count = 0
    for line in data:
        item, profit, volume = line.strip().split("\t")
        current_count_len = len(str(count))
        zerobuffer = "".join("0"* (count_len - current_count_len))
        quickbar += f"+ {zerobuffer}{count} {item} [{profit} ISK]\n- {item} [{volume}]\n"
        count += 1

    with open("quickbar.txt", "w") as file:
        file.write(quickbar)
    

get_jita_trades()