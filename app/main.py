from modules.habr import HabrModule
import asyncio

module = HabrModule("https://habr.com/ru/flows/develop/")


async def main():
    r = await module.gather_articles(module)
    print(r)

asyncio.run(main())