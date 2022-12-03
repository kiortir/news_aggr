import requests
import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict as std_asdict
from typing import Optional


def _date_from_timestamp(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).date()


@dataclass
class PublishTimestampMixin:
    publish_datetime: datetime.datetime

    # @property
    # def publish_date(self):
    #     return _date_from_timestamp(self.publish_timestapm)


@dataclass
class ArticlePreview(PublishTimestampMixin):
    article_url: str


def asdict(obj):
    return {**std_asdict(obj),
            **{a: getattr(obj, a) for a in getattr(obj, '__add_to_dict__', [])}}


@dataclass
class Url:
    address: str
    referenced_name: str
    __add_to_dict__ = ['content']

    @property
    def content(self) -> str:
        response = requests.get(self.address)
        return response.text


@dataclass
class Article(PublishTimestampMixin):
    author: Optional[str]

    title: str
    title_image_url: Optional[str]
    raw_body: str
    clean_body: str

    links: list[str]
    meta_tags: Optional[list[str]]


class BaseModule(ABC):

    @abstractmethod
    def get_next_url(self, previous_page: int | None = None) -> tuple[str, int]:
        ...

    @abstractmethod
    def fetch_raw_article_list(self, url: str) -> str | dict:
        raise NotImplementedError()

    @abstractmethod
    def parse_article_list(self, raw_article_preview_content: str | dict) -> list[ArticlePreview]:
        ...

    @abstractmethod
    def fetch_guard(self, parsed_article_preview_list):
        ...

    # FIXME: Проверить работоспособность

    def filter_article_previews(self, articles: list[ArticlePreview]):
        return articles
        today = datetime.datetime.now().date()
        return [article for article in articles if article.publish_datetime == today]

    def get_article_previews(self) -> list[ArticlePreview]:
        articles: list[ArticlePreview] = []

        shall_get_next = True
        previous_page = None
        while shall_get_next:
            url, previous_page = self.get_next_url(previous_page)
            raw_article_preview_content = self.fetch_raw_article_list(url)
            parsed_article_preview_list = self.parse_article_list(
                raw_article_preview_content)
            articles.extend(parsed_article_preview_list)

            shall_get_next = self.fetch_guard(parsed_article_preview_list)

        return self.filter_article_previews(articles)

    @abstractmethod
    def fetch_raw_article_content(self, url: str) -> str | dict:
        ...

    @abstractmethod
    def parse_article_content(self, raw_content: str | dict) -> Article:
        ...

    def _get_article(self, article_preview: ArticlePreview):
        article_url = article_preview.article_url
        raw_article_content = self.fetch_raw_article_content(article_url)
        parsed_article_content = self.parse_article_content(
            raw_article_content)
        return parsed_article_content

    def get_articles(self):
        return [self._get_article(article) for article in self.get_article_previews()]


# url = Url(
#     'https://habr.com/ru/post/703218/',
#     'Habr'
# )
