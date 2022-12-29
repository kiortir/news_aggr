import datetime
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import reduce
from typing import Callable, Iterable
import inspect
import functools

import httpx


@dataclass
class ArticlePreview:
    url: str
    publish_datetime: datetime.datetime


class arecursion(object):
    "Украл с хабра. Рандомно навесил async/await"

    def __init__(self, func):
        self.func = func

    async def __call__(self, *args, **kwargs):
        result = await self.func(*args, **kwargs)
        while callable(result):
            result = await result()
        return result

    async def call(self, *args, **kwargs):
        async def wrapper():
            return await self.func(*args, **kwargs)

        return wrapper


def allow_none(foo: Callable):

    @functools.wraps(foo)
    def wrapper(*args):
        if not len(args) or len(args) > 1:
            raise ValueError("Не предусмотрено для множественных аргументов")

        if not args[0]:
            return None

        return foo(*args)

    return wrapper


def isAsync(foo):
    return inspect.iscoroutine(foo)


async def a_apply(unit, f):
    result = f(unit)
    return await result if isAsync(result) else result


#!FIXME tail recursion?
async def a_reduce(f: Callable, it: Iterable, initial=None):

    for i in it:
        initial = await f(initial, i)

    return initial


def get_pipe(*functions):

    async def _pipe(unit):
        return await a_reduce(a_apply, functions, unit)

    return _pipe


class BaseModule(ABC):

    def __init__(self, base_url="") -> None:
        super().__init__()
        self.base_url = base_url

    def get_next_url(self, url: str, generations: int):
        return ""

    async def get_content(self, url: str) -> httpx.Response | None:
        print("Собираем содержимое")

        async with httpx.AsyncClient() as client:
            r = await client.get(url)
        return r


    def interpret_response(self, content: httpx.Response):
        return content.content

    def interpret_article_response(self, *args):
        return self.interpret_response(*args)

    @abstractmethod
    def parse_content(self, raw_content) -> list[ArticlePreview]:
        ...

    def filter_content(self, content: list[ArticlePreview]):
        return content

    def sort_content(self, content):
        return content

    @classmethod
    def guard_pipe(cls, content: list[ArticlePreview]):
        latest = content.pop()
        if latest.publish_datetime.date() == datetime.datetime.now().date():
            return content

    @arecursion
    async def gather_articles(self, page_url=None, articles=None, generation=1):
        
        if page_url == None:
            page_url = self.base_url

        if articles is None:
            articles = []

        pipe = get_pipe(
            *map(allow_none, [
                self.get_content,
                self.interpret_response,
                self.parse_content,
                self.guard_pipe,
                self.filter_content,
                self.sort_content,
            ]))

        page_articles = await pipe(page_url)

        if page_articles:
            articles.extend(page_articles)

            await self.gather_articles(
                self,
                self.get_next_url(page_url, generation),
                articles=articles,
                generation=generation + 1
            )

        return articles
