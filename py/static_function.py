# -*- coding: utf-8 -*-
#  www.runcode.ru
#  Project:DOA_1.01 |  Scripts:static_function | Author:RUNCODE | Date: 19.05.2019
#  ----------------------------------------------------------------

import threading
# from string import printable
# from transliterate import translit


def thread(func):
    """функция потоков"""

    def wrapper(*args, **kwargs):
        """потоки"""
        my_thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        my_thread.start()

    return wrapper


def thread_up(func):
    """функция потоков"""

    def wrapper(*args, **kwargs):
        """потоки"""
        my_thread2 = threading.Thread(target=func, args=args, kwargs=kwargs)
        my_thread2.start()
        my_thread2.join()

    return wrapper


def filter_int(number):
    """ filter int """
    number = ''.join(c for c in number if c not in '.')
    return number


def str_filter(text):
    """фильтр убиваем табы, пробелы, пернос строк"""
    result = ''.join(c for c in text if c not in ' \n\t\b')
    return result


def add_zero(zero):
    """add zero"""
    if zero < 10 or zero == 0:
        zero = '0' + str(zero)
    else:
        zero = str(zero)
    return zero