# -*- coding: utf-8 -*-
#  www.runcode.ru
#  ---------------------------------------------------------------------------------------------------------------------
import sys
import time

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QByteArray, QUrl, QUrlQuery, pyqtSlot
from PyQt5.QtNetwork import QNetworkCookie
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEnginePage, QWebEngineScript
from PyQt5.QtWebEngineCore import QWebEngineHttpRequest
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog
from lxml import html, etree

from py.static_function import thread

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/79.0.3945.88 Safari/537.36'
}


class Browser(QWebEngineView):
    """class auction, Browser"""

    def __init__(self, parent, sid, url):
        super().__init__()
        self.url = url
        self.sid = sid
        self.request = QWebEngineHttpRequest()
        self.user_agent = self.page().profile().defaultProfile()

        self.status_captcha = False
        self.loot_id = None
        self.item_id = None
        self.bet = None

        self.init_browser()

    def init_browser(self):
        self.setFixedSize(1350, 800)
        from doa import resource_path, ICON
        self.setWindowIcon(QtGui.QIcon(resource_path(ICON)))
        self.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)

        self.load_auction()

    def load_auction(self):
        self.user_agent.setHttpUserAgent(HEADERS['User-Agent'])
        cookie = QNetworkCookie(b'dosid', QByteArray(self.sid.encode()))
        self.page().profile().cookieStore().setCookie(cookie, QUrl(self.url))

        url_auction = f'{self.url}//indexInternal.es?action=internalAuction'
        self.setWindowTitle(url_auction)
        self.request.setUrl(QtCore.QUrl(url_auction))

        self.page().load(self.request)

    @thread
    def reload_page(self):
        self.page().toHtml(self.parse_shop)

    def parse_shop(self, view_html):
        tree = html.fromstring(view_html)
        url_token = tree.xpath('//form[@name="placeBid"]/@action')[0]
        auction_type = tree.xpath('//input[@name="auctionType"]/@value')[0]
        sub_action = tree.xpath('//input[@name="subAction"]/@value')[0]
        buy_button = tree.xpath('//input[@name="auction_buy_button"]/@value')[0]

        shop = [url_token, auction_type, sub_action, buy_button]

        self.post_shop(shop, self.loot_id, self.item_id, self.bet)

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
        self.load(self.request)

        print("роверяем на странице капчу =====>>>>>")

        self.captcha_check()

    def captcha_check(self):
        self.page().toHtml(self.parse_captcha)

    def parse_captcha(self, view_html):
        tree = html.fromstring(view_html)
        captcha = tree.xpath('//form[@id="captchaCheckForm"]')

        if captcha:
            self.status_captcha = True
            if not self.show():
                self.show()

            QMessageBox.information(self, "reCaptcha",
                                        "Unfortunately, the bot caught the captcha, solve it and close the browser window.")

    def closeEvent(self, event):
        """exit application """
        close = QMessageBox.question(self, "Quit Browser",
                                     "If you decide to captcha, then close the window, and click Start.",
                                     QMessageBox.Yes | QMessageBox.No)

        if close == QMessageBox.Yes:
            self.status_captcha = False
            event.accept()
        else:
            event.ignore()
