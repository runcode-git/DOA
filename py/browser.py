# -*- coding: utf-8 -*-
#  www.runcode.ru
#  ---------------------------------------------------------------------------------------------------------------------
import sys
import threading
import time
import traceback

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QByteArray, QUrl, QUrlQuery, pyqtSlot
from PyQt5.QtNetwork import QNetworkCookie
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEnginePage, QWebEngineScript
from PyQt5.QtWebEngineCore import QWebEngineHttpRequest
from lxml import html

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/79.0.3945.88 Safari/537.36'
}


def thread(func):
    """функция потоков"""

    def wrapper(*args, **kwargs):
        """потоки"""
        my_thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        my_thread.start()

    return wrapper


class Browser:
    """class auction, Browser"""

    def __init__(self, parent, sid, url):
        self.url = url
        self.sid = sid
        self.request = QWebEngineHttpRequest()
        self.browser = QWebEngineView()
        self.user_agent = self.browser.page().profile().defaultProfile()

        self.status_recaptcha = False
        self.loot_id = None
        self.item_id = None
        self.bet = None

        self.init_browser()

    def init_browser(self):
        self.browser.setFixedSize(1350, 800)
        from doa import resource_path, ICON
        self.browser.setWindowIcon(QtGui.QIcon(resource_path(ICON)))
        self.browser.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)

        self.load_auction()

    def load_auction(self):
        self.user_agent.setHttpUserAgent(HEADERS['User-Agent'])
        cookie = QNetworkCookie(b'dosid', QByteArray(self.sid.encode()))
        self.browser.page().profile().cookieStore().setCookie(cookie, QUrl(self.url))

        url_auction = f'{self.url}//indexInternal.es?action=internalAuction'
        self.browser.setWindowTitle(url_auction)
        self.request.setUrl(QtCore.QUrl(url_auction))

        self.browser.page().load(self.request)

    @thread
    def reload_page(self):
        self.browser.page().toHtml(self.parse_shop)

    def parse_shop(self, view_html):

        tree = html.fromstring(view_html)
        url_token = tree.xpath('//form[@name="placeBid"]/@action')[0]
        auction_type = tree.xpath('//input[@name="auctionType"]/@value')[0]
        sub_action = tree.xpath('//input[@name="subAction"]/@value')[0]
        buy_button = tree.xpath('//input[@name="auction_buy_button"]/@value')[0]

        shop = [url_token, auction_type, sub_action, buy_button]

        self.post_shop(shop, self.loot_id, self.item_id, self.bet)

    def load_html(self):
        self.browser.page().toHtml(self.parse_recaptcha)

    def parse_recaptcha(self, view_html):
        tree = html.fromstring(view_html)
        recaptcha = tree.xpath('//form[@id="captchaCheckForm"]')

        # site_key = tree.xpath('//div[@class="g-recaptcha recaptcha-holding-div"]')[0].attrib['data-sitekey']
        # print('[+]site_key: ' + site_key)

        if recaptcha:
            self.status_recaptcha = True
            if not self.browser.show():
                self.browser.show()
            self.browser.page().runJavaScript("""
            document.querySelector('[role="presentation"]').contentWindow.document.getElementById("recaptcha-anchor").click();

            setTimeout(function(){
                if (document.querySelectorAll('iframe')[1] == undefined){
                    document.querySelector('.button.button-green').click();
                } 
            //document.querySelectorAll('iframe')[1].contentWindow.document.getElementById("recaptcha-audio-button").click()
            },3000)
            """)
            self.browser.close()
            self.status_recaptcha = False

    def post_shop(self, shop, loot_id, item_id, bet):
        """post auction"""

        post_data = QUrlQuery()
        post_data.addQueryItem('auctionType', shop[1])
        post_data.addQueryItem('subAction', shop[2])
        post_data.addQueryItem('lootId', loot_id)
        post_data.addQueryItem('itemId', item_id)
        post_data.addQueryItem('credits', str(bet))
        post_data.addQueryItem('auction_buy_button', shop[3])

        url = self.url + shop[0]
        self.post_request(url, post_data)

    def post_request(self, url, post_data):
        self.request.setMethod(1)
        self.request.setHeader(b'Content-Type', b'application/x-www-form-urlencoded')
        self.request.setPostData(QByteArray(post_data.toString(QUrl.FullyEncoded).encode()))
        self.request.setUrl(QtCore.QUrl(url))
        self.browser.load(self.request)

        self.load_html()