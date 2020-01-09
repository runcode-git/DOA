# -*- coding: utf-8 -*-

import logging
import os
import random
import sys
import time
import traceback

from PyQt5.QtNetwork import QNetworkCookie
from PyQt5.QtWebEngineCore import QWebEngineHttpRequest
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings

import qtmodern.styles
import qtmodern.windows

from PyQt5 import QtCore, QtGui, uic
from PyQt5.QtCore import QSettings, QThread, pyqtSignal, QTimer, QObject, Qt, QByteArray, QUrl
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMessageBox, QMainWindow, QApplication, QTableWidgetItem, QHeaderView, QInputDialog

from py import server_lists
from py.authorize import login_user, login_sid, url_auction, user_name, parse_item_winner, post_shop, HEADERS
from py.crypto import encode, decode
from py.resurse_site import parse_version, load_guide
from py.static_function import filter_int, add_zero, thread_up, thread
from py.browser import Browser


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """

    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def get_info(info):
    settings = QSettings('./config/info.ini', QSettings.IniFormat)
    settings.setIniCodec('utf-8')
    return settings.value(f'Info/{info}')


NAME = get_info("name")
VERSION = get_info("version")
PROJECT = f"{NAME} {VERSION}"
ICON = f'doa.ico'


class LoginInUserThread(QThread):
    login_in = pyqtSignal(object, name="Login_in_User")

    def __init__(self, user, password):
        super().__init__()
        self.user = user
        self.password = password

    def run(self):
        login = login_user(self.user, self.password)
        self.login_in.emit(login)


class LoginInSidThread(QThread):
    login_in = pyqtSignal(object, name="Login_in_Sid")

    def __init__(self, server, sid):
        super().__init__()
        self.server = server
        self.sid = sid

    def run(self):
        login = login_sid(self.server, self.sid)
        self.login_in.emit(login)


class UpdateTable(QThread):
    signal_update_table = pyqtSignal(object)

    def __init__(self, login, dir_setting):
        super().__init__()

        self.login = login
        self.dir_setting = dir_setting

    def run(self):
        recourse = url_auction(self.login, self.dir_setting)
        self.signal_update_table.emit(recourse)


class UpdateItem(QThread):
    update = pyqtSignal(int, str, str, str, str)

    def __init__(self, items):
        super().__init__()

        self.items = items

    def run(self):
        for row in range(len(self.items)):
            item_type = self.items[row].xpath('//input[@id="item_hour_' + str(row) + '_lootId"]/@value')[0]  # тип
            item_user_game = self.items[row].xpath('//td[@class="auction_item_highest"]/text()')[
                row].strip()  # ник игрока
            item_bet_current = self.items[row].xpath('//td[@class="auction_item_current"]/text()')[
                row].strip()  # ставка играка
            item_my_bet = self.items[row].xpath('//td[@class="auction_item_you"]/text()')[row].strip()  # моя ставка

            self.update.emit(row, item_type, item_user_game, item_bet_current, item_my_bet)

        self.items.clear()


class BlockCheckThread(QThread):
    update_block = pyqtSignal(object)

    def __init__(self, row_table, table):
        super().__init__()

        self.row_table = row_table
        self.table = table

    def run(self):
        for item in range(self.row_table):
            item_checked = self.table.item(item, 3)

            self.update_block.emit(item_checked)


class ActionApp(QMainWindow):
    """class window auction bot"""

    def __init__(self):
        super().__init__()
        uic.loadUi(resource_path('ui/window.ui'), self)
        self.setWindowIcon(QtGui.QIcon(resource_path(ICON)))

        self.setWindowTitle(PROJECT)
        self.settings = QSettings('config/login_config.ini', QSettings.IniFormat)
        self.settings.setIniCodec('utf-8')
        self.settings.setFallbacksEnabled(False)
        self.tab_auction.setEnabled(False)

        self.logger = LoggerAuction(self)
        self.logger.parent = self.plainTextEdit
        self.logger.parent.ensureCursorVisible()
        self.logger.parent.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.logger.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', "%H:%M:%S"))
        logging.getLogger().addHandler(self.logger)
        logging.getLogger().setLevel(logging.INFO)
        self.logger.signal_log.connect(self.logger.parent.appendPlainText)

        logging.info("Welcome. Log in using a User or Sid")

        self.user_login_in = LoginUser(self)
        self.sid_login_in = LoginSid(self)
        self.text_guide.setHtml(load_guide())

    def closeEvent(self, event):
        """exit application """
        close = QMessageBox.question(self, "Quit", "Do you want to close the action?", QMessageBox.Yes | QMessageBox.No)
        if close == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


class LoginUser:
    """class login in and auth in auction, username and password"""

    def __init__(self, parent):

        self.win = parent
        self.thread_login = None
        self.settings = parent.settings
        self.tabWidget = parent.tabWidget
        self.tab_auction = parent.tab_auction
        self.tab_login = parent.tab_login
        self.tab_auction = parent.tab_auction
        self.line_username = parent.line_username
        self.line_password = parent.line_password
        self.checkBox = parent.checkBox
        self.btn_login_user = parent.btn_login_user

        login_setting = self.settings.value('login')

        if login_setting:
            self.line_username.setText(login_setting[0])
            self.line_password.setText(decode(login_setting[1], login_setting[0]))

        self.checkBox.setCheckState(2)
        self.btn_login_user.clicked.connect(self.login_in)
        self.btn_login_user.setCursor(Qt.PointingHandCursor)

    def login_in(self):
        """login in username"""
        if self.line_username.text() != '' and self.line_password.text() != '':
            self.thread_login = LoginInUserThread(self.line_username.text(), self.line_password.text())
            self.thread_login.login_in.connect(self.auth_in_user)
            self.thread_login.start()
        else:
            self.message_error_login()

    def auth_in_user(self, login):
        """auth in username"""
        if login:
            if self.checkBox.checkState():
                self.save_setting_user_password()

            Auction(self.win, login)

            self.tabWidget.setCurrentWidget(self.tab_auction)
            self.tab_auction.setEnabled(True)
            self.win.tab_login_in.setEnabled(False)

        elif login is None:
            logging.error('Check your internet connection settings!')
            QMessageBox.warning(self.win, 'Error', 'Check your internet connection settings!')

        else:
            self.message_error_login()

    def save_setting_user_password(self):
        """save setting login user"""
        encode_password = encode(self.line_password.text(), self.line_username.text())
        self.settings.setValue('login', [self.line_username.text(), encode_password])
        print(self.line_username.text(), encode_password)

    def message_error_login(self):
        message = 'Invalid login or password'
        logging.error(message)
        QMessageBox.warning(self.win, 'Error', message)


class LoginSid:
    """class login in and auth in auction, server and key sid """

    def __init__(self, parent):

        self.win = parent
        self.thread_login = None
        self.link_server = None
        self.list_server = None
        self.settings = parent.settings
        self.tabWidget = parent.tabWidget
        self.tab_auction = parent.tab_auction
        self.btn_login_sid = parent.btn_login_sid
        self.check_save_server = parent.check_save_server

        self.radio_euro = parent.radio_euro  # Europa
        self.radio_en = parent.radio_america  # America
        self.radio_de = parent.radio_de  # Germany
        self.radio_es = parent.radio_es  # Spain
        self.radio_fr = parent.radio_fr  # France
        self.radio_mx = parent.radio_mx  # Mexico
        self.radio_pl = parent.radio_pl  # Poland
        self.radio_tr = parent.radio_tr  # Turkey
        self.radio_usa = parent.radio_usa  # USA
        self.radio_br = parent.radio_br  # Brazil
        self.radio_ru = parent.radio_ru  # Russia

        self.combo_server = parent.combo_server
        self.line_sid = parent.line_sid
        self.check_save_server.setCheckState(2)

        self.radio_euro.toggled.connect(lambda: self.server(server_lists.europe))
        self.radio_en.toggled.connect(lambda: self.server(server_lists.america))
        self.radio_de.toggled.connect(lambda: self.server(server_lists.germany))
        self.radio_es.toggled.connect(lambda: self.server(server_lists.spain))
        self.radio_fr.toggled.connect(lambda: self.server(server_lists.france))
        self.radio_mx.toggled.connect(lambda: self.server(server_lists.mexico))
        self.radio_pl.toggled.connect(lambda: self.server(server_lists.poland))
        self.radio_tr.toggled.connect(lambda: self.server(server_lists.turkey))
        self.radio_usa.toggled.connect(lambda: self.server(server_lists.usa))
        self.radio_br.toggled.connect(lambda: self.server(server_lists.brazil))
        self.radio_ru.toggled.connect(lambda: self.server(server_lists.russia))

        self.btn_login_sid.clicked.connect(self.login_in)
        self.btn_login_sid.setCursor(Qt.PointingHandCursor)
        self.combo_server.activated[int].connect(self.on_activated_server)

        self.radio_btn_list = {
            self.radio_euro: 'radio_euro',
            self.radio_de: 'radio_de',
            self.radio_en: 'radio_en',
            self.radio_es: 'radio_es',
            self.radio_fr: 'radio_fr',
            self.radio_mx: 'radio_mx',
            self.radio_pl: 'radio_pl',
            self.radio_tr: 'radio_tr',
            self.radio_usa: 'radio_usa',
            self.radio_br: 'radio_br',
            self.radio_ru: 'radio_ru'
        }

        for radio_btn in self.radio_btn_list.keys():
            radio_btn.setCursor(Qt.PointingHandCursor)
            radio_btn.setChecked(self.settings.value('Setting/' + self.radio_btn_list[radio_btn], False, type=bool))

        server_item = self.settings.value('Setting/server')
        if server_item:
            self.combo_server.setCurrentIndex(int(server_item))
            self.on_activated_server(int(server_item))

    def server(self, list_server):
        """update global server"""
        self.list_server = None
        self.list_server = list_server
        self.combo_server.clear()

        for key in list_server.keys():
            self.combo_server.addItem(key)

        self.link_server = list_server[self.combo_server.itemText(0)]

    def on_activated_server(self, num):
        """activate global server"""
        self.link_server = self.list_server[self.combo_server.itemText(num)]

    def login_in(self):
        """login in key sid"""
        if self.link_server is not None and self.line_sid.text() != '':
            self.thread_login = LoginInSidThread(self.link_server, self.line_sid.text())
            self.thread_login.login_in.connect(self.auth_in_sid)
            self.thread_login.start()
        else:
            self.message_error_login()

    def auth_in_sid(self, login):
        """auth in key sid"""
        if login:
            if self.check_save_server.checkState():
                self.save_setting_server()

            logging.info('You have successfully logged in')
            logging.info(f'status:{login[0].status_code}  {login[0].url}')
            logging.info('Load the auction table')

            Auction(self.win, login)

            self.tabWidget.setCurrentWidget(self.tab_auction)
            self.tab_auction.setEnabled(True)
            self.win.tab_login_in.setEnabled(False)

        elif login is None:
            logging.error('Check your internet connection settings!')
            QMessageBox.warning(self.win, 'Error', 'Check your internet connection settings!')

        else:
            self.message_error_login()

    def message_error_login(self):
        message = 'Invalid server or key sid'
        logging.error(message)
        QMessageBox.warning(self.win, 'Error', message)

    def save_setting_server(self):
        self.settings.beginGroup("Setting")

        for radio_btn in self.radio_btn_list:
            self.settings.setValue(self.radio_btn_list[radio_btn], radio_btn.isChecked())

        self.settings.setValue('server', self.combo_server.currentIndex())
        self.settings.endGroup()


class Auction(QObject):
    start_update = pyqtSignal()
    stop_update = pyqtSignal()

    def __init__(self, parent=None, login=None):
        super().__init__(parent)

        self.credit = 0
        self.credit_min = 0
        self.time_second = 0
        self.time_minute = 0
        self.table_checked = 0
        self.count_winner = 0
        self.work_minute = 0
        self.work_second = 0
        self.work_hour = 0
        self.item_my_bet = 0
        self.select = []
        self.bet_list = []
        self.bet_check = []
        self.winner_list = []
        self.row_table = 0
        self.thread = None
        self.thread_up = None
        self.thread_block = None

        self.win = parent
        self.login = login[0]

        self.sid_url = login[1]

        self.browser = Browser(self, self.sid_url[0], self.sid_url[1])
        # self.browser.browser.show()

        self.version_bot = parse_version()
        logging.info(f"{self.version_bot}")
        self.username = user_name(self.login)
        self.win.setWindowTitle(f'{PROJECT} | {self.username}')

        path_dir = os.getcwd()
        self.dir_setting = F'config/{self.username}/'
        try:
            os.mkdir(f'{path_dir}/{self.dir_setting}')
        except OSError:
            print("Creation of the directory %s failed" % self.dir_setting)
        else:
            print("Successfully created the directory %s " % self.dir_setting)

        self.recourse = url_auction(self.login, self.dir_setting)

        self.dir_setting = F'config/{self.username}/'
        self.settings = QSettings(F'{self.dir_setting}{self.username}_config.ini', QSettings.IniFormat)
        self.settings.setIniCodec('utf-8')
        self.settings.setFallbacksEnabled(False)

        self.user_name = self.win.lb_user_name
        self.user_credits = self.win.lb_user_credits
        self.min_credits = self.win.lb_min_credits
        self.select_item = self.win.lb_select_item
        self.time_work_bot = self.win.lb_time_work_bot

        self.btn_limit_credit = self.win.btn_limit_credit
        self.btn_all_max_bet = self.win.btn_all_max_bet
        self.btn_update_win = self.win.btn_update_win
        self.btn_update_bot = self.win.btn_update_bot
        self.btn_donate = self.win.btn_donate
        self.start = self.win.btn_start

        self.timer_update = QTimer()
        self.timer_work = QTimer()
        self.timer = QTimer()

        self.pbm = self.win.pbm
        self.pb = self.win.pb

        self.caption = self.recourse[2]
        self.max_bet_setting = self.settings.value('Setting/all_max_bet_credit')
        self.table = self.win.table

        self.setup_auction()

    def setup_auction(self):
        self.start.setCursor(Qt.PointingHandCursor)
        self.btn_all_max_bet.setCursor(Qt.PointingHandCursor)
        self.btn_limit_credit.setCursor(Qt.PointingHandCursor)
        self.btn_update_win.setCursor(Qt.PointingHandCursor)
        self.btn_update_bot.setCursor(Qt.PointingHandCursor)
        self.btn_donate.setCursor(Qt.PointingHandCursor)

        self.btn_all_max_bet.clicked.connect(self.reset_max_bet_setting)
        self.btn_limit_credit.clicked.connect(self.min_credit_job)
        self.btn_update_win.clicked.connect(lambda: self.update_winner(self.select))
        self.btn_update_bot.clicked.connect(self.update_bot)
        self.btn_donate.clicked.connect(self.donate)
        self.start.clicked.connect(self.start_on_off)

        self.start.setCheckable(True)
        self.start.setToolTip('start bet auction')
        self.start.setStyleSheet("QPushButton {background-color: rgb(98, 132, 14); "
                                 "font: 10pt 'Verdana'; color: #fff;}")

        self.btn_donate.setStyleSheet("QPushButton {background-color: rgb(125, 102, 8); color: #ccc;}")
        self.pb.setStyleSheet("QProgressBar {font: 9pt 'Verdana'; color: #fff;}")

        print(PROJECT.strip())
        print(self.version_bot)

        if PROJECT.strip() != self.version_bot:
            self.btn_update_bot.setStyleSheet("QPushButton {background-color: rgb(98, 132, 14); color: #fff}")
            self.btn_update_bot.setText(f"UPDATE {self.version_bot}")
        else:
            self.btn_update_bot.setText('Site DOA')

        self.user_name.setText(f'User: {self.username}')
        self.settings.setValue('Setting/all_max_bet_credit', '1.000.000')

        # --------------Table--------------------

        self.table.setIconSize(QtCore.QSize(30, 30))
        self.table.horizontalHeader().setDefaultSectionSize(151)
        self.table.horizontalHeader().setMinimumSectionSize(10)

        self.table.verticalHeader().setVisible(False)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['Item', 'User', 'Bet', 'My Bet', 'Max Bet', 'Winner'])
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("QTableWidget {gridline-color: #262626; Background-color: #424242; "
                                 "alternate-background-color: #3a3a3a;}")
        self.size_head(0)
        self.size_head(5)

        # --------------time --------------------

        self.start_time(self.recourse[1])

        self.timer.timeout.connect(self.on_time)
        self.timer.start(1000)

        self.timer_work.timeout.connect(self.timer_work_bot)
        self.timer_work.start(1000)

        # запускаем таймер обновления
        self.timer_update.timeout.connect(self.update_table_thread)

        # сигнал обновления таблицы
        self.start_update.connect(self.start_update_timer)
        self.stop_update.connect(self.stop_update_timer)

        # клики
        self.table.itemDoubleClicked.connect(self.clicked_column)
        self.table.setMouseTracking(True)
        self.table.cellEntered.connect(self.cell_hover)

        logging.info('WELCOME AUCTION BOT ' + self.username)

        # создаем таблицу аукциона
        # ======================================================================================

        items = self.recourse[4]
        self.update_credit()
        self.row_table = len(items)
        self.table.setRowCount(self.row_table)

        # создаем строки таблицы
        for row in range(len(items)):
            item_name = items[row].xpath('//td[@class="auction_item_name_col"]/text()')[row].strip()  # имя объекта
            item_type = items[row].xpath('//input[@id="item_hour_' + str(row) + '_lootId"]/@value')[0]  # тип

            icon = QtGui.QIcon()

            icon.addPixmap(QtGui.QPixmap(resource_path("icons/" + str(item_type) + ".png")),
                           QtGui.QIcon.Normal, QtGui.QIcon.Off)
            #
            # icon.addPixmap(QtGui.QPixmap("icons/" + str(item_type) + ".png"), QtGui.QIcon.Normal,
            #                QtGui.QIcon.Off)

            row_icons = QTableWidgetItem()
            row_icons.setIcon(icon)
            row_icons.setBackground(QtGui.QColor(53, 53, 53))
            row_icons.setToolTip(item_name)
            self.table.setItem(row, 0, row_icons)

            # загружаем ник игрока
            row_user_name = QTableWidgetItem('-')
            row_user_name.setTextAlignment(QtCore.Qt.AlignCenter)
            style_row(row_user_name)
            self.table.setItem(row, 1, row_user_name)

            # загружаем ставки
            row_bet_current = QTableWidgetItem('0')
            row_bet_current.setTextAlignment(QtCore.Qt.AlignCenter)
            row_bet_current.setToolTip(item_type)
            style_row(row_bet_current)
            self.table.setItem(row, 2, row_bet_current)

            # максимальная ставка
            row_max_bet = QTableWidgetItem()
            row_max_bet.setTextAlignment(QtCore.Qt.AlignCenter)
            style_row(row_max_bet)
            row_max_bet.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsTristate)
            row_max_bet.setText(self.max_bet_setting)
            row_max_bet.setToolTip(f'Double click max bet limit {item_name}')
            self.table.setItem(row, 4, row_max_bet)

            # моя ставка
            row_my_bet = QTableWidgetItem()
            row_my_bet.setTextAlignment(QtCore.Qt.AlignCenter)
            style_row(row_my_bet)
            row_my_bet.setText('0')
            row_my_bet.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            row_my_bet.setCheckState(0)
            row_my_bet.setData(Qt.CheckStateRole, row_my_bet.checkState())
            row_my_bet.setToolTip(f'Double click to bet {item_name}')
            self.table.setItem(row, 3, row_my_bet)

            # колличество побед
            row_winner = QTableWidgetItem('0')
            row_winner.setTextAlignment(QtCore.Qt.AlignCenter)
            style_row(row_winner)
            self.table.setItem(row, 5, row_winner)
            self.winner_list.append(item_name)

        self.table.cellChanged.connect(self.save_settings)

        # update item table
        self.update_item(items)
        self.update_winner(self.winner_list)

    def cell_hover(self, row, column):
        item = self.table.item(row, column)

        if self.table.item(row, 3) == item:
            self.table.setCursor(Qt.PointingHandCursor)

        elif self.table.item(row, 4) == item:
            self.table.setCursor(Qt.PointingHandCursor)

        else:
            self.table.setCursor(Qt.CustomCursor)

    def update_bot(self):
        logging.info(f"update_bot ====================={self.version_bot}============================= ")
        os.system("start \"\" https://doa.runcode.ru/")

    def donate(self):
        logging.info(f"Thank you very much, I am very grateful to you {self.username} for the donation!")
        os.system("start \"\" https://www.runcode.ru/")

    def start_on_off(self):
        if self.start.isChecked():
            self.start.setText("Stop")
            logging.info(f'Start bet run :{self.start.isChecked()}')
            self.start.setToolTip('stop bet auction')
            self.start.setStyleSheet("QPushButton:checked {background-color: rgb(132, 14, 14); "
                                     "font: 10pt 'Verdana'; color: #ffffff;}")
            self.update_table_thread()

        else:
            self.start.setText("Start")
            self.start.setToolTip('start bet auction')
            self.start.setStyleSheet("QPushButton {background-color: rgb(98, 132, 14); "
                                     "font: 10pt 'Verdana'; color: #ffffff;}")
            logging.info(f'Stop bet run :{self.start.isChecked()}')

    def update_table_thread(self):
        if not self.thread_up:
            self.thread_up = UpdateTable(self.login, self.dir_setting)
            self.thread_up.signal_update_table.connect(self.table_shop)
            self.thread_up.finished.connect(self.on_finished_up)
            self.thread_up.start()

    def on_finished_up(self):
        self.thread_up = None

    def table_shop(self, recourse):
        """ загружаем объекты в таблицу """
        if recourse[0] is not None:

            self.recourse = recourse
            self.start_time(self.recourse[1])

            if not self.timer.isActive():
                self.win.tab_auction.setEnabled(True)
                self.timer_work.start(1000)
                self.timer.start(1000)
                self.start_on_off()

            items = self.recourse[4]

            # update item table
            self.update_credit()
            self.update_item(items)

        else:
            logging.error('Connection internet error! Check your internet connection settings!')
            self.start.setStyleSheet(None)
            self.win.tab_auction.setEnabled(False)
            self.timer_work.stop()
            self.timer.stop()

    def update_item(self, items):
        self.table.blockSignals(True)
        if not self.thread:
            self.thread = UpdateItem(items)
            self.thread.update.connect(self.table_up)
            self.thread.finished.connect(self.on_finished)
            self.thread.start()

    def on_finished(self):
        self.thread = None

        self.select_item.setText(f'Select item: {str(len(self.select))}')

        self.table.blockSignals(True)
        if len(self.select) == 4:
            if not self.thread_block:
                self.thread_block = BlockCheckThread(self.row_table, self.table)
                self.thread_block.update_block.connect(self.block_check)
                self.thread_block.finished.connect(self.finished_block)
                self.thread_block.start()
        else:
            if not self.thread_block:
                self.thread_block = BlockCheckThread(self.row_table, self.table)
                self.thread_block.update_block.connect(self.un_block_check)
                self.thread_block.finished.connect(self.finished_block)
                self.thread_block.start()

    def finished_block(self):
        self.thread_block = None
        self.state_checkbox()  # делаем проверку сбитых ставок
        self.bet_start()

        # роверяем выигрынные ставки за 24 часа
        if self.time_minute == 56 and self.time_second <= 20:
            self.update_winner(self.select)

        self.table.blockSignals(False)
        logging.info('======================= item table successfully updated ===========================')

    def table_up(self, row, item_type, item_user_game, item_bet_current, item_my_bet):

        self.item_my_bet = item_my_bet

        self.table.item(row, 1).setText(item_user_game)
        self.table.item(row, 2).setText(item_bet_current)
        self.table.item(row, 3).setText(item_my_bet)

        setting_bool = self.settings.value(f'Setting_max_bet_item/{item_type}')

        row_my_bet = self.table.item(row, 3)
        item_name = self.table.item(row, 0).toolTip()
        row_max_bet = self.table.item(row, 4)
        row_bet_current = self.table.item(row, 2)

        if setting_bool:
            row_max_bet.setText(setting_bool[1])
        else:
            row_max_bet.setText(self.settings.value('Setting/all_max_bet_credit'))

        # ставим ставку
        user = self.username
        credit = filter_int(self.credit)
        credit_min = filter_int(self.credit_min)
        item_my_bet = filter_int(item_my_bet)
        item_bet_current = filter_int(item_bet_current)
        row_max_bet = filter_int(row_max_bet.text())

        # проверяем свои ставки, на наличие и кто сбил, окрашиваем ячейку
        if user == item_user_game and int(item_my_bet) != 0:
            row_my_bet.setBackground(QtGui.QColor(98, 132, 14))  # зеленый
            logging.info(item_name + ' bet: ' + item_my_bet)  # ------ log info --------

        elif user != item_user_game and int(item_my_bet) != 0 and (int(row_max_bet) / 2) > int(item_bet_current):
            row_my_bet.setBackground(QtGui.QColor(132, 96, 14))  # оранжевый
            logging.info('Bet shot down:' + item_name + ': ' + item_my_bet)  # ------ log info --------

        elif user != item_user_game and int(item_my_bet) != 0 and int(row_max_bet) > int(item_bet_current):
            row_my_bet.setBackground(QtGui.QColor(132, 122, 14))  # оранжевый
            logging.info('Bet shot down:' + item_name + ': ' + item_my_bet)  # ------ log info --------

        elif user != item_user_game and int(item_my_bet) != 0:
            row_my_bet.setBackground(QtGui.QColor(132, 14, 14))  # красный
            logging.info('Bet shot down:' + item_name + ': ' + item_my_bet)  # ------ log info --------
        else:
            row_my_bet.setBackground(QtGui.QColor(53, 53, 53))

        # проверям настройки --------------------------------------------------------------------
        if setting_bool:
            row_my_bet.setCheckState(int(setting_bool[0]))
            # если чекбокс активен
            if row_my_bet.checkState() == 2:
                self.select.append(item_name)

                if int(credit) > int(credit_min):
                    # если ставка не привышает максимальную ставку
                    if int(item_bet_current) <= int(row_max_bet) or \
                            user == item_user_game and int(item_bet_current) > int(row_max_bet):

                        if user == item_user_game:
                            print(item_name + ' bet: ' + item_my_bet)
                        else:
                            # если ставка сбита
                            if user != item_user_game and int(item_my_bet) != 0:
                                print(item_name + ' bet shot down: ' + item_my_bet)
                                if self.bet_return():
                                    self.bet_list.append([item_name, row])
                                    pass

                            elif user != item_user_game and int(item_my_bet) == 0:
                                self.bet_list.append([item_name, row])
                                pass
                    else:
                        # ставка привышена
                        if int(item_my_bet) == 0:
                            row_my_bet.setBackground(QtGui.QColor(132, 14, 14))
                            pass
                else:
                    # закончились кредиты
                    self.start.setChecked(False)
                    self.start_on_off()
                    print("закончились кредиты ....")
                    logging.info('credits run out!!!')  # ------ log warning --------

            else:
                row_my_bet.setCheckState(0)
        else:
            row_my_bet.setCheckState(0)

        winner_bool = self.settings.value(f'Winner/{item_name}')
        item_winner = self.table.item(row, 5)
        item_winner.setBackground(QtGui.QColor(53, 53, 53))
        if winner_bool:
            if int(winner_bool) > 0:
                item_winner.setBackground(QtGui.QColor(98, 132, 14))

            item_winner.setText(str(winner_bool))
            item_winner.setToolTip('24 hour winnings: ' + item_name + ' = ' + str(winner_bool))
        else:
            item_winner.setText(str(self.count_winner))

    def size_head(self, width_head):
        """setting table header """
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(width_head, QHeaderView.ResizeToContents)

    def update_credit(self):

        self.info_log()

        self.credit_min = self.min_setting_credit()
        self.min_credits.setText('Limit: ' + self.credit_min)
        self.credit = self.recourse[3]
        self.user_credits.setText('Credit: ' + self.credit)

        self.winner_list = []
        self.select = []

    def info_log(self):
        """info_log"""
        print('обновляем страницу аукциона:', self.recourse[0].url, self.recourse[0].status_code)
        logging.info(self.recourse[0].url + ' status code:' + str(self.recourse[0].status_code) + ' end time auction: '
                     + str(add_zero(self.time_minute)) + ':' + str(add_zero(self.time_second)))

    def start_time(self, times):
        """ старт время  """

        time_site = times
        self.time_second = int(time_site[3] + time_site[4]) + 2
        self.time_minute = int(time_site[0] + time_site[1])

        self.on_time()

    def on_time(self):
        """ таймер времени """

        full_time = 60
        if self.time_second == 0:
            self.time_second = full_time

        self.time_second -= 1
        second = add_zero(self.time_second)
        minute = add_zero(self.time_minute)

        if second == '00':
            self.time_second = full_time
            self.time_minute -= 1

            if minute == '00':
                self.time_minute = 59
                self.win.logger.parent.clear()
                logging.info(
                    ' ========================== Start new Auction ==========================')
                self.update_table_thread()

        time_bar = self.caption + ' -- ' + str(minute) + ':' + str(second) + ' --'

        # запускаем обновление таблицы, по времени для сбитых ставок
        if self.time_minute == 0 and self.time_second == self.table_checked:
            self.update_table_thread()

        self.pb.setValue(full_time - int(minute))
        self.pbm.setValue(full_time - int(second))
        self.pb.setFormat(time_bar)

    def timer_work_bot(self):
        """ таймер времени """

        second = add_zero(self.work_second)
        minute = add_zero(self.work_minute)
        hour = add_zero(self.work_hour)

        if self.work_second != 59:
            self.work_second += 1
            print(hour + ":" + minute + ":" + second)

        else:
            self.work_second = 0
            self.work_minute += 1
            if self.work_minute == 59:
                self.work_minute = 0
                self.work_hour += 1

        self.time_work_bot.setText(' Time ' + str(hour) + ':' + str(minute) + ':' + str(second))

    def min_credit_job(self):
        """Min job credit auction"""

        num = self.min_setting_credit()
        num = int(filter_int(num))

        print(num)

        num, ok = QInputDialog.getInt(self.win, 'Min job credit auction', 'Min credit shop:', value=num, min=10000,
                                      step=10000)
        try:
            if ok:
                credits_int = '{:,}'.format(int(num)).replace(',', '.')
                self.min_credits.setText(f'Limit: {credits_int}')
                logging.info(f'MIN CREDIT SHOP: {credits_int}')  # ------ log message --------
                self.settings.beginGroup("Setting")
                self.settings.setValue('job_min_credit', credits_int)
                self.settings.endGroup()
                # запускаем  таймер обновление таблицы
                self.start_update.emit()
        except RuntimeError:
            print("работа аукциона до минимум кредитов изменилась")
            logging.error('Error save bet. Try again')  # ------ log message --------

    def min_setting_credit(self):
        """setting Min job credit auction"""

        min_credit = self.settings.value('Setting/job_min_credit')
        if min_credit:
            text = min_credit
        else:
            text = '1.000.000'

        return text

    def reset_max_bet_setting(self):
        """All item max bet credit auction"""

        num, ok = QInputDialog.getInt(self.win, 'Min job credit auction', 'Min credit shop:', value=20000, min=20000,
                                      step=10000)
        try:
            if ok:
                credit = '{:,}'.format(int(num)).replace(',', '.')

                for item_max_bet in range(self.table.rowCount()):
                    self.table.item(item_max_bet, 4).setText(credit)

                logging.info('ALL ITEM MAX BET CREDIT SHOP: ' + credit)  # ------ log message --------
                self.settings.beginGroup("Setting")
                self.settings.setValue('all_max_bet_credit', credit)
                self.settings.endGroup()
                # запускаем  таймер обновление таблицы
                self.start_update.emit()
        except RuntimeError:
            logging.error('Error save All max bet. Try again')  # ------ log message --------
            pass

    def start_update_timer(self):
        """start timer update"""
        if self.time_minute == 0 and self.time_second <= 50:
            time_up = round(random.uniform(10000, 15000))
        else:
            time_up = round(random.uniform(10000, 25000))

        print('следующее время обнавления страницы через: ' + str(time_up))
        self.table.reset()
        self.timer_update.start(time_up)

    def stop_update_timer(self):
        """stop timer update"""
        self.timer_update.stop()

    def save_settings(self, row, column=None):
        """ сохраняем пораметры в файл"""
        obj = self.table.item(row, 3)
        row_bet_current = self.table.item(row, 2)
        max_bet = self.table.item(row, 4)
        item = self.table.item(row, 0).toolTip()
        self.select = []

        if not obj.checkState():
            logging.info('LOT SHOT: ' + item)  # ------ log message --------
        else:
            logging.info('LOT ACTIVE: ' + item)  # ------ log message --------

        for item in range(self.row_table):
            if self.table.item(item, 3).checkState() == 2:
                self.select.append(item)

        if len(self.select) == 4:
            self.table.blockSignals(True)
            if not self.thread_block:
                self.thread_block = BlockCheckThread(self.row_table, self.table)
                self.thread_block.update_block.connect(self.block_check)
                self.thread_block.finished.connect(lambda: self.finished_save(row_bet_current, obj, max_bet))
                self.thread_block.start()

        else:
            self.table.blockSignals(True)
            if not self.thread_block:
                self.thread_block = BlockCheckThread(self.row_table, self.table)
                self.thread_block.update_block.connect(self.un_block_check)
                self.thread_block.finished.connect(lambda: self.finished_save(row_bet_current, obj, max_bet))
                self.thread_block.start()

    def finished_save(self, row_bet_current, obj, max_bet):
        self.thread_block = None
        self.select_item.setText('Select item: ' + str(len(self.select)))
        self.settings.beginGroup("Setting_max_bet_item")
        self.settings.setValue(row_bet_current.toolTip(), [obj.checkState(), max_bet.text()])
        self.settings.endGroup()
        self.table.blockSignals(False)

    @staticmethod
    def block_check(item_checked):
        if item_checked.checkState() != 2:
            item_checked.setFlags(Qt.NoItemFlags)
            item_checked.setToolTip(f'limits checked item')
            if item_checked.text() == '0':
                item_checked.setText('***')

    @staticmethod
    def un_block_check(item_checked):
        item_checked.setFlags(Qt.NoItemFlags)
        if item_checked.text() == '***':
            item_checked.setText('0')
        item_checked.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)

    @thread
    def update_winner(self, win_list):
        """ count winner item """

        logging.info('update item winner 24 hour')  # ------ log update --------
        try:
            for item_name in win_list:
                self.winner_up(item_name)

        except RuntimeError:
            print("No update winner item!")

    @thread_up
    def winner_up(self, item_name):

        count = parse_item_winner(item_name, self.username)

        self.settings.beginGroup("Winner")
        self.settings.setValue(item_name, count)
        self.settings.endGroup()

    @thread
    def bet_start(self):
        """ если аукцион только начался, рандомно выбираем время начало ставок """

        # если есть объекты, то ставим ставки
        time_bet_start = random.randrange(30, 50, 1)  # рандом (начальное значение, конечное значение, шаг)
        if int(self.time_minute) <= time_bet_start and len(self.bet_list) != 0 and self.start.isChecked():
            # if len(self.bet_list) != 0 and self.start.isChecked():
            print(self.bet_list)
            self.bet_run(self.bet_list)
        else:

            for item in self.bet_list:
                logging.info('Soon I will bet on: ' + item[0])  # ------ log bet --------

            self.start_update.emit()
            # ---- чистим массив ставок
            self.bet_list = []

    @thread_up
    def bet_run(self, list_lot, bet=None):
        """ ставим ставки, выделеных объектов """

        # останавливаем таймер обновления
        self.stop_update.emit()
        self.bet_list = []

        try:
            for row in list_lot:
                # ----время, через сколько делать ставку
                if bet is None:
                    bet_time = random.uniform(2, 4)
                    time.sleep(bet_time)
                    max_bet = self.table.item(row[1], 4).text()
                    bet_random = random.randrange(10000, int(filter_int(max_bet)) / 2, 10000)
                    bet_current = filter_int(self.table.item(row[1], 2).text())
                    if int(bet_current) == 0:
                        bet = int(bet_random)
                    else:
                        bet = int(bet_current) + int(random.randrange(10000, 1000000, 10000))

                loot_id = self.table.item(row[1], 2).toolTip()
                item_id = 'item_hour_' + str(row[1])

                if not self.browser.status_captcha:

                    self.browser.bet = bet
                    self.browser.loot_id = loot_id
                    self.browser.item_id = item_id

                    self.browser.reload_page()

                    print('Ставим ставку', row[0], item_id, bet)
                    logging.info('Bet on ' + row[0] + ' : ' + str(bet))  # ------ log bet --------

                else:
                    self.start.setChecked(False)
                    self.start_on_off()
                    print('Stop Auction bot, reCaptcha')
                    break

                bet = None

        except Exception as e:
            print('Ошибка:\n', traceback.format_exc())

        # запускаем  таймер обновление таблицы
        self.update_table_thread()
        self.start_update.emit()

    def bet_return(self):
        """status progress bar"""
        if self.time_minute == 0 and self.time_second <= self.table_checked:
            return True
        else:
            return False

    def state_checkbox(self):
        """status checkbox table bet down"""

        self.bet_check = []
        # проверяем таблицу на сбитые ставки
        for item in range(self.row_table):
            check_item = self.table.item(item, 3)
            row_max_bet = self.table.item(item, 4)
            row_bet_current = self.table.item(item, 2)
            user = self.table.item(item, 1).text()

            if check_item.checkState() == 2 and user != self.username and user != '-' and check_item.text() != '0' \
                    and int(filter_int(row_bet_current.text())) < int(filter_int(row_max_bet.text())):
                self.bet_check.append(check_item)

                # опеределяем время, чтобы сбить сбитые ставки
                if len(self.bet_check) > 1:
                    self.table_checked = len(self.bet_check) * 7
                else:
                    self.table_checked = len(self.bet_check) * 10

        print('Ставок сбито: ' + str(len(self.bet_check)) + ' сбиваем в: 00:' + str(add_zero(self.table_checked)))

    def clicked_column(self, item):
        """ редактирование max_bet, или ставим ставку индивидуально """
        self.stop_update.emit()
        if item.column() == 4:
            bet_current = self.table.item(item.row(), item.column())
            self.show_dialog(bet_current, filter_int(bet_current.text()))

            self.save_settings(item.row())

        elif item.column() == 3:
            bet = self.table.item(item.row(), item.column())
            max_bet = self.table.item(item.row(), 4).text()
            game_bet = self.table.item(item.row(), 2).text()
            item_name = self.table.item(item.row(), 0).toolTip()

            if game_bet == '0':
                max_bet = filter_int(max_bet)
                bet_random = random.randrange(10000, int(max_bet) / 2, 10000)
                self.show_dialog(bet, str(bet_random))

                if self.start.isChecked():
                    self.bet_run([[item_name, item.row()]], filter_int(bet.text()))
            else:
                game_bet = filter_int(game_bet)
                self.show_dialog(bet, int(game_bet) + 10000)

                if self.start.isChecked():
                    self.bet_run([[item_name, item.row()]], filter_int(bet.text()))
            pass

    def show_dialog(self, item, num):
        """ окно редактирование ставок """
        num = int(num)
        text, ok = QInputDialog.getInt(self.win, 'Input Dialog', 'Bet:', value=num, min=10000, step=10000)
        try:
            if ok:
                item.setText(('{:,}'.format(int(text)).replace(',', '.')))
                # запускаем  таймер обновление таблицы
                self.start_update.emit()
        except RuntimeError:
            print("надо повторить сохранить настройки")
            logging.error('Error save bet. Try again')  # ------ log message --------


def style_row(row):
    """ setting style table """
    row.setForeground(QColor(214, 214, 214))
    row.setFlags(Qt.NoItemFlags)


class LoggerAuction(QObject, logging.Handler):
    signal_log = pyqtSignal(object)

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

    def emit(self, record):
        msg = self.format(record)
        self.signal_log.emit(msg)


if __name__ == '__main__':
    app = QApplication([sys.argv, "--disable-web-security"])
    qtmodern.styles.dark(app)
    window = ActionApp()
    window.show()
    app.exec_()
