
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
import os
import asyncio

import esi_market
import esi_volume

asyncio.run(esi_market.download_all_orders())