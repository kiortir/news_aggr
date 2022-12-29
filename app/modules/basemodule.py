import asyncio
import datetime
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from functools import reduce
from typing import Callable, Iterable
import inspect
import functools

import httpx
from asynciolimiter import Limiter



@dataclass
class PublishDateTimeMixin:
    publish_datetime: datetime.datetime


@dataclass
class ArticlePreview(PublishDateTimeMixin):
    url: str


@dataclass
class Article(PublishDateTimeMixin):
    title: str
    title_img_url: str | None
    content: str
    
#FIXME: find elegant solution
def datetime_to_dict(z: dict):
    z['publish_datetime'] = z['publish_datetime'].timestamp()
    return z

def serialize_iter(g):
    return list(map(datetime_to_dict, map(asdict, g)))


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

    def __init__(self, base_url="", rate_limit=50) -> None:
        super().__init__()
        self.base_url = base_url
        self.rate_limiter = Limiter(rate_limit)
        self.client = httpx.AsyncClient()

    @abstractmethod
    def get_next_url(self, url: str, generations: int):
        ...

    async def get_content(self, url: str) -> httpx.Response | None:
        await self.rate_limiter.wait()
        print("Собираем содержимое", url)

        r = await self.client.get(url, follow_redirects=True)

        return r

    def interpret_response(self, content: httpx.Response):
        return content.text


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

    async def fetch_article_list(self, article_list: list[ArticlePreview]):

        article_coroutines = [self.get_content(
            article.url) for article in article_list]

        articles = await asyncio.gather(*article_coroutines)

        return articles

    async def collect_articles(self, article_list: list[ArticlePreview]):

        pipe = get_pipe(
            *map(allow_none, [
                self.fetch_article_list
            ])
        )

        return await pipe(article_list)

    def interpret_articles(self, articles):
        return map(self.interpret_article_response, articles)

    @abstractmethod
    async def parse_articles(self, raw_articles):
        ...

    async def extract(self):

        pipe = get_pipe(
            *map(allow_none, [
                self.gather_articles,
                self.collect_articles,
                self.interpret_articles,
                self.parse_articles,
                serialize_iter
            ])
        )

        return await pipe(self)
