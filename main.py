#TODO:
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
import data
data.id_translator_constructor()
