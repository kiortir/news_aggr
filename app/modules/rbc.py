
from json import loads, dump
from datetime import datetime
from bs4 import BeautifulSoup, Tag

from modules.basemodule import ArticlePreview, BaseModule, Article


def parse_article_title(article_content: Tag) -> str:
    return article_content.find('h1', class_='article__header__title-in').get_text(strip=True)


def parse_article_image(article_content: Tag) -> str | None:
    image_object = article_content.find('img', class_='smart-image__img')
    if not image_object:
        return None
    return image_object['src']


def parse_authors(article_content: Tag) -> list[str]:
    return [author.get_text(strip=True) for author in article_content.find_all('a', class_='article__authors__author')]


# def parse_all_links(article_content: Tag) -> list[str]:
#     return [href for url in article_content.find_all('a') if (href := getattr(url, 'href', None)) != None]


def parse_tags(article_content: Tag) -> list[str] | None:
    return [tag.get_text(strip=True) for tag in article_content.find_all('a', class_='article__tags__item')]


def parse_publish_date(article_content: Tag) -> datetime | None:
    datetime_object = article_content.find(
        'time', class_='article__header__date')
    if not datetime_object:
        return None
    return datetime.fromisoformat(datetime_object['datetime'])


class InvalidObjectException(Exception):
    ...


class RBCModule(BaseModule):
    def get_next_url(self, generation: int) -> tuple[str, int]:
        return self.base_url.format(generation * 100)


    def interpret_response(self, content):
        return content.json()

    def interpret_article_response(self, content):
        return content.text

    def parse_content(self, raw_articles: dict) -> list[ArticlePreview]:
        # raw_articles = loads(raw_article_preview_content)
        if 'items' not in raw_articles:
            raise InvalidObjectException(
                'Unable to parse: there are no `items` element in response.')

        raw_articles = raw_articles.get('items')
        articles = []

        for raw_article in raw_articles:
            article_publish_datetime = int(
                raw_article.get('publish_date_t', -1))
            article_front_url = raw_article.get('fronturl')
            article_preview = ArticlePreview(
                publish_datetime=datetime.fromtimestamp(
                    article_publish_datetime),
                url=article_front_url
            )
            articles.append(article_preview)

        return articles

    @classmethod
    def guard_pipe(cls, parsed_article_preview_list: list[ArticlePreview]):
        latest = parsed_article_preview_list[-1]

        if datetime.today().date() == latest.publish_datetime.date():
            return parsed_article_preview_list


    def sort_content(self, content: list):
        content.sort(key=lambda x: x.publish_datetime)
        return content

    def parse_article_content(self, raw_content: str) -> Article:
        bs = BeautifulSoup(raw_content, 'html.parser')
        article_content = bs.find('div', class_='article__content')

        return Article(
            content=article_content.text,

            publish_datetime=parse_publish_date(bs),
            # meta_tags=parse_tags(bs),
            # links=parse_all_links(bs),
            # author=parse_authors(bs),
            title=parse_article_title(bs),
            title_img_url=parse_article_image(bs),
            # raw_body=article_content.text,
            # clean_body=article_content.prettify()
        )

    async def parse_articles(self, raw_articles):
        return [self.parse_article_content(article) for article in raw_articles]


# if __name__ == "__main__":
#     rbc = RBCModule()
#     articles = rbc.get_articles()
#     dict_articles = [asdict(article) for article in articles]

#     for article in dict_articles:
#         if 'publish_datetime' in article and article.get('publish_datetime'):
#             article['publish_datetime'] = int(
#                 article['publish_datetime'].timestamp())
#     with open('rbc_res.json', 'w', encoding='UTF-8') as f:
#         dump(dict_articles, f, ensure_ascii=False)
