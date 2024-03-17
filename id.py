import os
import urllib.request
import zipfile

def maintain_sde()-> None:
    """
    Assures up-to-date SDE.
    """
    dir = os.getcwd()
    try:
        os.mkdir(dir+"\\data")
    except FileExistsError:
        pass
    datadir = dir + "\\data\\"
    checksum = ""

    # if no files, download
    if not os.path.exists(datadir+"sde.zip"):
        urllib.request.urlretrieve("https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/sde.zip", datadir+"\\sde.zip")
    if not os.path.exists(datadir+"checksum"):
        urllib.request.urlretrieve("https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/checksum", datadir+"\\checksum")

    # verify checksum validity
    modified_since_seconds = os.path.getmtime(datadir+"checksum")
    if modified_since_seconds > 60*60*24: # only once a day
        checksum = open(datadir+"checksum").read()
        urllib.request.urlretrieve("https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/checksum", datadir+"\\new_checksum")
        new_checksum = open(datadir+"\\new_checksum").read()
        if checksum != new_checksum:
            urllib.request.urlretrieve("https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/sde.zip", datadir+"\\sde.zip")
        os.remove(datadir+"\\checksum")
        os.rename(datadir+"\\new_checksum", datadir+"\\checksum")

def save_region_id_translation():
    regions = {}
    with zipfile.ZipFile(os.getcwd()+"/data/sde.zip", "r") as openzip:
        for name in openzip.namelist():
            tokens = name.split("/")
            if len(tokens) > 3:
                if tokens[3] == "eve" and tokens[-1] == "region.staticdata":
                    print(tokens[4])

save_region_id_translation()