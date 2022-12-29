from modules.basemodule import ArticlePreview, BaseModule
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
    parsed_content = demjson.decode(clean_tag_content)
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

    def get_next_url(self, url: str, generations: int):
        if generations == 1:
            return self.base_url

        return self.base_url + f'page{generations + 1}'

    def parse_content(self, raw_content) -> list[ArticlePreview]:
        soup = BeautifulSoup(raw_content, 'html.parser')

        parsed_content = _extract_hydration_script(soup)

        articles = [_extract_article_preview_data(
            article_preview_raw_content) for article_preview_raw_content in parsed_content.values()]

        return articles
