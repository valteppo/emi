"""
Get market data from raspberry pi.
"""
import os
import subprocess

def get_volume():
    """
    Replaces local volume with volume stored in raspi.
    """
    cwd = os.getcwd()

    # Out with the old
    old_vols = os.listdir(cwd+"/market/volume")
    for vol in old_vols:
        os.remove(cwd+"/market/volume/"+vol)
    # Load to transfer folder
    subprocess.run(["scp","-r", "user@pi:/home/user/emi/market", cwd+"/transfer"])
    # Relocate if ok
    for db in os.listdir(cwd+"/transfer/market/volume"):
        os.replace(cwd+"\\transfer\\market\\volume\\"+db , cwd+"\\market\\volume\\"+db)
