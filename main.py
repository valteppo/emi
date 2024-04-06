""" FIRST THINGS:
DONE, to test:
    - eve_map.system_connection_builder()

"""


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

"""
Operate with IDs, strings only for final translation.

Proper market ID listing:
    - esi_market.my_groups() are the desired groups.
    - link groups to items.

Get all lvl 4 agent systems and stations.

Check buy/sell orders in effect in system:
    - For buy, get the best nearest

"""

"""
System data
{"system_id" :  {"name": System name,
                "constellation": System constellation ID,
                "region": System region ID,
                "security": System security,
                "connections": [Connected system ID 1,
                                ... ,
                                Connected system ID n]
                }
}
"""
import data_handling
import esi_market

import asyncio

asyncio.run(esi_market.download_all_orders())

