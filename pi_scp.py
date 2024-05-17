"""
Get market data from raspberry pi.
"""
import os
from paramiko import SSHClient
from scp import SCPClient

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
    ssh = SSHClient()
    ssh.load_system_host_keys()
    ssh.connect(hostname='pi', username='user', password='user')
    cwd = os.getcwd()
    with SCPClient(ssh.get_transport()) as scp:
        scp.get(recursive=True, remote_path="/home/user/emi/transfer", local_path=cwd)

    # Relocate if ok
    for db in os.listdir(cwd+"/transfer/market/history"):
        os.replace(cwd+"\\transfer\\market\\history\\"+db , cwd+"\\market\\history\\"+db)
    for db in os.listdir(cwd+"/transfer/market/orders"):
        os.replace(cwd+"\\transfer\\market\\orders\\"+db , cwd+"\\market\\orders\\"+db)

def get_trades():
    ssh = SSHClient()
    ssh.load_system_host_keys()
    ssh.connect(hostname='pi', username='user', password='user')
    cwd = os.getcwd()

    with SCPClient(ssh.get_transport()) as scp:
        scp.get(recursive=True, remote_path="/home/user/emi/output/", local_path=cwd)

#get_trades()
get_orders_volumes()