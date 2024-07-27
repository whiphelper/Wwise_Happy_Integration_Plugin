from PyQt5 import uic
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QWidget, QMessageBox
from globals import *
from Logs import *


class Window_ProgressBar(QWidget):
    def __init__(self):
        super().__init__()

        # Load GUI
        self.ui = uic.loadUi("cf\\gui\\ProgressBar.ui")

        # Init
        self.progressBar = self.ui.progressBar


class Window_MessageBox(QWidget):
    def __init__(self):
        super().__init__()

    def MessageBox_NoticeOnly(self, titleText, infoText):
        messageBox = QMessageBox(QMessageBox.Warning, titleText, infoText)
        messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
        Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
        messageBox.exec_()

        if messageBox.clickedButton() == Qyes:
            pass

    @staticmethod
    def GetDefaultFont():
        if key["Language"] == "Chinese":
            Font_Def = key["DefaultFont_Chinese"]
        else:
            Font_Def = key["DefaultFont_English"]

        return Font_Def
