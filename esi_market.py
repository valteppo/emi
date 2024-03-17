import aiohttp
import asyncio
import os

import data

async def main():
    translate = data.translator()
    with open(os.getcwd()+"/data/k-spaceRegions.tsv", "r") as file:
        regions = file.read().split("\n")

    async with aiohttp.ClientSession() as session:
        for region in regions:
            orders = []
            if region == "Curse":
                url = "https://esi.evetech.net/latest/markets/"+"10000012"+"/orders/" # Curse the region and Curse the ship FUCK UYO CCP
            elif region == "Providence":
                url = "https://esi.evetech.net/latest/markets/"+"10000047"+"/orders/" #again!
            else:
                url = "https://esi.evetech.net/latest/markets/"+translate[region]+"/orders/"
            page = 1
            xpage = 0
            
            params = {"page":page}
            async with session.get(url=url, params=params) as resp:
                headers = dict(resp.headers)
                try:
                    xpage = int(headers["X-Pages"])
                except:
                    print(region)
                    print(headers)
                    exit()
                page_orders = await resp.json()
                [orders.append(i) for i in page_orders]
            if xpage != page:
                for i in range(2, xpage+1):
                    params = {"page":i}
                    async with session.get(url=url, params=params) as resp:
                        page_orders = await resp.json()
                        [orders.append(j) for j in page_orders]
            print(region, len(orders))

asyncio.run(main())