# -*- coding: utf-8 -*-
#  www.runcode.ru
#  Project:DOA_1.01 |  Scripts:update_version | Author:RUNCODE | Date: 01.06.2019
#  ----------------------------------------------------------------
import requests
from lxml import html, etree

url_bot = 'https://doa.runcode.ru/'
url_guide = "https://doa.runcode.ru/p/guide.html"

proxy = {
    # 'http': 'http://87.103.234.116:3128',
    # 'https': 'https:/91.208.39.70:8080'
}

session_update = requests.Session()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/60.0.3112.113 Safari/537.36 '
}


def parse_version():
    """парсим страницу и находим токен сессии"""
    try:
        get_html = session_update.get(url_bot, headers=headers, proxies=proxy)
        tree = html.fromstring(get_html.text)
        version = tree.xpath('//a[@class = "btn btn-success btn-sm"]/@title')[0].upper()
        print(version.strip())
        return version.strip()
    except requests.exceptions.ConnectionError:
        return False


def parse_guide():
    try:
        get_html = session_update.get(url_guide, headers=headers, proxies=proxy)
        tree = html.fromstring(get_html.content)
        guide = tree.xpath('//div[@class = "post-body entry-content float-container"]')[0]

        return etree.tostring(guide, encoding="unicode")
    except requests.exceptions.ConnectionError:
        return False


def load_guide():
    """сохраняем страницу guide """
    with open("config/guide.html", 'w', encoding='utf-8') as input_file:
        input_file.write(parse_guide())
    with open("config/guide.html", 'r', encoding='utf-8') as input_file:
        html_guide = input_file.read()

    return html_guide

# print(load_guide())
