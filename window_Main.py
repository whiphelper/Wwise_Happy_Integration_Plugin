import json
import logging
import os.path
import sys
import time
import traceback
from collections import Counter
from window_Message import *
import waapi
from PyQt5.QtGui import QKeySequence, QFont, QCursor, QColor, QBrush, QStandardItemModel, QStandardItem, \
    QTextCharFormat, QTextCursor, QPainter, QPen
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtWidgets import QMainWindow, QMenu, QAction, QFileDialog, QHeaderView, QTableWidgetItem, QColorDialog, \
    QComboBox, QLineEdit, QListWidget, QCheckBox, QListWidgetItem, QMessageBox, QApplication, QGraphicsView, \
    QVBoxLayout, QGraphicsScene, QSplitter
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl, qInstallMessageHandler
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import soundfile as sf
from window_InitSession import *
from window_KeyInfo import *
from BasicTools import *
from SimpleWaapi import *
from Logs import *
from globals import *
import globals

UndoList = []
RedoList = []


class EmittingStr(QWidget):  # 这个类的部分内容转载于：https://blog.csdn.net/weixin_39626452/article/details/86700430  本内容依据“CC BY-SA 4.0”许可证进行授权。要查看该许可证，可访问https://creativecommons.org/licenses/by-sa/4.0/
    textWritten = pyqtSignal(str)  # 定义一个发送str的信号

    def write(self, text):
        # self.stdout.write(str(text))  # 这一句本是输出到console的，这里注释掉是因为暂时不能输出到console
        self.textWritten.emit(str(text))
        QApplication.processEvents()

    def flush(self):
        pass


class CustomGraphicsView(QGraphicsView):
    DIYsingelClicked = pyqtSignal(float)
    whichButtonClicked = pyqtSignal(Qt.MouseButton)
    DIYdoubleClicked = pyqtSignal(float)

    def __init__(self, wavLength, parent=None):
        super().__init__(parent)
        self.wavLength = wavLength
        self.setRenderHint(QPainter.Antialiasing)
        self.temp_circle_item = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.moveRectangle)
        self.is_mouseLeftButton_pressed = False
        self.posX = {"press": "", "release": ""}
        self.isPlaying = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fitInView(self.sceneRect())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            scene_pos = self.mapToScene(pos)
            x = scene_pos.x()
            self.posX["press"] = x
            self.is_mouseLeftButton_pressed = True
            self.whichButtonClicked.emit(Qt.LeftButton)
        elif event.button() == Qt.RightButton:
            self.whichButtonClicked.emit(Qt.RightButton)
            self.removeCircle()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            scene_pos = self.mapToScene(pos)
            x = scene_pos.x()
            self.posX["release"] = x
            self.is_mouseLeftButton_pressed = False

            if self.isPlaying is False:
                if self.posX["press"] != self.posX["release"]:
                    # LOG.debug(self.posX)
                    pass

        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_mouseLeftButton_pressed is True and self.isPlaying is False:
            # 获取鼠标的坐标
            pos = event.pos()
            # 将坐标转换为场景中的坐标
            scene_pos = self.mapToScene(pos)
            # 获取坐标的x值
            x = scene_pos.x()
            # LOG.debug(int(x))
        else:
            pass

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.isPlaying = True
            pos = event.pos()
            scene_pos = self.mapToScene(pos)
            self.DIYdoubleClicked.emit(scene_pos.x())
            self.drawCircle(scene_pos)

    def drawCircle(self, pos):
        if self.temp_circle_item is not None:
            self.scene().removeItem(self.temp_circle_item)
        self.temp_circle_item = self.scene().addRect(pos.x(), 0, 1, 30, QPen(Qt.NoPen), QBrush(Qt.darkGray))
        self.temp_circle_item.setOpacity(0.3)
        self.timer.start(100)

    def moveRectangle(self):
        if self.temp_circle_item is not None:
            rect = self.temp_circle_item.rect()
            if self.wavLength == 0:
                x = rect.x()
            else:
                x = rect.x() + (108000 / self.wavLength)  # 每毫秒移动多少个单位
            if x >= 1000:
                self.removeCircle()
            else:
                self.viewport().update()
                rect.setX(x)
                self.temp_circle_item.setRect(rect)

    def removeCircle(self):
        if self.temp_circle_item is not None:
            self.timer.stop()
            self.scene().removeItem(self.temp_circle_item)
            self.temp_circle_item = None
            self.isPlaying = False


class monitorWwiseEXE(QThread):
    CurrentStatus = pyqtSignal(int)

    def __init__(self):
        super().__init__()

    def run(self):
        while True:
            result = SafetyCheck_WwiseRunningStatus_Detailed()
            self.CurrentStatus.emit(result)
            time.sleep(1)


class Thread_XlsxToJson(QThread):
    ProcessNum = pyqtSignal(list)

    def __init__(self, xlsxPath):
        super().__init__()
        self.xlsxPath = xlsxPath

    def run(self):
        SoundListXLSX = SimpleXLSX()
        SoundListXLSX.ReadXLSX(self.xlsxPath, 0)
        TotalRowCount = SoundListXLSX.GetMaxRow()

        NewJson = {
            "$ProjectStr$": global_curWwiseProjName,
            "$ProjectGUID$": global_curWwiseProjID,
            "Data_SoundList": {}
        }
        Data_SoundList = {}
        for i in range(key["StartRowNum"], TotalRowCount + 1):
            SoundID_text = SoundListXLSX.GetCellValue(key["Col_ID"] + str(i))
            SoundID_textColor = SoundListXLSX.get_cell_color_Font(key["Col_ID"] + str(i))
            SoundID_bgColor = SoundListXLSX.get_cell_color_Fill(key["Col_ID"] + str(i))

            Notes_text = self.AutoSwitch_NoneValue_Into_StringValue(
                SoundListXLSX.GetCellValue(key["Col_Notes"] + str(i)))
            Notes_textColor = SoundListXLSX.get_cell_color_Font(key["Col_Notes"] + str(i))
            Notes_bgColor = SoundListXLSX.get_cell_color_Fill(key["Col_Notes"] + str(i))

            EventName_text = self.AutoSwitch_NoneValue_Into_StringValue(
                SoundListXLSX.GetCellValue(key["Col_EventName"] + str(i)))
            EventName_textColor = SoundListXLSX.get_cell_color_Font(key["Col_EventName"] + str(i))
            EventName_bgColor = SoundListXLSX.get_cell_color_Fill(key["Col_EventName"] + str(i))

            BankName_text = self.AutoSwitch_NoneValue_Into_StringValue(
                SoundListXLSX.GetCellValue(key["Col_BankName"] + str(i)))
            BankName_textColor = SoundListXLSX.get_cell_color_Font(key["Col_BankName"] + str(i))
            BankName_bgColor = SoundListXLSX.get_cell_color_Fill(key["Col_BankName"] + str(i))

            KeyStr_text = self.AutoSwitch_NoneValue_Into_StringValue(
                SoundListXLSX.GetCellValue(key["Col_KeyStr"] + str(i)))
            KeyStr_textColor = SoundListXLSX.get_cell_color_Font(key["Col_KeyStr"] + str(i))
            KeyStr_bgColor = SoundListXLSX.get_cell_color_Fill(key["Col_KeyStr"] + str(i))

            BodyStr_text = self.AutoSwitch_NoneValue_Into_StringValue(
                SoundListXLSX.GetCellValue(key["Col_BodyStr"] + str(i)))
            BodyStr_textColor = SoundListXLSX.get_cell_color_Font(key["Col_BodyStr"] + str(i))
            BodyStr_bgColor = SoundListXLSX.get_cell_color_Fill(key["Col_BodyStr"] + str(i))

            TailStr_text = self.AutoSwitch_NoneValue_Into_StringValue(
                SoundListXLSX.GetCellValue(key["Col_TailStr"] + str(i)))
            TailStr_textColor = SoundListXLSX.get_cell_color_Font(key["Col_TailStr"] + str(i))
            TailStr_bgColor = SoundListXLSX.get_cell_color_Fill(key["Col_TailStr"] + str(i))

            RDM_text = self.AutoSwitch_NoneValue_Into_StringValue(SoundListXLSX.GetCellValue(key["Col_RDM"] + str(i)))
            RDM_textColor = SoundListXLSX.get_cell_color_Font(key["Col_RDM"] + str(i))
            RDM_bgColor = SoundListXLSX.get_cell_color_Fill(key["Col_RDM"] + str(i))

            Lock_text = self.AutoSwitch_NoneValue_Into_StringValue(SoundListXLSX.GetCellValue(key["Col_Lock"] + str(i)))
            Lock_textColor = SoundListXLSX.get_cell_color_Font(key["Col_Lock"] + str(i))
            Lock_bgColor = SoundListXLSX.get_cell_color_Fill(key["Col_Lock"] + str(i))

            MirrorFrom_text = self.AutoSwitch_NoneValue_Into_StringValue(
                SoundListXLSX.GetCellValue(key["Col_MirrorFrom"] + str(i)))
            MirrorFrom_textColor = SoundListXLSX.get_cell_color_Font(key["Col_MirrorFrom"] + str(i))
            MirrorFrom_bgColor = SoundListXLSX.get_cell_color_Fill(key["Col_MirrorFrom"] + str(i))

            Data_SoundList[SoundID_text] = {
                "ID_textColor": SoundID_textColor,
                "ID_bgColor": SoundID_bgColor,
                "Notes": {
                    "text": Notes_text,
                    "textColor": Notes_textColor,
                    "bgColor": Notes_bgColor
                },
                "EventName": {
                    "text": EventName_text,
                    "textColor": EventName_textColor,
                    "bgColor": EventName_bgColor
                },
                "BankName": {
                    "text": BankName_text,
                    "textColor": BankName_textColor,
                    "bgColor": BankName_bgColor
                },
                "KeyStr": {
                    "text": KeyStr_text,
                    "textColor": KeyStr_textColor,
                    "bgColor": KeyStr_bgColor
                },
                "BodyStr": {
                    "text": BodyStr_text,
                    "textColor": BodyStr_textColor,
                    "bgColor": BodyStr_bgColor
                },
                "TailStr": {
                    "text": TailStr_text,
                    "textColor": TailStr_textColor,
                    "bgColor": TailStr_bgColor
                },
                "RDM": {
                    "text": RDM_text,
                    "textColor": RDM_textColor,
                    "bgColor": RDM_bgColor
                },
                "Lock": {
                    "text": Lock_text,
                    "textColor": Lock_textColor,
                    "bgColor": Lock_bgColor
                },
                "MirrorFrom": {
                    "text": MirrorFrom_text,
                    "textColor": MirrorFrom_textColor,
                    "bgColor": MirrorFrom_bgColor
                }
            }
            EmitList = [i + 1, TotalRowCount]
            self.ProcessNum.emit(EmitList)

        NewJson["Data_SoundList"] = Data_SoundList
        PossibleSaveAsFolderPath = os.path.join(global_curWwisePath, key["ExportFolderName"])
        if not os.path.exists(PossibleSaveAsFolderPath):
            os.mkdir(PossibleSaveAsFolderPath)
        currentTimeStr = getCurrentTimeStr()
        Path_NewJson = PossibleSaveAsFolderPath + "\\SoundList_FromXLSX_" + currentTimeStr + ".json"
        SaveJson(NewJson, Path_NewJson)
        open_file_folder_highlight(Path_NewJson)

    @staticmethod
    def AutoSwitch_NoneValue_Into_StringValue(value):
        if value == "None":
            return ""
        else:
            return str(value)

    def __del__(self):
        self.wait()


class Thread_WwuToJson(QThread):
    ProcessNum = pyqtSignal(list)

    def __init__(self, WwiseCurrentProjectPath):
        super().__init__()
        self.WwiseCurrentProjectPath = WwiseCurrentProjectPath

    def run(self):
        eventPath = os.path.join(self.WwiseCurrentProjectPath, "Events")
        if os.path.exists(eventPath):
            eventInfoDict = Get_EventInfos_FromAllEventWWUs(eventPath)
            eventCount = len(eventInfoDict)
            if len(eventInfoDict) != 0:
                SoundListDict_New = CreateBasicStructure_SoundListDict()
                existIDList = []
                for index, eventStr, info in zip(range(len(eventInfoDict)), eventInfoDict.keys(), eventInfoDict.values()):
                    tempIDNotesList = Get_SoundID_FromNotes(str(info["Notes"]))
                    tempEventName = eventStr

                    # 决定ID的值
                    for item in tempIDNotesList:
                        if len(item[0]) != 0:  # 如果ID有值，说明notes里有ID信息
                            if item[0] not in existIDList:  # 判断这个ID是不是在existIDList记录中
                                existIDList.append(int(item[0]))
                                NewID = item[0]
                            else:
                                NewID = GenerateSmallestID(existIDList)
                                existIDList.append(int(NewID))
                        else:  # 如果ID没值，说明notes里没信息。则直接产生新的ID
                            NewID = GenerateSmallestID(existIDList)
                            existIDList.append(int(NewID))

                        infoDict = {
                            "ID_textColor": "#000000",
                            "ID_bgColor": "#ffffff",
                            "Notes": {
                                "text": "",
                                "textColor": "#000000",
                                "bgColor": "#ffffff"
                            },
                            "EventName": {
                                "text": "",
                                "textColor": "#000000",
                                "bgColor": "#ffffff"
                            },
                            "BankName": {
                                "text": "",
                                "textColor": "#000000",
                                "bgColor": "#ffffff"
                            },
                            "KeyStr": {
                                "text": "",
                                "textColor": "#000000",
                                "bgColor": "#ffffff"
                            },
                            "BodyStr": {
                                "text": "",
                                "textColor": "#000000",
                                "bgColor": "#ffffff"
                            },
                            "TailStr": {
                                "text": "",
                                "textColor": "#000000",
                                "bgColor": "#ffffff"
                            },
                            "RDM": {
                                "text": "",
                                "textColor": "#000000",
                                "bgColor": "#ffffff"
                            },
                            "Lock": {
                                "text": "",
                                "textColor": "#000000",
                                "bgColor": "#ffffff"
                            },
                            "MirrorFrom": {
                                "text": "",
                                "textColor": "#000000",
                                "bgColor": "#ffffff"
                            }
                        }
                        infoDict["Notes"]["text"] = item[1]
                        infoDict["EventName"]["text"] = tempEventName
                        SoundListDict_New["Data_SoundList"][str(NewID)] = infoDict
                        # LOG.info(str([str(NewID), tempEventName, item[1]]))

                    # 发送进度
                    EmitList = [index + 1, eventCount]
                    self.ProcessNum.emit(EmitList)

                # 保存为info.json
                currentTimeStr = getCurrentTimeStr()
                tarJsonPath = os.path.join(self.WwiseCurrentProjectPath, "info_" + currentTimeStr + ".json")
                SaveJson(SoundListDict_New, tarJsonPath)
                LOG.info(lan["LOG_LOG_CreateJsonInfoFromWwise"][L] + tarJsonPath)
                open_file_folder_highlight(tarJsonPath)

    def __del__(self):
        self.wait()


class Thread_JsonToXlsx(QThread):
    ProcessNum = pyqtSignal(list)

    def __init__(self, WwiseCurrentProjectPath):
        super().__init__()
        self.WwiseCurrentProjectPath = WwiseCurrentProjectPath

    def run(self):
        PossibleSaveAsFolderPath = os.path.join(global_curWwisePath, key["ExportFolderName"])
        if not os.path.exists(PossibleSaveAsFolderPath):
            os.mkdir(PossibleSaveAsFolderPath)
        currentTimeStr = getCurrentTimeStr()
        xlsxPath = PossibleSaveAsFolderPath + "\\SoundList_" + currentTimeStr + ".xlsx"
        if not os.path.exists(xlsxPath):
            # 创建空表
            xlsx = SimpleXLSX()
            xlsx.CreateMultiSheetXLSX(xlsxPath, ["Data_SoundList", "Data_KeyInfo"])

            # 写入数据Data_KeyInfo
            xlsx.ReadXLSX(xlsxPath, 1)
            xlsx.WriteCell("A1", str(KeyInfoDict["Data_KeyInfo"]))
            xlsx.SaveXLSX(xlsxPath)

            # 写入数据Data_SoundList
            xlsx.ReadXLSX(xlsxPath, 0)

            # 写入表头
            xlsx.WriteCell(key["Col_ID"] + "1", "ID")
            xlsx.WriteCell(key["Col_Notes"] + "1", "Notes")
            xlsx.WriteCell(key["Col_EventName"] + "1", "EventName")
            xlsx.WriteCell(key["Col_BankName"] + "1", "BankName")
            xlsx.WriteCell(key["Col_KeyStr"] + "1", "KeyStr")
            xlsx.WriteCell(key["Col_BodyStr"] + "1", "BodyStr")
            xlsx.WriteCell(key["Col_TailStr"] + "1", "TailStr")
            xlsx.WriteCell(key["Col_RDM"] + "1", "RDM")
            xlsx.WriteCell(key["Col_Lock"] + "1", "Lock")
            xlsx.WriteCell(key["Col_MirrorFrom"] + "1", "MirrorFrom")

            xlsx.BoldText(key["Col_ID"] + "1")
            xlsx.BoldText(key["Col_Notes"] + "1")
            xlsx.BoldText(key["Col_EventName"] + "1")
            xlsx.BoldText(key["Col_BankName"] + "1")
            xlsx.BoldText(key["Col_KeyStr"] + "1")
            xlsx.BoldText(key["Col_BodyStr"] + "1")
            xlsx.BoldText(key["Col_TailStr"] + "1")
            xlsx.BoldText(key["Col_RDM"] + "1")
            xlsx.BoldText(key["Col_Lock"] + "1")
            xlsx.BoldText(key["Col_MirrorFrom"] + "1")

            startRow = key["StartRowNum"]
            if type(startRow) is not int:  # 安全检查，防止用户输入有误
                startRow = 2
            SoundList = SoundListDict["Data_SoundList"]
            lenCount = len(SoundList)
            for index, ID, value in zip(range(lenCount), SoundList.keys(), SoundList.values()):
                Cell_ID = key["Col_ID"] + str(startRow)
                Notes = key["Col_Notes"] + str(startRow)
                EventName = key["Col_EventName"] + str(startRow)
                BankName = key["Col_BankName"] + str(startRow)
                KeyStr = key["Col_KeyStr"] + str(startRow)
                BodyStr = key["Col_BodyStr"] + str(startRow)
                TailStr = key["Col_TailStr"] + str(startRow)
                RDM = key["Col_RDM"] + str(startRow)
                Lock = key["Col_Lock"] + str(startRow)
                MirrorFrom = key["Col_MirrorFrom"] + str(startRow)

                xlsx.WriteCell_TextAndColor(Cell_ID, ID, value["ID_textColor"], value["ID_bgColor"])
                xlsx.WriteCell_TextAndColor(Notes, value["Notes"]["text"], value["Notes"]["textColor"],
                                            value["Notes"]["bgColor"])
                xlsx.WriteCell_TextAndColor(EventName, value["EventName"]["text"], value["EventName"]["textColor"],
                                            value["EventName"]["bgColor"])
                xlsx.WriteCell_TextAndColor(BankName, value["BankName"]["text"], value["BankName"]["textColor"],
                                            value["BankName"]["bgColor"])
                xlsx.WriteCell_TextAndColor(KeyStr, value["KeyStr"]["text"], value["KeyStr"]["textColor"],
                                            value["KeyStr"]["bgColor"])
                xlsx.WriteCell_TextAndColor(BodyStr, value["BodyStr"]["text"], value["BodyStr"]["textColor"],
                                            value["BodyStr"]["bgColor"])
                xlsx.WriteCell_TextAndColor(TailStr, value["TailStr"]["text"], value["TailStr"]["textColor"],
                                            value["TailStr"]["bgColor"])
                xlsx.WriteCell_TextAndColor(RDM, value["RDM"]["text"], value["RDM"]["textColor"],
                                            value["RDM"]["bgColor"])
                xlsx.WriteCell_TextAndColor(Lock, value["Lock"]["text"], value["Lock"]["textColor"],
                                            value["Lock"]["bgColor"])
                xlsx.WriteCell_TextAndColor(MirrorFrom, value["MirrorFrom"]["text"], value["MirrorFrom"]["textColor"],
                                            value["MirrorFrom"]["bgColor"])

                startRow += 1

                # 发送进度
                EmitList = [index + 1, len(SoundList)]
                self.ProcessNum.emit(EmitList)

            xlsx.SaveXLSX(xlsxPath)
            LOG.info(lan["GUI_LOG_XLSXHasBeenExported"][L] + str(xlsxPath))
            # LOG.info()
            open_file_folder_highlight(xlsxPath)

    def __del__(self):
        self.wait()


class Thread_GlobalMissingWAVRelink(QThread):
    ProcessNum = pyqtSignal(list)

    def __init__(self, WwiseCurrentProjectPath):
        super().__init__()
        self.WwiseCurrentProjectPath = WwiseCurrentProjectPath

    def SearchWAVPathInOriSFXPath(self, TarWAVName, WwiseOriginalPath):
        wavPool = []
        # 在指定范围中搜索WAV名
        p = Path(WwiseOriginalPath)
        tar = p.rglob(TarWAVName)

        for item in tar:
            item = str(item).replace(WwiseOriginalPath, "")
            wavPool.append(item)

        return wavPool

    def run(self):
        SFXFolderPath = self.WwiseCurrentProjectPath + "\\Originals\\SFX\\"
        ActorMixerWwuRootPath = self.WwiseCurrentProjectPath + "\\" + global_actorString
        wwuPathList = find_targetType_files(ActorMixerWwuRootPath, "wwu")
        if len(wwuPathList) != 0:
            count_missing = []
            count_relinked = []
            count_failed_foundNothing = []
            count_failed_foundMulti = []
            for index, wwuPath in zip(range(len(wwuPathList)), wwuPathList):
                tree = ET.parse(wwuPath)
                root = tree.getroot()

                for i in root.iter("AudioFileSource"):
                    for k in i.iter("Language"):
                        if k.text == "SFX":
                            for j in i.iter("AudioFile"):
                                # LOG.debug("当前wwu中记录的值是：" + j.text)
                                # 验证路径是否存在
                                if not os.path.exists(SFXFolderPath + j.text):
                                    count_missing.append(j.text)
                                    LOG.info(lan["LOG_LOG_FoundMissingWAV"][L] + j.text)
                                    # LOG.info()
                                    wavName = os.path.split(j.text)[1]
                                    PossibleWAVPathList = self.SearchWAVPathInOriSFXPath(wavName, SFXFolderPath)
                                    if len(PossibleWAVPathList) == 1:
                                        j.text = PossibleWAVPathList[0]
                                        count_relinked.append(j.text)
                                        LOG.info(lan["LOG_LOG_RelocateMissingWAV"][L] + j.text)
                                        # LOG.info()
                                        tree.write(wwuPath, 'UTF-8', xml_declaration=True)
                                    elif len(PossibleWAVPathList) == 0:
                                        count_failed_foundNothing.append(j.text)
                                        LOG.info(lan["LOG_LOG_RelocateMissingWAVFAIL_FindNothing"][L])
                                        # LOG.info()
                                    else:
                                        count_failed_foundMulti.append({j.text: PossibleWAVPathList})
                                        LOG.info(lan["LOG_LOG_RelocateMissingWAVFAIL_FindMulti"][L] + str(
                                            PossibleWAVPathList))
                                        # LOG.info()
                # 发送进度
                EmitList = [index + 1, len(wwuPathList)]
                self.ProcessNum.emit(EmitList)
            if len(count_missing) != 0:
                LOG.info("-------------------------------------------")
                LOG.info(lan["LOG_LOG_RelocateMissingWAV_Review_FoundMissing"][L] + str(count_missing))
                if len(count_relinked) != 0:
                    LOG.info(lan["LOG_LOG_RelocateMissingWAV_Review_Relinked"][L] + str(count_relinked))
                if len(count_failed_foundNothing) != 0:
                    LOG.info(lan["LOG_LOG_RelocateMissingWAV_Review_FailRelinked_foundNothing"][L] + str(
                        count_failed_foundNothing))
                if len(count_failed_foundMulti) != 0:
                    LOG.info(lan["LOG_LOG_RelocateMissingWAV_Review_FailRelinked_foundMulti"][L] + str(
                        count_failed_foundMulti))
                LOG.info(lan["LOG_LOG_RelocateMissingWAV_Finished"][L])
            else:
                LOG.info(lan["LOG_LOG_RelocateMissingWAV_Finished_Good"][L])
            LOG.info(lan["GUI_action_RelinkMissingWAV_End"][L])

    def __del__(self):
        self.wait()


class Thread_GetAllWAVPathFromEventStr(QThread):
    ProcessNum = pyqtSignal(list)

    def __init__(self, EventList, WwiseCurrentProjectPath):
        super().__init__()
        self.EventList = EventList
        self.WwiseCurrentProjectPath = WwiseCurrentProjectPath

    def run(self):
        wavFolderList = []
        for eventStr in self.EventList:
            if len(eventStr) != 0:
                wavList = Get_WavFolderPath_From_EventName(eventStr, self.WwiseCurrentProjectPath)
                for item in wavList:
                    wavFolderList.append(item)

        wavFolderList = list(set(wavFolderList))
        if len(wavFolderList) != 0:
            for index, item in zip(range(len(wavFolderList)), wavFolderList):
                open_file_folder_highlight(item)
                # 发送进度
                EmitList = [index + 1, len(wavFolderList)]
                self.ProcessNum.emit(EmitList)

    def __del__(self):
        self.wait()


class Thread_CheckIfWAVPathIsPlaceholder_FromEventStr(QThread):
    Result = pyqtSignal(list)

    def __init__(self, row, col, EventStr, WwiseCurrentProjectPath):
        super().__init__()
        self.EventStr = EventStr
        self.WwiseCurrentProjectPath = WwiseCurrentProjectPath
        self.row = row
        self.col = col

    def run(self):
        wavList = Get_AllWAVPath_From_EventName_FlatWAVPath(self.EventStr, self.WwiseCurrentProjectPath)
        placeHolderList = []
        for wavPath in wavList:
            dBFSResult = GetWAVMAXdBFS(wavPath)
            if dBFSResult == "-inf":
                placeHolderList.append(wavPath)

        self.Result.emit([self.row, self.col, placeHolderList])


class Thread_ForSaveAs(QThread):
    SaveAsSignal = pyqtSignal(int)

    def __init__(self):
        super(Thread_ForSaveAs, self).__init__()

    def run(self):
        minNum = key["AutoSaveAsEvery"]
        secNum = minNum * 60
        while True:
            time.sleep(secNum)
            self.SaveAsSignal.emit(1)

    def __del__(self):
        self.wait()


class Thread_GlobalSafetyCheck(QThread):
    def __init__(self):
        super().__init__()

    def run(self):
        try:
            SafetyCheckForGUI()
            LOG.info(lan["GUI_action_GlobalSafetyCheck_End"][L])
        except:
            traceback.print_exc()

    def __del__(self):
        self.wait()


class ComboCheckBox(QComboBox):  # 这个类的部分内容转载于：https://blog.csdn.net/qq_45444679/article/details/130933853  本内容依据“CC BY-SA 4.0”许可证进行授权。要查看该许可证，可访问https://creativecommons.org/licenses/by-sa/4.0/
    PopUp = pyqtSignal()

    def __init__(self, items: list):
        super(ComboCheckBox, self).__init__()
        self.items = ["All"] + items
        self.box_list = []
        self.text = QLineEdit()
        self.state = 0
        self.q = QListWidget()
        for i in range(len(self.items)):
            self.box_list.append(QCheckBox())
            self.box_list[i].setText(self.items[i])
            item = QListWidgetItem(self.q)
            self.q.setItemWidget(item, self.box_list[i])
            if i == 0:
                self.box_list[i].stateChanged.connect(self.all_selected)
            else:
                self.box_list[i].stateChanged.connect(self.show_selected)

        self.q.setStyleSheet("QScrollBar{width:15px}")
        self.setStyleSheet("width: 100px; height: 27px; font-size: 10px; font-family: Courier New")
        self.text.setReadOnly(True)
        self.setLineEdit(self.text)
        self.setModel(self.q.model())
        self.setView(self.q)

    def all_selected(self):
        if self.state == 0:
            self.state = 1
            for i in range(1, len(self.items)):
                self.box_list[i].setChecked(True)
        else:
            self.state = 0
            for i in range(1, len(self.items)):
                self.box_list[i].setChecked(False)
            self.show_selected()

    def get_selected(self):
        ret = []
        for i in range(1, len(self.items)):
            if self.box_list[i].isChecked():
                ret.append(self.box_list[i].text())
        return ret

    def show_selected(self):
        self.text.clear()
        ret = ';'.join(self.get_selected())
        self.text.setText(ret)

    def showPopup(self):
        self.PopUp.emit()
        QComboBox.showPopup(self)


class QTextEditHandler(logging.Handler):
    def __init__(self, textEditObj):
        super().__init__()
        self.textEdit = textEditObj
        self.formatt = QTextCharFormat()
        self.cursor = self.textEdit.textCursor()

    def emit(self, record):
        message = self.format(record)
        try:
            # 显示输出配置
            if any(error_str in message for error_str in global_logFormat["RED"]):
                self.formatt.setForeground(QColor("red"))
            elif any(error_str in message for error_str in global_logFormat["ORANGE"]):
                self.formatt.setForeground(QColor("orange"))
            elif any(error_str in message for error_str in global_logFormat["GREEN"]):
                self.formatt.setForeground(QColor("green"))
            elif any(error_str in message for error_str in global_logFormat["BLUE"]):
                self.formatt.setForeground(QColor("blue"))
            elif any(error_str in message for error_str in global_logFormat["PURPLE"]):
                self.formatt.setForeground(QColor("purple"))
            else:
                self.formatt.setForeground(QColor("gray"))

            self.cursor.movePosition(self.cursor.End)
            self.cursor.insertText(message, self.formatt)
            self.cursor.insertBlock()
            self.textEdit.setTextCursor(self.cursor)
            self.textEdit.ensureCursorVisible()
            QApplication.processEvents()
        except:
            traceback.print_exc()


class Window_Main(QMainWindow):
    def __init__(self):
        super().__init__()

        # Load GUI
        self.ui = uic.loadUi("cf\\gui\\MainWindow.ui")
        qInstallMessageHandler(lambda *args: None)

        # ------------------------------------------------------------------- Init Windows
        self.KeyInfoWindow = Window_KeyInfo()
        self.InitSessionWindow = Window_InitSession()
        self.ui.closeEvent = self.closeEvent

        # ------------------------------------------------------------------- Init Menu ----- File
        self.menu_File = self.ui.menu_File
        self.action_Load = self.ui.action_Load
        self.action_ExportSoundList = self.ui.action_ExportSoundList
        self.action_Save = self.ui.action_Save
        self.action_SaveAsJson = self.ui.action_SaveAsJson
        self.action_SaveAsXlsx = self.ui.action_SaveAsXlsx
        self.action_TransferXlsxIntoJson = self.ui.action_TransferXlsxIntoJson
        self.action_ShowHide_Filter = self.ui.action_ShowHide_Filter
        self.action_ShowHide_NamingArea = self.ui.action_ShowHide_NamingArea
        self.action_ShowHide_Console = self.ui.action_ShowHide_Console
        self.action_ShowHide_Waveform = self.ui.action_ShowHide_Waveform
        self.action_ShowHide_Preference = self.ui.action_ShowHide_Preference
        self.action_ShowHide_SearchText = self.ui.action_ShowHide_SearchText

        # ------------------------------------------------------------------- Init Menu ----- Edit
        self.menu_Edit = self.ui.menu_Edit
        self.action_Undo = self.ui.action_Undo
        self.action_Redo = self.ui.action_Redo
        self.action_AddLine = self.ui.action_AddLine
        self.action_DeleteLine = self.ui.action_DeleteLine
        self.action_Copy = self.ui.action_Copy
        self.action_Paste = self.ui.action_Paste
        self.action_Clear = self.ui.action_Clear

        # ------------------------------------------------------------------- Init Menu ----- Wwise
        self.menu_Wwise = self.ui.menu_Wwise
        self.action_GlobalSafetyCheck = self.ui.action_GlobalSafetyCheck
        self.action_RelinkMissingWAV = self.ui.action_RelinkMissingWAV
        self.action_InitiateSession = self.ui.action_InitiateSession
        self.action_EditKeyInfo = self.ui.action_ConfigKeyInfo
        self.action_GenerateProjectSheet = self.ui.action_GenerateProjectSheet
        self.action_OpenWwiseProjectFolder = self.ui.action_OpenWwiseProjectFolder

        # ------------------------------------------------------------------- Init Menu ----- Engine
        self.menu_Engine = self.ui.menu_Engine
        self.action_CheckSoundIDStatus = self.ui.action_CheckSoundIDStatus

        # ------------------------------------------------------------------- Init Menu ----- Help
        self.menu_Help = self.ui.menu_Help
        self.action_Document = self.ui.action_Document
        self.action_VersionInfo = self.ui.action_VersionInfo
        self.action_DevMode = self.ui.action_DevMode
        self.action_Disclaimer = self.ui.action_Disclaimer

        # ------------------------------------------------------------------- Init Panel ----- GUI
        self.pushButton_Save = self.ui.pushButton_Save
        self.label_UndoRedo = self.ui.label_UndoRedo
        self.horizontalLayout_Filter = self.ui.horizontalLayout_Filter
        self.Frame_Filter = self.ui.Frame_Filter
        self.lineEdit_Find = self.ui.lineEdit_Find
        self.label_Find = self.ui.label_Find
        self.FindCount = 1
        self.pushButton_Find = self.ui.pushButton_Find
        self.pushButton_GO = self.ui.pushButton_GO
        self.progressBar = self.ui.progressBar
        self.statusbar = self.ui.statusbar
        self.pushButton_ExpandSwitch = self.ui.pushButton_ExpandSwitch
        self.pushButton_MirrorID = self.ui.pushButton_MirrorID
        self.pushButton_Recreate = self.ui.pushButton_Recreate

        # ------------------------------------------------------------------- Init Panel ----- Table
        self.tableWidget_SoundSheet = self.ui.tableWidget_SoundSheet

        # ------------------------------------------------------------------- Init Panel ----- lineEdit_SearchText
        self.Frame_SearchText = self.ui.Frame_SearchText
        self.lineEdit_SearchText = self.ui.lineEdit_SearchText
        self.pushButton_up = self.ui.pushButton_up
        self.pushButton_down = self.ui.pushButton_down

        # ------------------------------------------------------------------- Init Panel ----- Log Console
        self.textEdit_Log = self.ui.textEdit_Log
        self.handler = QTextEditHandler(self.textEdit_Log)
        Log.addHandler(self.handler)

        self.label_LogDisplayLevel = self.ui.label_LogDisplayLevel
        self.comboBox_LogDisplayLevel = self.ui.comboBox_LogDisplayLevel

        # ------------------------------------------------------------------- Init Panel ----- Wavform
        self.Frame_AdvInfo = self.ui.Frame_AdvInfo
        self.label_EventObjectRefCountTag = self.ui.label_EventObjectRefCountTag
        self.label_EventObjectRefCount = self.ui.label_EventObjectRefCount
        self.comboBox_EventObjectRef = self.ui.comboBox_EventObjectRef
        self.label_RelatedWAVCountTag = self.ui.label_RelatedWAVCountTag
        self.label_RelatedWAVCount = self.ui.label_RelatedWAVCount
        self.comboBox_RelatedWAV = self.ui.comboBox_RelatedWAV
        self.Frame_Wavform = self.ui.Frame_Wavform
        self.pushButton_LocateWAV = self.ui.pushButton_LocateWAV

        # ------------------------------------------------------------------- Init Panel ----- Preference
        self.groupBox_Preference = self.ui.groupBox_Preference

        self.label_Language = self.ui.label_Language
        self.comboBox_Language = self.ui.comboBox_Language
        self.label_LanguageHint = self.ui.label_LanguageHint

        self.label_ShowWelcomePageWhenStart = self.ui.label_ShowWelcomePageWhenStart
        self.comboBox_ShowWelcomePageWhenStart = self.ui.comboBox_ShowWelcomePageWhenStart

        self.label_AutoLoadSoundSheetWhenStart = self.ui.label_AutoLoadSoundSheetWhenStart
        self.comboBox_AutoLoadSoundSheetWhenStart = self.ui.comboBox_AutoLoadSoundSheetWhenStart

        self.label_CopyPasteMode = self.ui.label_CopyPasteMode
        self.comboBox_CopyPasteMode = self.ui.comboBox_CopyPasteMode

        self.label_AutoSaveAs_Head = self.ui.label_AutoSaveAs_Head
        self.spinBox_AutoSaveAs = self.ui.spinBox_AutoSaveAs
        self.label_AutoSaveAs_Tail = self.ui.label_AutoSaveAs_Tail
        self.comboBox_AutoSaveAs = self.ui.comboBox_AutoSaveAs
        self.label_AutoSaveAs = self.ui.label_AutoSaveAs

        self.label_AutoGenerateBanks = self.ui.label_AutoGenerateBanks
        self.comboBox_AutoGenerateBanks = self.ui.comboBox_AutoGenerateBanks

        self.label_AutoColorForEventsNotInTable = self.ui.label_AutoColorForEventsNotInTable
        self.comboBox_AutoColorForEventsNotInTable = self.ui.comboBox_AutoColorForEventsNotInTable

        self.pushButton_QuickTest = self.ui.pushButton_QuickTest

        self.label_SaveAsDefaultFolderPath = self.ui.label_SaveAsDefaultFolderPath
        self.lineEdit_SaveAsDefaultFolderPath = self.ui.lineEdit_SaveAsDefaultFolderPath
        self.pushButton_SaveAsDefaultFolderPath = self.ui.pushButton_SaveAsDefaultFolderPath

        # ------------------------------------------------------------------- Init Panel ----- Set QSplitter
        self.verticalLayout_2by2 = self.ui.verticalLayout_2by2
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.tableWidget_SoundSheet)
        self.splitter.addWidget(self.Frame_SearchText)
        self.splitter.addWidget(self.textEdit_Log)
        self.splitter.setStretchFactor(0, 2)
        self.verticalLayout_2by2.addWidget(self.splitter)

        # ------------------------------------------------------------------- Set Logic ----- Window Stuck
        self.KeyInfoWindow.ui.setWindowModality(Qt.ApplicationModal)
        self.InitSessionWindow.ui.setWindowModality(Qt.ApplicationModal)

        # ------------------------------------------------------------------- Set Logic ----- Menu ----- File
        self.action_Load.triggered.connect(lambda: self.Load_SoundListJson(global_curWwiseInfoJson))
        self.action_EditKeyInfo.triggered.connect(lambda: self.OpenWindow(self.KeyInfoWindow))
        self.action_Save.triggered.connect(self.Save_WithSafetyCheck)
        self.action_ExportSoundList.triggered.connect(self.ExportSoundList)
        self.NeedSafeFlag = 0
        self.SetState_Save()
        self.action_SaveAsJson.triggered.connect(self.SaveAs_Json)
        self.action_SaveAsXlsx.triggered.connect(self.SaveAs_Xlsx)
        self.action_TransferXlsxIntoJson.triggered.connect(self.Action_TransferXlsxIntoJson)
        self.action_ShowHide_Filter.triggered.connect(lambda: self.ShowHidePanel(self.Frame_Filter))
        self.action_ShowHide_NamingArea.triggered.connect(self.ShowHideColumn)
        self.action_ShowHide_SearchText.triggered.connect(lambda: self.ShowHidePanel(self.Frame_SearchText))
        self.action_ShowHide_Console.triggered.connect(lambda: self.ShowHidePanel(self.textEdit_Log))
        self.action_ShowHide_Waveform.triggered.connect(lambda: self.ShowHidePanel(self.Frame_AdvInfo))
        self.action_ShowHide_Preference.triggered.connect(lambda: self.ShowHidePanel(self.groupBox_Preference))

        self.ui.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
        self.menu_File.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
        self.menu_File.setTitle(lan["GUI_Menu_File"][L])
        self.action_Load.setText(lan["GUI_action_Load"][L])
        self.action_ExportSoundList.setText(lan["GUI_action_Export"][L])
        self.action_EditKeyInfo.setText(lan["GUI_action_EditKeyInfo"][L])
        self.action_Save.setText(lan["GUI_action_Save"][L])
        self.action_SaveAsJson.setText(lan["GUI_action_SaveAsJson"][L])
        self.action_SaveAsXlsx.setText(lan["GUI_action_SaveAsXlsx"][L])
        self.action_TransferXlsxIntoJson.setText(lan["GUI_action_TransferXlsxIntoJson"][L])
        self.action_ShowHide_Filter.setText(lan["GUI_action_ShowHide_Filter"][L])
        self.action_ShowHide_NamingArea.setText(lan["GUI_action_ShowHide_NamingArea"][L])
        self.action_ShowHide_Console.setText(lan["GUI_action_ShowHide_Console"][L])
        self.action_ShowHide_Waveform.setText(lan["GUI_action_ShowHide_Waveform"][L])
        self.action_ShowHide_Preference.setText(lan["GUI_action_ShowHide_Preference"][L])
        self.action_ShowHide_SearchText.setText(lan["GUI_action_ShowHide_SearchText"][L])

        # ------------------------------------------------------------------- Set Logic ----- Menu ----- Edit
        self.action_Undo.triggered.connect(self.Action_Undo)
        self.action_Redo.triggered.connect(self.Action_Redo)
        self.action_AddLine.triggered.connect(self.Action_AddLine)
        self.action_DeleteLine.triggered.connect(self.Action_DelLine)
        self.action_Copy.triggered.connect(self.Action_CopyCell)
        self.action_Paste.triggered.connect(self.Action_PasteCell)
        self.action_Clear.triggered.connect(self.Action_ClearCell)

        self.menu_Edit.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
        self.menu_Edit.setTitle(lan["GUI_Menu_Edit"][L])
        self.action_Undo.setText(lan["GUI_action_Undo"][L])
        self.action_Redo.setText(lan["GUI_action_Redo"][L])
        self.action_AddLine.setText(lan["GUI_action_AddLine"][L])
        self.action_DeleteLine.setText(lan["GUI_action_DeleteLine"][L])
        self.action_Copy.setText(lan["GUI_action_Copy"][L])
        self.action_Paste.setText(lan["GUI_action_Paste"][L])
        self.action_Clear.setText(lan["GUI_action_Clear"][L])

        # ------------------------------------------------------------------- Set Logic ----- Menu ----- Wwise
        self.action_GlobalSafetyCheck.triggered.connect(self.PreCheck_GlobalSafetyCheck)
        self.action_RelinkMissingWAV.triggered.connect(self.PreCheck_RelinkMissingWAV)
        self.action_InitiateSession.triggered.connect(lambda: self.OpenWindow(self.InitSessionWindow))
        self.action_GenerateProjectSheet.triggered.connect(self.PreCheck_GenerateProjectSheet)
        self.action_OpenWwiseProjectFolder.triggered.connect(self.OpenWwiseProjectFolder)

        self.menu_Wwise.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
        self.menu_Wwise.setTitle(lan["GUI_Menu_Wwise"][L])
        self.action_GlobalSafetyCheck.setText(lan["GUI_action_GlobalSafetyCheck"][L])
        self.action_RelinkMissingWAV.setText(lan["GUI_SM_RC_action_RelinkWAV"][L])
        self.action_InitiateSession.setText(lan["GUI_action_InitiateSession"][L])
        self.action_GenerateProjectSheet.setText(lan["GUI_action_GenerateProjectSheet"][L])
        self.action_OpenWwiseProjectFolder.setText(lan["GUI_SM_RC_action_OpenWwiseProjectFolder"][L])

        self.Thread_GlobalSafetyCheck = None

        # ------------------------------------------------------------------- Set Logic ----- Menu ----- Engine
        self.action_CheckSoundIDStatus.triggered.connect(self.CheckSoundIDStatus)

        self.menu_Engine.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
        self.menu_Engine.setTitle(lan["GUI_Menu_Engine"][L])
        self.action_CheckSoundIDStatus.setText(lan["GUI_action_CheckSoundIDStatus"][L])

        # ------------------------------------------------------------------- Set Logic ----- Menu ----- Help
        self.action_Document.triggered.connect(self.OpenHelpDocument)
        self.menu_Help.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
        self.menu_Help.setTitle(lan["GUI_Menu_Help"][L])
        self.action_Document.setText(lan["GUI_action_Document"][L])
        self.action_VersionInfo.setText(lan["GUI_action_VersionInfo"][L])
        self.action_DevMode.triggered.connect(self.DevMode)
        self.action_DevMode.setText(lan["GUI_action_DevMode"][L])
        self.action_VersionInfo.triggered.connect(self.VersionInfo)
        self.action_Disclaimer.setText(lan["LOG_GUI_Disclaimer"][L])
        self.action_Disclaimer.triggered.connect(self.Disclaimer)

        # ------------------------------------------------------------------- Set Logic ----- Panel ----- GUI
        self.pushButton_Save.clicked.connect(self.Save_WithSafetyCheck)
        self.Frame_Filter.setVisible(False)
        self.pushButton_Find.clicked.connect(self.Find)
        self.pushButton_Find.setStyleSheet("QPushButton{border-image: url(cf/gui/icon_buttons/btn_find.png)}"
                                           "QPushButton:hover{border-image: url(cf/gui/icon_buttons/btn_find_hover.png)}"
                                           "QPushButton:pressed{border-image: url(cf/gui/icon_buttons/btn_find_press.png)}")

        self.pushButton_GO.setToolTip(lan["GUIText_GoBtn"][L])
        self.pushButton_GO.setStyleSheet("QPushButton{border-image: url(cf/gui/icon_buttons/btn_w.png)}"
                                         "QPushButton:hover{border-image: url(cf/gui/icon_buttons/btn_w_hover.png)}"
                                         "QPushButton:pressed{border-image: url(cf/gui/icon_buttons/btn_w_press.png)}")
        self.pushButton_ExpandSwitch.setToolTip(lan["GUI_SM_RC_action_ExpandSwitchObjByAdding"][L])
        self.pushButton_ExpandSwitch.setStyleSheet("QPushButton{border-image: url(cf/gui/icon_buttons/btn_expandswitch.png)}"
                                                   "QPushButton:hover{border-image: url(cf/gui/icon_buttons/btn_expandswitch_hover.png)}"
                                                   "QPushButton:pressed{border-image: url(cf/gui/icon_buttons/btn_expandswitch_press.png)}")
        self.pushButton_MirrorID.setToolTip(lan["GUIText_Mirror"][L])
        self.pushButton_MirrorID.setStyleSheet("QPushButton{border-image: url(cf/gui/icon_buttons/btn_mirror.png)}"
                                               "QPushButton:hover{border-image: url(cf/gui/icon_buttons/btn_mirror_hover.png)}"
                                               "QPushButton:pressed{border-image: url(cf/gui/icon_buttons/btn_mirror_press.png)}")
        self.pushButton_Recreate.setToolTip(lan["GUI_SM_RC_action_ReCreate"][L])
        self.pushButton_Recreate.setStyleSheet("QPushButton{border-image: url(cf/gui/icon_buttons/btn_recreate.png)}"
                                               "QPushButton:hover{border-image: url(cf/gui/icon_buttons/btn_recreate_hover.png)}"
                                               "QPushButton:pressed{border-image: url(cf/gui/icon_buttons/btn_recreate_press.png)}")

        self.pushButton_GO.clicked.connect(lambda: self.PreSafetyCheck_General(lan["SC_START_GO"][L], lan["SC_END_GO"][L], self.GO))
        self.pushButton_ExpandSwitch.clicked.connect(lambda: self.PreSafetyCheck_General(lan["SC_START_ExpandSwitch"][L], lan["SC_END_ExpandSwitch"][L], self.ExpandSwitch))
        self.pushButton_MirrorID.clicked.connect(lambda: self.PreSafetyCheck_General(lan["SC_START_MirrorEvent"][L], lan["SC_END_MirrorEvent"][L], self.MirrorData))
        self.pushButton_Recreate.clicked.connect(lambda: self.PreSafetyCheck_General(lan["SC_START_RecreateEvent"][L], lan["SC_END_RecreateEvent"][L], self.ReCreateCompletely))

        self.progressBar.setStyleSheet("QProgressBar::chunk{background:darkGray}")
        self.progressBar.setVisible(False)
        self.statusbar.setStyleSheet("color:red")

        # ------------------------------------------------------------------- Set Logic ----- Panel ----- Table
        self.tableWidget_SoundSheet.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget_SoundSheet.customContextMenuRequested.connect(self.RightClickMenu_tableWidget_SoundSheet)
        self.tableWidget_SoundSheet.setColumnWidth(key["Header_ID"], 60)
        self.tableWidget_SoundSheet.setColumnWidth(key["Header_Notes"], 350)
        self.tableWidget_SoundSheet.setColumnWidth(key["Header_EventName"], 230)
        self.tableWidget_SoundSheet.setColumnWidth(key["Header_BankName"], 100)
        self.tableWidget_SoundSheet.setColumnWidth(key["Header_KeyStr"], 100)
        self.tableWidget_SoundSheet.setColumnWidth(key["Header_BodyStr"], 100)
        self.tableWidget_SoundSheet.setColumnWidth(key["Header_TailStr"], 100)
        self.tableWidget_SoundSheet.setColumnWidth(key["Header_RDM"], 40)
        self.tableWidget_SoundSheet.setColumnWidth(key["Header_Lock"], 50)
        self.tableWidget_SoundSheet.setColumnWidth(key["Header_MirrorFrom"], 100)
        self.tableWidget_SoundSheet.cellChanged.connect(self.Action_AfterCellChanged)
        self.tableWidget_SoundSheet.itemSelectionChanged.connect(self.Action_AfterItemSelectionChanged)
        self.tableWidget_SoundSheet_Order = Qt.DescendingOrder

        # ------------------------------------------------------------------- Set Logic ----- Panel ----- lineEdit_SearchText
        self.Frame_SearchText.setVisible(True)
        self.pushButton_up.setVisible(False)
        self.pushButton_down.setVisible(False)
        self.lineEdit_SearchText.textChanged.connect(self.LineEditTextChanged_SearchText)
        self.pushButton_up.clicked.connect(self.find_previous)
        self.pushButton_down.clicked.connect(self.find_next)

        # ------------------------------------------------------------------- Set Logic ----- Panel ----- Log Console
        self.textEdit_Log.setContextMenuPolicy(Qt.CustomContextMenu)
        self.textEdit_Log.customContextMenuRequested.connect(self.RightClickMenu_textEdit_Log)
        # self.textEdit_Log.setVisible(False)

        # 实时显示输出, 将控制台的输出重定向到界面中
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        sys.stdout = EmittingStr(textWritten=self.outputWritten)
        sys.stderr = EmittingStr(textWritten=self.outputWritten)

        # ------------------------------------------------------------------- Set Logic ----- Panel ----- Wavform
        self.Frame_AdvInfo.setVisible(False)
        self.label_EventObjectRefCountTag.setText(lan["GUI_label_EventObjectRefCountTag"][L])
        self.label_RelatedWAVCountTag.setText(lan["GUI_label_RelatedWAVCountTag"][L])
        self.comboBox_EventObjectRef.currentIndexChanged.connect(self.FillWAVComboBox_by_ObjectRefComboBoxItem)

        self.WavformLayout = QVBoxLayout()
        self.WAVPlayer = QMediaPlayer()
        self.MatplotlibGraphicLength = 10
        self.MatplotlibGraphicHeight = 0.3
        self.graphicsView_Waveform = CustomGraphicsView(self.WAVPlayer.duration())
        self.graphicsView_Waveform.DIYdoubleClicked.connect(self.on_left_clicked)
        self.graphicsView_Waveform.whichButtonClicked.connect(self.WhichMouseClick)
        self.Frame_Wavform.setLayout(self.WavformLayout)
        self.comboBox_RelatedWAV.currentIndexChanged.connect(self.Display_Waveform)

        self.pushButton_LocateWAV.setText(lan["GUI_BTN_LocateSingleWAV"][L])
        self.pushButton_LocateWAV.clicked.connect(self.LocateSingleWAV)

        # ------------------------------------------------------------------- Set Logic ----- Panel ----- Preference
        self.groupBox_Preference.setVisible(False)
        self.Init_ComboBox_Status()
        self.comboBox_Language.currentIndexChanged.connect(self.RefreshJson_comboBox_Language)
        self.comboBox_ShowWelcomePageWhenStart.currentIndexChanged.connect(
            self.RefreshJson_comboBox_ShowWelcomePageWhenStart)
        self.Init_spinBox_AutoSaveAs_Status()
        self.spinBox_AutoSaveAs.valueChanged.connect(self.RefreshJson_spinBox_AutoSaveAs)
        self.comboBox_AutoSaveAs.currentIndexChanged.connect(self.RefreshJson_comboBox_AutoSaveAs)
        self.comboBox_AutoLoadSoundSheetWhenStart.currentIndexChanged.connect(
            self.RefreshJson_comboBox_AutoLoadSoundSheetWhenStart)
        self.comboBox_CopyPasteMode.currentIndexChanged.connect(self.RefreshJson_comboBox_CopyPasteMode)
        self.comboBox_AutoColorForEventsNotInTable.currentIndexChanged.connect(
            self.RefreshJson_comboBox_AutoColorForEventsNotInTable)
        self.comboBox_AutoGenerateBanks.currentIndexChanged.connect(self.RefreshJson_comboBox_AutoGenerateBanks)
        self.comboBox_LogDisplayLevel.currentIndexChanged.connect(self.RefreshJson_comboBox_LogDisplayLevel)

        self.pushButton_QuickTest.clicked.connect(self.QuickTest)
        if key["DevMode"] == "dev":
            self.pushButton_QuickTest.setVisible(True)
        else:
            self.pushButton_QuickTest.setVisible(False)

        if key["ifAutoSaveAs"] == "True":
            if key["AutoSaveAsEvery"] != 0:
                self.thread_SaveAs = Thread_ForSaveAs()
                self.thread_SaveAs.SaveAsSignal.connect(self.SaveAs_Json)
                self.thread_SaveAs.start()

        self.groupBox_Preference.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
        self.groupBox_Preference.setTitle(lan["GUI_label_Preference"][L])
        self.label_Language.setText(lan["GUI_label_Language"][L])
        self.label_LanguageHint.setText(lan["GUI_label_RestartTool_Hint_forLanguage"][L])
        self.label_LanguageHint.setStyleSheet("color:red")
        self.label_LanguageHint.setVisible(False)
        self.label_ShowWelcomePageWhenStart.setText(lan["GUI_label_ShowWelcomePageWhenStart"][L])
        self.label_AutoLoadSoundSheetWhenStart.setText(lan["GUI_label_AutoLoadSoundSheetWhenStart"][L])
        self.label_CopyPasteMode.setText(lan["GUI_label_CopyPasteMode"][L])
        self.label_AutoSaveAs_Head.setText(lan["GUI_label_AutoSaveAs_Head"][L])
        self.label_AutoSaveAs_Tail.setText(lan["GUI_label_AutoSaveAs_Tail"][L])
        self.label_AutoSaveAs.setText(lan["GUI_label_RestartTool_Hint"][L])
        self.label_AutoSaveAs.setStyleSheet("color:red")
        self.label_AutoSaveAs.setVisible(False)
        self.label_AutoColorForEventsNotInTable.setText(lan["GUI_label_AutoColorForEventsNotInTable"][L])
        self.label_AutoGenerateBanks.setText(lan["GUI_Label_AutoGenerateBanks"][L])
        self.label_LogDisplayLevel.setText(lan["GUI_Label_LogDisplayLevel"][L])
        self.label_SaveAsDefaultFolderPath.setText(lan["GUI_Label_SaveAsDefaultFolderPath"][L])
        self.lineEdit_SaveAsDefaultFolderPath.setText(LocalInfoDict["Path_DefaultSaveAsFolder"])
        self.lineEdit_SaveAsDefaultFolderPath.textChanged.connect(self.LineEditTextChanged_SaveAsDefaultFolderPath)
        self.pushButton_SaveAsDefaultFolderPath.setText(lan["GUI_pushButton_Modify"][L])
        self.pushButton_SaveAsDefaultFolderPath.clicked.connect(self.LocatePath_ForSaveAs)

        # ------------------------------------------------------------------- Set Shortcut
        self.action_Load.setShortcut(QKeySequence(key["ShortCut_action_Load"]))
        self.action_EditKeyInfo.setShortcut(QKeySequence(key["ShortCut_action_EditKeyInfo"]))
        self.action_Save.setShortcut(QKeySequence(key["ShortCut_action_Save"]))
        self.action_ShowHide_Filter.setShortcut(QKeySequence(key["ShortCut_action_ShowHide_Filter"]))
        self.action_ShowHide_NamingArea.setShortcut(QKeySequence(key["ShortCut_action_ShowHide_NamingArea"]))
        self.action_ShowHide_Console.setShortcut(QKeySequence(key["ShortCut_action_ShowHide_Console"]))
        self.action_ShowHide_Waveform.setShortcut(QKeySequence(key["ShortCut_action_ShowHide_Waveform"]))
        self.action_ShowHide_Preference.setShortcut(QKeySequence(key["ShortCut_action_ShowHide_Preference"]))
        self.action_ShowHide_SearchText.setShortcut(QKeySequence(key["ShortCut_action_ShowHide_SearchText"]))
        self.pushButton_up.setShortcut(QKeySequence(key["ShortCut_action_SearchText_Up"]))
        self.pushButton_down.setShortcut(QKeySequence(key["ShortCut_action_SearchText_Down"]))
        self.action_Undo.setShortcut(QKeySequence(key["ShortCut_action_Undo"]))
        self.action_Redo.setShortcut(QKeySequence(key["ShortCut_action_Redo"]))
        self.action_AddLine.setShortcut(QKeySequence(key["ShortCut_action_AddLine"]))
        self.action_DeleteLine.setShortcut(QKeySequence(key["ShortCut_action_DeleteLine"]))
        self.action_Copy.setShortcut(QKeySequence(key["ShortCut_action_Copy"]))
        self.action_Paste.setShortcut(QKeySequence(key["ShortCut_action_Paste"]))
        self.action_Clear.setShortcut(QKeySequence(key["ShortCut_action_Clear"]))
        self.action_Document.setShortcut(QKeySequence(key["ShortCut_action_Document"]))

        # ------------------------------------------------------------------- Set Final Touches
        self.WwiseStatusCheck()
        self.ui.show()
        self.Init_IfAutoLoadJson()
        self.Init_Filter()
        QuickTest_HideFile("rec.log")

    # ----------------------------------------------------------------------------- Global Init
    def WwiseStatusCheck(self):
        self.Progress_monitorWwiseEXE = monitorWwiseEXE()
        self.Progress_monitorWwiseEXE.CurrentStatus.connect(self.IfCloseSelfWindow)
        self.Progress_monitorWwiseEXE.start()

    def IfCloseSelfWindow(self, msgInt):
        if msgInt == 1:
            pass
        elif msgInt == 0:
            self.SaveAndClose()
        else:
            self.Progress_monitorWwiseEXE.terminate()
            self.SaveAndClose()
            MSGWindow = Window_MessageBox()
            MSGWindow.MessageBox_NoticeOnly(lan["GUI_WwiseProcessNotice_DetectMultiple_Title"][L], lan["GUI_WwiseProcessNotice_DetectMultiple_Text"][L])

    def SaveAndClose(self):
        self.KeyInfoWindow.ui.close()
        self.InitSessionWindow.ui.close()
        self.Save(global_curWwiseInfoJson)
        self.ui.close()

    def Init_ComboBox_Status(self):
        # comboBox_Language
        if key["Language"] == "Chinese":
            self.comboBox_Language.setCurrentIndex(0)
        elif key["Language"] == "English":
            self.comboBox_Language.setCurrentIndex(1)
        else:
            self.comboBox_Language.setCurrentIndex(0)

        # self.comboBox_ShowWelcomePageWhenStart
        self.comboBox_ShowWelcomePageWhenStart.setItemText(0, lan["GUI_comboBox_Never"][L])
        self.comboBox_ShowWelcomePageWhenStart.setItemText(1, lan["GUI_comboBox_Yes"][L])

        if key["ifNotShowWelcome"] == "True":
            self.comboBox_ShowWelcomePageWhenStart.setCurrentIndex(0)
        else:
            self.comboBox_ShowWelcomePageWhenStart.setCurrentIndex(1)

        # comboBox_AutoSave
        self.comboBox_AutoSaveAs.setItemText(0, lan["GUI_comboBox_Yes"][L])
        self.comboBox_AutoSaveAs.setItemText(1, lan["GUI_comboBox_Never"][L])

        if key["ifAutoSaveAs"] == "True":
            self.comboBox_AutoSaveAs.setCurrentIndex(0)
        else:
            self.comboBox_AutoSaveAs.setCurrentIndex(1)

        # comboBox_AutoLoadSoundSheetWhenStartWhenStart
        self.comboBox_AutoLoadSoundSheetWhenStart.setItemText(0, lan["GUI_comboBox_Yes"][L])
        self.comboBox_AutoLoadSoundSheetWhenStart.setItemText(1, lan["GUI_comboBox_Never"][L])

        if key["ifAutoLoadSoundListJson"] == "True":
            self.comboBox_AutoLoadSoundSheetWhenStart.setCurrentIndex(0)
        else:
            self.comboBox_AutoLoadSoundSheetWhenStart.setCurrentIndex(1)

        # comboBox_CopyPasteClearMode
        self.comboBox_CopyPasteMode.setItemText(0, lan["GUI_comboBox_TextOnly"][L])
        self.comboBox_CopyPasteMode.setItemText(1, lan["GUI_comboBox_TextAndBGColor"][L])
        self.comboBox_CopyPasteMode.setItemText(2, lan["GUI_comboBox_BGColor"][L])

        if key["CopyPasteMode"] == "TextOnly":
            self.comboBox_CopyPasteMode.setCurrentIndex(0)
        elif key["CopyPasteMode"] == "TextAndBGColor":
            self.comboBox_CopyPasteMode.setCurrentIndex(1)
        elif key["CopyPasteMode"] == "BGColorOnly":
            self.comboBox_CopyPasteMode.setCurrentIndex(2)
        else:
            self.comboBox_CopyPasteMode.setCurrentIndex(0)

        # comboBox_AutoColorForEventsNotInTable
        self.comboBox_AutoColorForEventsNotInTable.setItemText(0, lan["GUI_comboBox_Yes"][L])
        self.comboBox_AutoColorForEventsNotInTable.setItemText(1, lan["GUI_comboBox_Never"][L])

        if key["ifColorAfterGlobalSafetyCheck"] == "True":
            self.comboBox_AutoColorForEventsNotInTable.setCurrentIndex(0)
        else:
            self.comboBox_AutoColorForEventsNotInTable.setCurrentIndex(1)

        # comboBox_AutoGenerateBanks
        self.comboBox_AutoGenerateBanks.setItemText(0, lan["GUI_comboBox_Yes"][L])
        self.comboBox_AutoGenerateBanks.setItemText(1, lan["GUI_comboBox_Never"][L])

        if key["AutoGenerateBanks"] == "True":
            self.comboBox_AutoGenerateBanks.setCurrentIndex(0)
        else:
            self.comboBox_AutoGenerateBanks.setCurrentIndex(1)

        # comboBox_LogDisplayLevel
        if key["DevMode"] == "dev":
            self.Init_ComboBox_Log_DevMode()
        else:
            self.Init_ComboBox_Log_UserMode()

    def Init_ComboBox_Log_UserMode(self):
        self.comboBox_LogDisplayLevel.insertItem(0, lan["GUI_comboBox_LogDisplayLevel_CRITICAL"][L])
        self.comboBox_LogDisplayLevel.insertItem(1, lan["GUI_comboBox_LogDisplayLevel_ERROR"][L])
        self.comboBox_LogDisplayLevel.insertItem(2, lan["GUI_comboBox_LogDisplayLevel_WARNING"][L])
        self.comboBox_LogDisplayLevel.insertItem(3, lan["GUI_comboBox_LogDisplayLevel_INFO"][L])

        if key["LogDisplayLevel"] == "CRITICAL":
            self.comboBox_LogDisplayLevel.setCurrentIndex(0)
            Log.setLevel(logging.CRITICAL)
        elif key["LogDisplayLevel"] == "ERROR":
            self.comboBox_LogDisplayLevel.setCurrentIndex(1)
            Log.setLevel(logging.ERROR)
        elif key["LogDisplayLevel"] == "WARNING":
            self.comboBox_LogDisplayLevel.setCurrentIndex(2)
            Log.setLevel(logging.WARNING)
        elif key["LogDisplayLevel"] == "INFO":
            self.comboBox_LogDisplayLevel.setCurrentIndex(3)
            Log.setLevel(logging.INFO)
        else:
            self.comboBox_LogDisplayLevel.setCurrentIndex(3)
            Log.setLevel(logging.INFO)

    def Init_ComboBox_Log_DevMode(self):
        self.comboBox_LogDisplayLevel.insertItem(0, lan["GUI_comboBox_LogDisplayLevel_CRITICAL"][L])
        self.comboBox_LogDisplayLevel.insertItem(1, lan["GUI_comboBox_LogDisplayLevel_ERROR"][L])
        self.comboBox_LogDisplayLevel.insertItem(2, lan["GUI_comboBox_LogDisplayLevel_WARNING"][L])
        self.comboBox_LogDisplayLevel.insertItem(3, lan["GUI_comboBox_LogDisplayLevel_INFO"][L])
        self.comboBox_LogDisplayLevel.insertItem(4, lan["GUI_comboBox_LogDisplayLevel_DEBUG"][L])

        if key["LogDisplayLevel"] == "CRITICAL":
            self.comboBox_LogDisplayLevel.setCurrentIndex(0)
            Log.setLevel(logging.CRITICAL)
        elif key["LogDisplayLevel"] == "ERROR":
            self.comboBox_LogDisplayLevel.setCurrentIndex(1)
            Log.setLevel(logging.ERROR)
        elif key["LogDisplayLevel"] == "WARNING":
            self.comboBox_LogDisplayLevel.setCurrentIndex(2)
            Log.setLevel(logging.WARNING)
        elif key["LogDisplayLevel"] == "INFO":
            self.comboBox_LogDisplayLevel.setCurrentIndex(3)
            Log.setLevel(logging.INFO)
        elif key["LogDisplayLevel"] == "DEBUG":
            self.comboBox_LogDisplayLevel.setCurrentIndex(4)
            Log.setLevel(logging.DEBUG)
        else:
            self.comboBox_LogDisplayLevel.setCurrentIndex(3)
            Log.setLevel(logging.INFO)

    def Init_IfAutoLoadJson(self):
        if key["ifAutoLoadSoundListJson"] == "True":
            self.Load_SoundListJson(global_curWwiseInfoJson)

    def Init_IfAutoScanProject(self):
        LOG.debug("\n>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> [自动生成音频表] ?????????????????????????????????")
        if global_curWwiseInfoJson is not None and os.path.exists(global_curWwiseInfoJson):
            if CheckIfJsonIsValidSoundSheet(global_curWwiseInfoJson) is True:
                Dict_Data = SoundListDict["Data_SoundList"]
                TotalNum = len(Dict_Data)
                if TotalNum == 0:
                    messageBox = QMessageBox(QMessageBox.Information, lan["GUI_action_Load_Msg_AutoScan_Title"][L], lan["GUI_action_Load_Msg_AutoScan_Text"][L])
                    messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
                    Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
                    Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
                    messageBox.exec_()
                    if messageBox.clickedButton() == Qyes:
                        self.GenerateProjectSheet()
                        currentTimeStr = getCurrentTimeStr()
                        tarJsonPath = os.path.join(global_curWwisePath, "info_" + currentTimeStr + ".json")
                        LOG.debug(">>>>> 新json的路径：" + tarJsonPath)
                        LOG.debug(">>>>> 时间戳：" + currentTimeStr)
                        # 以下需要等待线程结束后再推进
                        while not os.path.exists(tarJsonPath):
                            LOG.debug(">>> not yet...")
                            if os.path.exists(tarJsonPath):
                                LOG.debug(">>> Got it!")
                                NewSLDict = LoadJson(tarJsonPath, "gbk")
                                LOG.debug(">>>>> 生成新表Dict")
                                if NewSLDict.get("Data_SoundList", "@#$") != "@#$":
                                    SoundListDict["Data_SoundList"] = NewSLDict["Data_SoundList"]
                                    LOG.debug(">>>>> 覆盖Dict：")
                                    LOG.debug(NewSLDict["Data_SoundList"])
                                    SaveJson(SoundListDict, global_curWwiseInfoJson)
                                    self.Load_SoundListJson(global_curWwiseInfoJson)

    def Init_spinBox_AutoSaveAs_Status(self):
        if key["ifAutoSaveAs"] == "True":
            self.spinBox_AutoSaveAs.setReadOnly(False)
            if key["AutoSaveAsEvery"] == "":
                self.spinBox_AutoSaveAs.setValue(5)
            else:
                self.spinBox_AutoSaveAs.setValue(int(key["AutoSaveAsEvery"]))
        else:
            self.spinBox_AutoSaveAs.cleanText()
            self.spinBox_AutoSaveAs.setReadOnly(True)

    def Init_Filter(self):
        self.CurrentKeyStrInTable = self.GetAllKeyStrFromTable()
        self.comboBox_Filter = ComboCheckBox(self.GetAllKeyStrFromTable())
        for i in range(len(self.CurrentKeyStrInTable) + 1):
            self.comboBox_Filter.box_list[i].stateChanged.connect(self.RefreshCheckedBoxList)
        self.horizontalLayout_Filter.addWidget(self.comboBox_Filter)

    # ----------------------------------------------------------------------------- Window Menu Func ----- File
    def Load_SoundListJson(self, Path_SoundList):
        # 加载前，先清空遗留数据的显示
        print()
        self.textEdit_Log.clear()
        self.tableWidget_SoundSheet.setRowCount(0)
        self.tableWidget_SoundSheet.clearContents()

        # 清理Undo或Redo历史防止误修改
        UndoList.clear()
        RedoList.clear()
        self.UndoRedoNumShow()

        if Path_SoundList is not None and os.path.exists(Path_SoundList):
            if CheckIfJsonIsValidSoundSheet(Path_SoundList) is True:
                columnCount = self.tableWidget_SoundSheet.columnCount()
                # 给当前窗口的Table写入数据
                Dict_Data = SoundListDict["Data_SoundList"]
                TotalNum = len(Dict_Data)
                self.tableWidget_SoundSheet.setRowCount(TotalNum)
                for row, keyy in zip(range(TotalNum), Dict_Data.keys()):
                    for col in range(columnCount):
                        if col == key["Header_ID"]:
                            item = QTableWidgetItem(keyy)
                            item.setForeground(QColor(Dict_Data[keyy]["ID_textColor"]))
                            item.setBackground(QColor(Dict_Data[keyy]["ID_bgColor"]))
                        elif col == key["Header_Notes"]:
                            item = QTableWidgetItem(Dict_Data[keyy]["Notes"]["text"])
                            item.setForeground(QColor(Dict_Data[keyy]["Notes"]["textColor"]))
                            item.setBackground(QColor(Dict_Data[keyy]["Notes"]["bgColor"]))
                        elif col == key["Header_EventName"]:
                            item = QTableWidgetItem(Dict_Data[keyy]["EventName"]["text"])
                            item.setForeground(QColor(Dict_Data[keyy]["EventName"]["textColor"]))
                            item.setBackground(QColor(Dict_Data[keyy]["EventName"]["bgColor"]))
                        elif col == key["Header_BankName"]:
                            item = QTableWidgetItem(Dict_Data[keyy]["BankName"]["text"])
                            item.setForeground(QColor(Dict_Data[keyy]["BankName"]["textColor"]))
                            item.setBackground(QColor(Dict_Data[keyy]["BankName"]["bgColor"]))
                        elif col == key["Header_KeyStr"]:
                            item = QTableWidgetItem(Dict_Data[keyy]["KeyStr"]["text"])
                            item.setForeground(QColor(Dict_Data[keyy]["KeyStr"]["textColor"]))
                            item.setBackground(QColor(Dict_Data[keyy]["KeyStr"]["bgColor"]))
                        elif col == key["Header_BodyStr"]:
                            item = QTableWidgetItem(Dict_Data[keyy]["BodyStr"]["text"])
                            item.setForeground(QColor(Dict_Data[keyy]["BodyStr"]["textColor"]))
                            item.setBackground(QColor(Dict_Data[keyy]["BodyStr"]["bgColor"]))
                        elif col == key["Header_TailStr"]:
                            item = QTableWidgetItem(Dict_Data[keyy]["TailStr"]["text"])
                            item.setForeground(QColor(Dict_Data[keyy]["TailStr"]["textColor"]))
                            item.setBackground(QColor(Dict_Data[keyy]["TailStr"]["bgColor"]))
                        elif col == key["Header_RDM"]:
                            item = QTableWidgetItem(Dict_Data[keyy]["RDM"]["text"])
                            item.setForeground(QColor(Dict_Data[keyy]["RDM"]["textColor"]))
                            item.setBackground(QColor(Dict_Data[keyy]["RDM"]["bgColor"]))
                            item.setTextAlignment(Qt.AlignCenter | Qt.AlignCenter)
                        elif col == key["Header_Lock"]:
                            item = QTableWidgetItem(Dict_Data[keyy]["Lock"]["text"])
                            item.setForeground(QColor(Dict_Data[keyy]["Lock"]["textColor"]))
                            item.setBackground(QColor(Dict_Data[keyy]["Lock"]["bgColor"]))
                            item.setTextAlignment(Qt.AlignCenter | Qt.AlignCenter)
                        elif col == key["Header_MirrorFrom"]:
                            item = QTableWidgetItem(Dict_Data[keyy]["MirrorFrom"]["text"])
                            item.setForeground(QColor(Dict_Data[keyy]["MirrorFrom"]["textColor"]))
                            item.setBackground(QColor(Dict_Data[keyy]["MirrorFrom"]["bgColor"]))
                        else:
                            item = QTableWidgetItem("")
                            item.setForeground(QColor("#000000"))
                            item.setBackground(QColor("#ffffff"))

                        self.tableWidget_SoundSheet.setItem(row, col, item)
                        # 设置进度条
                        CurrentStep = row + 1
                        self.ShowProgress([CurrentStep, TotalNum])

                # 高亮最下面一行
                self.tableWidget_SoundSheet.scrollToBottom()

                # 给KeyInfo窗口写入数据（先清空，再写入）
                self.KeyInfoWindow.listWidget_KeyStrList.clear()
                self.KeyInfoWindow.ClearPanel()
                self.KeyInfoWindow.Init_PanelDisplay()

                # 刷新保存按钮状态
                self.NeedSafeFlag = 0
                self.SetState_Save()

                # Load完成，标签状态变更
                globals.LoadFlag = True
                LOG.info(lan["LOG_LOG_SoundListLoaded"][L])
            else:
                LOG.info(lan["GUI_LOG_InvalidSoundListJson"][L] + str(Path_SoundList))
        else:
            LOG.warning(lan["LOG_PathIsNotExist"][L] + str(Path_SoundList))

    def AddEmptyLineAtInit(self):
        line = self.tableWidget_SoundSheet.rowCount()
        self.tableWidget_SoundSheet.setRowCount(line + 1)
        return line

    def Save_WithSafetyCheck(self):  # 保存前需要安全检查，判断即将保存的文件是否属于当前wwise工程（用户可能在保持工具开启的状态下，关闭当前Wwise工程，又开启了另一个工程）
        try:  # 关闭Wwise的瞬间立即点击保存，可能使运行卡死（原因待研究）
            WwiseStatus = SimpleWaapi()
            currentProjectID = WwiseStatus.get_WwiseCurrentProjectID()
            if currentProjectID is not None:
                # 获取当前json中的Wwise工程ID
                TempSoundListDict = LoadJson(global_curWwiseInfoJson, "gbk")
                WwiseProjectID_inJSON = TempSoundListDict.get("$ProjectGUID$", "")

                # 比较id
                if WwiseProjectID_inJSON != currentProjectID:
                    messageBox = QMessageBox(QMessageBox.Warning, lan["GUI_LOG_SafetyCheck_ForSave"][L], lan["GUI_LOG_CurrentWwiseNotMatchCurrentTableData"][L] + "\n\n--> " + str(WwiseProjectID_inJSON) + "\n--> " + str(currentProjectID))
                    messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
                    Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
                    Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
                    messageBox.exec_()
                    if messageBox.clickedButton() == Qyes:
                        self.Save(global_curWwiseInfoJson)
                        self.ui.close()
                else:
                    self.Save(global_curWwiseInfoJson)
            else:
                LOG.warning(lan["LOG_SM_def_SafetyCheck_FAIL"][L])
        except:
            traceback.print_exc()

    def Save(self, jsonFilePath):
        if globals.LoadFlag is True:  # 这里先判断表格是否处于已加载状态，防止将json误刷成空数据！
            # 先恢复显示所有隐藏的信息
            self.showAllRow()

            # 先检查ID是否有重复、缺失
            CheckResult = self.SafetyCheck_SoundID_Global()
            if len(CheckResult) != 0:  # 到这里，说明检测到非法ID
                MissingIDLineList = CheckResult.get("MissingIDLineList", [])
                InvalidIDStrList = CheckResult.get("InvalidIDStrList", [])
                DuplicatedIDList = CheckResult.get("DuplicatedIDList", [])

                if len(MissingIDLineList) != 0:
                    LOG.warning(lan["GUI_LOG_MissingIDLine"][L] + str(MissingIDLineList))
                if len(InvalidIDStrList) != 0:
                    LOG.warning(lan["GUI_LOG_InvalidIDLine"][L] + str(InvalidIDStrList))
                if len(DuplicatedIDList) != 0:
                    LOG.warning(lan["GUI_LOG_InvalidIDLine"][L] + str(DuplicatedIDList))

            # 如果ID安全检查能通过，则开始全量扫描Table数据
            else:
                self.progressBar.setVisible(True)
                TotalRowNum = self.tableWidget_SoundSheet.rowCount()
                Data_SoundList_ReScan = {}
                ProgressBar_Count = 0
                for i in range(TotalRowNum):
                    Temp_ID = ""
                    TempDict = {
                        "ID_textColor": "",
                        "ID_bgColor": "",
                        "Notes": {
                            "text": "",
                            "textColor": "",
                            "bgColor": ""
                        },
                        "EventName": {
                            "text": "",
                            "textColor": "",
                            "bgColor": ""
                        },
                        "BankName": {
                            "text": "",
                            "textColor": "",
                            "bgColor": ""
                        },
                        "KeyStr": {
                            "text": "",
                            "textColor": "",
                            "bgColor": ""
                        },
                        "BodyStr": {
                            "text": "",
                            "textColor": "",
                            "bgColor": ""
                        },
                        "TailStr": {
                            "text": "",
                            "textColor": "",
                            "bgColor": ""
                        },
                        "RDM": {
                            "text": "",
                            "textColor": "",
                            "bgColor": ""
                        },
                        "Lock": {
                            "text": "",
                            "textColor": "",
                            "bgColor": ""
                        },
                        "MirrorFrom": {
                            "text": "",
                            "textColor": "",
                            "bgColor": ""
                        }
                    }
                    for g in range(self.tableWidget_SoundSheet.columnCount()):
                        if self.tableWidget_SoundSheet.item(i, g) is not None:
                            text = self.tableWidget_SoundSheet.item(i, g).text()
                            textColor = self.tableWidget_SoundSheet.item(i, g).foreground().color().name()
                            bgColor = self.tableWidget_SoundSheet.item(i, g).background().color().name()
                            if g == 0:
                                Temp_ID = text
                                Data_SoundList_ReScan[text] = TempDict
                                Data_SoundList_ReScan[Temp_ID]["ID_textColor"] = textColor
                                Data_SoundList_ReScan[Temp_ID]["ID_bgColor"] = bgColor
                            elif g == 1:
                                Data_SoundList_ReScan[Temp_ID]["Notes"]["text"] = text
                                Data_SoundList_ReScan[Temp_ID]["Notes"]["textColor"] = textColor
                                Data_SoundList_ReScan[Temp_ID]["Notes"]["bgColor"] = bgColor
                            elif g == 2:
                                Data_SoundList_ReScan[Temp_ID]["EventName"]["text"] = text
                                Data_SoundList_ReScan[Temp_ID]["EventName"]["textColor"] = textColor
                                Data_SoundList_ReScan[Temp_ID]["EventName"]["bgColor"] = bgColor
                            elif g == 3:
                                Data_SoundList_ReScan[Temp_ID]["BankName"]["text"] = text
                                Data_SoundList_ReScan[Temp_ID]["BankName"]["textColor"] = textColor
                                Data_SoundList_ReScan[Temp_ID]["BankName"]["bgColor"] = bgColor
                            elif g == 4:
                                Data_SoundList_ReScan[Temp_ID]["KeyStr"]["text"] = text
                                Data_SoundList_ReScan[Temp_ID]["KeyStr"]["textColor"] = textColor
                                Data_SoundList_ReScan[Temp_ID]["KeyStr"]["bgColor"] = bgColor
                            elif g == 5:
                                Data_SoundList_ReScan[Temp_ID]["BodyStr"]["text"] = text
                                Data_SoundList_ReScan[Temp_ID]["BodyStr"]["textColor"] = textColor
                                Data_SoundList_ReScan[Temp_ID]["BodyStr"]["bgColor"] = bgColor
                            elif g == 6:
                                Data_SoundList_ReScan[Temp_ID]["TailStr"]["text"] = text
                                Data_SoundList_ReScan[Temp_ID]["TailStr"]["textColor"] = textColor
                                Data_SoundList_ReScan[Temp_ID]["TailStr"]["bgColor"] = bgColor
                            elif g == 7:
                                Data_SoundList_ReScan[Temp_ID]["RDM"]["text"] = text
                                Data_SoundList_ReScan[Temp_ID]["RDM"]["textColor"] = textColor
                                Data_SoundList_ReScan[Temp_ID]["RDM"]["bgColor"] = bgColor
                            elif g == 8:
                                Data_SoundList_ReScan[Temp_ID]["Lock"]["text"] = text
                                Data_SoundList_ReScan[Temp_ID]["Lock"]["textColor"] = textColor
                                Data_SoundList_ReScan[Temp_ID]["Lock"]["bgColor"] = bgColor
                            elif g == 9:
                                Data_SoundList_ReScan[Temp_ID]["MirrorFrom"]["text"] = text
                                Data_SoundList_ReScan[Temp_ID]["MirrorFrom"]["textColor"] = textColor
                                Data_SoundList_ReScan[Temp_ID]["MirrorFrom"]["bgColor"] = bgColor

                    # 同步进度条信息
                    ProgressBar_Count += 1
                    self.progressBar.setValue(int(ProgressBar_Count / TotalRowNum * 100))

                # 保存JSON
                SoundListDict["Data_SoundList"] = Data_SoundList_ReScan
                SaveJson(SoundListDict, jsonFilePath)

                # 隐藏进度条
                self.progressBar.setValue(0)
                self.progressBar.setVisible(False)

                # 刷新保存按钮状态
                self.NeedSafeFlag = 0
                self.SetState_Save()
                self.statusbar.showMessage("")
        else:
            self.statusbar.showMessage(lan["LOG_LoadAlert"][L])

    def Save_JsonForEngine(self, jsonFilePath):
        if globals.LoadFlag is True:  # 这里先判断表格是否处于已加载状态，防止将json误刷成空数据！
            # 先恢复显示所有隐藏的信息
            self.showAllRow()

            # 先检查ID是否有重复、缺失
            CheckResult = self.SafetyCheck_SoundID_Global()
            if len(CheckResult) != 0:  # 到这里，说明检测到非法ID
                MissingIDLineList = CheckResult.get("MissingIDLineList", [])
                InvalidIDStrList = CheckResult.get("InvalidIDStrList", [])
                DuplicatedIDList = CheckResult.get("DuplicatedIDList", [])

                if len(MissingIDLineList) != 0:
                    LOG.warning(lan["GUI_LOG_MissingIDLine"][L] + str(MissingIDLineList))
                if len(InvalidIDStrList) != 0:
                    LOG.warning(lan["GUI_LOG_InvalidIDLine"][L] + str(InvalidIDStrList))
                if len(DuplicatedIDList) != 0:
                    LOG.warning(lan["GUI_LOG_InvalidIDLine"][L] + str(DuplicatedIDList))

            # 如果ID安全检查能通过，则开始全量扫描Table数据
            else:
                self.progressBar.setVisible(True)
                TotalRowNum = self.tableWidget_SoundSheet.rowCount()
                Data_SoundList_ReScan = {}
                ProgressBar_Count = 0
                for i in range(TotalRowNum):
                    Temp_ID = ""
                    TempDict = {
                        # "ID_textColor": "",
                        # "ID_bgColor": "",
                        "Notes": {
                            "text": ""
                            # "textColor": "",
                            # "bgColor": ""
                        },
                        "EventName": {
                            "text": ""
                            # "textColor": "",
                            # "bgColor": ""
                        },
                        "BankName": {
                            "text": ""
                            # "textColor": "",
                            # "bgColor": ""
                        }
                        # "KeyStr": {
                        #     "text": "",
                        #     "textColor": "",
                        #     "bgColor": ""
                        # },
                        # "BodyStr": {
                        #     "text": "",
                        #     "textColor": "",
                        #     "bgColor": ""
                        # },
                        # "TailStr": {
                        #     "text": "",
                        #     "textColor": "",
                        #     "bgColor": ""
                        # },
                        # "RDM": {
                        #     "text": "",
                        #     "textColor": "",
                        #     "bgColor": ""
                        # },
                        # "Lock": {
                        #     "text": "",
                        #     "textColor": "",
                        #     "bgColor": ""
                        # },
                        # "MirrorFrom": {
                        #     "text": "",
                        #     "textColor": "",
                        #     "bgColor": ""
                        # }
                    }
                    for g in range(self.tableWidget_SoundSheet.columnCount()):
                        if self.tableWidget_SoundSheet.item(i, g) is not None:
                            text = self.tableWidget_SoundSheet.item(i, g).text()
                            # textColor = self.tableWidget_SoundSheet.item(i, g).foreground().color().name()
                            # bgColor = self.tableWidget_SoundSheet.item(i, g).background().color().name()
                            if g == 0:
                                Temp_ID = text
                                Data_SoundList_ReScan[text] = TempDict
                                # Data_SoundList_ReScan[Temp_ID]["ID_textColor"] = textColor
                                # Data_SoundList_ReScan[Temp_ID]["ID_bgColor"] = bgColor
                            elif g == 1:
                                Data_SoundList_ReScan[Temp_ID]["Notes"]["text"] = text
                                # Data_SoundList_ReScan[Temp_ID]["Notes"]["textColor"] = textColor
                                # Data_SoundList_ReScan[Temp_ID]["Notes"]["bgColor"] = bgColor
                            elif g == 2:
                                Data_SoundList_ReScan[Temp_ID]["EventName"]["text"] = text
                                # Data_SoundList_ReScan[Temp_ID]["EventName"]["textColor"] = textColor
                                # Data_SoundList_ReScan[Temp_ID]["EventName"]["bgColor"] = bgColor
                            elif g == 3:
                                Data_SoundList_ReScan[Temp_ID]["BankName"]["text"] = text
                                # Data_SoundList_ReScan[Temp_ID]["BankName"]["textColor"] = textColor
                                # Data_SoundList_ReScan[Temp_ID]["BankName"]["bgColor"] = bgColor
                            # elif g == 4:
                            #     Data_SoundList_ReScan[Temp_ID]["KeyStr"]["text"] = text
                            #     Data_SoundList_ReScan[Temp_ID]["KeyStr"]["textColor"] = textColor
                            #     Data_SoundList_ReScan[Temp_ID]["KeyStr"]["bgColor"] = bgColor
                            # elif g == 5:
                            #     Data_SoundList_ReScan[Temp_ID]["BodyStr"]["text"] = text
                            #     Data_SoundList_ReScan[Temp_ID]["BodyStr"]["textColor"] = textColor
                            #     Data_SoundList_ReScan[Temp_ID]["BodyStr"]["bgColor"] = bgColor
                            # elif g == 6:
                            #     Data_SoundList_ReScan[Temp_ID]["TailStr"]["text"] = text
                            #     Data_SoundList_ReScan[Temp_ID]["TailStr"]["textColor"] = textColor
                            #     Data_SoundList_ReScan[Temp_ID]["TailStr"]["bgColor"] = bgColor
                            # elif g == 7:
                            #     Data_SoundList_ReScan[Temp_ID]["RDM"]["text"] = text
                            #     Data_SoundList_ReScan[Temp_ID]["RDM"]["textColor"] = textColor
                            #     Data_SoundList_ReScan[Temp_ID]["RDM"]["bgColor"] = bgColor
                            # elif g == 8:
                            #     Data_SoundList_ReScan[Temp_ID]["Lock"]["text"] = text
                            #     Data_SoundList_ReScan[Temp_ID]["Lock"]["textColor"] = textColor
                            #     Data_SoundList_ReScan[Temp_ID]["Lock"]["bgColor"] = bgColor
                            # elif g == 9:
                            #     Data_SoundList_ReScan[Temp_ID]["MirrorFrom"]["text"] = text
                            #     Data_SoundList_ReScan[Temp_ID]["MirrorFrom"]["textColor"] = textColor
                            #     Data_SoundList_ReScan[Temp_ID]["MirrorFrom"]["bgColor"] = bgColor

                    # 同步进度条信息
                    ProgressBar_Count += 1
                    self.progressBar.setValue(int(ProgressBar_Count / TotalRowNum * 100))

                # 保存JSON
                LiteDict = {"$ProjectStr$": global_curWwiseProjName, "$ProjectGUID$": global_curWwiseProjID, "Data_SoundList": Data_SoundList_ReScan}
                SaveJson(LiteDict, jsonFilePath)
                LOG.info(lan["GUI_LOG_JSONHasBeenExported"][L] + str(jsonFilePath))
                open_file_folder_highlight(jsonFilePath)

                # 隐藏进度条
                self.progressBar.setValue(0)
                self.progressBar.setVisible(False)

                # 刷新保存按钮状态
                self.NeedSafeFlag = 0
                self.SetState_Save()
                self.statusbar.showMessage("")
        else:
            self.statusbar.showMessage(lan["LOG_LoadAlert"][L])

    def SetState_Save(self):
        if self.NeedSafeFlag == 0:
            self.pushButton_Save.setStyleSheet("QPushButton{border-image: url(cf/gui/icon_buttons/btn_save.png)}"
                                               "QPushButton:hover{border-image: url(cf/gui/icon_buttons/btn_save_hover.png)}"
                                               "QPushButton:pressed{border-image: url(cf/gui/icon_buttons/btn_save_press.png)}")
        else:
            self.pushButton_Save.setStyleSheet("QPushButton{border-image: url(cf/gui/icon_buttons/btn_unsave.png)}"
                                               "QPushButton:hover{border-image: url(cf/gui/icon_buttons/btn_unsave_hover.png)}"
                                               "QPushButton:pressed{border-image: url(cf/gui/icon_buttons/btn_unsave_press.png)}")

    def SaveAs_Json(self):
        currentTimeStr = getCurrentTimeStr()
        PossibleSaveAsFolderPath = os.path.join(global_curWwisePath, key["ExportFolderName"])
        if not os.path.exists(PossibleSaveAsFolderPath):
            os.mkdir(PossibleSaveAsFolderPath)
        jsonFilePath = os.path.join(PossibleSaveAsFolderPath, "SoundList_" + currentTimeStr + ".json")

        # 保存完整json
        self.Save(jsonFilePath)
        LOG.info(lan["GUI_LOG_JSONHasBeenExported"][L] + str(jsonFilePath))
        open_file_folder_highlight(jsonFilePath)

    def ExportSoundList(self):
        # 保存客户端用json
        PossibleSaveAsFolderPath_ForEngine = LocalInfoDict.get("Path_DefaultSaveAsFolder", "@#$")
        if len(PossibleSaveAsFolderPath_ForEngine) != 0 and PossibleSaveAsFolderPath_ForEngine != "@#$" and os.path.exists(PossibleSaveAsFolderPath_ForEngine):
            fullPath = os.path.join(PossibleSaveAsFolderPath_ForEngine, "SoundList.json")
            if fullPath == "C:\\SoundList.json":
                LOG.warning(lan["GUI_LOG_JSONCanNotBeSavedAtCRoot"][L])
            else:
                self.Save_JsonForEngine(fullPath)

    def SaveAs_Xlsx(self):
        self.Progress_JsonToXlsx = Thread_JsonToXlsx(global_curWwisePath)
        self.Progress_JsonToXlsx.ProcessNum.connect(self.ShowProgress)
        self.Progress_JsonToXlsx.start()

    def Action_TransferXlsxIntoJson(self):
        try:
            Path_xlsx = self.LocatePath_WriteIntoLocalJson("File", "Path_SoundListXlsx")
            if Path_xlsx is not None and Path_xlsx.endswith(".xlsx"):
                self.Progress_XlsxToJson = Thread_XlsxToJson(Path_xlsx)
                self.Progress_XlsxToJson.ProcessNum.connect(self.ShowProgress)
                self.Progress_XlsxToJson.start()
        except:
            traceback.print_exc()

    def Refresh_Filter(self):
        try:
            self.ClearLayout(self.horizontalLayout_Filter)
            self.Init_Filter()
        except:
            traceback.print_exc()

    # ----------------------------------------------------------------------------- Window Menu Func ----- Edit
    def Action_Undo(self):
        # 先断联cellChanged信号，否则会默认触发CellChanged对单元格内容新旧的强行获取
        self.tableWidget_SoundSheet.cellChanged.disconnect(self.Action_AfterCellChanged)

        if len(UndoList) != 0:
            # Undo时，将UndoList里pop掉的一个，转移到RedoList中备用
            lastItemInfo = UndoList.pop()
            RedoList.append(lastItemInfo)
            # LOG.debug(RedoList)
            # LOG.debug(lastItemInfo)
            keyStr = list(lastItemInfo[0].keys())[0]
            # LOG.debug(keyStr)

            if keyStr == "KeyboardInput" or keyStr == "PasteInput" or keyStr == "ClearInput":
                for obj in lastItemInfo:
                    # LOG.debug(obj[keyStr])
                    oldrow = obj[keyStr]["Old"]["row"]
                    oldcol = obj[keyStr]["Old"]["column"]
                    oldtext = obj[keyStr]["Old"]["text"]
                    oldtextColor = obj[keyStr]["Old"]["textColor"]
                    oldbgColor = obj[keyStr]["Old"]["bgColor"]

                    # 写入变化
                    newCell = QTableWidgetItem()
                    newCell.setText(oldtext)
                    newCell.setFont(QFont(key["DefaultFont_English"], key["DefaultFont_Size"]))
                    newCell.setForeground(QColor(oldtextColor))
                    newCell.setBackground(QColor(oldbgColor))
                    if oldcol in [0, 7, 8, 9]:
                        newCell.setTextAlignment(Qt.AlignCenter | Qt.AlignCenter)
                    self.tableWidget_SoundSheet.setItem(oldrow, oldcol, newCell)

            elif keyStr == "DelLineInput":
                for lineobj in lastItemInfo:
                    for itemGroup in lineobj[keyStr]:
                        # 新增行，并恢复新增行的原始内容
                        row = itemGroup[0]["row"]
                        self.tableWidget_SoundSheet.insertRow(row)
                        for item in itemGroup:
                            col = item["column"]
                            newCell = QTableWidgetItem()
                            newCell.setText(item["text"])
                            newCell.setFont(QFont(key["DefaultFont_English"], key["DefaultFont_Size"]))
                            newCell.setForeground(QColor(item["textColor"]))
                            newCell.setBackground(QColor(item["bgColor"]))
                            if col in [0, 7, 8, 9]:
                                newCell.setTextAlignment(Qt.AlignCenter | Qt.AlignCenter)
                            self.tableWidget_SoundSheet.setItem(row, col, newCell)

            elif keyStr == "AddLineInput":
                self.tableWidget_SoundSheet.removeRow(lastItemInfo[0]["AddLineInput"])
            else:
                pass

        self.UndoRedoNumShow()
        self.NeedSafeFlag = 1
        self.SetState_Save()

        # 恢复cellChanged连接
        self.tableWidget_SoundSheet.cellChanged.connect(self.Action_AfterCellChanged)

    def Action_Redo(self):
        # 先断联cellChanged信号，否则会默认触发CellChanged对单元格内容新旧的强行获取
        self.tableWidget_SoundSheet.cellChanged.disconnect(self.Action_AfterCellChanged)

        if len(RedoList) != 0:
            # Redo时，将RedoList里pop掉的一个，转回到UndoList中备用
            lastItemInfo = RedoList.pop()
            UndoList.append(lastItemInfo)

            keyStr = list(lastItemInfo[0].keys())[0]

            if keyStr == "KeyboardInput" or keyStr == "PasteInput" or keyStr == "ClearInput":
                for obj in lastItemInfo:
                    # LOG.debug(obj[keyStr])
                    oldrow = obj[keyStr]["New"]["row"]
                    oldcol = obj[keyStr]["New"]["column"]
                    oldtext = obj[keyStr]["New"]["text"]
                    oldtextColor = obj[keyStr]["New"]["textColor"]
                    oldbgColor = obj[keyStr]["New"]["bgColor"]

                    # 写入变化
                    newCell = QTableWidgetItem()
                    newCell.setText(oldtext)
                    newCell.setFont(QFont(key["DefaultFont_English"], key["DefaultFont_Size"]))
                    newCell.setForeground(QColor(oldtextColor))
                    newCell.setBackground(QColor(oldbgColor))
                    if oldcol in [0, 7, 8, 9]:
                        newCell.setTextAlignment(Qt.AlignCenter | Qt.AlignCenter)
                    self.tableWidget_SoundSheet.setItem(oldrow, oldcol, newCell)

            elif keyStr == "DelLineInput":
                for lineobj in lastItemInfo:
                    for group in lineobj[keyStr]:
                        self.tableWidget_SoundSheet.removeRow(group[0]["row"])

            elif keyStr == "AddLineInput":
                for lineobj in lastItemInfo:
                    row = lineobj[keyStr]
                    self.tableWidget_SoundSheet.insertRow(row)
                    self.InitNewEmptyLine(row)

        self.UndoRedoNumShow()
        self.NeedSafeFlag = 1
        self.SetState_Save()

        # 恢复cellChanged连接
        self.tableWidget_SoundSheet.cellChanged.connect(self.Action_AfterCellChanged)

    def UndoRedoNumShow(self):
        undoNum = len(UndoList)
        redoNum = len(RedoList)
        if undoNum == 0 and redoNum == 0:
            # self.statusbar.showMessage("")
            self.label_UndoRedo.setText("")
        else:
            # self.statusbar.showMessage("Undo: " + str(undoNum) + "  " + "Redo: " + str(redoNum))
            self.label_UndoRedo.setText(str(undoNum) + " " + str(redoNum))

    def InitNewEmptyLine(self, row):
        for item in range(self.tableWidget_SoundSheet.columnCount()):
            newCell = QTableWidgetItem()
            if item == 0:
                newCell.setText(str(self.GenerateNewID()))
            else:
                newCell.setText("")
            newCell.setFont(QFont(key["DefaultFont_English"], key["DefaultFont_Size"]))
            newCell.setForeground(QColor("#000000"))
            newCell.setBackground(QColor("#ffffff"))
            if item in [0, 7, 8, 9]:
                newCell.setTextAlignment(Qt.AlignCenter | Qt.AlignCenter)
            self.tableWidget_SoundSheet.setItem(row, item, newCell)

    def Action_AddLine(self):
        # 先断联cellChanged信号，否则会默认触发CellChanged对单元格内容新旧的强行获取
        self.tableWidget_SoundSheet.cellChanged.disconnect(self.Action_AfterCellChanged)

        line = self.tableWidget_SoundSheet.rowCount()
        s_items = self.tableWidget_SoundSheet.selectedItems()  # 获取当前所有选择的items
        selected_rows = []  # 求出所选择的行数

        if len(s_items) != 0:  # 说明用户先选中了某一行或某些行，再进行新增
            for i in s_items:
                row = i.row()
                if row not in selected_rows:
                    selected_rows.append(row)
            selected_rows = sorted(selected_rows)
            self.tableWidget_SoundSheet.insertRow(selected_rows[0])

            # 初始化新增的行内容
            self.InitNewEmptyLine(selected_rows[0])

            insertRowRecord = [{"AddLineInput": selected_rows[0]}]
            UndoList.append(insertRowRecord)

            # 新动作产生时，要清空RedoList，防止凭空Redo出遗弃的历史动作
            RedoList.clear()
            self.UndoRedoNumShow()

            self.NeedSafeFlag = 1
            self.SetState_Save()

            # 恢复cellChanged连接
            self.tableWidget_SoundSheet.cellChanged.connect(self.Action_AfterCellChanged)

            return selected_rows[0]

        else:  # 说明用户啥也没选，直接新增
            # 先判断是否是空表
            if globals.LoadFlag is True:
                self.tableWidget_SoundSheet.setRowCount(line + 1)

                # 初始化新增的行内容
                self.InitNewEmptyLine(line)

                insertRowRecord = [{"AddLineInput": line}]
                UndoList.append(insertRowRecord)

                # 新动作产生时，要清空RedoList，防止凭空Redo出遗弃的历史动作
                RedoList.clear()
                self.UndoRedoNumShow()

                self.NeedSafeFlag = 1
                self.SetState_Save()

                # 恢复cellChanged连接
                self.tableWidget_SoundSheet.cellChanged.connect(self.Action_AfterCellChanged)

                return line
            else:
                LOG.warning(lan["LOG_LoadAlert"][L])

                # 恢复cellChanged连接
                self.tableWidget_SoundSheet.cellChanged.connect(self.Action_AfterCellChanged)

                return None

    def Action_AddLine_AtBottom(self):
        if globals.LoadFlag is True:
            # 先断联cellChanged信号，否则会默认触发CellChanged对单元格内容新旧的强行获取
            self.tableWidget_SoundSheet.cellChanged.disconnect(self.Action_AfterCellChanged)

            line = self.tableWidget_SoundSheet.rowCount()
            self.tableWidget_SoundSheet.setRowCount(line + 1)

            # 初始化新增的行内容
            self.InitNewEmptyLine(line)

            insertRowRecord = [{"AddLineInput": line}]
            UndoList.append(insertRowRecord)

            # 新动作产生时，要清空RedoList，防止凭空Redo出遗弃的历史动作
            RedoList.clear()
            self.UndoRedoNumShow()

            self.NeedSafeFlag = 1
            self.SetState_Save()

            # 恢复cellChanged连接
            self.tableWidget_SoundSheet.cellChanged.connect(self.Action_AfterCellChanged)

            return line

    def Action_DelLine(self):
        s_items = self.tableWidget_SoundSheet.selectedItems()  # 获取当前所有选择的items
        if len(s_items) != 0:
            selected_rows = []
            for i in s_items:  # 求出所选择的行数
                row = i.row()
                if row not in selected_rows:
                    selected_rows.append(row)

            # 根据上一步统计出来的用户选择的行数，进一步把行内每个单元格的数据记录下来
            OldDataOfEachLine = []
            for r in range(len(sorted(selected_rows))):
                oneLineGroup = []
                for e in range(self.tableWidget_SoundSheet.columnCount()):
                    oldtext = self.tableWidget_SoundSheet.item(selected_rows[r], e).text()
                    oldtextColor = self.tableWidget_SoundSheet.item(selected_rows[r], e).foreground().color().name()
                    oldbgColor = self.tableWidget_SoundSheet.item(selected_rows[r], e).background().color().name()
                    singleLine_Old = {
                        "row": selected_rows[r],
                        "column": e,
                        "text": oldtext,
                        "textColor": oldtextColor,
                        "bgColor": oldbgColor
                    }
                    oneLineGroup.append(singleLine_Old)
                    # LOG.debug(singleLine_Old)
                OldDataOfEachLine.append(oneLineGroup)

            FinalPack = {"DelLineInput": OldDataOfEachLine}
            UndoList.append([FinalPack])

            # 删除行
            for r in range(len(sorted(selected_rows))):
                self.tableWidget_SoundSheet.removeRow(selected_rows[r] - r)

            # 新动作产生时，要清空RedoList，防止凭空Redo出遗弃的历史动作
            RedoList.clear()
            self.UndoRedoNumShow()

            # 更新保存状态
            self.NeedSafeFlag = 1
            self.SetState_Save()

    def Action_ClearCell(self):
        # 先断联cellChanged信号，否则会默认触发CellChanged对单元格内容新旧的强行获取
        self.tableWidget_SoundSheet.cellChanged.disconnect(self.Action_AfterCellChanged)

        s_items = self.tableWidget_SoundSheet.selectedItems()
        if len(s_items) != 0:
            finalList = []
            for item, tempdictOld in zip(s_items, self.CellSelected_Old):
                # tempdictOld = self.CellSelected_Old

                # 根据用户自定义CopyPasteClear选项执行不同的结果
                if key["CopyPasteMode"] == "TextOnly":
                    tempdictNew = {
                        "row": item.row(),
                        "column": item.column(),
                        "text": "",
                        "textColor": item.foreground().color().name(),
                        "bgColor": item.background().color().name()
                    }
                    finalPack = {"ClearInput": {"Old": tempdictOld, "New": tempdictNew}}
                    finalList.append(finalPack)

                    # 清除Text
                    item.setText("")

                elif key["CopyPasteMode"] == "TextAndBGColor":
                    tempdictNew = {
                        "row": item.row(),
                        "column": item.column(),
                        "text": "",
                        "textColor": item.foreground().color().name(),
                        "bgColor": "#ffffff"
                    }
                    finalPack = {"ClearInput": {"Old": tempdictOld, "New": tempdictNew}}
                    finalList.append(finalPack)

                    # 清除Text和BGColor
                    item.setText("")
                    item.setBackground(QColor("#ffffff"))

                elif key["CopyPasteMode"] == "BGColorOnly":
                    tempdictNew = {
                        "row": item.row(),
                        "column": item.column(),
                        "text": item.text(),
                        "textColor": item.foreground().color().name(),
                        "bgColor": "#ffffff"
                    }
                    finalPack = {"ClearInput": {"Old": tempdictOld, "New": tempdictNew}}
                    finalList.append(finalPack)

                    # 清除BGColor
                    item.setBackground(QColor("#ffffff"))

            # LOG.debug(finalList)
            UndoList.append(finalList)

            # 新动作产生时，要清空RedoList，防止凭空Redo出遗弃的历史动作
            RedoList.clear()
            self.UndoRedoNumShow()

            # 更新保存状态
            self.NeedSafeFlag = 1
            self.SetState_Save()

        # 恢复cellChanged连接
        self.tableWidget_SoundSheet.cellChanged.connect(self.Action_AfterCellChanged)

    def Action_CopyCell(self):
        self.copied_cells = sorted(self.tableWidget_SoundSheet.selectedIndexes())

    def Action_PasteCell(self):
        # 先断联cellChanged信号，否则会默认触发CellChanged对单元格内容新旧的强行获取
        self.tableWidget_SoundSheet.cellChanged.disconnect(self.Action_AfterCellChanged)

        try:
            if len(self.copied_cells) != 0:
                r = self.tableWidget_SoundSheet.currentRow() - self.copied_cells[0].row()
                c = self.tableWidget_SoundSheet.currentColumn() - self.copied_cells[0].column()
                PasteAllRecord = []
                for cell in self.copied_cells:
                    oldtext = self.tableWidget_SoundSheet.item(cell.row() + r, cell.column() + c).text()
                    oldtextColor = self.tableWidget_SoundSheet.item(cell.row() + r,
                                                                    cell.column() + c).foreground().color().name()
                    oldbgColor = self.tableWidget_SoundSheet.item(cell.row() + r,
                                                                  cell.column() + c).background().color().name()
                    # LOG.debug(["WAS --> ", cell.row() + r, cell.column() + c, oldtext, oldtextColor, oldbgColor])
                    Targettext = self.tableWidget_SoundSheet.item(cell.row(), cell.column()).text()
                    TargettextColor = self.tableWidget_SoundSheet.item(cell.row(),
                                                                       cell.column()).foreground().color().name()
                    TargetbgColor = self.tableWidget_SoundSheet.item(cell.row(), cell.column()).background().color().name()
                    # LOG.debug(["Will Be --> ", cell.row() + r, cell.column() + c, Targettext, TargettextColor, TargetbgColor])

                    singleCell_Old = {
                        "row": cell.row() + r,
                        "column": cell.column() + c,
                        "text": oldtext,
                        "textColor": oldtextColor,
                        "bgColor": oldbgColor
                    }

                    # 根据用户自定义CopyPasteClear的值，进行分流
                    if key["CopyPasteMode"] == "TextOnly":
                        singleCell_New = {
                            "row": cell.row() + r,
                            "column": cell.column() + c,
                            "text": Targettext,
                            "textColor": TargettextColor,
                            "bgColor": oldbgColor
                        }

                        # 写入变化
                        newCell = QTableWidgetItem()
                        newCell.setText(Targettext)
                        newCell.setFont(QFont(key["DefaultFont_English"], key["DefaultFont_Size"]))
                        newCell.setForeground(QColor(TargettextColor))
                        newCell.setBackground(QColor(oldbgColor))
                        if cell.column() + c in [0, 7, 8, 9]:
                            newCell.setTextAlignment(Qt.AlignCenter | Qt.AlignCenter)
                        self.tableWidget_SoundSheet.setItem(cell.row() + r, cell.column() + c, newCell)

                    elif key["CopyPasteMode"] == "TextAndBGColor":
                        singleCell_New = {
                            "row": cell.row() + r,
                            "column": cell.column() + c,
                            "text": Targettext,
                            "textColor": TargettextColor,
                            "bgColor": TargetbgColor
                        }

                        # 写入变化
                        newCell = QTableWidgetItem()
                        newCell.setText(Targettext)
                        newCell.setFont(QFont(key["DefaultFont_English"], key["DefaultFont_Size"]))
                        newCell.setForeground(QColor(TargettextColor))
                        newCell.setBackground(QColor(TargetbgColor))
                        if cell.column() + c in [0, 7, 8, 9]:
                            newCell.setTextAlignment(Qt.AlignCenter | Qt.AlignCenter)
                        self.tableWidget_SoundSheet.setItem(cell.row() + r, cell.column() + c, newCell)

                    elif key["CopyPasteMode"] == "BGColorOnly":
                        singleCell_New = {
                            "row": cell.row() + r,
                            "column": cell.column() + c,
                            "text": oldtext,
                            "textColor": oldtextColor,
                            "bgColor": TargetbgColor
                        }

                        # 写入变化
                        newCell = QTableWidgetItem()
                        newCell.setText(oldtext)
                        newCell.setFont(QFont(key["DefaultFont_English"], key["DefaultFont_Size"]))
                        newCell.setForeground(QColor(oldtextColor))
                        newCell.setBackground(QColor(TargetbgColor))
                        if cell.column() + c in [0, 7, 8, 9]:
                            newCell.setTextAlignment(Qt.AlignCenter | Qt.AlignCenter)
                        self.tableWidget_SoundSheet.setItem(cell.row() + r, cell.column() + c, newCell)

                    else:
                        singleCell_New = {
                            "row": cell.row() + r,
                            "column": cell.column() + c,
                            "text": Targettext,
                            "textColor": TargettextColor,
                            "bgColor": oldbgColor
                        }

                        # 写入变化
                        newCell = QTableWidgetItem()
                        newCell.setText(Targettext)
                        newCell.setFont(QFont(key["DefaultFont_English"], key["DefaultFont_Size"]))
                        newCell.setForeground(QColor(TargettextColor))
                        newCell.setBackground(QColor(oldbgColor))
                        if cell.column() + c in [0, 7, 8, 9]:
                            newCell.setTextAlignment(Qt.AlignCenter | Qt.AlignCenter)
                        self.tableWidget_SoundSheet.setItem(cell.row() + r, cell.column() + c, newCell)

                    datagroup = {"PasteInput": {"Old": singleCell_Old, "New": singleCell_New}}
                    PasteAllRecord.append(datagroup)

                UndoList.append(PasteAllRecord)

                # 新动作产生时，要清空RedoList，防止凭空Redo出遗弃的历史动作
                RedoList.clear()
                self.UndoRedoNumShow()

                self.NeedSafeFlag = 1
                self.SetState_Save()
        except:
            pass

        # 恢复cellChanged连接
        self.tableWidget_SoundSheet.cellChanged.connect(self.Action_AfterCellChanged)

    # ----------------------------------------------------------------------------- Window Menu Func ----- Wwise
    def PreCheck_GlobalSafetyCheck(self):
        self.MessageBox_NoArgs(lan["LOG_MessageBox_PreComfirm_Title"][L],
                               lan["LOG_MessageBox_PreComfirm_Text_LongTimeNotice"][L], self.GlobalSafetyCheck)

    def GlobalSafetyCheck(self):
        SafetyCheckLog.clear()
        try:
            LOG.info(lan["GUI_action_GlobalSafetyCheck_Start"][L])
            self.Thread_GlobalSafetyCheck = Thread_GlobalSafetyCheck()
            self.Thread_GlobalSafetyCheck.start()

            if len(SafetyCheckLog) == 0:
                pass
            else:
                if key["ifColorAfterGlobalSafetyCheck"] == "True":
                    try:
                        color = SimpleWaapi()
                        LOG.debug("[SW实例创建][Main][GlobalSafetyCheck]")
                        for i in ColorGUIDPool:
                            color.ColorGUID(i)
                        color.__del__()
                        LOG.debug("[SW实例清除***][Main][GlobalSafetyCheck]")

                        SafetyCheckLog.clear()
                        ColorGUIDPool.clear()
                    except:
                        traceback.print_exc()
                        SafetyCheckLog.clear()
                        ColorGUIDPool.clear()
                        LOG.error(lan["LOG_SM_WwiseOpen_FAIL"][L])
                else:
                    SafetyCheckLog.clear()
                    ColorGUIDPool.clear()
                    pass
        except:
            traceback.print_exc()
            SafetyCheckLog.clear()
            ColorGUIDPool.clear()
            LOG.error(lan["LOG_SM_def_SafetyCheck_FAIL"][L])

    def PreCheck_RelinkMissingWAV(self):
        self.MessageBox_NoArgs(lan["LOG_MessageBox_PreComfirm_Title"][L],
                               lan["LOG_MessageBox_PreComfirm_Text_LongTimeNotice"][L], self.RelinkMissingWAV)

    def RelinkMissingWAV(self):
        LOG.info(lan["GUI_action_RelinkMissingWAV_Start"][L])
        try:
            self.Progress_GlobalMissingWAVRelink = Thread_GlobalMissingWAVRelink(global_curWwisePath)
            self.Progress_GlobalMissingWAVRelink.ProcessNum.connect(self.ShowProgress)
            self.Progress_GlobalMissingWAVRelink.start()
        except:
            traceback.print_exc()
            LOG.error(lan["GUI_SM_RC_action_RelinkWAV_FAILED"][L])

    def PreCheck_GenerateProjectSheet(self):
        self.MessageBox_NoArgs(lan["LOG_MessageBox_PreComfirm_Title"][L],
                               lan["LOG_MessageBox_PreComfirm_Text_LongTimeNotice"][L], self.GenerateProjectSheet)

    def GenerateProjectSheet(self):
        self.Progress_WwuToJson = Thread_WwuToJson(global_curWwisePath)
        self.Progress_WwuToJson.ProcessNum.connect(self.ShowProgress)
        self.Progress_WwuToJson.start()

    def OpenWwiseProjectFolder(self):
        open_file_folder_highlight(global_curWwiseProjPath)

    # ----------------------------------------------------------------------------- Window Menu Func ----- Engine
    def CheckIfSoundIDStatusJsonIsValid(self, TarDict):
        try:
            TYPEOF_ID_ExistInSoundList_NotExistInEngine = type(TarDict["ID_ExistInSoundList_NotExistInEngine"])
            TYPEOF_ID_ExistInEngine_NotExistInSoundList = type(TarDict["ID_ExistInEngine_NotExistInSoundList"])
            TYPEOF_ID_FoundDuplicate_InEngine = type(TarDict["ID_FoundDuplicate_InEngine"])
            TYPEOF_Event_ExistInSoundList_NotExistInEngine = type(TarDict["Event_ExistInSoundList_NotExistInEngine"])
            TYPEOF_Event_ExistInEngine_NotExistInSoundList = type(TarDict["Event_ExistInEngine_NotExistInSoundList"])
            TYPEOF_Event_FoundDuplicate_InEngine = type(TarDict["Event_FoundDuplicate_InEngine"])
            if (TYPEOF_ID_ExistInSoundList_NotExistInEngine is not list) or (
                    TYPEOF_ID_ExistInEngine_NotExistInSoundList is not list) or (
                    TYPEOF_ID_FoundDuplicate_InEngine is not dict) or (
                    TYPEOF_Event_ExistInEngine_NotExistInSoundList is not list) or (
                    TYPEOF_Event_ExistInSoundList_NotExistInEngine is not list) or (
                    TYPEOF_Event_FoundDuplicate_InEngine is not dict):
                return False
            else:
                return True
        except:
            traceback.print_exc()
            return False

    def CheckSoundIDStatus(self):
        try:
            # 先直接查看文件，如果文件在，判断有效性
            Path_SoundIDStatusJson = LocalInfoDict["Path_SoundIDSTatusReport"]
            if os.path.exists(Path_SoundIDStatusJson) and Path_SoundIDStatusJson.endswith(".json"):  # 说明base.json里的文件路径有效
                # 判断有效性
                SoundIDStatusReportDict = LoadJson(Path_SoundIDStatusJson, "gbk")
                validReport = self.CheckIfSoundIDStatusJsonIsValid(SoundIDStatusReportDict)
                if validReport is True:  # 说明json有效，直接打印结果
                    LOG.info(lan["GUI_action_CheckSoundIDStatus_Report"][L])
                    if len(SoundIDStatusReportDict["ID_ExistInSoundList_NotExistInEngine"]) != 0:
                        LOG.warning(lan["GUI_action_CheckSoundIDStatus_ID_ExistInSoundList_NotExistInEngine"][L])
                        LOG.warning(SoundIDStatusReportDict["ID_ExistInSoundList_NotExistInEngine"])
                    if len(SoundIDStatusReportDict["ID_ExistInEngine_NotExistInSoundList"]) != 0:
                        LOG.warning(lan["GUI_action_CheckSoundIDStatus_ID_ExistInEngine_NotExistInSoundList"][L])
                        LOG.warning(SoundIDStatusReportDict["ID_ExistInEngine_NotExistInSoundList"])
                    if len(SoundIDStatusReportDict["ID_FoundDuplicate_InEngine"]) != 0:
                        LOG.warning(lan["GUI_action_CheckSoundIDStatus_ID_FoundDuplicate_InEngine"][L])
                        LOG.warning(SoundIDStatusReportDict["ID_FoundDuplicate_InEngine"])
                    if len(SoundIDStatusReportDict["Event_ExistInSoundList_NotExistInEngine"]) != 0:
                        LOG.warning(lan["GUI_action_CheckSoundIDStatus_Event_ExistInSoundList_NotExistInEngine"][L])
                        LOG.warning(SoundIDStatusReportDict["Event_ExistInSoundList_NotExistInEngine"])
                    if len(SoundIDStatusReportDict["Event_ExistInEngine_NotExistInSoundList"]) != 0:
                        LOG.warning(lan["GUI_action_CheckSoundIDStatus_Event_ExistInEngine_NotExistInSoundList"][L])
                        LOG.warning(SoundIDStatusReportDict["Event_ExistInEngine_NotExistInSoundList"])
                    if len(SoundIDStatusReportDict["Event_FoundDuplicate_InEngine"]) != 0:
                        LOG.warning(lan["GUI_action_CheckSoundIDStatus_Event_FoundDuplicate_InEngine"][L])
                        LOG.warning(SoundIDStatusReportDict["Event_FoundDuplicate_InEngine"])
                    if len(SoundIDStatusReportDict["ID_ExistInSoundList_NotExistInEngine"]) == 0 and len(
                            SoundIDStatusReportDict["ID_ExistInEngine_NotExistInSoundList"]) == 0 and len(
                            SoundIDStatusReportDict["ID_FoundDuplicate_InEngine"]) == 0 and len(
                            SoundIDStatusReportDict["Event_ExistInSoundList_NotExistInEngine"]) == 0 and len(
                            SoundIDStatusReportDict["Event_ExistInEngine_NotExistInSoundList"]) == 0 and len(
                            SoundIDStatusReportDict["Event_FoundDuplicate_InEngine"]) == 0:
                        LOG.info(lan["GUI_action_CheckSoundIDStatus_Report_AllGood"][L])
                else:  # 说明json格式无效，提示重新指派
                    Path_SoundIDStatusJson = self.LocatePath_SoundIDStatusJson("File", "Path_SoundIDSTatusReport")
                    if Path_SoundIDStatusJson is not None and Path_SoundIDStatusJson.endswith(".json"):
                        # 判断有效性
                        SoundIDStatusReportDict = LoadJson(Path_SoundIDStatusJson, "gbk")
                        validReport = self.CheckIfSoundIDStatusJsonIsValid(SoundIDStatusReportDict)
                        if validReport is True:
                            # 先保存新路径
                            LocalInfoDict["Path_SoundIDSTatusReport"] = Path_SoundIDStatusJson
                            SaveJson(LocalInfoDict, global_curWwiseLocalJson)
                            # 再分析内容
                            LOG.info(lan["GUI_action_CheckSoundIDStatus_Report"][L])
                            if len(SoundIDStatusReportDict["ID_ExistInSoundList_NotExistInEngine"]) != 0:
                                LOG.warning(lan["GUI_action_CheckSoundIDStatus_ID_ExistInSoundList_NotExistInEngine"][L])
                                LOG.warning(SoundIDStatusReportDict["ID_ExistInSoundList_NotExistInEngine"])
                            if len(SoundIDStatusReportDict["ID_ExistInEngine_NotExistInSoundList"]) != 0:
                                LOG.warning(lan["GUI_action_CheckSoundIDStatus_ID_ExistInEngine_NotExistInSoundList"][L])
                                LOG.warning(SoundIDStatusReportDict["ID_ExistInEngine_NotExistInSoundList"])
                            if len(SoundIDStatusReportDict["ID_FoundDuplicate_InEngine"]) != 0:
                                LOG.warning(lan["GUI_action_CheckSoundIDStatus_ID_FoundDuplicate_InEngine"][L])
                                LOG.warning(SoundIDStatusReportDict["ID_FoundDuplicate_InEngine"])
                            if len(SoundIDStatusReportDict["Event_ExistInSoundList_NotExistInEngine"]) != 0:
                                LOG.warning(lan["GUI_action_CheckSoundIDStatus_Event_ExistInSoundList_NotExistInEngine"][L])
                                LOG.warning(SoundIDStatusReportDict["Event_ExistInSoundList_NotExistInEngine"])
                            if len(SoundIDStatusReportDict["Event_ExistInEngine_NotExistInSoundList"]) != 0:
                                LOG.warning(lan["GUI_action_CheckSoundIDStatus_Event_ExistInEngine_NotExistInSoundList"][L])
                                LOG.warning(SoundIDStatusReportDict["Event_ExistInEngine_NotExistInSoundList"])
                            if len(SoundIDStatusReportDict["Event_FoundDuplicate_InEngine"]) != 0:
                                LOG.warning(lan["GUI_action_CheckSoundIDStatus_Event_FoundDuplicate_InEngine"][L])
                                LOG.warning(SoundIDStatusReportDict["Event_FoundDuplicate_InEngine"])
                            if len(SoundIDStatusReportDict["ID_ExistInSoundList_NotExistInEngine"]) == 0 and len(
                                    SoundIDStatusReportDict["ID_ExistInEngine_NotExistInSoundList"]) == 0 and len(
                                    SoundIDStatusReportDict["ID_FoundDuplicate_InEngine"]) == 0 and len(
                                    SoundIDStatusReportDict["Event_ExistInSoundList_NotExistInEngine"]) == 0 and len(
                                    SoundIDStatusReportDict["Event_ExistInEngine_NotExistInSoundList"]) == 0 and len(
                                    SoundIDStatusReportDict["Event_FoundDuplicate_InEngine"]) == 0:
                                LOG.info(lan["GUI_action_CheckSoundIDStatus_Report_AllGood"][L])
                    else:
                        LOG.warning(lan["GUI_action_CheckSoundIDStatus_InvalidJson"][L] + str(Path_SoundIDStatusJson))
            else:  # 说明base.json里的文件路径无效，提示重新指派
                Path_SoundIDStatusJson = self.LocatePath_SoundIDStatusJson("File", "Path_SoundIDSTatusReport")
                if Path_SoundIDStatusJson is not None and Path_SoundIDStatusJson.endswith(".json"):
                    # 判断有效性
                    SoundIDStatusReportDict = LoadJson(Path_SoundIDStatusJson, "gbk")
                    validReport = self.CheckIfSoundIDStatusJsonIsValid(SoundIDStatusReportDict)
                    if validReport is True:
                        # 先保存新路径
                        LocalInfoDict["Path_SoundIDSTatusReport"] = Path_SoundIDStatusJson
                        SaveJson(LocalInfoDict, global_curWwiseLocalJson)
                        # 再分析内容
                        LOG.info(lan["GUI_action_CheckSoundIDStatus_Report"][L])
                        if len(SoundIDStatusReportDict["ID_ExistInSoundList_NotExistInEngine"]) != 0:
                            LOG.warning(SoundIDStatusReportDict["ID_ExistInSoundList_NotExistInEngine"])
                        if len(SoundIDStatusReportDict["ID_ExistInEngine_NotExistInSoundList"]) != 0:
                            LOG.warning(SoundIDStatusReportDict["ID_ExistInEngine_NotExistInSoundList"])
                        if len(SoundIDStatusReportDict["ID_FoundDuplicate_InEngine"]) != 0:
                            LOG.warning(SoundIDStatusReportDict["ID_FoundDuplicate_InEngine"])
                        if len(SoundIDStatusReportDict["Event_ExistInSoundList_NotExistInEngine"]) != 0:
                            LOG.warning(SoundIDStatusReportDict["Event_ExistInSoundList_NotExistInEngine"])
                        if len(SoundIDStatusReportDict["Event_ExistInEngine_NotExistInSoundList"]) != 0:
                            LOG.warning(SoundIDStatusReportDict["Event_ExistInEngine_NotExistInSoundList"])
                        if len(SoundIDStatusReportDict["Event_FoundDuplicate_InEngine"]) != 0:
                            LOG.warning(SoundIDStatusReportDict["Event_FoundDuplicate_InEngine"])
                        if len(SoundIDStatusReportDict["ID_ExistInSoundList_NotExistInEngine"]) == 0 and len(
                                SoundIDStatusReportDict["ID_ExistInEngine_NotExistInSoundList"]) == 0 and len(
                                SoundIDStatusReportDict["ID_FoundDuplicate_InEngine"]) == 0 and len(
                                SoundIDStatusReportDict["Event_ExistInSoundList_NotExistInEngine"]) == 0 and len(
                                SoundIDStatusReportDict["Event_ExistInEngine_NotExistInSoundList"]) == 0 and len(
                                SoundIDStatusReportDict["Event_FoundDuplicate_InEngine"]) == 0:
                            LOG.info(lan["GUI_action_CheckSoundIDStatus_Report_AllGood"][L])
                    else:
                        LOG.warning(lan["GUI_action_CheckSoundIDStatus_InvalidJson"][L] + str(Path_SoundIDStatusJson))
                else:
                    LOG.warning(lan["GUI_action_CheckSoundIDStatus_InvalidJson"][L] + str(Path_SoundIDStatusJson))
        except:
            traceback.print_exc()

    # ----------------------------------------------------------------------------- Window Menu Func ----- Help
    def OpenHelpDocument(self):
        if key["Language"] == "Chinese":
            documentPath = "cf\\Document_Chinese.pdf"
        else:
            documentPath = "cf\\Document_English.pdf"

        if os.path.exists(documentPath):
            openFile(documentPath)
        else:
            LOG.warning(lan["LOG_PathIsNotExist"][L] + documentPath)

    def VersionInfo(self):
        messageBox = QMessageBox(QMessageBox.Information, lan["GUI_action_VersionInfo"][L], lan["GUI_action_VersionInfo_InfoText"][L])
        messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
        Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
        Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
        messageBox.exec_()

        if messageBox.clickedButton() == Qyes:
            pass

    def Disclaimer(self):
        messageBox = QMessageBox(QMessageBox.Warning, lan["LOG_GUI_Disclaimer"][L], lan["GUI_SafetyAlert_Content"][L])
        messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
        Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
        messageBox.exec_()

        if messageBox.clickedButton() == Qyes:
            pass

    def DevMode(self):
        devText = self.lineEdit_Find.text()
        if devText == "dev":
            key["DevMode"] = "dev"
            SaveJson(key, global_UserPreferenceJsonPath)
        else:
            key["DevMode"] = ""
            SaveJson(key, global_UserPreferenceJsonPath)

    # ----------------------------------------------------------------------------- Panel Func ----- GUI
    def GetAllKeyStrFromTable(self):
        try:
            KeyStrList = []
            for i in range(self.tableWidget_SoundSheet.rowCount()):  # 遍历大表的每一行
                KeyStr = self.tableWidget_SoundSheet.item(i, 4).text()  # 获取KeyStr单元格中的数据
                if KeyStr is not None:
                    KeyStrList.append(KeyStr)
            # 去重整理
            KeyStrList = list(set(KeyStrList))
            return KeyStrList
        except:
            traceback.print_exc()

    def RefreshCheckedBoxList(self):
        try:
            CheckedPool = []
            self.showAllRow()
            # 依次检查每一个Box_list的Check状态，如果Checked，则将TextStr记录在CheckedPool中
            for i in range(len(self.CurrentKeyStrInTable) + 1):
                boolstate = self.comboBox_Filter.box_list[i].isChecked()
                if boolstate is True:
                    boxtext = self.comboBox_Filter.box_list[i].text()
                    CheckedPool.append(boxtext)

            self.HideRowsNeedToHide(CheckedPool)
        except:
            traceback.print_exc()

    def showAllRow(self):
        line = self.tableWidget_SoundSheet.rowCount()
        for i in range(0, line):
            self.tableWidget_SoundSheet.showRow(i)

    def HideRowsNeedToHide(self, keyStr: list):
        # 获得所有的行Index列表
        TotalRowNum = []
        for k in range(0, self.tableWidget_SoundSheet.rowCount()):
            TotalRowNum.append(k)

        # 获得所有需要Show的行Index列表
        RowsNeedToShow = []
        for k in keyStr:
            for i in range(0, self.tableWidget_SoundSheet.rowCount()):
                if self.tableWidget_SoundSheet.item(i, 4).text() == k:
                    RowsNeedToShow.append(i)
        RowsNeedToShow = sorted(RowsNeedToShow)

        # 得出所有需要Hide的行Index列表
        for p in RowsNeedToShow:
            if p in TotalRowNum:
                TotalRowNum.remove(p)

        RowsNeedToHide = TotalRowNum

        # 隐藏需要隐藏的行
        for h in RowsNeedToHide:
            self.tableWidget_SoundSheet.hideRow(h)

        return RowsNeedToHide

    def Find(self):
        Result = []
        TargetStr = self.lineEdit_Find.text()
        if len(TargetStr) != 0:
            for i in range(self.tableWidget_SoundSheet.rowCount()):
                for j in range(self.tableWidget_SoundSheet.columnCount()):
                    if self.tableWidget_SoundSheet.item(i, j) is not None:
                        value = self.tableWidget_SoundSheet.item(i, j).text()
                        if TargetStr in value:
                            Result.append([i, j])
            Num = len(Result)

            if Num != 0:
                TarNum = self.FindCount % Num
                self.tableWidget_SoundSheet.setCurrentCell(Result[TarNum][0], Result[TarNum][1])
                # self.statusbar.showMessage(str(TarNum + 1) + "/" + str(Num))
                self.label_Find.setText(str(TarNum + 1) + "/" + str(Num))
                self.FindCount += 1
        else:
            self.label_Find.setText("")

    def GO(self, validRowList):
        try:
            # 获取选中的行数
            # rowList = self.GetSelectedRows()
            rowList = validRowList
            if len(rowList) != 0:  # 如果有被选中的行
                aoligei = SimpleWaapi()
                LOG.debug("[SW实例创建][Main][GO]")
                # 获取所有的ID
                AllIDList = []
                for row in range(self.tableWidget_SoundSheet.rowCount()):
                    AllIDList.append(self.tableWidget_SoundSheet.item(row, key["Header_ID"]).text())

                # 逐行安全检查，通过的执行写入
                for r, index in zip(rowList, range(len(rowList))):
                    vID = self.tableWidget_SoundSheet.item(r, key["Header_ID"]).text()
                    vfName = self.tableWidget_SoundSheet.item(r, key["Header_KeyStr"]).text()
                    vsName = self.tableWidget_SoundSheet.item(r, key["Header_BodyStr"]).text()
                    vtName = self.tableWidget_SoundSheet.item(r, key["Header_TailStr"]).text()
                    vRanNum = self.tableWidget_SoundSheet.item(r, key["Header_RDM"]).text()
                    Lock = self.tableWidget_SoundSheet.item(r, key["Header_Lock"]).text()

                    # 先确认ID是否有非法的，有的话跳过循环！
                    duplicatedIDCheck = self.SafetyCheck_ID(vID, AllIDList)
                    if len(duplicatedIDCheck) != 0:
                        LOG.warning(str(duplicatedIDCheck) + lan["LOG_SM_def_WaapiGo_DuplicatedIDPreCheck"][L])
                        break

                    # 确认当前行的Lock值，如果已被标记过，则跳过（continue）当前行的执行，并将Log传入GoLog待打印
                    if str(Lock) == "0" or str(Lock) == key["LockedStrValue"]:
                        LOG.warning("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_LockCheck_SKIP"][L])
                        continue

                    # 确认fName是否合法，否则直接跳过
                    if vfName not in list(KeyInfoDict["Data_KeyInfo"].keys()):
                        LOG.warning("Line" + str(r + 1) + ": " + lan["LOG_NSG_def_nameStrGen_fnameInvalid_Skip"][L])
                        continue

                    # 如果上一步Lock检查未被跳过，则继续执行Create NameStr，产生字符串大包装
                    LOG.warning("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_LockCheck_PASS"][L])

                    # 产生命名大礼包
                    tempNTG = aoligei.nameStrGen(vID, vfName, vsName, vtName, vRanNum)

                    # tempNTG[0]是Error小包，如果该小包中产生了报错信息，则直接离开（if/else）当前行的执行，并将信息传入GoLog待打印
                    if len(tempNTG[0]) != 0:
                        LOG.warning("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_NamingErrorCheck_FAIL"][L])
                        LOG.warning(tempNTG[0])
                    # 否则如果tempNTG[0]为空，则开始执行Create WAV，在本地产生wav文件
                    else:
                        LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_NamingErrorCheck_PASS"][L])
                        # 生成wav
                        wavErrorLog = aoligei.wavGen(vID, vfName, vsName, vtName, vRanNum)

                        # 再次确认命名的合法性（wavGen方法中，除了自己ADVCopy方法的Error之外，也包含return了nameStrGen的[0]号位的Error信息）
                        if len(wavErrorLog) != 0:
                            LOG.warning("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_WAVCreate_NOTGOOD"][L])
                        # 如果wavGen方法没有报错，则意味着wav已顺利生成，随即打印成功信息
                        else:
                            LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_WAVCreate_PASS"][L])

                            # 到这一步为止，可以开始执行Waapi GO了
                            # 这一步，是根据关键词Type类型，自动选择调用哪一个Func！“info.json”文件里的配置参与了PickFunc方法
                            LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_StructureTypeCheck"][L])
                            WaapiGoType = KeyInfoDict["Data_KeyInfo"][vfName]["Structure_Type"]
                            try:
                                # WAPPI GO执行，成功后，然后打印成功信息
                                LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_OnGoing"][L])
                                getattr(aoligei, WaapiGoType)(vID, vfName, vsName, vtName, vRanNum)
                                LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_DONE"][L])

                                # 将EventStr和Lock写入TABLEALL
                                try:
                                    if WaapiGoType != "type2d_gun":
                                        if tempNTG[1][1][-3:] == "_LP":  # 如果命名中标注了循环，则需要再新增一行，补充Stop事件的Event信息
                                            # 写Play
                                            self.WriteCell_ForTable(r, key["Header_EventName"], vID, "EventName", tempNTG[1][2])
                                            # 在表格底部新增一行（写StopEvent、Notes、Lock，同时给Stop行更新Wwise里的Notes）
                                            NewLineNum = self.Action_AddLine_AtBottom()
                                            # 给新行写StopEvent
                                            self.WriteCell_ForTable(NewLineNum, key["Header_EventName"], vID, "EventName",
                                                                    "Stop_" + tempNTG[1][1])
                                            # 给新行写StopNotes
                                            vNotes = self.tableWidget_SoundSheet.item(r, key["Header_Notes"]).text()
                                            self.WriteCell_ForTable(NewLineNum, key["Header_Notes"], vID, "Notes", vNotes)
                                            # 给Stop新行更新Wwise里的Notes
                                            vEvent_Stop = self.tableWidget_SoundSheet.item(NewLineNum,
                                                                                           key["Header_EventName"]).text()
                                            vID_Stop = self.tableWidget_SoundSheet.item(NewLineNum, key["Header_ID"]).text()
                                            # GUID_Stop = aoligei.getSingleEventGUIDFromEventWWU(vEvent_Stop)
                                            GUID_Stop = aoligei.get_EventGUID_From_EventName(vEvent_Stop)
                                            # if len(GUID_Stop) != 0:
                                            if GUID_Stop is not None and len(GUID_Stop) != 0:
                                                NewNotes = "#" + str(vID_Stop) + "#," + str(vNotes)
                                                aoligei.setNotesForGUID(GUID_Stop, NewNotes)
                                            # 给新行写StopLock
                                            self.WriteCell_ForTable(NewLineNum, key["Header_Lock"], vID, "Lock",
                                                                    key["LockedStrValue"])
                                        else:
                                            # 写Play
                                            self.WriteCell_ForTable(r, key["Header_EventName"], vID, "EventName", tempNTG[1][2])
                                    else:
                                        # 写Play
                                        self.WriteCell_ForTable(r, key["Header_EventName"], vID, "EventName", tempNTG[1][2])

                                        # 在表格底部新增一行（写LoopEvent、Notes、Lock，同时给Stop行更新Wwise里的Notes）
                                        NewLineNum = self.Action_AddLine_AtBottom()
                                        # 给新行写LoopEvent
                                        self.WriteCell_ForTable(NewLineNum, key["Header_EventName"], vID, "EventName",
                                                                "Play_" + tempNTG[1][1] + "_LP")
                                        # 给新行写LoopNotes
                                        vNotes = self.tableWidget_SoundSheet.item(r, key["Header_Notes"]).text() + "-Loop"
                                        self.WriteCell_ForTable(NewLineNum, key["Header_Notes"], vID, "Notes", vNotes)
                                        # 给Loop新行更新Wwise里的Notes
                                        vEvent_Stop = self.tableWidget_SoundSheet.item(NewLineNum, key["Header_EventName"]).text()
                                        vID_Stop = self.tableWidget_SoundSheet.item(NewLineNum, key["Header_ID"]).text()
                                        # GUID_Stop = aoligei.getSingleEventGUIDFromEventWWU(vEvent_Stop)
                                        GUID_Stop = aoligei.get_EventGUID_From_EventName(vEvent_Stop)
                                        # if len(GUID_Stop) != 0:
                                        if GUID_Stop is not None and len(GUID_Stop) != 0:
                                            NewNotes = "#" + str(vID_Stop) + "#," + str(vNotes)
                                            aoligei.setNotesForGUID(GUID_Stop, NewNotes)
                                        # 给新行写StopLock
                                        self.WriteCell_ForTable(NewLineNum, key["Header_Lock"], vID, "Lock",
                                                                key["LockedStrValue"])

                                        # 在表格底部新增一行（写StopEvent、Notes、Lock，同时给Stop行更新Wwise里的Notes）
                                        NewLineNum = self.Action_AddLine_AtBottom()
                                        # 给新行写StopEvent
                                        self.WriteCell_ForTable(NewLineNum, key["Header_EventName"], vID, "EventName", "Stop_" + tempNTG[1][1] + "_LP")
                                        # 给新行写StopNotes
                                        vNotes = self.tableWidget_SoundSheet.item(r, key["Header_Notes"]).text() + "-Stop Loop"
                                        self.WriteCell_ForTable(NewLineNum, key["Header_Notes"], vID, "Notes", vNotes)
                                        # 给Stop新行更新Wwise里的Notes
                                        vEvent_Stop = self.tableWidget_SoundSheet.item(NewLineNum, key["Header_EventName"]).text()
                                        vID_Stop = self.tableWidget_SoundSheet.item(NewLineNum, key["Header_ID"]).text()
                                        # GUID_Stop = aoligei.getSingleEventGUIDFromEventWWU(vEvent_Stop)
                                        GUID_Stop = aoligei.get_EventGUID_From_EventName(vEvent_Stop)
                                        # if len(GUID_Stop) != 0:
                                        if GUID_Stop is not None and len(GUID_Stop) != 0:
                                            NewNotes = "#" + str(vID_Stop) + "#," + str(vNotes)
                                            aoligei.setNotesForGUID(GUID_Stop, NewNotes)
                                        # 给新行写StopLock
                                        self.WriteCell_ForTable(NewLineNum, key["Header_Lock"], vID, "Lock", key["LockedStrValue"])

                                    # 给Event更新Notes
                                    vEvent = self.tableWidget_SoundSheet.item(r, key["Header_EventName"]).text()
                                    vNotes = self.tableWidget_SoundSheet.item(r, key["Header_Notes"]).text()
                                    # GUID = aoligei.getSingleEventGUIDFromEventWWU(vEvent)
                                    GUID = aoligei.get_EventGUID_From_EventName(vEvent)
                                    # if len(GUID) != 0:
                                    if GUID is not None and len(GUID) != 0:
                                        NewNotes = "#" + str(vID) + "#," + str(vNotes)
                                        aoligei.setNotesForGUID(GUID, NewNotes)

                                        # 给新的ObjectRef更新Notes
                                        NewObjectRefCup = aoligei.getObjectRefFromEventStr(vEvent)
                                        if len(NewObjectRefCup) != 0:
                                            NewObjectRefGUID = list(NewObjectRefCup.keys())
                                            for i in NewObjectRefGUID:
                                                aoligei.setNotesForGUID(i, NewNotes)

                                    # 如果AutoGenerateBanks没有选中，说明在这一步就可以写入Lock，否则Lock写入要留到下一轮
                                    if key["AutoGenerateBanks"] != "True":
                                        self.WriteCell_ForTable(r, key["Header_Lock"], vID, "Lock", key["LockedStrValue"])

                                    # 更新进度条信息
                                    CurStep = index + 1
                                    TotalStep = len(rowList)
                                    self.ShowProgress([CurStep, TotalStep])
                                    LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_WriteTable_DONE"][L])
                                except:
                                    traceback.print_exc()
                                    LOG.warning(lan["LOG_SM_def_WaapiGo_WriteTable_FAIL"][L])
                                    continue
                            except:
                                traceback.print_exc()
                                LOG.warning("< Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_FAIL"][L])
                                continue

                # 如果自动打Bank选项开启，则自动进行下一步，否则跳过
                if key["AutoGenerateBanks"] == "True":
                    LOG.info(lan["LOG_WG_HalfFINISHED"][L])

                    # 开始打Bank
                    CollectChangedBanks = []
                    for r in rowList:
                        Lock = self.tableWidget_SoundSheet.item(r, key["Header_Lock"]).text()
                        if Lock != "1" and Lock != 1:
                            vEvent = self.tableWidget_SoundSheet.item(r, key["Header_EventName"]).text()
                            bnkList = aoligei.GetBNKNameFromEventStr(vEvent)
                            if len(bnkList) != 0:
                                for i in bnkList:
                                    CollectChangedBanks.append(i)

                    # Waapi预备标记
                    AutoGenerateSoundBankFlag = True
                    if len(CollectChangedBanks) != 0:
                        for i in CollectChangedBanks:
                            WaapiStatusResult = aoligei.GenerateOneBNK(i)
                            if WaapiStatusResult is False:
                                AutoGenerateSoundBankFlag = False
                                break

                    if AutoGenerateSoundBankFlag is False:
                        for r in rowList:
                            # LOG.info(lan["LOG_WG_ProcessingLine"][L] + str(r + 1) + "  ********************************")
                            vID = self.tableWidget_SoundSheet.item(r, key["Header_ID"]).text()
                            self.WriteCell_ForTable(r, key["Header_Lock"], vID, "Lock", key["LockedStrValue"])
                    else:
                        # 将Bank信息写入XLSX
                        # 统计List
                        List_FilledBankInfo = []
                        List_SkippedInfo = []
                        List_NoEventInfo = []
                        List_CanNotFindBankInfo = []
                        List_MoreThanOneBankInfo = []

                        # 如果行号List不为空，开始WAAPIGO逐行循环执行
                        for r in rowList:
                            LOG.info(lan["LOG_WG_ProcessingLine"][L] + str(r + 1))

                            # 从当前行的每一个单元格中取值
                            vID = self.tableWidget_SoundSheet.item(r, key["Header_ID"]).text()
                            vEvent = self.tableWidget_SoundSheet.item(r, key["Header_EventName"]).text()
                            vBank = self.tableWidget_SoundSheet.item(r, key["Header_BankName"]).text()

                            if vEvent == "None":
                                vEvent = ""
                            if vBank == "None":
                                vBank = ""

                            if len(vEvent) == 0:
                                List_NoEventInfo.append(str(r + 1))
                                LOG.warning(lan["LOG_SM_def_FillBankInfo_NOEVENTINFO"][L])
                            else:
                                BankList = LocateEventBankLocation(vEvent,
                                                                   LocalInfoDict["ActualGeneratedSoundBankPathOfOnePlatform"])
                                if len(vBank) == 0:
                                    # 判断Bank结果是否合法
                                    if len(BankList) == 1:
                                        self.WriteCell_ForTable(r, key["Header_BankName"], vID, "BankName", BankList[0])
                                        List_FilledBankInfo.append(str(r + 1))
                                        LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_FillBankInfo_FINISHED"][L])
                                    elif len(BankList) == 0:
                                        List_CanNotFindBankInfo.append(str(r + 1))
                                        LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_FillBankInfo_ORPHAN"][L])
                                    elif len(BankList) > 1:
                                        List_MoreThanOneBankInfo.append(str(r + 1))
                                        LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_FillBankInfo_MORETHANONE"][L])
                                else:
                                    List_SkippedInfo.append(str(r + 1))
                                    LOG.warning(lan["LOG_SM_def_FillBankInfo_SKIPPED"][L])

                            self.WriteCell_ForTable(r, key["Header_Lock"], vID, "Lock", key["LockedStrValue"])

                        LOG.info(lan["LOG_WG_AutoGenerateBankReport"][L])
                        if len(List_FilledBankInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_FilledBankInfo"][L])
                            LOG.info(List_FilledBankInfo)
                        if len(List_SkippedInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_SkippedInfo"][L])
                            LOG.info(List_SkippedInfo)
                        if len(List_NoEventInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_NoEventInfo"][L])
                            LOG.info(List_NoEventInfo)
                        if len(List_CanNotFindBankInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_CanNotFindBankInfo"][L])
                            LOG.info(List_CanNotFindBankInfo)
                        if len(List_MoreThanOneBankInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_MoreThanOneBankInfo"][L])
                            LOG.info(List_MoreThanOneBankInfo)

                # 整体保存（如果表格数据量很大，还是放在最后保存吧。等找到快速保存的办法，再改为逐步保存）
                SaveJson(SoundListDict, global_curWwisePath + "\\info.json")
                LOG.info(lan["LOG_WG_ALLFINISHED"][L])

                # 手动断联
                aoligei.__del__()
                LOG.debug("[SW实例清除***][Main][GO]")
        except:
            traceback.print_exc()

    def ExpandSwitch(self, validRowList):
        try:
            # 获取选中的行数
            rowList = validRowList
            # rowList = self.GetSelectedRows()
            if len(rowList) != 0:  # 如果有被选中的行
                aoligei = SimpleWaapi()
                # 获取所有的ID
                AllIDList = []
                for row in range(self.tableWidget_SoundSheet.rowCount()):
                    AllIDList.append(self.tableWidget_SoundSheet.item(row, key["Header_ID"]).text())

                for r, index in zip(rowList, range(len(rowList))):
                    vID = self.tableWidget_SoundSheet.item(r, key["Header_ID"]).text()
                    vNotes = self.tableWidget_SoundSheet.item(r, key["Header_Notes"]).text()
                    vEvent = self.tableWidget_SoundSheet.item(r, key["Header_EventName"]).text()
                    vBank = self.tableWidget_SoundSheet.item(r, key["Header_BankName"]).text()
                    vfName = self.tableWidget_SoundSheet.item(r, key["Header_KeyStr"]).text()
                    vsName = self.tableWidget_SoundSheet.item(r, key["Header_BodyStr"]).text()
                    vtName = self.tableWidget_SoundSheet.item(r, key["Header_TailStr"]).text()
                    vRanNum = self.tableWidget_SoundSheet.item(r, key["Header_RDM"]).text()
                    Lock = self.tableWidget_SoundSheet.item(r, key["Header_Lock"]).text()

                    # 先确认ID是否有非法的，有的话跳过循环！
                    duplicatedIDCheck = self.SafetyCheck_ID(vID, AllIDList)
                    if len(duplicatedIDCheck) != 0:
                        LOG.warning(str(duplicatedIDCheck) + lan["LOG_SM_def_WaapiGo_DuplicatedIDPreCheck"][L])
                        break

                    # 确认当前行的Lock值，如果已被标记过，则跳过（continue）当前行的执行，并将Log传入GoLog待打印
                    if str(Lock) == "0" or str(Lock) == key["LockedStrValue"]:
                        LOG.warning("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_LockCheck_SKIP"][L])
                        continue

                    # 确认fName是否合法，否则直接跳过
                    if vfName not in list(KeyInfoDict["Data_KeyInfo"].keys()):
                        LOG.warning("Line" + str(r + 1) + ": " + lan["LOG_NSG_def_nameStrGen_fnameInvalid_Skip"][L])
                        continue

                    # 为type2d_gun临时添加判断，临时阻止ExpandSwitch、Mirror、ReCreate功能
                    KEYSTRDICT = KeyInfoDict["Data_KeyInfo"].get(vfName, "!@#")
                    if KEYSTRDICT != "!@#":
                        if KEYSTRDICT["Structure_Type"] == "type2d_gun":
                            LOG.warning("Line" + str(r + 1) + ": " + lan["LOG_NSG_def_nameStrGen_type2dgunNotAvalible_Skip"][L])
                            continue

                    # 如果上一步Lock检查未被跳过，则继续执行Create NameStr，产生字符串大包装
                    LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_LockCheck_PASS"][L])

                    if len(vEvent) != 0:
                        # 判断Event里是否包含KeyName字符串，确认从属关系！如果不包含，提示跳过！
                        if vfName not in vEvent:
                            LOG.warning("Line" + str(r + 1) + ": " +
                                  lan["LOG_SM_def_ExpandSwitch_EventStrNotContainerKeyName_Skipped"][L])
                            continue

                        # 判断Event是否可能不是“Play”类型
                        if vEvent.find("Play_") == -1:
                            LOG.warning(
                                "Line" + str(r + 1) + ": " + lan["LOG_SM_def_ExpandSwitch_NotPlayEvent_Skipped"][L])
                            continue

                        # 判断Event是否存在于WWU，0代表没找到，1代表找到了。找到的话再继续向后执行。
                        # existResult = CheckIfEventExistFromEventWWU(vEvent)
                        existResult = aoligei.get_EventGUID_From_EventName(vEvent)

                        if existResult is None:
                            LOG.warning("Line" + str(r + 1) + ": " + lan["LOG_SM_def_ExpandSwitch_Skipped"][L])
                            continue
                        else:
                            # info.json Path预检查，如果不通过，直接终止循环
                            pathCheckLog = aoligei.PathsCheckLog()

                            if len(pathCheckLog) != 0:
                                for log in pathCheckLog:
                                    LOG.debug(log)
                                LOG.warning(lan["LOG_SM_def_WaapiGo_InfoPathPreCheck"][L])
                                aoligei.__del__()
                                break

                            # 单纯检查命名安全，不合法的行直接跳过（暂不检查是否已存在）
                            # 首先确认fName是否合法，否则直接跳过
                            if vfName not in list(KeyInfoDict["Data_KeyInfo"].keys()):
                                LOG.warning("Line" + str(r + 1) + ": " + lan["LOG_NSG_def_nameStrGen_fnameInvalid_Skip"][L])
                                continue

                            # 在这里检查typet，如果是的话，产生命名大礼包和生成wav用WaapiGo内置方法
                            tempNameError = aoligei.nameStrGenWithoutCheckDuplicate(vID, vfName, vsName, vtName, vRanNum)

                            # tempNameError[0]是Error小包，如果该小包中产生了报错信息，则直接跳过当前行的执行，并将信息传入GoLog待打印
                            if len(tempNameError[0]) != 0:
                                LOG.warning("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_NamingErrorCheck_FAIL"][L])
                            else:
                                # 统计当前Event的ObjectRef数量、GUID、名称（如果ObjectRef大于1，log提示手动修改后，跳过）
                                ObjectRefResult = aoligei.getObjectRefFromEventStr(vEvent)
                                LOG.debug(ObjectRefResult)

                                # 如果Event里面没东西，就直接搁置当前Event
                                if len(ObjectRefResult) == 0:
                                    LOG.warning("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_NoObjectRef_skip"][L])
                                    continue
                                # 如果Event里的ObjectRef数量大于1，跳过，不执行本行
                                elif len(ObjectRefResult) > 1:
                                    LOG.warning("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_MoreThanOneObjectRef"][L])
                                    continue
                                else:
                                    ObjectRefStr = list(ObjectRefResult.values())[0]

                                    # 检查ObjectRef里是否包含KeyName字符！
                                    if vfName not in ObjectRefStr:
                                        LOG.warning("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_ObjectRefHasNoKeyNameStr"][L])
                                        continue
                                    else:
                                        LOG.info("\nLine" + str(r + 1) + lan["LOG_SM_def_WaapiGo_FoundOneObjectRef"][L])

                                    # 如果上一步Lock检查未被跳过，则开始执行ObejctRef分析！
                                    ObjectRefGUID = list(ObjectRefResult.keys())[0]
                                    LOG.debug(ObjectRefGUID)
                                    NewGUIDPaths = aoligei.CreateAndGetNewPathsOfNewGUIDs(ObjectRefGUID)
                                    LOG.debug(NewGUIDPaths)

                                    if len(NewGUIDPaths) == 0:
                                        LOG.warning(lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_NoNeedExpandSwitch"][L])
                                    else:
                                        LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_NewGUIDCreated"][L])
                                        NewPair = aoligei.GetNewInfoForIndiExpandSwitchFunc(vfName, vRanNum, NewGUIDPaths)

                                        if len(NewPair) != 0:
                                            LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_GetTargetPair"][L])
                                            wavGenError = wavGenForExpandSwitchFunc(NewPair, vfName)
                                            LOG.debug(wavGenError)
                                            if len(wavGenError) != 0:
                                                LOG.warning(lan["LOG_SM_def_WaapiGo_wavGenForExpandSwitchFunc"][L])
                                            else:
                                                LOG.info(
                                                    "Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_WAVCreate_PASS"][
                                                        L])
                                                # 到这一步为止，可以开始执行Waapi GO, 批量导入WAV了
                                                LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_OnGoing"][L])
                                                try:
                                                    aoligei.ImportNewObjsForExpandSwitchFunc(vID, vfName,
                                                                                             vsName, vtName,
                                                                                             vRanNum, NewPair)
                                                    if key["AutoGenerateBanks"] != "True":
                                                        self.WriteCell_ForTable(r, key["Header_Lock"], vID, "Lock",
                                                                                key["LockedStrValue"])

                                                    # 更新进度条信息
                                                    CurStep = index + 1
                                                    TotalStep = len(rowList)
                                                    self.ShowProgress([CurStep, TotalStep])
                                                    LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_DONE"][L])
                                                except:
                                                    traceback.print_exc()
                                                    LOG.warning("< Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_FAIL"][L])
                                                    continue

                # 如果自动打Bank选项开启，则自动进行下一步，否则跳过
                if key["AutoGenerateBanks"] == "True":
                    LOG.info(lan["LOG_WG_HalfFINISHED"][L])

                    # 开始打Bank
                    CollectChangedBanks = []
                    for r in rowList:
                        Lock = self.tableWidget_SoundSheet.item(r, key["Header_Lock"]).text()
                        if Lock != "1" and Lock != 1:
                            vEvent = self.tableWidget_SoundSheet.item(r, key["Header_EventName"]).text()
                            bnkList = aoligei.GetBNKNameFromEventStr(vEvent)
                            if len(bnkList) != 0:
                                for i in bnkList:
                                    CollectChangedBanks.append(i)

                    # Waapi预备标记
                    AutoGenerateSoundBankFlag = True
                    if len(CollectChangedBanks) != 0:
                        for i in CollectChangedBanks:
                            WaapiStatusResult = aoligei.GenerateOneBNK(i)
                            if WaapiStatusResult is False:
                                AutoGenerateSoundBankFlag = False
                                break

                    if AutoGenerateSoundBankFlag is False:
                        for r in rowList:
                            # LOG.info(lan["LOG_WG_ProcessingLine"][L] + str(r + 1) + "  ********************************")
                            vID = self.tableWidget_SoundSheet.item(r, key["Header_ID"]).text()
                            self.WriteCell_ForTable(r, key["Header_Lock"], vID, "Lock", key["LockedStrValue"])
                    else:
                        # 将Bank信息写入XLSX
                        # 统计List
                        List_FilledBankInfo = []
                        List_SkippedInfo = []
                        List_NoEventInfo = []
                        List_CanNotFindBankInfo = []
                        List_MoreThanOneBankInfo = []

                        # 如果行号List不为空，开始WAAPIGO逐行循环执行
                        for r in rowList:
                            LOG.info(lan["LOG_WG_ProcessingLine"][L] + str(r + 1))

                            # 从当前行的每一个单元格中取值
                            vID = self.tableWidget_SoundSheet.item(r, key["Header_ID"]).text()
                            vEvent = self.tableWidget_SoundSheet.item(r, key["Header_EventName"]).text()
                            vBank = self.tableWidget_SoundSheet.item(r, key["Header_BankName"]).text()

                            if vEvent == "None":
                                vEvent = ""
                            if vBank == "None":
                                vBank = ""

                            if len(vEvent) == 0:
                                List_NoEventInfo.append(str(r + 1))
                                LOG.warning(lan["LOG_SM_def_FillBankInfo_NOEVENTINFO"][L])
                            else:
                                BankList = LocateEventBankLocation(vEvent,
                                                                   LocalInfoDict["ActualGeneratedSoundBankPathOfOnePlatform"])

                                # 判断Bank结果是否合法
                                if len(BankList) == 1:
                                    self.WriteCell_ForTable(r, key["Header_BankName"], vID, "BankName", BankList[0])
                                    List_FilledBankInfo.append(str(r + 1))
                                    LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_FillBankInfo_FINISHED"][L])
                                elif len(BankList) == 0:
                                    List_CanNotFindBankInfo.append(str(r + 1))
                                    LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_FillBankInfo_ORPHAN"][L])
                                elif len(BankList) > 1:
                                    List_MoreThanOneBankInfo.append(str(r + 1))
                                    LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_FillBankInfo_MORETHANONE"][L])
                                # else:
                                #     List_SkippedInfo.append(str(r))
                                #     LOG.info(lan["LOG_SM_def_FillBankInfo_SKIPPED"][L])

                            self.WriteCell_ForTable(r, key["Header_Lock"], vID, "Lock", key["LockedStrValue"])

                        LOG.info(lan["LOG_WG_AutoGenerateBankReport"][L])
                        if len(List_FilledBankInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_FilledBankInfo"][L])
                            LOG.info(List_FilledBankInfo)
                        if len(List_SkippedInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_SkippedInfo"][L])
                            LOG.info(List_SkippedInfo)
                        if len(List_NoEventInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_NoEventInfo"][L])
                            LOG.info(List_NoEventInfo)
                        if len(List_CanNotFindBankInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_CanNotFindBankInfo"][L])
                            LOG.info(List_CanNotFindBankInfo)
                        if len(List_MoreThanOneBankInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_MoreThanOneBankInfo"][L])
                            LOG.info(List_MoreThanOneBankInfo)

                # 整体保存（如果表格数据量很大，还是放在最后保存吧。等找到快速保存的办法，再改为逐步保存）
                SaveJson(SoundListDict, global_curWwiseInfoJson)
                LOG.info(lan["LOG_WG_ALLFINISHED"][L])

                # 手动断联
                aoligei.__del__()
        except:
            traceback.print_exc()

    def MirrorData(self, validRowList):
        try:
            # 获取选中的行数
            # rowList = self.GetSelectedRows()
            rowList = validRowList
            if len(rowList) != 0:  # 如果有被选中的行
                LOG.info(lan["LOG_MirrorStarted"][L])
                aoligei = SimpleWaapi()
                # 获取所有的ID
                AllIDList = []
                for row in range(self.tableWidget_SoundSheet.rowCount()):
                    AllIDList.append(self.tableWidget_SoundSheet.item(row, key["Header_ID"]).text())

                for r, index in zip(rowList, range(len(rowList))):
                    vID = self.tableWidget_SoundSheet.item(r, key["Header_ID"]).text()
                    vfName = self.tableWidget_SoundSheet.item(r, key["Header_KeyStr"]).text()
                    vsName = self.tableWidget_SoundSheet.item(r, key["Header_BodyStr"]).text()
                    vtName = self.tableWidget_SoundSheet.item(r, key["Header_TailStr"]).text()
                    vRanNum = self.tableWidget_SoundSheet.item(r, key["Header_RDM"]).text()
                    vLock = self.tableWidget_SoundSheet.item(r, key["Header_Lock"]).text()
                    vMirrorID = self.tableWidget_SoundSheet.item(r, key["Header_MirrorFrom"]).text()

                    # 为type2d_gun临时添加判断，临时阻止ExpandSwitch、Mirror、ReCreate功能
                    KEYSTRDICT = KeyInfoDict["Data_KeyInfo"].get(vfName, "!@#")
                    if KEYSTRDICT != "!@#":
                        if KEYSTRDICT["Structure_Type"] == "type2d_gun":
                            LOG.warning("Line" + str(r + 1) + ": " + lan["LOG_NSG_def_nameStrGen_type2dgunNotAvalible_Skip"][L])
                            continue

                    # 寻找K列有数据的行，检查该行安全锁是否解锁
                    if vLock == "1":
                        LOG.warning(lan["LOG_SM_def_List_SkippedInfo"][L] + str(r + 1))
                        continue
                    if vMirrorID == "None" and vLock != "1":
                        vMirrorID = ""
                    if len(vMirrorID) == 0:
                        continue
                    else:
                        # 检查vMirrorID是否和vID重复
                        if vMirrorID == vID:
                            LOG.warning(lan["LOG_SM_def_MirrorData_InvalidMirrorID_SameAsCurrentID"][L])
                            continue

                        # 检查vMirrorID是否存在
                        if vMirrorID not in AllIDList:
                            LOG.warning(lan["LOG_SM_def_MirrorData_InvalidMirrorID_NotExist"][L])
                            continue

                        # 检查vMirrorID是否全场唯一
                        count = 0
                        for i in AllIDList:
                            if i == vMirrorID:
                                count += 1
                        if count != 1:
                            LOG.warning(lan["LOG_SM_def_MirrorData_InvalidMirrorID_NotOnlyOne"][L])
                            continue

                        # 定位给到目标ID的行，检查Event下属WAV，整理所有WAV路径
                        Row_TargetID = ""
                        for roww in range(self.tableWidget_SoundSheet.rowCount()):
                            eachID = self.tableWidget_SoundSheet.item(roww, key["Header_ID"]).text()
                            if eachID == vMirrorID:
                                Row_TargetID = str(roww)
                                LOG.info(lan["LOG_SM_def_MirrorData_LocateTargetIDRow"][L] + str(roww + 1))
                                break
                        if len(Row_TargetID) == 0:
                            LOG.warning(lan["LOG_SM_def_MirrorData_CanNotLocateTargetIDRow"][L])
                            continue
                        else:
                            Row_TargetID = int(Row_TargetID)
                            tfName = self.tableWidget_SoundSheet.item(Row_TargetID, key["Header_KeyStr"]).text()
                            tRanNum = self.tableWidget_SoundSheet.item(Row_TargetID, key["Header_RDM"]).text()
                            tEvent = self.tableWidget_SoundSheet.item(Row_TargetID, key["Header_EventName"]).text()

                            # 先检查以上四个字符串是否合法
                            if vfName not in list(KeyInfoDict["Data_KeyInfo"].keys()):
                                LOG.warning(lan["LOG_Mirror_InvalidString"][L] + str(vfName) + " ----> " + str(r + 1))
                            elif tfName not in list(KeyInfoDict["Data_KeyInfo"].keys()):
                                LOG.warning(lan["LOG_Mirror_InvalidString"][L] + str(tfName) + " ----> " + str(Row_TargetID + 1))
                            elif vRanNum not in key["validRanNum"]:
                                LOG.warning(lan["LOG_Mirror_InvalidString"][L] + str(vRanNum) + " ----> " + str(r + 1))
                            elif tRanNum not in key["validRanNum"]:
                                LOG.warning(lan["LOG_Mirror_InvalidString"][L] + str(tRanNum) + " ----> " + str(Row_TargetID + 1))
                            else:
                                # 先对比：两个ID对应内容的type模板一致性
                                if KeyInfoDict["Data_KeyInfo"][vfName]["Structure_Type"] in ["type2d_vo", "type1d_vo"] or \
                                        KeyInfoDict["Data_KeyInfo"][tfName]["Structure_Type"] in ["type2d_vo", "type1d_vo"]:
                                    LOG.warning(lan["LOG_Mirror_CanNotSupportVoiceType"][L])
                                else:
                                    if KeyInfoDict["Data_KeyInfo"][vfName]["Structure_Type"] != \
                                            KeyInfoDict["Data_KeyInfo"][tfName]["Structure_Type"]:
                                        LOG.warning(lan["LOG_Mirror_DifferentTypeWarning"][L])
                                    else:
                                        # 先对比：如果是type3d类型，对比随机数数量; 如果是typet类型，对比引用模板的一致性
                                        if KeyInfoDict["Data_KeyInfo"][vfName]["Structure_Type"] == \
                                                KeyInfoDict["Data_KeyInfo"][tfName][
                                                    "Structure_Type"] == "type3d" and vRanNum != tRanNum:
                                            LOG.warning(lan["LOG_Mirror_Differenttype3dRDM"][L])
                                        elif KeyInfoDict["Data_KeyInfo"][vfName]["Structure_Type"] == \
                                                KeyInfoDict["Data_KeyInfo"][tfName]["Structure_Type"] == "typet" and \
                                                KeyInfoDict["Data_KeyInfo"][vfName]["Path_InWwise_UserDefinedTemplate"] != \
                                                KeyInfoDict["Data_KeyInfo"][tfName]["Path_InWwise_UserDefinedTemplate"]:
                                            LOG.warning(lan["LOG_Mirror_DifferenttypetTemplate"][L])
                                        else:
                                            ObjectRefsDict = aoligei.getObjectRefFromEventStr(tEvent)
                                            ObjectRefs = list(ObjectRefsDict.keys())
                                            currentWwiseOriginalPath = aoligei.get_CurrentWwiseSession_OriginalsFolderPath()
                                            TotalWAVPathList = []
                                            for i in ObjectRefs:
                                                wavPathList = aoligei.getWAVPathsFromObjectRefGUID(i)
                                                for j in wavPathList:
                                                    TotalWAVPathList.append(currentWwiseOriginalPath + "\\" + j)

                                            # 检查TotalWAVPathList是否为空
                                            if len(TotalWAVPathList) == 0:
                                                LOG.error(lan["LOG_CanNotFindMirrorRequestWAV"][L])
                                            else:
                                                # 再检查是否有静音替条，静音替条的数量是否只是局部
                                                SilenceCheckLog = []
                                                for wav in TotalWAVPathList:
                                                    dBFSResult = GetWAVMAXdBFS(wav)
                                                    if dBFSResult == "-inf":
                                                        SilenceCheckLog.append(wav)
                                                if len(SilenceCheckLog) == len(TotalWAVPathList):
                                                    LOG.warning(lan["LOG_Mirror_TargetWAVAreAllSilence"][L])
                                                    LOG.warning(SilenceCheckLog)
                                                else:
                                                    # 检查当前行的命名是否合法（是否全场无重复）
                                                    LOG.info(lan["LOG_WG_ProcessingLine"][L] + str(r + 1))

                                                    # 确认ID是否有非法的，有的话跳过循环！
                                                    duplicatedIDCheck = self.SafetyCheck_ID(vID, AllIDList)
                                                    if len(duplicatedIDCheck) != 0:
                                                        LOG.warning(str(duplicatedIDCheck) +
                                                              lan["LOG_SM_def_WaapiGo_DuplicatedIDPreCheck"][L])
                                                        break

                                                    # 确认当前行的Lock值，如果已被标记过，则跳过（continue）当前行的执行，并将Log传入GoLog待打印
                                                    if str(vLock) == "0" or str(vLock) == key["LockedStrValue"]:
                                                        LOG.warning(
                                                            "Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_LockCheck_SKIP"][
                                                                L])
                                                        continue

                                                    # 确认fName是否合法，否则直接跳过
                                                    if vfName not in list(KeyInfoDict["Data_KeyInfo"].keys()):
                                                        LOG.warning("Line" + str(r + 1) + ": " +
                                                              lan["LOG_NSG_def_nameStrGen_fnameInvalid_Skip"][L])
                                                        continue

                                                    # 如果上一步Lock检查未被跳过，则继续执行Create NameStr，产生字符串大包装
                                                    LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_LockCheck_PASS"][L])

                                                    # 产生命名大礼包
                                                    tempNTG = aoligei.nameStrGen(vID, vfName, vsName, vtName, vRanNum)

                                                    # tempNTG[0]是Error小包，如果该小包中产生了报错信息，则直接离开（if/else）当前行的执行，并将信息传入GoLog待打印
                                                    if len(tempNTG[0]) != 0:
                                                        LOG.warning("Line" + str(r + 1) +
                                                              lan["LOG_SM_def_WaapiGo_NamingErrorCheck_FAIL"][L])
                                                    else:
                                                        # 否则如果tempNTG[0]为空，则开始对比WAV数量，在本地产生镜像wav文件
                                                        LOG.info("Line" + str(r + 1) +
                                                              lan["LOG_SM_def_WaapiGo_NamingErrorCheck_PASS"][L])
                                                        flatList = [x for x in flatten(tempNTG[2])]
                                                        # LOG.debug(flatList)
                                                        # LOG.debug(TotalWAVPathList)
                                                        countFlag = 0

                                                        ADVTotalLog = []
                                                        for newWAVPath in flatList:
                                                            # 先判断是SFX还是Voices关键字
                                                            tempStr = TotalWAVPathList[0]
                                                            tempStrKey = tempStr.replace(currentWwiseOriginalPath + "\\",
                                                                                         "")[0:3]
                                                            # LOG.debug(tempStrKey)
                                                            # LOG.debug(oldWAVPath)
                                                            if tempStrKey != "SFX":
                                                                LOG.warning(lan["LOG_Mirror_NotSupportVOType"][L])
                                                            else:
                                                                TargetPathStr = currentWwiseOriginalPath + "\\SFX\\"
                                                                ADVErrorLog = ADVQuickCopy(TotalWAVPathList[countFlag],
                                                                                           TargetPathStr,
                                                                                           newWAVPath + ".wav")
                                                                if len(ADVErrorLog) != 0:
                                                                    ADVTotalLog.append("Error")
                                                                else:
                                                                    LOG.info(TotalWAVPathList[
                                                                              countFlag] + " -----> " + TargetPathStr + newWAVPath + ".wav" + "\n")

                                                                countFlag += 1
                                                                if countFlag == len(TotalWAVPathList):
                                                                    countFlag = 0

                                                        if len(ADVTotalLog) != 0:
                                                            LOG.warning("Line" + str(r + 1) +
                                                                  lan["LOG_SM_def_WaapiGo_WAVCreate_NOTGOOD"][L])
                                                            # 如果wavGen方法没有报错，则意味着wav已顺利生成，随即打印成功信息
                                                        else:
                                                            LOG.info("Line" + str(r + 1) +
                                                                  lan["LOG_SM_def_WaapiGo_WAVCreate_PASS"][L])

                                                            # 到这一步为止，可以开始执行Waapi GO了
                                                            # 这一步，是根据关键词Type类型，自动选择调用哪一个Func！“info.json”文件里的配置参与了PickFunc方法
                                                            LOG.info("Line" + str(r + 1) +
                                                                  lan["LOG_SM_def_WaapiGo_StructureTypeCheck"][L])
                                                            WaapiGoType = KeyInfoDict["Data_KeyInfo"][vfName][
                                                                "Structure_Type"]
                                                            try:
                                                                # WAPPI GO执行，成功后，然后打印成功信息
                                                                LOG.info(
                                                                    "Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_OnGoing"][
                                                                        L])
                                                                getattr(aoligei, WaapiGoType)(vID, vfName, vsName, vtName,
                                                                                              vRanNum)
                                                                LOG.info(
                                                                    "Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_DONE"][L])

                                                                # 将EventStr和Lock写入TABLEALL
                                                                try:
                                                                    if tempNTG[1][1][
                                                                       -3:] == "_LP":  # 如果命名中标注了循环，则需要再新增一行，补充Stop事件的Event信息
                                                                        # 写Play
                                                                        self.WriteCell_ForTable(r, key["Header_EventName"],
                                                                                                vID, "EventName",
                                                                                                tempNTG[1][2])
                                                                        # 在表格底部新增一行（写StopEvent、Notes、Lock，同时给Stop行更新Wwise里的Notes）
                                                                        NewLineNum = self.Action_AddLine_AtBottom()
                                                                        # 给新行写StopEvent
                                                                        self.WriteCell_ForTable(NewLineNum,
                                                                                                key["Header_EventName"],
                                                                                                vID, "EventName",
                                                                                                "Stop_" + tempNTG[1][1])
                                                                        # 给新行写StopNotes
                                                                        vNotes = self.tableWidget_SoundSheet.item(r, key[
                                                                            "Header_Notes"]).text()
                                                                        self.WriteCell_ForTable(NewLineNum,
                                                                                                key["Header_Notes"], vID,
                                                                                                "Notes", vNotes)
                                                                        # 给Stop新行更新Wwise里的Notes
                                                                        vEvent_Stop = self.tableWidget_SoundSheet.item(
                                                                            NewLineNum, key["Header_EventName"]).text()
                                                                        vID_Stop = self.tableWidget_SoundSheet.item(
                                                                            NewLineNum, key["Header_ID"]).text()
                                                                        # GUID_Stop = aoligei.getSingleEventGUIDFromEventWWU(vEvent_Stop)
                                                                        GUID_Stop = aoligei.get_EventGUID_From_EventName(
                                                                            vEvent_Stop)
                                                                        # if len(GUID_Stop) != 0:
                                                                        if GUID_Stop is not None and len(GUID_Stop) != 0:
                                                                            NewNotes = "#" + str(vID_Stop) + "#," + str(
                                                                                vNotes)
                                                                            aoligei.setNotesForGUID(GUID_Stop, NewNotes)
                                                                        # 给新行写StopLock
                                                                        self.WriteCell_ForTable(NewLineNum,
                                                                                                key["Header_Lock"], vID,
                                                                                                "Lock",
                                                                                                key["LockedStrValue"])
                                                                    else:
                                                                        # 写Play
                                                                        self.WriteCell_ForTable(r, key["Header_EventName"],
                                                                                                vID, "EventName",
                                                                                                tempNTG[1][2])

                                                                    # 给Event更新Notes
                                                                    vEvent = self.tableWidget_SoundSheet.item(r, key[
                                                                        "Header_EventName"]).text()
                                                                    vNotes = self.tableWidget_SoundSheet.item(r, key[
                                                                        "Header_Notes"]).text()
                                                                    # GUID = aoligei.getSingleEventGUIDFromEventWWU(vEvent)
                                                                    GUID = aoligei.get_EventGUID_From_EventName(vEvent)
                                                                    # if len(GUID) != 0:
                                                                    if GUID is not None and len(GUID) != 0:
                                                                        NewNotes = "#" + str(vID) + "#," + str(vNotes)
                                                                        aoligei.setNotesForGUID(GUID, NewNotes)

                                                                        # 给新的ObjectRef更新Notes
                                                                        NewObjectRefCup = aoligei.getObjectRefFromEventStr(
                                                                            vEvent)
                                                                        if len(NewObjectRefCup) != 0:
                                                                            NewObjectRefGUID = list(NewObjectRefCup.keys())
                                                                            for i in NewObjectRefGUID:
                                                                                aoligei.setNotesForGUID(i, NewNotes)

                                                                    # 如果AutoGenerateBanks没有选中，说明在这一步就可以写入Lock，否则Lock写入要留到下一轮
                                                                    if key["AutoGenerateBanks"] != "True":
                                                                        self.WriteCell_ForTable(r, key["Header_Lock"], vID,
                                                                                                "Lock",
                                                                                                key["LockedStrValue"])

                                                                    # 更新进度条信息
                                                                    CurStep = index + 1
                                                                    TotalStep = len(rowList)
                                                                    self.ShowProgress([CurStep, TotalStep])
                                                                    LOG.info("Line" + str(r + 1) +
                                                                          lan["LOG_SM_def_WaapiGo_WriteTable_DONE"][L])
                                                                except:
                                                                    traceback.print_exc()
                                                                    LOG.error(lan["LOG_SM_def_WaapiGo_WriteTable_FAIL"][L])
                                                                    continue
                                                            except:
                                                                traceback.print_exc()
                                                                LOG.error(
                                                                    "< Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_FAIL"][
                                                                        L])
                                                                continue

                # 如果自动打Bank选项开启，则自动进行下一步，否则跳过
                if key["AutoGenerateBanks"] == "True":
                    LOG.info(lan["LOG_WG_HalfFINISHED"][L])

                    # 开始打Bank
                    CollectChangedBanks = []
                    for r in rowList:
                        Lock = self.tableWidget_SoundSheet.item(r, key["Header_Lock"]).text()
                        if Lock != "1" and Lock != 1:
                            vEvent = self.tableWidget_SoundSheet.item(r, key["Header_EventName"]).text()
                            bnkList = aoligei.GetBNKNameFromEventStr(vEvent)
                            if len(bnkList) != 0:
                                for i in bnkList:
                                    CollectChangedBanks.append(i)

                    # Waapi预备标记
                    AutoGenerateSoundBankFlag = True
                    if len(CollectChangedBanks) != 0:
                        for i in CollectChangedBanks:
                            WaapiStatusResult = aoligei.GenerateOneBNK(i)
                            if WaapiStatusResult is False:
                                AutoGenerateSoundBankFlag = False
                                break

                    if AutoGenerateSoundBankFlag is False:
                        for r in rowList:
                            # LOG.info(lan["LOG_WG_ProcessingLine"][L] + str(r + 1) + "  ********************************")
                            vID = self.tableWidget_SoundSheet.item(r, key["Header_ID"]).text()
                            self.WriteCell_ForTable(r, key["Header_Lock"], vID, "Lock", key["LockedStrValue"])
                    else:
                        # 将Bank信息写入XLSX
                        # 统计List
                        List_FilledBankInfo = []
                        List_SkippedInfo = []
                        List_NoEventInfo = []
                        List_CanNotFindBankInfo = []
                        List_MoreThanOneBankInfo = []

                        # 如果行号List不为空，开始WAAPIGO逐行循环执行
                        for r in rowList:
                            LOG.info(lan["LOG_WG_ProcessingLine"][L] + str(r + 1))

                            # 从当前行的每一个单元格中取值
                            vID = self.tableWidget_SoundSheet.item(r, key["Header_ID"]).text()
                            vEvent = self.tableWidget_SoundSheet.item(r, key["Header_EventName"]).text()
                            vBank = self.tableWidget_SoundSheet.item(r, key["Header_BankName"]).text()

                            if vEvent == "None":
                                vEvent = ""
                            if vBank == "None":
                                vBank = ""

                            if len(vEvent) == 0:
                                List_NoEventInfo.append(str(r + 1))
                                LOG.warning(lan["LOG_SM_def_FillBankInfo_NOEVENTINFO"][L])
                            else:
                                BankList = LocateEventBankLocation(vEvent,
                                                                   LocalInfoDict["ActualGeneratedSoundBankPathOfOnePlatform"])
                                if len(vBank) == 0:
                                    # 判断Bank结果是否合法
                                    if len(BankList) == 1:
                                        self.WriteCell_ForTable(r, key["Header_BankName"], vID, "BankName", BankList[0])
                                        List_FilledBankInfo.append(str(r + 1))
                                        LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_FillBankInfo_FINISHED"][L])
                                    elif len(BankList) == 0:
                                        List_CanNotFindBankInfo.append(str(r + 1))
                                        LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_FillBankInfo_ORPHAN"][L])
                                    elif len(BankList) > 1:
                                        List_MoreThanOneBankInfo.append(str(r + 1))
                                        LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_FillBankInfo_MORETHANONE"][L])
                                else:
                                    List_SkippedInfo.append(str(r + 1))
                                    LOG.warning(lan["LOG_SM_def_FillBankInfo_SKIPPED"][L])

                                self.WriteCell_ForTable(r, key["Header_Lock"], vID, "Lock", key["LockedStrValue"])

                        LOG.info(lan["LOG_WG_AutoGenerateBankReport"][L])
                        if len(List_FilledBankInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_FilledBankInfo"][L])
                            LOG.info(List_FilledBankInfo)
                        if len(List_SkippedInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_SkippedInfo"][L])
                            LOG.info(List_SkippedInfo)
                        if len(List_NoEventInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_NoEventInfo"][L])
                            LOG.info(List_NoEventInfo)
                        if len(List_CanNotFindBankInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_CanNotFindBankInfo"][L])
                            LOG.info(List_CanNotFindBankInfo)
                        if len(List_MoreThanOneBankInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_MoreThanOneBankInfo"][L])
                            LOG.info(List_MoreThanOneBankInfo)

                # 整体保存（如果表格数据量很大，还是放在最后保存吧。等找到快速保存的办法，再改为逐步保存）
                SaveJson(SoundListDict, global_curWwiseInfoJson)
                LOG.info(lan["LOG_MirrorEnded"][L])

                # 手动断联
                aoligei.__del__()
        except:
            traceback.print_exc()

    def ReCreateCompletely(self, validRowList):
        try:
            # 获取选中的行数
            rowList = validRowList
            # rowList = self.GetSelectedRows()
            if len(rowList) != 0:  # 如果有被选中的行
                aoligei = SimpleWaapi()
                # 获取所有的ID
                AllIDList = []
                for row in range(self.tableWidget_SoundSheet.rowCount()):
                    AllIDList.append(self.tableWidget_SoundSheet.item(row, key["Header_ID"]).text())

                # 逐行安全检查，通过的执行写入
                for r, index in zip(rowList, range(len(rowList))):
                    vID = self.tableWidget_SoundSheet.item(r, key["Header_ID"]).text()
                    vfName = self.tableWidget_SoundSheet.item(r, key["Header_KeyStr"]).text()
                    vsName = self.tableWidget_SoundSheet.item(r, key["Header_BodyStr"]).text()
                    vtName = self.tableWidget_SoundSheet.item(r, key["Header_TailStr"]).text()
                    vRanNum = self.tableWidget_SoundSheet.item(r, key["Header_RDM"]).text()
                    Lock = self.tableWidget_SoundSheet.item(r, key["Header_Lock"]).text()

                    # 为type2d_gun临时添加判断，临时阻止ExpandSwitch、Mirror、ReCreate功能
                    KEYSTRDICT = KeyInfoDict["Data_KeyInfo"].get(vfName, "!@#")
                    if KEYSTRDICT != "!@#":
                        if KEYSTRDICT["Structure_Type"] == "type2d_gun":
                            LOG.warning("Line" + str(r + 1) + ": " + lan["LOG_NSG_def_nameStrGen_type2dgunNotAvalible_Skip"][L])
                            continue

                    # 先确认ID是否有非法的，有的话跳过循环！
                    duplicatedIDCheck = self.SafetyCheck_ID(vID, AllIDList)
                    if len(duplicatedIDCheck) != 0:
                        LOG.warning(str(duplicatedIDCheck) + lan["LOG_SM_def_WaapiGo_DuplicatedIDPreCheck"][L])
                        break

                    # 确认当前行的Lock值，如果已被标记过，则跳过（continue）当前行的执行，并将Log传入GoLog待打印
                    if str(Lock) == "0" or str(Lock) == key["LockedStrValue"]:
                        LOG.warning("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_LockCheck_SKIP"][L])
                        continue

                    # 确认当前是否有Event字符串
                    EventStr = self.tableWidget_SoundSheet.item(r, key["Header_EventName"]).text()
                    if len(EventStr) != 0:
                        # 判断Event是否可能不是“Play”类型
                        if EventStr.find("Play_") == -1:
                            LOG.warning("Line" + str(r + 1) + ": " + lan["LOG_SM_def_ExpandSwitch_NotPlayEvent_Skipped"][L])
                            continue
                        else:
                            # 判断Event是否存在于WWU，len!=0代表找到了。找到的话再继续向后执行。
                            # existResult_GUID = aoligei.getSingleEventGUIDFromEventWWU(EventStr)
                            # existdisuseResult_GUID = aoligei.getSingleEventGUIDFromEventWWU(EventStr + "_disuse")
                            existResult_GUID = aoligei.get_EventGUID_From_EventName(EventStr)
                            existdisuseResult_GUID = aoligei.get_EventGUID_From_EventName(EventStr + "_disuse")

                            # 先判断disuse是否已存在，如果已存在，直接跳过
                            # if len(existdisuseResult_GUID) != 0:
                            if existdisuseResult_GUID is not None and len(existdisuseResult_GUID) != 0:
                                LOG.warning("Line" + str(r + 1) + ": " + lan["LOG_SM_def_ExpandSwitch_disuseExist_Skipped"][L])
                                continue
                            # if len(existResult_GUID) == 0:
                            if existResult_GUID is not None and len(existResult_GUID) == 0:
                                LOG.warning("Line" + str(r + 1) + ": " + lan["LOG_SM_def_ExpandSwitch_Skipped"][L])
                                continue
                            else:
                                # 确认fName是否合法，否则直接跳过
                                if vfName not in list(KeyInfoDict["Data_KeyInfo"].keys()):
                                    LOG.warning("Line" + str(r + 1) + ": " + lan["LOG_NSG_def_nameStrGen_fnameInvalid_Skip"][L])
                                    continue

                                # 如果上一步Lock检查未被跳过，则继续执行Create NameStr，产生字符串大包装
                                LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_LockCheck_PASS"][L])

                                # 产生命名大礼包
                                tempNTG = aoligei.nameStrGenWithoutCheckDuplicate(vID, vfName, vsName, vtName, vRanNum)

                                # tempNTG[0]是Error小包，如果该小包中产生了报错信息，则直接离开（if/else）当前行的执行，并将信息传入GoLog待打印
                                if len(tempNTG[0]) != 0:
                                    LOG.warning("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_NamingErrorCheck_FAIL"][L])
                                # 否则如果tempNTG[0]为空，则开始执行Create WAV，在本地产生wav文件
                                else:
                                    # 统计当前Event的ObjectRef数量、GUID、名称（如果ObjectRef大于1，log提示手动修改后，跳过）
                                    ObjectRefResult = aoligei.getObjectRefFromEventStr(EventStr)
                                    # 如果Event里面没东西，就直接重命名、搁置当前Event
                                    if len(ObjectRefResult) == 0:
                                        aoligei.RenameEventToDisuse(EventStr)
                                        LOG.warning("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_NoObjectRef"][L])
                                    # 如果Event里的ObjectRef数量大于1，跳过，不执行本行
                                    elif len(ObjectRefResult) > 1:
                                        LOG.warning("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_MoreThanOneObjectRef"][L])
                                        continue
                                    else:
                                        ObjectRefGUID = list(ObjectRefResult.keys())[0]
                                        LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_FoundOneObjectRef"][L])

                                        # 将当前Event名和ObjectRef名称批量重命名
                                        aoligei.RenameEventToDisuse(EventStr)
                                        aoligei.RenameObjNameToDisuseByGUID(ObjectRefGUID)

                                        # 如果上一步Lock检查未被跳过，则继续执行Create NameStr，产生字符串大包装
                                        tempNTG = aoligei.nameStrGen(vID, vfName, vsName, vtName, vRanNum)
                                        # tempNTG[0]是Error小包，如果该小包中产生了报错信息，则直接离开（if/else）当前行的执行，并将信息传入GoLog待打印
                                        if len(tempNTG[0]) != 0:
                                            LOG.warning("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_NamingErrorCheck_FAIL"][L])
                                        else:
                                            LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_NamingErrorCheck_PASS"][L])

                                            # 生成wav
                                            wavErrorLog = aoligei.wavGen(vID, vfName, vsName, vtName, vRanNum)

                                            # 再次确认命名的合法性（wavGen方法中，除了自己ADVCopy方法的Error之外，也包含return了nameStrGen的[0]号位的Error信息）
                                            if len(wavErrorLog) != 0:
                                                LOG.warning("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_WAVCreate_NOTGOOD"][L])
                                            # 如果wavGen方法没有报错，则意味着wav已顺利生成，随即打印成功信息
                                            else:
                                                LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_WAVCreate_PASS"][L])

                                                # 到这一步为止，可以开始执行Waapi GO了
                                                # 这一步，是根据关键词Type类型，自动选择调用哪一个Func！“info.json”文件里的配置参与了PickFunc方法
                                                LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_StructureTypeCheck"][L])
                                                WaapiGoType = KeyInfoDict["Data_KeyInfo"][vfName]["Structure_Type"]
                                                try:
                                                    # WAPPI GO执行，成功后，然后打印成功信息
                                                    LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_OnGoing"][L])
                                                    getattr(aoligei, WaapiGoType)(vID, vfName, vsName, vtName, vRanNum)
                                                    LOG.info("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_DONE"][L])

                                                    # 将EventStr和Lock写入TABLEALL
                                                    try:
                                                        if tempNTG[1][1][
                                                           -3:] == "_LP":  # 如果命名中标注了循环，则需要再新增一行，补充Stop事件的Event信息
                                                            # 写Play
                                                            self.WriteCell_ForTable(r, key["Header_EventName"], vID,
                                                                                    "EventName", tempNTG[1][2])
                                                            # 在表格底部新增一行（写StopEvent、Notes、Lock，同时给Stop行更新Wwise里的Notes）
                                                            NewLineNum = self.Action_AddLine_AtBottom()
                                                            # 给新行写StopEvent
                                                            self.WriteCell_ForTable(NewLineNum, key["Header_EventName"],
                                                                                    vID, "EventName",
                                                                                    "Stop_" + tempNTG[1][1])
                                                            # 给新行写StopNotes
                                                            vNotes = self.tableWidget_SoundSheet.item(r, key[
                                                                "Header_Notes"]).text()
                                                            self.WriteCell_ForTable(NewLineNum, key["Header_Notes"], vID,
                                                                                    "Notes", vNotes)
                                                            # 给Stop新行更新Wwise里的Notes
                                                            vEvent_Stop = self.tableWidget_SoundSheet.item(NewLineNum, key[
                                                                "Header_EventName"]).text()
                                                            vID_Stop = self.tableWidget_SoundSheet.item(NewLineNum, key[
                                                                "Header_ID"]).text()
                                                            # GUID_Stop = aoligei.getSingleEventGUIDFromEventWWU(vEvent_Stop)
                                                            GUID_Stop = aoligei.get_EventGUID_From_EventName(vEvent_Stop)
                                                            # if len(GUID_Stop) != 0:
                                                            if GUID_Stop is not None and len(GUID_Stop) != 0:
                                                                NewNotes = "#" + str(vID_Stop) + "#," + str(vNotes)
                                                                aoligei.setNotesForGUID(GUID_Stop, NewNotes)
                                                            # 给新行写StopLock
                                                            self.WriteCell_ForTable(NewLineNum, key["Header_Lock"], vID,
                                                                                    "Lock", key["LockedStrValue"])
                                                        else:
                                                            # 写Play
                                                            self.WriteCell_ForTable(r, key["Header_EventName"], vID,
                                                                                    "EventName", tempNTG[1][2])

                                                        # 给Event更新Notes
                                                        vEvent = self.tableWidget_SoundSheet.item(r, key[
                                                            "Header_EventName"]).text()
                                                        vNotes = self.tableWidget_SoundSheet.item(r, key[
                                                            "Header_Notes"]).text()
                                                        # GUID = aoligei.getSingleEventGUIDFromEventWWU(vEvent)
                                                        GUID = aoligei.get_EventGUID_From_EventName(vEvent)
                                                        # if len(GUID) != 0:
                                                        if GUID is not None and len(GUID) != 0:
                                                            NewNotes = "#" + str(vID) + "#," + str(vNotes)
                                                            aoligei.setNotesForGUID(GUID, NewNotes)

                                                            # 给新的ObjectRef更新Notes
                                                            NewObjectRefCup = aoligei.getObjectRefFromEventStr(vEvent)
                                                            if len(NewObjectRefCup) != 0:
                                                                NewObjectRefGUID = list(NewObjectRefCup.keys())
                                                                for i in NewObjectRefGUID:
                                                                    aoligei.setNotesForGUID(i, NewNotes)

                                                        # 如果AutoGenerateBanks没有选中，说明在这一步就可以写入Lock，否则Lock写入要留到下一轮
                                                        if key["AutoGenerateBanks"] != "True":
                                                            self.WriteCell_ForTable(r, key["Header_Lock"], vID, "Lock",
                                                                                    key["LockedStrValue"])

                                                        # 更新进度条信息
                                                        CurStep = index + 1
                                                        TotalStep = len(rowList)
                                                        self.ShowProgress([CurStep, TotalStep])
                                                        LOG.info(
                                                            "Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_WriteTable_DONE"][
                                                                L])
                                                    except:
                                                        traceback.print_exc()
                                                        LOG.error(lan["LOG_SM_def_WaapiGo_WriteTable_FAIL"][L])
                                                        continue
                                                except:
                                                    traceback.print_exc()
                                                    LOG.error("< Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_FAIL"][L])
                                                    continue

                # 如果自动打Bank选项开启，则自动进行下一步，否则跳过
                if key["AutoGenerateBanks"] == "True":
                    LOG.info(lan["LOG_WG_HalfFINISHED"][L])

                    # 开始打Bank
                    CollectChangedBanks = []
                    for rrr in rowList:
                        Lock = self.tableWidget_SoundSheet.item(rrr, key["Header_Lock"]).text()
                        if Lock != "1" and Lock != 1:
                            vEvent = self.tableWidget_SoundSheet.item(rrr, key["Header_EventName"]).text()
                            bnkList = aoligei.GetBNKNameFromEventStr(vEvent)
                            if len(bnkList) != 0:
                                for i in bnkList:
                                    CollectChangedBanks.append(i)

                    # Waapi预备标记
                    AutoGenerateSoundBankFlag = True
                    if len(CollectChangedBanks) != 0:
                        for i in CollectChangedBanks:
                            WaapiStatusResult = aoligei.GenerateOneBNK(i)
                            if WaapiStatusResult is False:
                                AutoGenerateSoundBankFlag = False
                                break

                    if AutoGenerateSoundBankFlag is False:
                        for r in rowList:
                            # LOG.info(lan["LOG_WG_ProcessingLine"][L] + str(r + 1) + "  ********************************")
                            vID = self.tableWidget_SoundSheet.item(r, key["Header_ID"]).text()
                            self.WriteCell_ForTable(r, key["Header_Lock"], vID, "Lock", key["LockedStrValue"])
                    else:
                        # 将Bank信息写入XLSX
                        # 统计List
                        List_FilledBankInfo = []
                        List_SkippedInfo = []
                        List_NoEventInfo = []
                        List_CanNotFindBankInfo = []
                        List_MoreThanOneBankInfo = []

                        # 如果行号List不为空，开始WAAPIGO逐行循环执行
                        for rr in rowList:
                            LOG.info(lan["LOG_WG_ProcessingLine"][L] + str(rr + 1))

                            # 从当前行的每一个单元格中取值
                            vID = self.tableWidget_SoundSheet.item(rr, key["Header_ID"]).text()
                            vEvent = self.tableWidget_SoundSheet.item(rr, key["Header_EventName"]).text()
                            vBank = self.tableWidget_SoundSheet.item(rr, key["Header_BankName"]).text()

                            if vEvent == "None":
                                vEvent = ""
                            if vBank == "None":
                                vBank = ""

                            if len(vEvent) == 0:
                                List_NoEventInfo.append(str(rr + 1))
                                LOG.warning(lan["LOG_SM_def_FillBankInfo_NOEVENTINFO"][L])
                            else:
                                BankList = LocateEventBankLocation(vEvent,
                                                                   LocalInfoDict["ActualGeneratedSoundBankPathOfOnePlatform"])
                                if len(vBank) == 0:
                                    # 判断Bank结果是否合法
                                    if len(BankList) == 1:
                                        self.WriteCell_ForTable(rr, key["Header_BankName"], vID, "BankName", BankList[0])
                                        List_FilledBankInfo.append(str(rr + 1))
                                        LOG.info("Line" + str(rr + 1) + lan["LOG_SM_def_FillBankInfo_FINISHED"][L])
                                    elif len(BankList) == 0:
                                        List_CanNotFindBankInfo.append(str(rr + 1))
                                        LOG.warning("Line" + str(rr + 1) + lan["LOG_SM_def_FillBankInfo_ORPHAN"][L])
                                    elif len(BankList) > 1:
                                        List_MoreThanOneBankInfo.append(str(rr + 1))
                                        LOG.warning("Line" + str(rr + 1) + lan["LOG_SM_def_FillBankInfo_MORETHANONE"][L])
                                else:
                                    List_SkippedInfo.append(str(rr + 1))
                                    LOG.warning(lan["LOG_SM_def_FillBankInfo_SKIPPED"][L])

                            self.WriteCell_ForTable(rr, key["Header_Lock"], vID, "Lock", key["LockedStrValue"])

                        LOG.info(lan["LOG_WG_AutoGenerateBankReport"][L])
                        if len(List_FilledBankInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_FilledBankInfo"][L])
                            LOG.info(List_FilledBankInfo)
                        if len(List_SkippedInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_SkippedInfo"][L])
                            LOG.info(List_SkippedInfo)
                        if len(List_NoEventInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_NoEventInfo"][L])
                            LOG.info(List_NoEventInfo)
                        if len(List_CanNotFindBankInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_CanNotFindBankInfo"][L])
                            LOG.info(List_CanNotFindBankInfo)
                        if len(List_MoreThanOneBankInfo) != 0:
                            LOG.info(lan["LOG_SM_def_List_MoreThanOneBankInfo"][L])
                            LOG.info(List_MoreThanOneBankInfo)

                # 整体保存（如果表格数据量很大，还是放在最后保存吧。等找到快速保存的办法，再改为逐步保存）
                SaveJson(SoundListDict, global_curWwisePath + "\\info.json")
                LOG.info(lan["LOG_WG_ALLFINISHED"][L])

                # 手动断联
                aoligei.__del__()
        except:
            traceback.print_exc()

    def ShowProgress(self, listOfTwoNum):
        PercentageNum = int(listOfTwoNum[0] / listOfTwoNum[1] * 100)

        # Use ProgressBar
        self.progressBar.setVisible(True)
        self.progressBar.setValue(PercentageNum)

        if PercentageNum == 100:
            self.progressBar.setValue(0)
            self.progressBar.setVisible(False)

    def ProgressBar_ForceClose(self):
        self.progressBar.setValue(0)
        self.progressBar.setVisible(False)

    # ----------------------------------------------------------------------------- Panel Func ----- Table
    def Action_AfterItemSelectionChanged(self):
        try:
            items = self.tableWidget_SoundSheet.selectedItems()
            if len(items) != 0:  # 如果没有这个判断，从空表加载时每一个Item都是[]为空
                self.CellSelected_Old = []
                for item in items:
                    CellSelected_Old = {
                        "row": item.row(),
                        "column": item.column(),
                        "text": item.text(),
                        "textColor": item.foreground().color().name(),
                        "bgColor": item.background().color().name()
                    }
                    self.CellSelected_Old.append(CellSelected_Old)
        except:
            traceback.print_exc()

    def Action_AfterCellChanged(self):
        try:
            items = self.tableWidget_SoundSheet.selectedItems()
            if len(items) != 0:  # 如果没有这个判断，从空表加载时每一个Item都是[]为空
                finalList = []
                for item, SingleCellChange_Old in zip(items, self.CellSelected_Old):
                    SingleCellChange_New = {
                        "row": item.row(),
                        "column": item.column(),
                        "text": item.text(),
                        "textColor": item.foreground().color().name(),
                        "bgColor": item.background().color().name()
                    }
                    # SingleCellChange_Old = self.CellSelected_Old
                    finalPack = {"KeyboardInput": {"Old": SingleCellChange_Old, "New": SingleCellChange_New}}
                    finalList.append(finalPack)

                # LOG.debug(finalList)
                UndoList.append(finalList)

                # 新动作产生时，要清空RedoList，防止凭空Redo出遗弃的历史动作
                RedoList.clear()
                self.UndoRedoNumShow()

                # 显示保存提示
                self.NeedSafeFlag = 1
                self.SetState_Save()
        except:
            traceback.print_exc()

    def RightClickMenu_tableWidget_SoundSheet(self):
        Menu = QMenu(self)
        Menu.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))

        action_PlayEvent = QAction(lan["GUI_SM_RC_action_PlayEvent"][L], self)
        Menu.addAction(action_PlayEvent)
        action_PlayEvent.triggered.connect(self.PlayEvent)

        action_StopEvent = QAction(lan["GUI_SM_RC_action_StopAllEvent"][L], self)
        Menu.addAction(action_StopEvent)
        action_StopEvent.triggered.connect(self.StopEvent)

        action_AnalyseEvent = QAction(lan["GUI_SM_RC_action_AnalyseEvent"][L], self)
        Menu.addAction(action_AnalyseEvent)
        action_AnalyseEvent.triggered.connect(self.AnalyseEvent)

        action_DiagnoseEvent = QAction(lan["GUI_SM_RC_action_DiagnoseEvent"][L], self)
        Menu.addAction(action_DiagnoseEvent)
        action_DiagnoseEvent.triggered.connect(self.DiagnoseEvent)

        Menu.addSeparator()

        action_RefreshNoteForEvent = QAction(lan["GUI_SM_RC_action_RenewNotesForEvents"][L], self)
        Menu.addAction(action_RefreshNoteForEvent)
        action_RefreshNoteForEvent.triggered.connect(self.PreCheck_RefreshNoteForEvent)

        action_FillBankInfo = QAction(lan["GUI_SM_RC_action_FillBankInfo"][L], self)
        Menu.addAction(action_FillBankInfo)
        action_FillBankInfo.triggered.connect(self.PreCheck_FillBankInfo)

        Menu.addSeparator()

        action_OpenWAVFolder = QAction(lan["GUI_SM_RC_action_LocateWAVFolder"][L], self)
        Menu.addAction(action_OpenWAVFolder)
        action_OpenWAVFolder.triggered.connect(self.OpenWAVFolder)

        action_CheckWAVPlaceholder = QAction(lan["GUI_SM_RC_action_CheckWAVSilence"][L], self)
        Menu.addAction(action_CheckWAVPlaceholder)
        action_CheckWAVPlaceholder.triggered.connect(self.PreCheck_CheckWAVPlaceholder)

        Menu.addSeparator()

        action_SetColor_Text = QAction(lan["GUI_SM_RC_action_SetCellTextColor"][L], self)
        Menu.addAction(action_SetColor_Text)
        action_SetColor_Text.triggered.connect(self.SetColor_ForCellText)

        action_SetColor_Background = QAction(lan["GUI_SM_RC_action_SetCellBackgroundColor"][L], self)
        Menu.addAction(action_SetColor_Background)
        action_SetColor_Background.triggered.connect(self.SetColor_ForCellBackground)

        Menu.addSeparator()

        action_ExportRequest_Chinese = QAction(lan["GUI_SM_RC_action_CreateRequestXLSX"][L], self)
        Menu.addAction(action_ExportRequest_Chinese)
        action_ExportRequest_Chinese.triggered.connect(self.ExportRequestXLSX)

        Menu.addSeparator()

        action_ChangeOrder = QAction(lan["GUI_action_Order"][L], self)
        Menu.addAction(action_ChangeOrder)
        action_ChangeOrder.triggered.connect(self.ChangeOrder)

        Menu.popup(QCursor.pos())

    def PlayEvent(self):
        try:
            go = SimpleWaapi()
            rowList = self.GetSelectedRows()
            if len(rowList) == 1:
                eventText = self.tableWidget_SoundSheet.item(rowList[0], key["Header_EventName"]).text()
                eventGUID = go.get_EventGUID_From_EventName(eventText)
                if eventGUID is None:
                    pass
                else:
                    go.PlayAnEvent(eventGUID)
                    go.FocusOrPopUp(eventGUID)
            go.__del__()
        except:
            traceback.print_exc()

    def StopEvent(self):
        try:
            go = SimpleWaapi()
            go.StopAllEvent()
            go.__del__()
        except:
            traceback.print_exc()

    def AnalyseEvent(self):
        try:
            rowList = self.GetSelectedRows()
            if len(rowList) == 1:
                eventText = self.tableWidget_SoundSheet.item(rowList[0], key["Header_EventName"]).text()
                if len(eventText) == 0:
                    self.label_EventObjectRefCount.setText("0")
                    self.label_RelatedWAVCount.setText("0")
                    self.comboBox_EventObjectRef.clear()
                    self.comboBox_RelatedWAV.clear()
                else:
                    go = SimpleWaapi()
                    eventGUID = go.get_EventGUID_From_EventName(eventText)
                    if eventGUID is None:
                        self.label_EventObjectRefCount.setText("0")
                        self.label_RelatedWAVCount.setText("0")
                        self.comboBox_EventObjectRef.clear()
                        self.comboBox_RelatedWAV.clear()
                        pass
                    else:
                        eventStructureDict = go.Get_AllWAVPath_From_EventName_InActionLayer(eventText)
                        if len(eventStructureDict) == 0:
                            self.label_EventObjectRefCount.setText("0")
                            self.label_RelatedWAVCount.setText("0")
                            self.comboBox_EventObjectRef.clear()
                            self.comboBox_RelatedWAV.clear()
                            pass
                        else:
                            self.Frame_AdvInfo.setVisible(True)
                            actionDict = eventStructureDict[eventText]["Action"]
                            actionCount = str(len(actionDict))
                            self.label_EventObjectRefCount.setText(actionCount)
                            EventInfoDict.clear()
                            for action, actionInfo in zip(actionDict.keys(), actionDict.values()):
                                PropertyNameStr = actionInfo["PropertyName"]
                                ObjectRefName = actionInfo["ObjectRef"]["Name"]
                                ObjectRefType = actionInfo["ObjectRef"]["Type"]
                                wavPathList = actionInfo["ObjectRef"]["wavPath"]
                                linkMark = " --> "
                                ObjectRefOptionStr = PropertyNameStr + linkMark + ObjectRefType + linkMark + ObjectRefName
                                EventInfoDict[ObjectRefOptionStr] = wavPathList

                            # 写入comboBox
                            if len(EventInfoDict) != 0:
                                self.comboBox_EventObjectRef.clear()
                                self.comboBox_RelatedWAV.clear()
                                for actionObj, wavList in zip(EventInfoDict.keys(), EventInfoDict.values()):
                                    self.comboBox_EventObjectRef.addItem(actionObj)
                    go.__del__()
        except:
            traceback.print_exc()

    def DiagnoseEvent(self):
        try:
            rowList = self.GetSelectedRows()
            # 先逐个检查选中的Events是否都存在，将确定存在的整理到新的List中
            ValidEventList = []
            InvalidEventList = []
            if len(rowList) != 0:
                go = SimpleWaapi()
                for i in rowList:
                    eventText = self.tableWidget_SoundSheet.item(i, key["Header_EventName"]).text()
                    if len(eventText) == 0:
                        pass
                    else:
                        eventGUID = go.get_EventGUID_From_EventName(eventText)
                        if eventGUID is None:
                            InvalidEventList.append(eventText)
                        else:
                            ValidEventList.append(eventText)

            # 如果发现不存在的，提示用户是否进一步检查
            if len(InvalidEventList) != 0:
                messageBox = QMessageBox(QMessageBox.Warning,
                                         lan["GUI_SM_RC_action_DiagnoseEvent_MessageBox_Title"][L],
                                         lan["GUI_SM_RC_action_DiagnoseEvent_MessageBox_Text"][L] + str(InvalidEventList) + lan["GUI_SM_RC_action_DiagnoseEvent_MessageBox_Text_B"][L] + str(ValidEventList))
                messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
                Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
                Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
                messageBox.exec_()
                if messageBox.clickedButton() == Qyes:
                    if len(ValidEventList) != 0:
                        LOG.info(lan["GUI_LOG_DiagnoseEvent_Start"][L] + str(ValidEventList))
                        for eventStr in ValidEventList:
                            go.print_UltraInfoOfEvent(eventStr)
            else:
                if len(ValidEventList) != 0:
                    LOG.info(lan["GUI_LOG_DiagnoseEvent_Start"][L] + str(ValidEventList))
                    for eventStr in ValidEventList:
                        go.print_UltraInfoOfEvent(eventStr)


        except:
            traceback.print_exc()

    def PreCheck_FillBankInfo(self):
        rowList = self.GetSelectedRows()
        if len(rowList) != 0:
            if len(rowList) > 100:
                messageBox = QMessageBox(QMessageBox.Warning,
                                         lan["GUI_SM_RC_action_TooManyRowSelected_MessageBox_Title"][L],
                                         lan["GUI_SM_RC_action_TooManyRowSelected_MessageBox_Text"][L])
                messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
                Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
                Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
                messageBox.exec_()
                if messageBox.clickedButton() == Qyes:
                    self.FillBankInfo()
            else:
                self.FillBankInfo()

    def FillBankInfo(self):
        try:
            go = SimpleWaapi()
            try:
                rowList = self.GetSelectedRows()
                if len(rowList) != 0:
                    for row in rowList:
                        idText = self.tableWidget_SoundSheet.item(row, key["Header_ID"]).text()
                        eventText = self.tableWidget_SoundSheet.item(row, key["Header_EventName"]).text()
                        if len(eventText) != 0:
                            eventGUID = go.get_EventGUID_From_EventName(eventText)
                            if eventGUID is None:
                                pass
                            else:
                                bankNameList = LocateEventBankLocation(eventText, LocalInfoDict[
                                    "ActualGeneratedSoundBankPathOfOnePlatform"])
                                if len(bankNameList) == 0:
                                    pass
                                else:
                                    if len(bankNameList) == 1:
                                        newitem = QTableWidgetItem(bankNameList[0])
                                        newitem.setForeground(
                                            QColor(SoundListDict["Data_SoundList"][idText]["BankName"]["textColor"]))
                                        newitem.setBackground(
                                            QColor(SoundListDict["Data_SoundList"][idText]["BankName"]["bgColor"]))
                                        self.tableWidget_SoundSheet.setItem(row, key["Header_BankName"], newitem)
                                        LOG.info(lan["LOG_SM_def_FillBankInfo_Mark"][L] + str(row + 1) + "   " + idText + " " + eventText + " --> " + str(bankNameList[0]))
                                    else:
                                        bnkStr = ""
                                        for Str in bankNameList:
                                            bnkStr = bnkStr + "," + Str
                                        bnkStr = bnkStr[1:]

                                        newitem = QTableWidgetItem(bnkStr)
                                        newitem.setForeground(
                                            QColor(SoundListDict["Data_SoundList"][idText]["BankName"]["textColor"]))
                                        newitem.setBackground(
                                            QColor(SoundListDict["Data_SoundList"][idText]["BankName"]["bgColor"]))
                                        self.tableWidget_SoundSheet.setItem(row, key["Header_BankName"], newitem)
                                        LOG.info(lan["LOG_SM_def_FillBankInfo_Mark"][L] + str(row + 1) + "   " + idText + " " + eventText + " --> " + str(bnkStr))
            except:
                traceback.print_exc()
            go.__del__()
        except:
            traceback.print_exc()

    def PreCheck_RefreshNoteForEvent(self):
        rowList = self.GetSelectedRows()
        if len(rowList) != 0:
            if len(rowList) > 100:
                messageBox = QMessageBox(QMessageBox.Warning,
                                         lan["GUI_SM_RC_action_TooManyRowSelected_MessageBox_Title"][L],
                                         lan["GUI_SM_RC_action_TooManyRowSelected_MessageBox_Text"][L])
                messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
                Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
                Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
                messageBox.exec_()
                if messageBox.clickedButton() == Qyes:
                    self.RefreshNoteForEvent()
            else:
                self.RefreshNoteForEvent()

    def RefreshNoteForEvent(self):
        try:
            go = SimpleWaapi()
            rowList = self.GetSelectedRows()
            if len(rowList) != 0:
                # 先获取全局信息，分组后，再执行的方法
                EventNotesDict = {}
                for row in rowList:
                    idText = self.tableWidget_SoundSheet.item(row, key["Header_ID"]).text()
                    noteText = self.tableWidget_SoundSheet.item(row, key["Header_Notes"]).text()
                    eventText = self.tableWidget_SoundSheet.item(row, key["Header_EventName"]).text()
                    if len(eventText) == 0:
                        pass
                    else:
                        eventGUID = go.get_EventGUID_From_EventName(eventText)
                        if eventGUID is None:
                            pass
                        else:
                            TarNoteStr = "#" + idText + "#," + noteText
                            if EventNotesDict.get(eventGUID, "@#$") == "@#$":
                                EventNotesDict[eventGUID] = [TarNoteStr]
                            else:
                                EventNotesDict[eventGUID].append(TarNoteStr)
                # LOG.info(EventNotesDict)

                for kk, vv in zip(EventNotesDict.keys(), EventNotesDict.values()):
                    vvv = ConnectStr(vv)
                    # LOG.info(vvv)
                    go.RenewNotesForGUID(kk, vvv)
                    eventName = go.get_NameOfGUID(kk)
                    LOG.info(lan["GUI_SM_RC_action_RenewNotesForEvents_Mark"][L] + " --> " + str(eventName) + " --> " + vvv)

                # # 直接逐行执行的方法
                # for row in rowList:
                #     idText = self.tableWidget_SoundSheet.item(row, key["Header_ID"]).text()
                #     noteText = self.tableWidget_SoundSheet.item(row, key["Header_Notes"]).text()
                #     eventText = self.tableWidget_SoundSheet.item(row, key["Header_EventName"]).text()
                #     if len(eventText) == 0:
                #         pass
                #     else:
                #         eventGUID = go.get_EventGUID_From_EventName(eventText)
                #         if eventGUID is None:
                #             pass
                #         else:
                #             TarNoteStr = "#" + idText + "#," + noteText
                #             go.RenewNotesForGUID(eventGUID, TarNoteStr)
                #             LOG.info(lan["GUI_SM_RC_action_RenewNotesForEvents_Mark"][L] + str(row + 1) + "   " + idText + " " + eventText + " --> " + noteText)
            go.__del__()
        except:
            traceback.print_exc()

    def OpenWAVFolder(self):
        try:
            rowList = self.GetSelectedRows()
            eventList = []
            if len(rowList) != 0:
                for row in rowList:
                    eventText = self.tableWidget_SoundSheet.item(row, key["Header_EventName"]).text()
                    eventList.append(eventText)

                self.Progress_GetAllWAVPathFromEventStr = Thread_GetAllWAVPathFromEventStr(eventList, global_curWwisePath)
                self.Progress_GetAllWAVPathFromEventStr.ProcessNum.connect(self.ShowProgress)
                self.Progress_GetAllWAVPathFromEventStr.start()
        except:
            traceback.print_exc()

    def PreCheck_CheckWAVPlaceholder(self):
        rowList = self.GetSelectedRows()
        if len(rowList) != 0:
            if len(rowList) > 100:
                messageBox = QMessageBox(QMessageBox.Warning, lan["GUI_SM_RC_action_TooManyRowSelected_MessageBox_Title"][L], lan["GUI_SM_RC_action_TooManyRowSelected_MessageBox_Text"][L])
                messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
                Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
                Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
                messageBox.exec_()
                if messageBox.clickedButton() == Qyes:
                    self.CheckWAVPlaceholder()
            else:
                self.CheckWAVPlaceholder()

    def CheckWAVPlaceholder(self):
        try:
            rowList = self.GetSelectedRows()
            if len(rowList) != 0:
                for row in rowList:
                    eventText = self.tableWidget_SoundSheet.item(row, key["Header_EventName"]).text()
                    if len(eventText) == 0:
                        pass
                    else:
                        LOG.info("\n --> " + str(row + 1) + " " + eventText)
                        wavList = Get_AllWAVPath_From_EventName_FlatWAVPath(eventText, global_curWwisePath)
                        placeHolderList = []
                        for wavPath in wavList:
                            dBFSResult = GetWAVMAXdBFS(wavPath)
                            if dBFSResult == "-inf":
                                placeHolderList.append(wavPath)
                        if len(placeHolderList) == 0:
                            LOG.info(lan["LOG_Pass"][L])
                        self.SetColor_ForWAVPlaceholder([row, key["Header_MirrorFrom"], placeHolderList])
        except:
            traceback.print_exc()

    def SetColor_ForCellText(self):
        # 打开调色板
        PickColor = QColorDialog.getColor()
        color = PickColor.name()

        s_items = self.tableWidget_SoundSheet.selectedItems()  # 获取当前所有选择的items
        for i in s_items:
            i.setForeground(QBrush(QColor(color)))

    def SetColor_ForCellBackground(self):
        # 打开调色板
        PickColor = QColorDialog.getColor()
        color = PickColor.name()

        s_items = self.tableWidget_SoundSheet.selectedItems()  # 获取当前所有选择的items
        for i in s_items:
            i.setBackground(QBrush(QColor(color)))

    def SetColor_ForCellText_ByColorStr(self, row, col, colorStr):
        self.tableWidget_SoundSheet.item(row, col).setForeground(QColor(colorStr))

    def SetColor_ForCellBackground_ByColorStr(self, row, col, colorStr):
        self.tableWidget_SoundSheet.item(row, col).setBackground(QColor(colorStr))

    def SetColor_ForWAVPlaceholder(self, RowColWavList):
        row = RowColWavList[0]
        col = RowColWavList[1]
        placeholderList = RowColWavList[2]

        if len(placeholderList) != 0:
            LOG.warning(lan["LOG_Mirror_TheseWAVsAreSilence"][L] + str(row + 1))
            for wavPath in placeholderList:
                LOG.info(wavPath)
            self.SetColor_ForCellBackground_ByColorStr(row, col, key["DefaultWAVPlaceHolderColor"])

    def ExportRequestXLSX(self):
        try:
            # 获取选中的行数
            rowList = self.GetSelectedRows()
            if len(rowList) != 0:
                # 预备数据池
                ListForExport = []
                NotesForExport = []

                aoligei = SimpleWaapi()
                for r in rowList:
                    vID = self.tableWidget_SoundSheet.item(r, key["Header_ID"]).text()
                    vfName = self.tableWidget_SoundSheet.item(r, key["Header_KeyStr"]).text()
                    vsName = self.tableWidget_SoundSheet.item(r, key["Header_BodyStr"]).text()
                    vtName = self.tableWidget_SoundSheet.item(r, key["Header_TailStr"]).text()
                    vRanNum = self.tableWidget_SoundSheet.item(r, key["Header_RDM"]).text()
                    vNotes = self.tableWidget_SoundSheet.item(r, key["Header_Notes"]).text()

                    tempNTG = aoligei.nameStrGenWithoutCheckDuplicate(vID, vfName, vsName, vtName, vRanNum)

                    # tempNTG[0]是Error小包，如果该小包中产生了报错信息，则直接离开（if/else）当前行的执行，并将信息传入GoLog待打印
                    if len(tempNTG[0]) != 0:
                        LOG.warning("Line" + str(r + 1) + lan["LOG_SM_def_WaapiGo_NamingErrorCheck_FAIL"][L])
                    else:
                        # 生成wav大包
                        # 判断是否为type2d_gun类型
                        if type(tempNTG[2]) is dict:
                            tempList = []
                            for subList in tempNTG[2].values():
                                tempList.append(subList)
                            flatList = [x for x in flatten(tempList)]
                        else:
                            flatList = [x for x in flatten(tempNTG[2])]

                        for items in flatList:
                            ListForExport.append(str(items))

                        # 生成Notes打包
                        if vNotes is not None:
                            NotesForExport.append(vNotes)
                            NotesPlaceholderNum = len(flatList) - 1
                            for n in range(NotesPlaceholderNum):
                                NotesForExport.append("")
                        else:
                            for n in range(len(flatList)):
                                NotesForExport.append("")
                aoligei.__del__()

                # 复制需求表并预备写入
                PossibleSaveAsFolderPath = os.path.join(global_curWwisePath, key["ExportFolderName"])
                if not os.path.exists(PossibleSaveAsFolderPath):
                    os.mkdir(PossibleSaveAsFolderPath)
                targetFileName = "SoundRequest_" + getCurrentTimeStr() + ".xlsx"
                ADVQuickCopy("cf\\RequestTemplate.xlsx", PossibleSaveAsFolderPath, targetFileName)

                # 检查新XLSX是否存在
                NewXLSXName = os.path.join(PossibleSaveAsFolderPath, targetFileName)

                if not os.path.exists(NewXLSXName):
                    LOG.warning(lan["LOG_SC_def_CanNotFindPath"][L] + NewXLSXName)
                else:
                    rXLSX = SimpleXLSX()

                    # 写入列表
                    rXLSX.ReadXLSX(NewXLSXName, 0)
                    if len(ListForExport) != 0 and len(ListForExport) == len(NotesForExport):
                        for i, j in zip(range(len(ListForExport)), range(len(NotesForExport))):
                            rXLSX.WriteCell("A" + str(i + 11), ListForExport[i])
                            rXLSX.WriteCell("D" + str(j + 11), NotesForExport[j])
                    rXLSX.SaveXLSX(NewXLSXName)

                    rXLSX.ReadXLSX(NewXLSXName, 1)
                    if len(ListForExport) != 0 and len(ListForExport) == len(NotesForExport):
                        for i, j in zip(range(len(ListForExport)), range(len(NotesForExport))):
                            rXLSX.WriteCell("A" + str(i + 11), ListForExport[i])
                            rXLSX.WriteCell("D" + str(j + 11), NotesForExport[j])
                    rXLSX.SaveXLSX(NewXLSXName)

                    LOG.info(lan["LOG_RequestXLSXHasBeenCreated"][L])
                    open_file_folder_highlight(NewXLSXName)
        except:
            traceback.print_exc()

    # ----------------------------------------------------------------------------- Panel Func ----- Search Text
    def LineEditTextChanged_SearchText(self):
        search_text = self.lineEdit_SearchText.text()

        # 清除之前的高亮
        cursor = self.textEdit_Log.textCursor()
        cursor.select(cursor.Document)
        formatt = QTextCharFormat()
        formatt.setBackground(Qt.transparent)  # 将背景设置为透明
        cursor.mergeCharFormat(formatt)
        cursor.clearSelection()

        # 设置高亮格式
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor("yellow"))

        # 查找并高亮所有匹配项
        cursor = self.textEdit_Log.document().find(search_text)
        while not cursor.isNull() and not search_text.isspace():
            cursor.mergeCharFormat(highlight_format)
            cursor = self.textEdit_Log.document().find(search_text, cursor)

    def find_next(self):
        # LOG.info("NEXT~~~~~")
        pass

    def find_previous(self):
        # LOG.info("Previous~~~~~")
        pass

    # ----------------------------------------------------------------------------- Panel Func ----- Log Console
    def cleanup(self):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr

    def outputWritten(self, message):
        # 显示输出配置
        formatt = QTextCharFormat()
        if any(error_str in message for error_str in global_logFormat["RED"]):
            formatt.setForeground(QColor("red"))
        elif any(error_str in message for error_str in global_logFormat["ORANGE"]):
            formatt.setForeground(QColor("orange"))
        elif any(error_str in message for error_str in global_logFormat["GREEN"]):
            formatt.setForeground(QColor("green"))
        elif any(error_str in message for error_str in global_logFormat["BLUE"]):
            formatt.setForeground(QColor("blue"))
        elif any(error_str in message for error_str in global_logFormat["PURPLE"]):
            formatt.setForeground(QColor("purple"))
        else:
            formatt.setForeground(QColor("gray"))

        cursor = self.textEdit_Log.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(message, formatt)
        cursor.insertBlock()
        self.textEdit_Log.setTextCursor(cursor)
        self.textEdit_Log.ensureCursorVisible()

    def update_text_edit(self, message):
        # 显示输出配置
        formatt = QTextCharFormat()
        if any(error_str in message for error_str in global_logFormat["RED"]):
            formatt.setForeground(QColor("red"))
        elif any(error_str in message for error_str in global_logFormat["ORANGE"]):
            formatt.setForeground(QColor("orange"))
        elif any(error_str in message for error_str in global_logFormat["GREEN"]):
            formatt.setForeground(QColor("green"))
        elif any(error_str in message for error_str in global_logFormat["BLUE"]):
            formatt.setForeground(QColor("blue"))
        elif any(error_str in message for error_str in global_logFormat["PURPLE"]):
            formatt.setForeground(QColor("purple"))
        else:
            formatt.setForeground(QColor("gray"))

        cursor = self.textEdit_Log.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(message, formatt)
        cursor.insertBlock()
        self.textEdit_Log.setTextCursor(cursor)
        self.textEdit_Log.ensureCursorVisible()

    def update_text_edit_amazing(self, listObj):
        message = listObj[0]
        colorStr = listObj[1]
        # 显示输出配置
        formatt = QTextCharFormat()
        formatt.setForeground(QColor(colorStr))
        cursor = self.textEdit_Log.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(message, formatt)
        cursor.insertBlock()
        self.textEdit_Log.setTextCursor(cursor)
        self.textEdit_Log.ensureCursorVisible()

    def RightClickMenu_textEdit_Log(self):
        Menu = QMenu(self)
        Menu.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))

        action_ClearLog = QAction(lan["GUI_SM_RC_action_clearLog"][L], self)
        Menu.addAction(action_ClearLog)
        action_ClearLog.triggered.connect(self.ClearLog)

        Menu.addSeparator()

        action_StopGlobalCheck = QAction(lan["GUI_SM_RC_action_StopGlobalCheck"][L], self)
        Menu.addAction(action_StopGlobalCheck)
        action_StopGlobalCheck.triggered.connect(self.StopGlobalCheck)

        Menu.addSeparator()

        if key["DevMode"] == "dev":
            action_ExportLog = QAction(lan["GUI_SM_RC_action_exportLog"][L], self)
            Menu.addAction(action_ExportLog)
            action_ExportLog.triggered.connect(self.ExportLog)

        Menu.popup(QCursor.pos())

    def ClearLog(self):
        self.textEdit_Log.clear()

    def StopGlobalCheck(self):
        if self.Thread_GlobalSafetyCheck is not None and self.Thread_GlobalSafetyCheck.isRunning():
            self.Thread_GlobalSafetyCheck.terminate()
            LOG.info(lan["GUI_action_GlobalSafetyCheck_End"][L])

    def ExportLog(self):
        try:
            if os.path.exists(global_debugLogPath):
                subprocess.Popen(['notepad.exe', global_debugLogPath])
        except:
            traceback.print_exc()
            LOG.error(lan["LOG_SM_def_exportLog_FAIL"][L])

    # ----------------------------------------------------------------------------- Panel Func ----- Wavform
    def LocateSingleWAV(self):
        currentWavPath = self.comboBox_RelatedWAV.currentText()
        if len(currentWavPath) != 0 and os.path.exists(currentWavPath):
            open_file_folder_highlight(currentWavPath)

    # ----------------------------------------------------------------------------- Panel Func ----- Preference
    def RefreshJson_comboBox_Language(self):
        self.label_LanguageHint.setVisible(True)
        if self.comboBox_Language.currentIndex() == 0:
            key["Language"] = "Chinese"
        else:
            key["Language"] = "English"

        SaveJson(key, "cf\\json\\UserPreference.json")

    def RefreshJson_comboBox_ShowWelcomePageWhenStart(self):
        if self.comboBox_ShowWelcomePageWhenStart.currentIndex() == 0:
            key["ifNotShowWelcome"] = "True"
        else:
            key["ifNotShowWelcome"] = "False"

        SaveJson(key, "cf\\json\\UserPreference.json")

    def RefreshJson_comboBox_AutoLoadSoundSheetWhenStart(self):
        if self.comboBox_AutoLoadSoundSheetWhenStart.currentIndex() == 0:
            key["ifAutoLoadSoundListJson"] = "True"
        else:
            key["ifAutoLoadSoundListJson"] = "False"

        SaveJson(key, "cf\\json\\UserPreference.json")

    def RefreshJson_comboBox_AutoColorForEventsNotInTable(self):
        if self.comboBox_AutoColorForEventsNotInTable.currentIndex() == 0:
            key["ifColorAfterGlobalSafetyCheck"] = "True"
        else:
            key["ifColorAfterGlobalSafetyCheck"] = "False"

        SaveJson(key, "cf\\json\\UserPreference.json")

    def RefreshJson_comboBox_CopyPasteMode(self):
        if self.comboBox_CopyPasteMode.currentIndex() == 0:
            key["CopyPasteMode"] = "TextOnly"
        elif self.comboBox_CopyPasteMode.currentIndex() == 1:
            key["CopyPasteMode"] = "TextAndBGColor"
        elif self.comboBox_CopyPasteMode.currentIndex() == 2:
            key["CopyPasteMode"] = "BGColorOnly"

        SaveJson(key, "cf\\json\\UserPreference.json")

    def RefreshJson_spinBox_AutoSaveAs(self):
        value = self.spinBox_AutoSaveAs.value()
        if key["ifAutoSaveAs"] == "True":
            if value != 0:
                key["AutoSaveAsEvery"] = value
            else:
                key["AutoSaveAsEvery"] = 5
        else:
            key["AutoSaveAsEvery"] = 0

        self.label_AutoSaveAs.setVisible(True)
        SaveJson(key, "cf\\json\\UserPreference.json")

    def RefreshJson_comboBox_AutoSaveAs(self):
        if self.comboBox_AutoSaveAs.currentIndex() == 0:
            key["ifAutoSaveAs"] = "True"
            self.spinBox_AutoSaveAs.setReadOnly(False)
            if self.spinBox_AutoSaveAs.value() == 0:
                self.spinBox_AutoSaveAs.setValue(5)
        else:
            key["ifAutoSaveAs"] = "False"
            self.spinBox_AutoSaveAs.setValue(0)
            self.spinBox_AutoSaveAs.setReadOnly(True)

        self.label_AutoSaveAs.setVisible(True)
        self.RefreshJson_spinBox_AutoSaveAs()
        SaveJson(key, "cf\\json\\UserPreference.json")

    def RefreshJson_comboBox_AutoGenerateBanks(self):
        if self.comboBox_AutoGenerateBanks.currentIndex() == 0:
            key["AutoGenerateBanks"] = "True"
        else:
            key["AutoGenerateBanks"] = "False"

        SaveJson(key, "cf\\json\\UserPreference.json")

    def RefreshJson_comboBox_LogDisplayLevel(self):
        if self.comboBox_LogDisplayLevel.currentIndex() == 0:
            key["LogDisplayLevel"] = "CRITICAL"
            Log.setLevel(logging.CRITICAL)
        elif self.comboBox_LogDisplayLevel.currentIndex() == 1:
            key["LogDisplayLevel"] = "ERROR"
            Log.setLevel(logging.ERROR)
        elif self.comboBox_LogDisplayLevel.currentIndex() == 2:
            key["LogDisplayLevel"] = "WARNING"
            Log.setLevel(logging.WARNING)
        elif self.comboBox_LogDisplayLevel.currentIndex() == 3:
            key["LogDisplayLevel"] = "INFO"
            Log.setLevel(logging.INFO)
        elif self.comboBox_LogDisplayLevel.currentIndex() == 4:
            key["LogDisplayLevel"] = "DEBUG"
            Log.setLevel(logging.DEBUG)

        SaveJson(key, "cf\\json\\UserPreference.json")

    def LocatePath_ForSaveAs(self):
        Pathh = self.LocatePath_WriteIntoBaseJson("Folder")
        if Pathh is not None:
            self.lineEdit_SaveAsDefaultFolderPath.setText(Pathh)

    def LineEditTextChanged_SaveAsDefaultFolderPath(self):
        try:
            currentText = self.lineEdit_SaveAsDefaultFolderPath.text()
            if os.path.exists(currentText):
                self.lineEdit_SaveAsDefaultFolderPath.setStyleSheet("color:black")
                self.lineEdit_SaveAsDefaultFolderPath.setFont(QFont(self.GetDefaultFont()))
                LocalInfoDict["Path_DefaultSaveAsFolder"] = currentText
                SaveJson(LocalInfoDict, global_curWwiseLocalJson)
            else:
                if len(currentText) != 0:
                    self.lineEdit_SaveAsDefaultFolderPath.setStyleSheet("color:red")
                    self.lineEdit_SaveAsDefaultFolderPath.setFont(QFont(self.GetDefaultFont()))
                else:
                    self.lineEdit_SaveAsDefaultFolderPath.setStyleSheet("color:red")
                    self.lineEdit_SaveAsDefaultFolderPath.setFont(QFont(self.GetDefaultFont()))
                    LocalInfoDict["Path_DefaultSaveAsFolder"] = currentText
                    SaveJson(LocalInfoDict, global_curWwiseLocalJson)
        except:
            traceback.print_exc()

    # ----------------------------------------------------------------------------- Waveform
    def FillWAVComboBox_by_ObjectRefComboBoxItem(self):
        self.comboBox_RelatedWAV.clear()
        currentText = self.comboBox_EventObjectRef.currentText()
        if len(currentText) != 0:
            self.label_RelatedWAVCount.setText(str(len(EventInfoDict[currentText])))
            for wavPath in EventInfoDict[currentText]:
                self.comboBox_RelatedWAV.addItem(wavPath)

    def Display_Waveform(self):
        wavPath = self.comboBox_RelatedWAV.currentText()
        if len(wavPath) != 0 and os.path.exists(wavPath):
            self.WAVPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(wavPath)))
            try:
                signal, sample_rate = sf.read(wavPath)
                # 创建matplotlib图形
                fig = Figure(figsize=(self.MatplotlibGraphicLength, self.MatplotlibGraphicHeight))
                fig.subplots_adjust(top=1, bottom=0, left=0, right=1, hspace=0, wspace=0)
                ax = fig.add_subplot(111)
                ax.plot(signal, color="#DCDCDC")
                ax.set_axis_off()
                ax.margins(0, 0)

                canvas = FigureCanvas(fig)
                self.graphicsView_Scene = QGraphicsScene()
                self.graphicsView_Scene.addWidget(canvas)

                # 在这里加进程判断，如果上一个还在，先停止上一个
                self.graphicsView_Waveform.removeCircle()
                self.graphicsView_Waveform.setScene(self.graphicsView_Scene)
                self.WavformLayout.addWidget(self.graphicsView_Waveform)
                self.WavformLayout.setContentsMargins(0, 0, 0, 0)
                self.Frame_Wavform.setFixedHeight(80)
            except:
                traceback.print_exc()

    def on_left_clicked(self, x):
        duration = self.WAVPlayer.duration()
        self.graphicsView_Waveform.wavLength = duration
        self.graphicsView_Waveform.removeCircle()
        positionMs = duration * x / (self.MatplotlibGraphicLength * 100)
        self.WAVPlayer.setPosition(int(positionMs))
        self.WAVPlayer.play()

    def WhichMouseClick(self, button):
        if button == 2:
            self.WAVPlayer.stop()

    # ----------------------------------------------------------------------------- Global Func Utility
    def QuickTest(self):
        pass

    def GenerateNewID(self):
        # 获取当前所有ID，转为int值，储存在list中
        currentIDList = self.CollectValuesFromColumn(key["Header_ID"])
        newID = GenerateSmallestID(currentIDList)
        return newID

    def SafetyCheck_SoundID_Global(self):
        InvalidList = {}

        AllIDList = []
        InvalidIDStr = []
        MissingIDLineList = []

        for i in range(self.tableWidget_SoundSheet.rowCount()):  # 遍历大表的每一行
            ValueID = self.tableWidget_SoundSheet.item(i, 0).text()  # 获取ID单元格中的数据
            # LOG.debug(ValueID)
            if ValueID is not None and len(ValueID) != 0:  # 检查ID是否缺失（None或长度为0）
                AllIDList.append(ValueID)
                checkResult = ifValidID(ValueID)  # 进一步检查ID内是否包含非法字符
                if checkResult is False:
                    InvalidIDStr.append(i + 1)
            else:
                MissingIDLineList.append(i + 1)

        if len(MissingIDLineList) != 0:  # 这里说明ID缺失，保存到InvalidList中预备返回
            InvalidList["MissingIDLineList"] = MissingIDLineList
        if len(InvalidIDStr) != 0:  # 这里说明ID中存在非法字符，保存到InvalidList中预备返回
            InvalidList["InvalidIDStrList"] = InvalidIDStr

        # 进一步查重
        compare = dict(Counter(AllIDList))
        compareResult = [Key for Key, value in compare.items() if value > 1]

        if len(compareResult) != 0:  # 这里说明存在重复的ID，保存到InvalidList中预备返回
            InvalidList["DuplicatedIDList"] = compareResult

        return InvalidList

    def ShowHidePanel(self, guiObject):
        if guiObject.isVisible() is False:
            if guiObject is self.Frame_Filter:
                self.Refresh_Filter()
            guiObject.setVisible(True)
        else:
            guiObject.setVisible(False)

    def ShowHideColumn(self):
        TarColumn = [4, 5, 6, 7, 8, 9]
        for col in TarColumn:
            if self.tableWidget_SoundSheet.isColumnHidden(col) is False:
                self.tableWidget_SoundSheet.setColumnHidden(col, True)
            else:
                self.tableWidget_SoundSheet.setColumnHidden(col, False)

    @staticmethod
    def ClearLayout(layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    @staticmethod
    def AutoSwitch_NoneValue_Into_StringValue(value):
        if value == "None":
            return ""
        else:
            return str(value)

    @staticmethod
    def GetDefaultFont():
        if key["Language"] == "Chinese":
            Font_Def = key["DefaultFont_Chinese"]
        else:
            Font_Def = key["DefaultFont_English"]

        return Font_Def

    @staticmethod
    def OpenWindow(windowObject):
        windowObject.ui.show()

    @staticmethod
    def LocatePath_WriteIntoLocalJson(FileType, TargetKeyStr):
        """
        :param FileType: File; Folder
        :param TargetKeyStr: key
        :return: Absolute Path
        """

        file_dialog = QFileDialog()

        if FileType == "File":
            file_dialog.setFileMode(QFileDialog.AnyFile)
        elif FileType == "Folder":
            file_dialog.setFileMode(QFileDialog.DirectoryOnly)
        else:
            file_dialog.setFileMode(QFileDialog.AnyFile)

        previousPath = LocalInfoDict[TargetKeyStr]
        if file_dialog.exec_():
            selected_path = str(file_dialog.selectedFiles()[0])
            selected_path = selected_path.replace("/", "\\")
            LocalInfoDict[TargetKeyStr] = selected_path
            SaveJson(LocalInfoDict, global_curWwiseLocalJson)
            return selected_path
        else:
            LocalInfoDict[TargetKeyStr] = previousPath
            SaveJson(LocalInfoDict, global_curWwiseLocalJson)
            return None

    @staticmethod
    def LocatePath_SoundIDStatusJson(FileType, TargetKeyStr):
        """
        :param FileType: File; Folder
        :param TargetKeyStr: key
        :return: Absolute Path
        """

        file_dialog = QFileDialog()

        if FileType == "File":
            file_dialog.setFileMode(QFileDialog.AnyFile)
        elif FileType == "Folder":
            file_dialog.setFileMode(QFileDialog.DirectoryOnly)
        else:
            file_dialog.setFileMode(QFileDialog.AnyFile)

        previousPath = LocalInfoDict[TargetKeyStr]
        if file_dialog.exec_():
            selected_path = str(file_dialog.selectedFiles()[0])
            selected_path = selected_path.replace("/", "\\")
            LocalInfoDict[TargetKeyStr] = selected_path
            SaveJson(LocalInfoDict, global_curWwiseLocalJson)
            return selected_path
        else:
            LocalInfoDict[TargetKeyStr] = previousPath
            SaveJson(LocalInfoDict, global_curWwiseLocalJson)
            return None

    @staticmethod
    def LocatePath_WriteIntoBaseJson(FileType):
        """
        :param FileType: File; Folder
        :param TargetKeyStr: key
        :return: Absolute Path
        """

        file_dialog = QFileDialog()

        if FileType == "File":
            file_dialog.setFileMode(QFileDialog.AnyFile)
        elif FileType == "Folder":
            file_dialog.setFileMode(QFileDialog.DirectoryOnly)
        else:
            file_dialog.setFileMode(QFileDialog.AnyFile)

        if file_dialog.exec_():
            selected_path = str(file_dialog.selectedFiles()[0])
            selected_path = selected_path.replace("/", "\\")
            return selected_path
        else:
            return None

    def CollectValuesFromColumn(self, column):
        textList = []
        rowCount = self.tableWidget_SoundSheet.rowCount()
        if rowCount != 0:
            if column not in [key["Header_ID"], key["Header_Notes"], key["Header_EventName"], key["Header_BankName"],
                              key["Header_KeyStr"], key["Header_BodyStr"], key["Header_TailStr"], key["Header_RDM"],
                              key["Header_Lock"], key["Header_MirrorFrom"]]:
                LOG.error(lan["GUI_LOG_ColumnNumNotValid"][L] + str(column))
            else:
                for row in range(rowCount):
                    if self.tableWidget_SoundSheet.item(row, column) is not None:
                        if column == key["Header_ID"]:
                            idStr = self.tableWidget_SoundSheet.item(row, column).text()
                            if SafetyCheck_IfCharInStringAreAllNum(idStr) is True:
                                textList.append(int(idStr))
                        else:
                            textList.append(self.tableWidget_SoundSheet.item(row, column).text())
        return textList

    def GetSelectedRows(self):
        rowList = []
        items = self.tableWidget_SoundSheet.selectedItems()
        for cell in items:
            rowList.append(cell.row())

        rowList = sorted(list(set(rowList)))

        return rowList

    def GetSelectedCols(self):
        ColList = []
        items = self.tableWidget_SoundSheet.selectedItems()
        for cell in items:
            ColList.append(cell.column())

        ColList = sorted(list(set(ColList)))

        return ColList

    def MessageBox(self, titleText, infoText, func, *args):
        messageBox = QMessageBox(QMessageBox.Warning, titleText, infoText)
        messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
        Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
        Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
        messageBox.exec_()

        if messageBox.clickedButton() == Qyes:
            func(*args)

    def MessageBox_NoArgs(self, titleText, infoText, func):
        messageBox = QMessageBox(QMessageBox.Warning, titleText, infoText)
        messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
        Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
        Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
        messageBox.exec_()

        if messageBox.clickedButton() == Qyes:
            func()

    def MessageBox_NoticeOnly(self, titleText, infoText):
        messageBox = QMessageBox(QMessageBox.Warning, titleText, infoText)
        messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
        Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
        Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
        messageBox.exec_()

        if messageBox.clickedButton() == Qyes:
            pass

    def closeEvent(self, event):
        # 先检查ID是否有重复、缺失
        CheckResult = self.SafetyCheck_SoundID_Global()
        if len(CheckResult) != 0:  # 到这里，说明检测到非法ID
            MissingIDLineList = CheckResult.get("MissingIDLineList", [])
            InvalidIDStrList = CheckResult.get("InvalidIDStrList", [])
            DuplicatedIDList = CheckResult.get("DuplicatedIDList", [])

            if len(MissingIDLineList) != 0:
                LOG.warning(lan["GUI_LOG_MissingIDLine"][L] + str(MissingIDLineList))
                event.ignore()
            if len(InvalidIDStrList) != 0:
                LOG.warning(lan["GUI_LOG_InvalidIDLine"][L] + str(InvalidIDStrList))
                event.ignore()
            if len(DuplicatedIDList) != 0:
                LOG.warning(lan["GUI_LOG_InvalidIDLine"][L] + str(DuplicatedIDList))
                event.ignore()
        else:
            if self.NeedSafeFlag == 1:
                # 关闭窗口时触发以下事件
                messageBox = QMessageBox(QMessageBox.Warning, lan["GUI_LOG_SafetyCheckBeforeSave"][L],
                                         lan["GUI_LOG_NotSavedYet"][L])
                messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
                Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
                Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
                messageBox.exec_()
                if messageBox.clickedButton() == Qyes:
                    event.accept()
                else:
                    event.ignore()

    def Get_AllCurrentID(self):
        # 获取所有的ID
        AllIDList = []
        for row in range(self.tableWidget_SoundSheet.rowCount()):
            AllIDList.append(self.tableWidget_SoundSheet.item(row, key["Header_ID"]).text())
        return AllIDList

    def Get_AllCurrentKeyStr(self):
        # 获取所有的KeyStr
        AllKeyStrList = []
        for row in range(self.tableWidget_SoundSheet.rowCount()):
            AllKeyStrList.append(self.tableWidget_SoundSheet.item(row, key["Header_KeyStr"]).text())
        AllKeyStrList = list(set(AllKeyStrList))
        return AllKeyStrList

    def SafetyCheck_ID(self, SoundID, AllSoundIDList):
        errorLog = []

        # 全量检查待执行区域内是否存在合法ID、缺失ID、重复ID（存入非法ID组）（将表格全局所有ID汇总到ListA中，将待执行区域的ID会中的ListB中；遍历ListB中每一个ID，与ListA中的每一个元素对比，将同样的值放在新List中，检查新List的元素数量，如果大于1，说明这个ID有重复）
        # 合法ID检查（输入是否合法、是否缺失）
        if SoundID == "None" or ifValidID(SoundID) is False:
            errorLog.append("error")

        # 重复ID检查
        if SoundID != "None" and len(SoundID) != 0:
            tempCount = 0
            for sid in AllSoundIDList:
                if sid == SoundID:
                    tempCount += 1
            if tempCount > 1:
                errorLog.append("error")

        return errorLog

    def WriteCell_ForTable(self, tarRow, tarCol, tarID, tarObj, text):
        item = QTableWidgetItem(text)
        item.setForeground(QColor(SoundListDict["Data_SoundList"][tarID][tarObj]["textColor"]))
        item.setBackground(QColor(SoundListDict["Data_SoundList"][tarID][tarObj]["bgColor"]))
        self.tableWidget_SoundSheet.setItem(tarRow, tarCol, item)

    def SetColor_ColumnHeader_Background(self):
        for col_index in [4, 5, 6, 7, 8, 9]:
            font = QFont(key["DefaultFont_English"])
            font.setBold(True)
            self.tableWidget_SoundSheet.horizontalHeaderItem(col_index).setFont(font)
            self.tableWidget_SoundSheet.horizontalHeaderItem(col_index).setBackground(QColor(255, 0, 0))

    def PreSafetyCheck_General(self, startLog, endLog, func):
        # 先判断保存状态
        if self.NeedSafeFlag == 1:
            # 关闭窗口时触发以下事件
            messageBox = QMessageBox(QMessageBox.Warning, lan["GUI_LOG_NotSavedYet_PreCheckBeforeImplement_Title"][L],
                                     lan["GUI_LOG_NotSavedYet_PreCheckBeforeImplement_Text"][L])
            messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
            Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
            Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
            messageBox.exec_()
            if messageBox.clickedButton() == Qyes:
                pass
        else:
            # 获取选中的行数
            rowList = self.GetSelectedRows()
            TotalRowNum = len(rowList)
            if TotalRowNum != 0:  # 如果有被选中的行
                # 提示安全检查开始
                LOG.info(startLog)
                self.textEdit_Log.setVisible(True)
                self.Frame_SearchText.setVisible(True)
                # Log.info(startLog)

                # 获取全局所有ID
                AllIDList = self.Get_AllCurrentID()

                # 创建ErrorDict结构
                ErrorDictLog = {
                    "Invalid_Lock": [],
                    "Invalid_ID": {},
                    "Invalid_KeyStr": {},
                    "Invalid_KeyStr_Path": [],
                    "Invalid_RDM": {},
                    "Invalid_EventStr": {},
                    "Invalid_MirrorID": {},
                    "Invalid_BankFilled": {}
                }
                invalidRowList = []

                # 连接Wwise
                aoligei = SimpleWaapi()

                # 预备进度条
                self.progressBar.setVisible(True)
                ProgressBar_Count = 0

                # 获取每一行的Lock、ID、KeyStr、RDM的值
                for row in rowList:
                    text_Lock = self.tableWidget_SoundSheet.item(row, key["Header_Lock"]).text()
                    text_ID = self.tableWidget_SoundSheet.item(row, key["Header_ID"]).text()
                    text_KeyStr = self.tableWidget_SoundSheet.item(row, key["Header_KeyStr"]).text()
                    text_RDM = self.tableWidget_SoundSheet.item(row, key["Header_RDM"]).text()
                    text_EventName = self.tableWidget_SoundSheet.item(row, key["Header_EventName"]).text()
                    text_MirrorFrom = self.tableWidget_SoundSheet.item(row, key["Header_MirrorFrom"]).text()
                    text_BankName = self.tableWidget_SoundSheet.item(row, key["Header_BankName"]).text()

                    # 检查Lock状态
                    if len(text_Lock) != 0:
                        ErrorDictLog["Invalid_Lock"].append(row + 1)
                        invalidRowList.append(row)

                    # 检查ID状态
                    PossibleDuplicatedID = self.SafetyCheck_ID(text_ID, AllIDList)
                    if len(PossibleDuplicatedID) != 0:
                        ErrorDictLog["Invalid_ID"][lan["SC_ROW"][L] + str(row + 1)] = text_ID
                        invalidRowList.append(row)

                    # 检查KeyStr状态
                    if len(text_KeyStr) == 0 or text_KeyStr not in list(KeyInfoDict["Data_KeyInfo"].keys()):
                        ErrorDictLog["Invalid_KeyStr"][lan["SC_ROW"][L] + str(row + 1)] = text_KeyStr
                        invalidRowList.append(row)
                    else:
                        result = aoligei.Check_IfKeyStrWWUInWwise(text_KeyStr)
                        if result is False:
                            ErrorDictLog["Invalid_KeyStr"][lan["SC_ROW"][L] + str(row + 1)] = text_KeyStr
                            invalidRowList.append(row)

                        wwisePathCheckResult = aoligei.Check_IfPathsOfKeyStrExistInWwise(text_KeyStr)
                        if len(wwisePathCheckResult) != 0:
                            ErrorDictLog["Invalid_KeyStr_Path"] = wwisePathCheckResult
                            invalidRowList.append(row)

                    # 检查RDM状态
                    if text_RDM not in key["validRanNum"]:
                        ErrorDictLog["Invalid_RDM"][lan["SC_ROW"][L] + str(row + 1)] = text_RDM
                        invalidRowList.append(row)

                    # 单独给ExpandSwitch和ReCreateCompletely做进一步检查
                    if func.__name__ == "ExpandSwitch" or func.__name__ == "ReCreateCompletely":
                        # 检查EventStr状态
                        if len(text_EventName) == 0:
                            ErrorDictLog["Invalid_EventStr"][lan["SC_ROW"][L] + str(row + 1)] = text_EventName
                            invalidRowList.append(row)

                    # 单独给MirrorID做进一步检查
                    if func.__name__ == "MirrorData":
                        # 检查MirrorID状态
                        if len(text_MirrorFrom) == 0:
                            ErrorDictLog["Invalid_MirrorID"][lan["SC_ROW"][L] + str(row + 1)] = text_MirrorFrom
                            invalidRowList.append(row)

                    # 判断Bank信息是否清除
                    if len(text_BankName) != 0:
                        ErrorDictLog["Invalid_BankFilled"][lan["SC_ROW"][L] + str(row + 1)] = text_BankName
                        invalidRowList.append(row)

                    # 更新ProgressBar状态
                    ProgressBar_Count += 1
                    self.progressBar.setValue(int(ProgressBar_Count / TotalRowNum * 100))

                # 确保与Wwise断联
                aoligei.__del__()

                # 收起进度条
                self.progressBar.setVisible(False)

                # 清算ErrorDict，打印报告
                invalidRowList = list(set(invalidRowList))
                if len(invalidRowList) != 0:
                    # 获取合法的行
                    validRowList = []
                    validRowList_forUserRead = []
                    for row in rowList:
                        if row not in invalidRowList:
                            validRowList.append(row)
                            validRowList_forUserRead.append(row + 1)

                    # 打印不合法的行信息
                    if len(ErrorDictLog["Invalid_Lock"]) != 0:
                        LOG.warning("\n" + lan["SC_Invalid_Lock"][L])
                        LOG.warning(str(ErrorDictLog["Invalid_Lock"]))

                    if len(ErrorDictLog["Invalid_ID"]) != 0:
                        LOG.warning("\n" + lan["SC_Invalid_ID"][L])
                        LOG.warning(ErrorDictLog["Invalid_ID"])

                    if len(ErrorDictLog["Invalid_KeyStr"]) != 0:
                        LOG.warning("\n" + lan["SC_Invalid_KeyStr"][L])
                        LOG.warning(ErrorDictLog["Invalid_KeyStr"])

                    if len(ErrorDictLog["Invalid_KeyStr_Path"]) != 0:
                        LOG.warning("\n" + lan["SC_Invalid_KeyStr_Path"][L])
                        LOG.warning(ErrorDictLog["Invalid_KeyStr_Path"])

                    if len(ErrorDictLog["Invalid_RDM"]) != 0:
                        LOG.warning("\n" + lan["SC_Invalid_RDM"][L])
                        LOG.warning(ErrorDictLog["Invalid_RDM"])

                    if len(ErrorDictLog["Invalid_EventStr"]) != 0:
                        LOG.warning("\n" + lan["SC_Invalid_EventStr"][L])
                        LOG.warning(ErrorDictLog["Invalid_EventStr"])

                    if len(ErrorDictLog["Invalid_MirrorID"]) != 0:
                        LOG.warning("\n" + lan["SC_Invalid_MirrorID"][L])
                        LOG.warning(ErrorDictLog["Invalid_MirrorID"])

                    if len(ErrorDictLog["Invalid_BankFilled"]) != 0:
                        LOG.warning("\n" + lan["SC_Invalid_BankFilled"][L])
                        LOG.warning(ErrorDictLog["Invalid_BankFilled"])

                    # 打印进度
                    LOG.info(endLog)

                    # 弹窗提示，用户选择
                    if len(validRowList) != 0:
                        self.MessageBox(lan["SC_END_WindowTitle"][L],
                                        lan["SC_END_WindowText"][L] + str(validRowList_forUserRead),
                                        func, validRowList)
                    else:
                        self.MessageBox(lan["SC_END_WindowTitle"][L], lan["SC_END_WindowText_ALLFAILED"][L],
                                        func, validRowList)
                else:
                    # 打印进度
                    LOG.info(endLog)
                    textMatch = {
                        self.GO: "SC_SafetyCheckStartNotice_Text_GO",
                        self.ExpandSwitch: "SC_SafetyCheckStartNotice_Text_ExpandSwitch",
                        self.MirrorData: "SC_SafetyCheckStartNotice_Text_MirrorID",
                        self.ReCreateCompletely: "SC_SafetyCheckStartNotice_Text_RereateEvent"
                    }
                    self.MessageBox(lan["SC_SafetyCheckStartNotice_Title"][L],
                                    lan[textMatch[func]][L], func, rowList)

    def ChangeOrder(self):
        # 先判断保存状态
        if self.NeedSafeFlag == 1:
            # 关闭窗口时触发以下事件
            messageBox = QMessageBox(QMessageBox.Warning, lan["GUI_LOG_NotSavedYet_PreCheckBeforeSorting_Title"][L],
                                     lan["GUI_LOG_NotSavedYet_PreCheckBeforeImplement_Text"][L])
            messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
            Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
            Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
            messageBox.exec_()
            if messageBox.clickedButton() == Qyes:
                pass
        else:
            # 获取选中的行数
            colList = self.GetSelectedCols()
            TotalColNum = len(colList)
            if TotalColNum == 1:  # 如果有选中某个特定的行
                self.textEdit_Log.setVisible(True)
                self.Frame_SearchText.setVisible(True)
                col = colList[0]
                # 根据行数排序
                if self.tableWidget_SoundSheet_Order == Qt.DescendingOrder:
                    self.tableWidget_SoundSheet_Order = Qt.AscendingOrder
                else:
                    self.tableWidget_SoundSheet_Order = Qt.DescendingOrder

                # 无法撤销提示
                messageBox = QMessageBox(QMessageBox.Warning, lan["GUI_LOG_OrderCanNotBeRedo_Title"][L],
                                         lan["GUI_LOG_OrderCanNotBeRedo_Text"][L])
                messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
                Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
                Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
                messageBox.exec_()
                if messageBox.clickedButton() == Qyes:
                    self.tableWidget_SoundSheet.sortItems(col, self.tableWidget_SoundSheet_Order)

                    # 添加提示保存
                    self.NeedSafeFlag = 1
                    self.SetState_Save()

                    # 清理Undo或Redo历史防止误修改
                    UndoList.clear()
                    RedoList.clear()
                    self.UndoRedoNumShow()

                    LOG.info(lan["GUI_LOG_Ordered_Done"][L])
            else:
                LOG.info(lan["GUI_LOG_Ordered_Cancel"][L])

