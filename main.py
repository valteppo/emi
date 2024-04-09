
""" Control loop
Janitor:
    Check folders exist.
    Check sde exists.
    Build system info database.
Download orders.
Determine best buy/sell locations in periphery regions.
Get arbritrage candidates from price differences.
Get market history for candidate items.
Determine average volume.
Determine hauling costs.
Determine best items.
Form item list to buy.
Form eve market compliant string.
"""

import janitor
import time
import datetime

time_start = time.time()
janitor.update_esi_data()
with open("log.tsv", "a") as file:
    file.write(str(datetime.datetime.today())+"\t"+str(time.time()-time_start)+"\n")
