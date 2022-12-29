import json
from modules.habr import HabrModule
import asyncio

module = HabrModule("https://habr.com/ru/flows/develop/")


async def main():
    r = await module.extract()
    with open('results.json', 'w', encoding='utf-8') as f:
        json.dump(r, f, ensure_ascii=False)

asyncio.run(main())
