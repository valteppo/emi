import aiohttp
import asyncio
import os

import data



async def region_market_data():
    """
    Downloads the public market data from k-space regions
    """
    translate = data.translator()

    url_start = "https://esi.evetech.net/latest/markets/"
    async with aiohttp.ClientSession() as session:
        pass

