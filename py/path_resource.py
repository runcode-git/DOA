# --------# -*- coding: utf-8 -*----------------------------------
#  www.runcode.ru
#  Project:DOA_1.01 |  Scripts:path_resource | Author:runcode | Date: 17.11.18
#  ----------------------------------------------------------------
import os
import sys


class PathResource:
    """docstring for PathResource"""

    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)
