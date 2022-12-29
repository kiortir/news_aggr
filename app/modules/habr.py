from modules.basemodule import ArticlePreview, BaseModule, Article
from bs4 import BeautifulSoup
import demjson3 as demjson

import datetime


def _extract_hydration_script(soup: BeautifulSoup) -> dict:
    script_tags = soup.find_all('script')

    script = None

    for script_tag in script_tags:
        if script_tag.text.startswith('window.__INITIAL_STATE__'):
            script = script_tag
            break

    if script is None:
        return {}
    clean_tag_content = script.text.split(';(function')[0][25:]
    parsed_content = demjson.decode(clean_tag_content, encoding="UTF-8")
    if parsed_content is None:
        return {}
    return parsed_content[
        'articlesList']['articlesList']   # type: ignore


def _parse_datetime(datetimestr: str):
    return datetime.datetime.strptime(datetimestr[:-6], '%Y-%m-%dT%H:%M:%S')


def _extract_article_preview_data(article_preview_data: dict) -> ArticlePreview:
    article_id = article_preview_data['id']
    raw_publish_datetime = article_preview_data['timePublished']
    parsed_datetime = _parse_datetime(raw_publish_datetime)
    article = ArticlePreview(
        publish_datetime=parsed_datetime,
        url=f'https://habr.com/ru/post/{article_id}/'
    )
    return article


class HabrModule(BaseModule):

    def get_next_url(self, url: str, generation: int):
        print(url, generation)
        if generation == 0:
            return self.base_url

        return self.base_url + f'page{generation + 1}'

    def parse_content(self, raw_content) -> list[ArticlePreview]:
        soup = BeautifulSoup(raw_content, 'html.parser')

        parsed_content = _extract_hydration_script(soup)

        articles = [_extract_article_preview_data(
            article_preview_raw_content) for article_preview_raw_content in parsed_content.values()]

        return articles

    async def parse_article(self, raw_content):
        soup = BeautifulSoup(raw_content, 'html.parser')

        parsed_content = list(_extract_hydration_script(soup).values())[0]

        # author = parsed_content['author']['fullname']
        title = parsed_content.get('titleHtml')
        # FIXME: Переделать проверку на наличие фото
        try:
            title_image = parsed_content['leadData']['image']['url']
        except TypeError:
            title_image = None
        tags = [tag['titleHtml'] for tag in parsed_content['tags']]
        raw_body = parsed_content['textHtml']

        cleaning_soup = BeautifulSoup(raw_body, 'html.parser')
        clean_body = cleaning_soup.text
        time_published = parsed_content['timePublished']

        # FIXME: Переосмыслить с учетом наличия объекта URL

        links = [href for url in cleaning_soup.find_all(
            'a') if (href := getattr(url, 'href', None)) != None]

        article = Article(
            publish_datetime=_parse_datetime(time_published),
            # author=author,
            title=title,
            title_img_url=title_image,
            # clean_body=clean_body,
            content=raw_body,
            # meta_tags=tags,
            # links=links
        )

        return article

    async def parse_articles(self, raw_articles):
        return [await self.parse_article(article) for article in raw_articles]
