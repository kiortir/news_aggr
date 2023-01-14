import json
from modules.habr import HabrModule
from modules.rbc import RBCModule
import asyncio

module = RBCModule(
    "https://www.rbc.ru/search/ajax/?project=rbcnews&offset={0}&limit=100")


def timeit(fn):
    import time
    async def wrapper():
        start = time.perf_counter()
        r = await fn()
        end = time.perf_counter()
        print(f"elapsed: {end-start:.{2}f}")
        return r
    return wrapper

@timeit
async def main():
    r = await module.extract()
    print(len(r))
    with open('results.json', 'w', encoding='utf-8') as f:
        json.dump(r, f, ensure_ascii=False)

asyncio.run(main())
