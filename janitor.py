"""
Maintain data and repo.
"""

import data
import esi_market
import aiohttp
import asyncio

data.id_translator_constructor()
asyncio.run(esi_market.download_all_orders())
esi_market.construct_prices()
esi_market.download_all_histories()