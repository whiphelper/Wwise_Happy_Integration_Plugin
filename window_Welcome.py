from PyQt5.QtWidgets import QApplication
import sys
from window_Main import *
from globals import *


class Window_Welcome(QWidget):
    def __init__(self):
        super().__init__()

        # Load GUI
        self.ui = uic.loadUi("cf\\gui\\Welcome.ui")
        self.ui.setWindowTitle(lan["GUIText_WelcomeTitle"][L])

        # Init items
        self.label_Welcome = self.ui.label_Welcome
        self.label_WelcomeText = self.ui.label_WelcomeText

        self.textEdit_WwiseInfo = self.ui.textEdit_WwiseInfo
        self.label_WwiseSessionPath = self.ui.label_WwiseSessionPath
        self.lineEdit_WwiseSessionPath = self.ui.lineEdit_WwiseSessionPath
        self.pushButton_WwiseSessionPath = self.ui.pushButton_WwiseSessionPath
        self.label_Log = self.ui.label_Log
        self.pushButton_LaunchTool = self.ui.pushButton_LaunchTool
        self.checkBox_DoNotShowOnStartUp = self.ui.checkBox_DoNotShowOnStartUp

        # Set Logic
        self.label_Welcome.setText(lan["GUIText_Welcome_PluginNameText"][L])
        self.label_Welcome.setFont(QFont(self.GetDefaultFont(), lan["GUIText_Welcome_PluginNameText_FontSize"][L]))
        self.label_WelcomeText.setText(lan["GUIText_Welcome_PluginName"][L])
        self.label_WelcomeText.setFont(QFont(self.GetDefaultFont(), lan["GUIText_Welcome_PluginName_FontSize"][L]))

        self.textEdit_WwiseInfo.setReadOnly(True)
        self.label_WwiseSessionPath.setText(lan["GUI_LOG_WwiseProjectFolderPath"][L])
        self.pushButton_WwiseSessionPath.setText(lan["GUIText_LabelBrowseWwisePath"][L])
        self.label_WwiseSessionPath.setVisible(False)
        self.lineEdit_WwiseSessionPath.setVisible(False)
        self.pushButton_WwiseSessionPath.setVisible(False)
        self.pushButton_LaunchTool.setText(lan["GUIText_label_LaunchTool"][L])
        self.checkBox_DoNotShowOnStartUp.setText(lan["GUI_checkbox_donotshowWelcomePageonnextstartup"][L])

        self.label_Log.setVisible(False)
        self.pushButton_WwiseSessionPath.clicked.connect(self.LocatePath_WwiseSessionAtWelcomeStage)
        self.lineEdit_WwiseSessionPath.setText(global_curWwisePath)
        self.lineEdit_WwiseSessionPath.setReadOnly(True)
        self.pushButton_LaunchTool.clicked.connect(self.OpenWindow_Main)

        self.checkBox_DoNotShowOnStartUp.stateChanged.connect(self.RefreshJsonLog_CheckedBox)

        if len(self.SafetyCheck_WwiseSessionPath()) != 0:
            self.lineEdit_WwiseSessionPath.setStyleSheet("color:red")
            self.label_Log.setStyleSheet("color:red")
            self.label_Log.setText(lan["GUIText_InvalidWwiseSessionPath"][L])
            self.pushButton_LaunchTool.setEnabled(False)

        if not self.CheckIfInfoJsonIsValid():
            self.label_Log.setStyleSheet("color:red")
            self.label_Log.setText(lan["GUIText_SafetyCheck_InfoJson_Failed"][L])

        self.PrintWwiseInfo()

    def RefreshJsonLog_CheckedBox(self):
        if self.checkBox_DoNotShowOnStartUp.isChecked() is True:
            key["ifNotShowWelcome"] = "True"
        else:
            key["ifNotShowWelcome"] = "False"

        SaveJson(key, global_UserPreferenceJsonPath)

    def OpenWindow_Main(self):
        messageBox = QMessageBox(QMessageBox.Warning, lan["LOG_GUI_Disclaimer"][L], lan["GUI_SafetyAlert_Content"][L])
        messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))

        Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
        Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
        messageBox.exec_()

        if messageBox.clickedButton() == Qyes:
            self.ui.close()
            self.MainWindow = Window_Main()

    def LocatePath_WwiseSessionAtWelcomeStage(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.DirectoryOnly)

        PreviousPath = self.lineEdit_WwiseSessionPath.text()

        if file_dialog.exec_():
            selected_path = str(file_dialog.selectedFiles()[0])
            selected_path = selected_path.replace("/", "\\")
            self.lineEdit_WwiseSessionPath.setText(selected_path)
        else:
            self.lineEdit_WwiseSessionPath.setText(PreviousPath)

    def SafetyCheck_WwiseSessionPath(self):
        errorlog = []
        if os.path.exists(global_curWwisePath) is False:
            errorlog.append("error")
        elif os.path.exists(global_actorPath) is False:
            errorlog.append("error")
        elif os.path.exists(global_eventPath) is False:
            errorlog.append("error")

        return errorlog

    def CheckIfValidInfoJsonInWwiseSessionPath(self):
        errorLog = []
        if not os.path.exists(global_curWwiseInfoJson):
            errorLog.append("error")
            self.label_Log.setStyleSheet("color:red")
            self.label_Log.setText(lan["GUIText_CanNotFindInfoJson"][L])
        elif not self.CheckIfInfoJsonIsValid():
            self.label_Log.setStyleSheet("color:red")
            self.label_Log.setText(lan["GUIText_SafetyCheck_InfoJson_Failed"][L])
        return errorLog

    def SaveBaseJson(self):
        try:
            if len(self.SafetyCheck_WwiseSessionPath()) != 0:
                self.lineEdit_WwiseSessionPath.setStyleSheet("color:red")
                self.label_Log.setStyleSheet("color:red")
                self.label_Log.setText(lan["GUIText_InvalidWwiseSessionPath"][L])
            elif len(self.CheckIfValidInfoJsonInWwiseSessionPath()) != 0:
                self.label_Log.setStyleSheet("color:red")
                self.label_Log.setText(lan["GUIText_SafetyCheck_InfoJson_Failed"][L])
            else:
                self.label_Log.setText("")
                self.lineEdit_WwiseSessionPath.setStyleSheet("color:black")

                TempKey = ujson.load(open(global_curWwiseInfoJson, "r", encoding="gbk"))
                projectStr = TempKey["$ProjectStr$"]
                self.label_Log.setStyleSheet("color:red")
                self.label_Log.setText(lan["GUIText_FoundTargetInfoJson"][L] + projectStr + lan["GUIText_RestartTool"][L])
                self.pushButton_LaunchTool.setEnabled(False)
                SaveJson(key, global_UserPreferenceJsonPath)
        except:
            self.label_Log.setText(lan["GUIText_SaveBaseJsonFailed"][L])

    def CheckIfInfoJsonIsValid(self):
        try:
            TempKey = ujson.load(open(global_curWwiseInfoJson, "r", encoding="gbk"))
            projectStr = TempKey["$ProjectStr$"]
            self.label_Log.setStyleSheet("color:blue")
            self.label_Log.setText(lan["GUIText_FoundTargetInfoJson"][L] + projectStr + lan["GUIText_label_ClickLaunchTool"][L])
            return True
        except:
            return False

    def PrintWwiseInfo(self):
        # 预备全局变量
        self.textEdit_WwiseInfo.append(lan["GUIText_InfoText_ProjectPath"][L])
        self.textEdit_WwiseInfo.append(global_curWwiseProjPath)

        self.textEdit_WwiseInfo.append("\n*********************************************************")
        self.textEdit_WwiseInfo.append(lan["GUIText_InfoText_MultiLanguage"][L])
        self.textEdit_WwiseInfo.append(global_voicePath)
        for i in global_LanFolderInfoList:
            self.textEdit_WwiseInfo.append(" --> " + i["folderPath"])

        self.textEdit_WwiseInfo.append("\n*********************************************************")
        self.textEdit_WwiseInfo.append(lan["GUIText_InfoText_GeneratedSoundBankPath"][L])
        for aa, bb in zip(global_SoundBankPathList.keys(), global_SoundBankPathList.values()):
            if aa is not None:
                self.textEdit_WwiseInfo.append(aa + " --> " + bb)
        self.textEdit_WwiseInfo.append("\n*********************************************************")
        self.textEdit_WwiseInfo.append(lan["GUIText_InfoText_CoreSoundListFile"][L])
        self.textEdit_WwiseInfo.append(global_curWwiseInfoJson)
        self.textEdit_WwiseInfo.append(global_curWwiseBaseJson)
        self.textEdit_WwiseInfo.append(global_curWwiseLocalJson)

    def MessageBox(self, titleText, infoText, func, *args):
        messageBox = QMessageBox(QMessageBox.Warning, titleText, infoText)
        messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))

        Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
        Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
        messageBox.exec_()

        if messageBox.clickedButton() == Qyes:
            func(*args)

    @staticmethod
    def GetDefaultFont():
        if key["Language"] == "Chinese":
            Font_Def = key["DefaultFont_Chinese"]
        else:
            Font_Def = key["DefaultFont_English"]

        return Font_Def
