try:
    from parsing_modules.abs_module import Article, ArticlePreview, BaseModule, asdict
except ModuleNotFoundError:
    from abs_module import BaseModule, ArticlePreview, Article, asdict

import json
import datetime
# from dataclasses import asdict

import demjson
import requests
from bs4 import BeautifulSoup


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
        article_url=f'https://habr.com/ru/post/{article_id}/'
    )
    return article


class HabrModule(BaseModule):

    base_url = 'https://habr.com/ru/flows/develop/'

    def get_next_url(self, previous_page: int | None = None) -> tuple[str, int]:
        if previous_page is None:
            return self.base_url, 2

        return self.base_url + f'page{previous_page}', previous_page + 1

    def fetch_raw_article_list(self, url: str) -> str:
        response = requests.get(url)
        return response.text

    def parse_article_list(self, raw_article_preview_content: str) -> list[ArticlePreview]:
        soup = BeautifulSoup(raw_article_preview_content, 'html.parser')

        parsed_content = _extract_hydration_script(soup)

        articles = [_extract_article_preview_data(
            article_preview_raw_content) for article_preview_raw_content in parsed_content.values()]

        articles.sort(key=lambda x: x.publish_datetime)
        return articles

    # FIXME: Учесть часовые пояса, разобраться с timedelta
    def fetch_guard(self, parsed_article_preview_list):

        earliest_pusblished_article: ArticlePreview = parsed_article_preview_list[0]
        timedelta: datetime.timedelta = datetime.datetime.now() - \
            earliest_pusblished_article.publish_datetime
        return timedelta.days < 1

    def fetch_raw_article_content(self, url: str) -> str:
        response = requests.get(url)
        return response.text

    def parse_article_content(self, raw_content: str) -> Article:
        soup = BeautifulSoup(raw_content, 'html.parser')

        parsed_content = list(_extract_hydration_script(soup).values())[0]

        author = parsed_content['author']['fullname']
        title = parsed_content['titleHtml']
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
            author=author,
            title=title,
            title_image_url=title_image,
            clean_body=clean_body,
            raw_body=raw_body,
            meta_tags=tags,
            links=links
        )

        return article


if __name__ == '__main__':
    module = HabrModule()
    articles = module.get_articles()
    dict_articles = [asdict(article) for article in articles]

    for article in dict_articles:
        article['publish_datetime'] = article['publish_datetime'].timestamp()
    with open('habr_res.json', 'w', encoding='UTF-8') as f:
        json.dump(dict_articles, f, ensure_ascii=False)
