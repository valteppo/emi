import aiohttp
import asyncio
import os

async def region_market_data():
    """
    Downloads the public market data from k-space regions
    """

    url_start = "https://esi.evetech.net/latest/markets/"
    async with aiohttp.ClientSession() as session:
        pass
