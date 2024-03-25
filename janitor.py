"""
Maintain data and repo.
"""

import data
import esi_market
import asyncio
import eve_map

# data.id_translator_constructor()
eve_map.download_kills()
eve_map.construct_regional_npc_grinder_coverage(3)
asyncio.run(esi_market.download_all_orders())
esi_market.construct_prices()
