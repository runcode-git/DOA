# -*- coding: utf-8 -*-
#  www.runcode.ru
#  Project:DOA_1.01 |  Scripts:authorize | Author:RUNCODE | Date: 22.05.2019
#  --------------------------------------------------------------------------
import logging
import requests
from lxml import etree
from lxml import html

url_game = 'https://www.darkorbit.com'

proxy = {
    # 'http': 'http://87.103.234.116:3128',
    # 'https': 'https:/91.208.39.70:8080'
}

session = requests.Session()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/60.0.3112.113 Safari/537.36 '
}


def parse_url_token():
    """парсим страницу и находим токен сессии"""
    try:
        get_html = session.get(url_game, headers=headers, proxies=proxy)
        tree = html.fromstring(get_html.text)
        token = tree.xpath('//form[@class = "bgcdw_login_form"]/@action')[0]
        return token
    except requests.exceptions.ConnectionError:
        return False


def login_user(user, password):
    """параметры формы входа"""
    parameters = {
        "username": user,
        "password": password
    }
    # делаем пост запрос на вход
    if parse_url_token():
        post = session.post(parse_url_token(), data=parameters, headers=headers, proxies=proxy)
        server_url = post.url[post.url.index("https"):post.url.index("com") + len("com")]
        try_url = server_url + '/indexInternal.es?action=internalStart&prc=100'
        if post.url == try_url:
            logging.info(f'status:{post.status_code}  {post.url}')
            logging.info('You have successfully logged in')
            print(post.status_code)
            print(post.url)
            return post
        else:
            print(post.url)
            print('=================')
            print('Error', server_url)
            return False
    else:
        return None


def login_sid(server, sid):
    """вход sid"""
    try:
        link = 'https://' + server + '.darkorbit.com/indexInternal.es?action=internalStart&prc=100'
        login = session.get(link, cookies={'dosid': sid}, headers=headers, proxies=proxy)
        server_url = link[link.index("https"):link.index("com") + len("com")]
        try_url = server_url + '/indexInternal.es?action=internalStart&prc=100'
        if login.url == try_url:
            print(login.status_code)
            print(login.url)
            return login
        else:
            print(login.url)
            print('=================')
            print('Error')
            return False
    except requests.exceptions.ConnectionError:
        return None


def url_auction(post):
    try:
        auction_url = post.url[post.url.index("https"):post.url.index("com") + len("com")]
        auction_url += '/indexInternal.es?action=internalAuction'
        auction_url = session.get(auction_url, headers=headers, proxies=proxy)

        if auction_url.status_code == 200:
            logging.info('Load the auction table')
            tree = save_html_read(auction_url)  # save html, read

            times = parse_time(tree)  # parse time
            label = label_auction(tree)  # parse label
            credit = user_credit(tree)  # parse credit
            items = parse_auction_table(tree)  # parse items table
            shop = parse_shop(tree)

            return auction_url, times, label, credit, items, shop

    except requests.exceptions.ConnectionError:
        return None, None, 'Connection Error', None, [], None


def save_html_read(auction_url):
    """сохраняем страницу аукцина """

    with open("config/auction.html", 'w', encoding='utf-8') as input_file:
        input_file.write(auction_url.text)

    with open("config/auction.html", 'r', encoding='utf-8') as input_file:
        html_table = input_file.read()

    tree = html.fromstring(html_table)

    return tree


def label_auction(tree):
    """парсим лейбл перед часами аукциона"""
    label = tree.xpath('//div[@id = "auction_countdown"]/text()')[0]
    label = ''.join(c for c in label if c not in '1234567890:\n\t').strip(' ')

    return label


def user_credit(tree):
    """parse user credit"""
    credit = tree.xpath('//div[@id = "header_credits"]/text()')[0]
    credit = ''.join(c for c in credit if c not in ' \n\t')

    return credit


def parse_time(tree):
    """парсим время аукциона"""
    script = tree.xpath('//div[@class="realContainer"]/script')[0]
    if 'counterHour' in str(etree.tostring(script)):
        text = script.text
        times = text[text.index("var counterHour  = {"):text.index("var counterDay  = {")]
        times = times.split('\n')
        minute = times[2].strip(' minute: ,')
        seconds = times[1].strip(' second: ,')
        if int(seconds) < 10:
            seconds = '0' + seconds
            pass
        if int(minute) < 10:
            minute = '0' + minute
            pass
        times = (minute + ':' + seconds)

        return times


def parse_auction_table(tree):
    """parse auction table"""
    table = tree.xpath('//table[@class="auctionItemList"]/tbody[@class="auction_item_wrapper"]')[0]
    items = table.xpath('.//tr')

    return items


def token_url(url):
    """parse token"""
    tree = html.fromstring(url.text)
    item = tree.xpath('//form[@name="placeBid"]/@action')[0]

    return item


def parse_shop(tree):
    url_token = tree.xpath('//form[@name="placeBid"]/@action')[0]
    auction_type = tree.xpath('//input[@name="auctionType"]/@value')[0]
    sub_action = tree.xpath('//input[@name="subAction"]/@value')[0]
    buy_button = tree.xpath('//input[@name="auction_buy_button"]/@value')[0]

    return url_token, auction_type, sub_action, buy_button


def parse_item_winner(item_win, nick_win):
    """parse_item_winner"""

    with open('config/auction.html', 'r', encoding='utf-8') as file:
        html_table = file.read()

    tree = html.fromstring(html_table)
    winner_list = tree.xpath('//tbody[@class="auction_item_wrapper auction_history_wrapper"]')

    winn_count = []
    for table in winner_list:
        items = table.xpath('.//tr')
        for item in items:

            name_item = item.xpath('.//td[@class="auction_history_name_col"]')[0].text.strip()
            nick_winner = item.xpath('.//td[@class="auction_history_winner"]')[0].text.strip()

            if name_item == item_win and nick_winner == nick_win:
                winn_count.append(name_item)

    return len(winn_count)


def user_name(post):
    """parse user name"""
    tree = html.fromstring(post.text)
    username = tree.xpath('//div[@class = "userInfoLine"]/text()')[1]
    username = ''.join(c for c in username if c not in ' \n\t')
    return username


def post_shop(auction_url, shop, loot_id, item_id, bet):
    """post auction"""
    auction_url = auction_url[auction_url.index("https"):auction_url.index("com") + len("com")]

    parameters_shop = {
        'auctionType': shop[1],
        'subAction': shop[2],
        'lootId': loot_id,
        'itemId': item_id,
        'credits': bet,
        'auction_buy_button': shop[3]
    }

    url_post_shop = auction_url + shop[0]
    session.post(url_post_shop, data=parameters_shop, headers=headers, proxies=proxy)

