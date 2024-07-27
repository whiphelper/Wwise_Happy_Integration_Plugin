import os.path
import traceback

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QCursor
from PyQt5.QtWidgets import QWidget, QFileDialog, QHeaderView, QTableWidgetItem, QMenu, QAction
from SimpleWaapi import *


class Window_InitSession(QWidget):
    def __init__(self):
        super().__init__()

        # Load GUI
        self.ui = uic.loadUi("cf\\gui\\InitSession.ui")
        self.ui.setWindowTitle(lan["GUI_InitSession_WindowTitle"][L])

        # Init items
        self.pushButton_WriteIntoWwise = self.ui.pushButton_WriteIntoWwise
        self.lineEdit_ActualGeneratedBankPath = self.ui.lineEdit_ActualGeneratedBankPath
        self.pushButton_CheckDiff = self.ui.pushButton_CheckDiff
        self.pushButton_ActualGeneratedBankPath = self.ui.pushButton_ActualGeneratedBankPath
        self.lineEdit_AddColumnForTable = self.ui.lineEdit_AddColumnForTable
        self.pushButton_LocatePath_SoundIDSTatusReport = self.ui.pushButton_LocatePath_SoundIDSTatusReport
        self.lineEdit_SoundIDSTatusReportPath = self.ui.lineEdit_SoundIDSTatusReportPath

        self.groupBox_ProjectSettings = self.ui.groupBox_ProjectSettings
        self.groupBox_Bus = self.ui.groupBox_Bus
        self.treeWidget_Bus = self.ui.treeWidget_Bus
        self.listWidget_CurrentBusStatus = self.ui.listWidget_CurrentBusStatus
        self.groupBox_PitchRandom = self.ui.groupBox_PitchRandom
        self.groupBox_Switch = self.ui.groupBox_Switch
        self.groupBox_State = self.ui.groupBox_State
        self.groupBox_RTPC = self.ui.groupBox_RTPC
        self.groupBox_Conversion = self.ui.groupBox_Conversion
        self.groupBox_Attenuation = self.ui.groupBox_Attenuation
        self.groupBox_SideChain = self.ui.groupBox_SideChain

        self.label_ProjectSettings = self.ui.label_ProjectSettings_Read
        self.label_Bus = self.ui.label_Bus_Read
        self.label_Switch = self.ui.label_Switch_Read
        self.label_State = self.ui.label_State_Read
        self.label_Conversion = self.ui.label_Conversion_Read
        self.label_Attenuation = self.ui.label_Attenuation_Read
        self.label_RTPC = self.ui.label_RTPC_Read
        self.label_SideChain = self.ui.label_SideChain_Read

        self.label_ProjectSettings_Write = self.ui.label_ProjectSettings_Write
        self.label_Bus_Write = self.ui.label_Bus_Write
        self.label_Switch_Write = self.ui.label_Switch_Write
        self.label_State_Write = self.ui.label_State_Write
        self.label_Conversion_Write = self.ui.label_Conversion_Write
        self.label_Attenuation_Write = self.ui.label_Attenuation_Write
        self.label_RTPC_Write = self.ui.label_RTPC_Write
        self.label_SideChain_Write = self.ui.label_SideChain_Write

        self.checkbox_GenerateMultipleBanks = self.ui.checkbox_GenerateMultipleBanks
        self.checkbox_SoundBankGeneratePrintGUID = self.ui.checkbox_SoundBankGeneratePrintGUID
        self.checkbox_SoundBankGenerateMaxAttenuationInfo = self.ui.checkbox_SoundBankGenerateMaxAttenuationInfo
        self.checkBox_SoundBankGenerateEstimatedDuration = self.ui.checkBox_SoundBankGenerateEstimatedDuration
        self.checkbox_GenerateSoundBankJSON = self.ui.checkbox_GenerateSoundBankJSON

        self.label_PitchRandom_Min = self.ui.label_PitchRandom_Min
        self.label_PitchRandom_Max = self.ui.label_PitchRandom_Max
        self.lineEdit_PitchRandom_Min = self.ui.lineEdit_PitchRandom_Min
        self.lineEdit_PitchRandom_Max = self.ui.lineEdit_PitchRandom_Max

        self.tableWidget_Switch = self.ui.tableWidget_Switch
        self.tableWidget_State = self.ui.tableWidget_State
        self.tableWidget_RTPC = self.ui.tableWidget_RTPC
        self.tableWidget_Conversion = self.ui.tableWidget_Conversion
        self.tableWidget_Attenuation = self.ui.tableWidget_Attenuation
        self.tableWidget_SideChain = self.ui.tableWidget_SideChain

        self.tableWidget_Switch.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tableWidget_State.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tableWidget_RTPC.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tableWidget_Conversion.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tableWidget_Attenuation.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tableWidget_SideChain.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.tableWidget_Switch.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget_Switch.customContextMenuRequested.connect(
            lambda: self.RightClickMenu_tableWidget_SoundSheet(self.tableWidget_Switch))
        self.tableWidget_State.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget_State.customContextMenuRequested.connect(
            lambda: self.RightClickMenu_tableWidget_SoundSheet(self.tableWidget_State))
        self.tableWidget_RTPC.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget_RTPC.customContextMenuRequested.connect(
            lambda: self.RightClickMenu_tableWidget_SoundSheet(self.tableWidget_RTPC))
        self.tableWidget_Attenuation.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget_Attenuation.customContextMenuRequested.connect(
            lambda: self.RightClickMenu_tableWidget_SoundSheet(self.tableWidget_Attenuation))
        self.tableWidget_SideChain.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget_SideChain.customContextMenuRequested.connect(
            lambda: self.RightClickMenu_tableWidget_SoundSheet(self.tableWidget_SideChain))

        # Set Logic
        self.pushButton_CheckDiff.setText(lan["GUI_BTN_CheckDiff"][L])
        self.pushButton_WriteIntoWwise.setText(lan["GUI_BTN_WriteIntoWwise"][L])
        self.pushButton_CheckDiff.clicked.connect(self.PreCheck_CheckDiff)
        self.pushButton_WriteIntoWwise.clicked.connect(self.WriteIntoWwise)
        self.pushButton_WriteIntoWwise.setEnabled(False)
        self.lineEdit_AddColumnForTable.setReadOnly(True)
        self.lineEdit_AddColumnForTable.setPlaceholderText(lan["GUI_InitSession_AddNewPlaceholderText"][L])
        self.lineEdit_AddColumnForTable.textChanged.connect(lambda: self.LineEditTextChanged_AddNewName(self.lineEdit_AddColumnForTable))

        self.pushButton_ActualGeneratedBankPath.setText(lan["GUI_BTN_ActualGeneratedSoundBankPathOfOnePlatform"][L])
        self.pushButton_ActualGeneratedBankPath.clicked.connect(self.LocatePath_UserDefined_ActualGeneratedSoundBank)
        self.lineEdit_ActualGeneratedBankPath.setText(LocalInfoDict["ActualGeneratedSoundBankPathOfOnePlatform"])
        self.lineEdit_ActualGeneratedBankPath.textChanged.connect(lambda: self.LineEditTextChanged_ActualSoundBankPath(self.lineEdit_ActualGeneratedBankPath))

        self.pushButton_LocatePath_SoundIDSTatusReport.setText(lan["GUI_LineEdit_Path_SoundIDSTatusReport"][L])
        self.pushButton_LocatePath_SoundIDSTatusReport.clicked.connect(self.LocatePath_UserDefined_SoundIDSTatusReportPath)
        self.lineEdit_SoundIDSTatusReportPath.setText(LocalInfoDict["Path_SoundIDSTatusReport"])
        self.lineEdit_SoundIDSTatusReportPath.textChanged.connect(lambda: self.LineEditTextChanged_SoundIDSTatusReportPath(self.lineEdit_SoundIDSTatusReportPath))

        self.groupBox_ProjectSettings.setTitle(lan["GUI_InitSession_ProjectSettings"][L])
        self.groupBox_Bus.setTitle(lan["GUI_InitSession_Bus"][L])
        self.groupBox_PitchRandom.setTitle(lan["GUI_InitSession_Pitch"][L])
        self.groupBox_Switch.setTitle(lan["GUI_InitSession_Switch"][L])
        self.groupBox_State.setTitle(lan["GUI_InitSession_State"][L])
        self.groupBox_RTPC.setTitle(lan["GUI_InitSession_RTPC"][L])
        self.groupBox_Conversion.setTitle(lan["GUI_InitSession_Conversion"][L])
        self.groupBox_Attenuation.setTitle(lan["GUI_InitSession_Attenuations"][L])
        self.groupBox_SideChain.setTitle(lan["GUI_InitSession_SideChain"][L])

        self.treeWidget_Bus.setVisible(True)
        self.listWidget_CurrentBusStatus.setVisible(False)

        self.checkbox_GenerateSoundBankJSON.setVisible(False)
        self.checkbox_GenerateMultipleBanks.stateChanged.connect(lambda: self.CheckBox_StateChanged_WriteJson(self.checkbox_GenerateMultipleBanks))
        self.checkbox_SoundBankGeneratePrintGUID.stateChanged.connect(lambda: self.CheckBox_StateChanged_WriteJson(self.checkbox_SoundBankGeneratePrintGUID))
        self.checkbox_SoundBankGenerateMaxAttenuationInfo.stateChanged.connect(lambda: self.CheckBox_StateChanged_WriteJson(self.checkbox_SoundBankGenerateMaxAttenuationInfo))
        self.checkBox_SoundBankGenerateEstimatedDuration.stateChanged.connect(lambda: self.CheckBox_StateChanged_WriteJson(self.checkBox_SoundBankGenerateEstimatedDuration))

        self.label_PitchRandom_Min.setText(lan["GUI_InitSession_label_PitchRandom_Min"][L])
        self.label_PitchRandom_Max.setText(lan["GUI_InitSession_label_PitchRandom_Max"][L])
        self.lineEdit_PitchRandom_Min.textChanged.connect(self.LineEdit_TextChanged_WriteJson)
        self.lineEdit_PitchRandom_Max.textChanged.connect(self.LineEdit_TextChanged_WriteJson)

        self.Init_WaapiStatusLabels()
        # self.CheckDiff()
        self.TableCellChanged_Connect()

    # ----------------------------------------------------------------------- Init Funcs
    def Init_WaapiStatusLabels(self):
        # ------------------------------------------------------------------------------------------ Read
        self.label_ProjectSettings.setText(lan["GUI_InitSession_ThisVersionCanNotSync"][L])
        self.SetTextColor_WithLanguageConsidered(self.label_ProjectSettings, "red", 8)

        self.label_Bus.setText(lan["GUI_InitSession_ThisVersionCanNotSync"][L])
        self.SetTextColor_WithLanguageConsidered(self.label_Bus, "red", 8)

        self.label_Switch.setText(lan["GUI_InitSession_ThisVersionCanNotSync"][L])
        self.SetTextColor_WithLanguageConsidered(self.label_Switch, "red", 8)

        self.label_State.setText(lan["GUI_InitSession_ThisVersionCanNotSync"][L])
        self.SetTextColor_WithLanguageConsidered(self.label_State, "red", 8)

        self.label_Conversion.setText(lan["GUI_InitSession_ThisVersionCanNotSync"][L])
        self.SetTextColor_WithLanguageConsidered(self.label_Conversion, "red", 8)

        self.label_Attenuation.setText(lan["GUI_InitSession_ThisVersionCanNotSync"][L])
        self.SetTextColor_WithLanguageConsidered(self.label_Attenuation, "red", 8)

        self.label_RTPC.setText(lan["GUI_InitSession_ThisVersionCanNotSync"][L])
        self.SetTextColor_WithLanguageConsidered(self.label_RTPC, "red", 8)

        self.label_SideChain.setText(lan["GUI_InitSession_ThisVersionCanNotSync"][L])
        self.SetTextColor_WithLanguageConsidered(self.label_SideChain, "red", 8)

        # ------------------------------------------------------------------------------------------ Write
        self.label_ProjectSettings_Write.setText(lan["GUI_InitSession_ThisVersionCanNotWrite"][L])
        self.SetTextColor_WithLanguageConsidered(self.label_ProjectSettings_Write, "red", 8)

        self.label_Bus_Write.setText(lan["GUI_InitSession_ThisVersionCanNotWrite"][L])
        self.SetTextColor_WithLanguageConsidered(self.label_Bus_Write, "red", 8)

        self.label_Switch_Write.setText(lan["GUI_InitSession_ThisVersionCanNotWrite"][L])
        self.SetTextColor_WithLanguageConsidered(self.label_Switch_Write, "red", 8)

        self.label_State_Write.setText(lan["GUI_InitSession_ThisVersionCanNotWrite"][L])
        self.SetTextColor_WithLanguageConsidered(self.label_State_Write, "red", 8)

        self.label_Conversion_Write.setText(lan["GUI_InitSession_ThisVersionCanNotWrite"][L])
        self.SetTextColor_WithLanguageConsidered(self.label_Conversion_Write, "red", 8)

        self.label_Attenuation_Write.setText(lan["GUI_InitSession_ThisVersionCanNotWrite"][L])
        self.SetTextColor_WithLanguageConsidered(self.label_Attenuation_Write, "red", 8)

        self.label_RTPC_Write.setText(lan["GUI_InitSession_ThisVersionCanNotWrite"][L])
        self.SetTextColor_WithLanguageConsidered(self.label_RTPC_Write, "red", 8)

        self.label_SideChain_Write.setText(lan["GUI_InitSession_ThisVersionCanNotWrite"][L])
        self.SetTextColor_WithLanguageConsidered(self.label_SideChain_Write, "red", 8)

        # ------------------------------------------------------------------------------------------ Read
        self.label_ProjectSettings.setVisible(False)
        self.label_Bus.setVisible(False)
        self.label_Switch.setVisible(False)
        self.label_State.setVisible(False)
        self.label_Conversion.setVisible(False)
        self.label_Attenuation.setVisible(False)
        self.label_RTPC.setVisible(False)
        self.label_SideChain.setVisible(False)

        # ------------------------------------------------------------------------------------------ Write
        self.label_ProjectSettings_Write.setVisible(False)
        self.label_Bus_Write.setVisible(False)
        self.label_Switch_Write.setVisible(False)
        self.label_State_Write.setVisible(False)
        self.label_Conversion_Write.setVisible(False)
        self.label_Attenuation_Write.setVisible(False)
        self.label_RTPC_Write.setVisible(False)
        self.label_SideChain_Write.setVisible(False)

        # 根据KeyInfoDict["WaapiStatusDict_Read"]直接安排GUI显示结果
        if KeyInfoDict["WaapiStatusDict_Read"]["Init_ProjectSettings"] == "False":
            self.label_ProjectSettings.setVisible(True)
        if KeyInfoDict["WaapiStatusDict_Read"]["Init_BUS"] == "False":
            self.label_Bus.setVisible(True)
        if KeyInfoDict["WaapiStatusDict_Read"]["Init_Switch"] == "False":
            self.label_Switch.setVisible(True)
        if KeyInfoDict["WaapiStatusDict_Read"]["Init_State"] == "False":
            self.label_State.setVisible(True)
        if KeyInfoDict["WaapiStatusDict_Read"]["Init_RTPC_Value"] == "False":
            self.label_RTPC.setText(lan["GUI_InitSession_ThisVersionCanNotSync_Value"][L])
            self.label_RTPC.setVisible(True)
        if KeyInfoDict["WaapiStatusDict_Read"]["Init_RTPC"] == "False":
            self.label_RTPC.setText(lan["GUI_InitSession_ThisVersionCanNotSync"][L])
            self.label_RTPC.setVisible(True)
        if KeyInfoDict["WaapiStatusDict_Read"]["Init_SideChain"] == "False":
            self.label_SideChain.setVisible(True)
        if KeyInfoDict["WaapiStatusDict_Read"]["Init_Attenuation_Value"] == "False":
            self.label_Attenuation.setText(lan["GUI_InitSession_ThisVersionCanNotSync_Value"][L])
            self.label_Attenuation.setVisible(True)
        if KeyInfoDict["WaapiStatusDict_Read"]["Init_Attenuation"] == "False":
            self.label_Attenuation.setText(lan["GUI_InitSession_ThisVersionCanNotSync"][L])
            self.label_Attenuation.setVisible(True)
        if KeyInfoDict["WaapiStatusDict_Read"]["Init_Conversion"] == "False":
            self.label_Conversion.setVisible(True)

        # 根据KeyInfoDict["WaapiStatusDict_Write"]直接安排GUI显示结果
        if KeyInfoDict["WaapiStatusDict_Write"]["Init_ProjectSettings"] == "False":
            self.label_ProjectSettings_Write.setVisible(True)
        if KeyInfoDict["WaapiStatusDict_Write"]["Init_BUS"] == "False":
            self.label_Bus_Write.setVisible(True)
        if KeyInfoDict["WaapiStatusDict_Write"]["Init_Switch"] == "False":
            self.label_Switch_Write.setVisible(True)
        if KeyInfoDict["WaapiStatusDict_Write"]["Init_State"] == "False":
            self.label_State_Write.setVisible(True)
        if KeyInfoDict["WaapiStatusDict_Write"]["Init_RTPC_Value"] == "False":
            self.label_RTPC_Write.setText(lan["GUI_InitSession_ThisVersionCanNotWrite_Value"][L])
            self.label_RTPC_Write.setVisible(True)
        if KeyInfoDict["WaapiStatusDict_Write"]["Init_RTPC"] == "False":
            self.label_RTPC_Write.setText(lan["GUI_InitSession_ThisVersionCanNotWrite"][L])
            self.label_RTPC_Write.setVisible(True)
        if KeyInfoDict["WaapiStatusDict_Write"]["Init_SideChain"] == "False":
            self.label_SideChain_Write.setVisible(True)
        if KeyInfoDict["WaapiStatusDict_Write"]["Init_Attenuation_Value"] == "False":
            self.label_Attenuation_Write.setVisible(True)
            self.label_Attenuation_Write.setText(lan["GUI_InitSession_ThisVersionCanNotWrite_Value"][L])
        if KeyInfoDict["WaapiStatusDict_Write"]["Init_Attenuation"] == "False":
            self.label_Attenuation_Write.setText(lan["GUI_InitSession_ThisVersionCanNotWrite"][L])
            self.label_Attenuation_Write.setVisible(True)
        if KeyInfoDict["WaapiStatusDict_Write"]["Init_Conversion"] == "False":
            self.label_Conversion_Write.setVisible(True)

    def Init_ProjectSettings(self):
        if KeyInfoDict["Init_ProjectSettings"]["GenerateMultipleBanks"] == "True":
            self.checkbox_GenerateMultipleBanks.setChecked(True)
        else:
            self.checkbox_GenerateMultipleBanks.setChecked(False)

        if KeyInfoDict["Init_ProjectSettings"]["SoundBankGeneratePrintGUID"] == "True":
            self.checkbox_SoundBankGeneratePrintGUID.setChecked(True)
        else:
            self.checkbox_SoundBankGeneratePrintGUID.setChecked(False)

        if KeyInfoDict["Init_ProjectSettings"]["SoundBankGenerateMaxAttenuationInfo"] == "True":
            self.checkbox_SoundBankGenerateMaxAttenuationInfo.setChecked(True)
        else:
            self.checkbox_SoundBankGenerateMaxAttenuationInfo.setChecked(False)

        if KeyInfoDict["Init_ProjectSettings"]["SoundBankGenerateEstimatedDuration"] == "True":
            self.checkBox_SoundBankGenerateEstimatedDuration.setChecked(True)
        else:
            self.checkBox_SoundBankGenerateEstimatedDuration.setChecked(False)

    def Init_Table_For_Switch_State_Conversion(self, dictInfo, tableObj):
        try:
            # LOG.debug(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> 初始化Table——Switch_State_Conversion")
            # if tableObj is self.tableWidget_Switch:
            #     LOG.debug("[Init_Table] Switch入参Dict：")
            # elif tableObj is self.tableWidget_State:
            #     LOG.debug("[Init_Table] State入参Dict：")
            # elif tableObj is self.tableWidget_Conversion:
            #     LOG.debug("[Init_Table] Conversion入参Dict：")

            # LOG.debug(dictInfo)
            GroupNameList = list(dictInfo.keys())
            objList = list(dictInfo.values())
            countMaxRowNum = 0
            for sl in objList:
                if len(sl) > countMaxRowNum:
                    countMaxRowNum = len(sl)
            Row = countMaxRowNum
            Col = len(GroupNameList)

            # 添加保护，确保至少有一行新增
            if Row == 0:
                Row = 1

            if Row != 0 and Col != 0:
                # 加载前，先清空遗留数据的显示
                tableObj.setRowCount(0)
                tableObj.clearContents()
                # 初始化行列
                tableObj.setRowCount(Row + 20)
                tableObj.setColumnCount(Col)
                # 初始化Header
                tableObj.setHorizontalHeaderLabels(GroupNameList)
                # 填充child
                # 根据tableObj判断UniqueName
                UniqueName = ""
                if tableObj is self.tableWidget_Switch:
                    UniqueName = "SwitchGroup"
                elif tableObj is self.tableWidget_State:
                    UniqueName = "StateGroup"

                for col, GroupName in zip(range(Col), GroupNameList):
                    objList = dictInfo[GroupName]
                    # 如果Wwise里有，文字变蓝色
                    if len(UniqueName) != 0:
                        wgoResult = self.initWwise.get_Path_From_UniqueNameStr(UniqueName, GroupName)
                    else:
                        wgoResult = ""

                    # 判断objectList数量，如果数量为空，需确保依然创建一行有空白内容的QTableWidgetItem，否则会导致删除无效
                    if len(objList) == 0:
                        cellItem = QTableWidgetItem("")
                        # 如果Wwise里有，设置文字颜色
                        if wgoResult is not None and len(wgoResult) != 0:
                            cellItem.setBackground(QColor(key["DefaultColor_Gray"]))
                            cellItem.setFlags(cellItem.flags() ^ Qt.ItemIsEditable)
                        else:
                            cellItem.setBackground(QColor(key["DefaultColor_White"]))
                        tableObj.setItem(0, col, cellItem)
                    else:
                        for row, child in zip(range(len(objList)), objList):
                            cellItem = QTableWidgetItem(child)
                            # 如果Wwise里有，设置文字颜色
                            if wgoResult is not None and len(wgoResult) != 0:
                                cellItem.setBackground(QColor(key["DefaultColor_Gray"]))
                                cellItem.setFlags(cellItem.flags() ^ Qt.ItemIsEditable)
                            else:
                                cellItem.setBackground(QColor(key["DefaultColor_White"]))
                            tableObj.setItem(row, col, cellItem)
        except:
            traceback.print_exc()

    def Init_Table_For_RTPC_SideChain_Attenuation(self, dictInfo, tableObj):
        try:
            # LOG.debug(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> 初始化Table——RTPC_SideChain_Attenuation")
            # if tableObj is self.tableWidget_RTPC:
            #     LOG.debug("[Init_Table] RTPC入参Dict：")
            # elif tableObj is self.tableWidget_SideChain:
            #     LOG.debug("[Init_Table] SideChain入参Dict：")
            # elif tableObj is self.tableWidget_Attenuation:
            #     LOG.debug("[Init_Table] Attenuation入参Dict：")
            #
            # LOG.debug(dictInfo)
            GroupNameList = list(dictInfo.keys())
            objList = list(dictInfo.values())
            countMaxRowNum = 0
            for sl in objList:  # 这里2019不支持的原因，sl可能从上一级返回的是None
                if len(sl) > countMaxRowNum:
                    countMaxRowNum = len(sl)
            Row = countMaxRowNum
            Col = len(GroupNameList)

            if Col != 0:
                # 加载前，先清空遗留数据的显示
                tableObj.setRowCount(0)
                tableObj.clearContents()
                # 初始化行列
                tableObj.setRowCount(Row)
                tableObj.setColumnCount(Col)
                # 初始化Header
                tableObj.setHorizontalHeaderLabels(GroupNameList)
                # 设置行名
                VerticalHeaderList = list(dictInfo[GroupNameList[0]].keys())
                tableObj.setVerticalHeaderLabels(VerticalHeaderList)
                # 填充child
                # 根据tableObj判断UniqueName
                UniqueName = ""
                if tableObj is self.tableWidget_RTPC:
                    UniqueName = "GameParameter"
                elif tableObj is self.tableWidget_SideChain:
                    UniqueName = "Effect"
                elif tableObj is self.tableWidget_Attenuation:
                    UniqueName = "Attenuation"

                for col, GroupName in zip(range(Col), GroupNameList):
                    objDict = dictInfo[GroupName]
                    rowCount = len(objDict)
                    wgoResult = self.initWwise.get_Path_From_UniqueNameStr(UniqueName, GroupName)
                    for row, child in zip(range(rowCount), list(objDict.values())):
                        # 写入单元格信息
                        cellItem = QTableWidgetItem(child)
                        # 如果Wwise里有，设置文字颜色
                        if wgoResult is not None and len(wgoResult) != 0:
                            cellItem.setBackground(QColor(key["DefaultColor_Gray"]))
                            cellItem.setFlags(cellItem.flags() ^ Qt.ItemIsEditable)
                        else:
                            cellItem.setBackground(QColor(key["DefaultColor_White"]))
                        tableObj.setItem(row, col, cellItem)
        except:
            traceback.print_exc()

    def Init_GUI_All(self):
        self.Init_ProjectSettings()
        self.Init_Table_For_Switch_State_Conversion(KeyInfoDict["Init_Switch"], self.tableWidget_Switch)
        self.Init_Table_For_Switch_State_Conversion(KeyInfoDict["Init_State"], self.tableWidget_State)
        self.Init_Table_For_Switch_State_Conversion(KeyInfoDict["Init_Conversion"], self.tableWidget_Conversion)
        self.Init_Table_For_RTPC_SideChain_Attenuation(KeyInfoDict["Init_RTPC"], self.tableWidget_RTPC)
        self.Init_Table_For_RTPC_SideChain_Attenuation(KeyInfoDict["Init_SideChain"], self.tableWidget_SideChain)
        self.Init_Table_For_RTPC_SideChain_Attenuation(KeyInfoDict["Init_Attenuation"], self.tableWidget_Attenuation)

    # ----------------------------------------------------------------------- Funcs
    def RightClickMenu_tableWidget_SoundSheet(self, tableObj):
        Menu = QMenu(self)
        Menu.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))

        action_AddNewColumn = QAction(lan["GUI_InitSession_action_AddNewColumn"][L], self)
        Menu.addAction(action_AddNewColumn)
        action_AddNewColumn.triggered.connect(lambda: self.AddNewColumn_FromTable(tableObj))

        Menu.addSeparator()

        action_RemoveColumn = QAction(lan["GUI_InitSession_action_RemoveColumn"][L], self)
        Menu.addAction(action_RemoveColumn)
        action_RemoveColumn.triggered.connect(lambda: self.RemoveColumn_FromTable(tableObj))

        Menu.popup(QCursor.pos())

    def CreateColumn_ForTable(self, coltext, tableObj):
        try:
            colNum = tableObj.columnCount()
            tableObj.insertColumn(colNum)
            newHeaderItem = QTableWidgetItem(coltext)
            newHeaderItem.setBackground(QColor(key["DefaultColor_White"]))
            tableObj.setHorizontalHeaderItem(colNum, newHeaderItem)

            # 给单元格添加实际的单元格对象
            rowCount = tableObj.rowCount()
            for row in range(rowCount):
                newCellItem = QTableWidgetItem("")
                newCellItem.setBackground(QColor(key["DefaultColor_White"]))
                tableObj.setItem(row, colNum, newCellItem)
        except:
            traceback.print_exc()

    def AddNewColumn_FromTable(self, tableObj):
        try:
            # 先检查lineEdit的值是否合法
            newText = self.lineEdit_AddColumnForTable.text()
            if not check_string(newText) or len(newText) == 0:
                pass
            else:
                if tableObj is self.tableWidget_Switch:
                    newText = "Switch_" + newText
                    # 进一步判断是否已存在于json
                    if newText not in list(KeyInfoDict["Init_Switch"].keys()):
                        self.CreateColumn_ForTable(newText, tableObj)
                elif tableObj is self.tableWidget_State:
                    newText = "State_" + newText
                    # 进一步判断是否已存在于json
                    if newText not in list(KeyInfoDict["Init_State"].keys()):
                        self.CreateColumn_ForTable(newText, tableObj)
                elif tableObj is self.tableWidget_RTPC:
                    newText = "RTPC_" + newText
                    # 进一步判断是否已存在于json
                    if newText not in list(KeyInfoDict["Init_RTPC"].keys()):
                        self.CreateColumn_ForTable(newText, tableObj)
                elif tableObj is self.tableWidget_SideChain:
                    newText = "SC_" + newText
                    # 进一步判断是否已存在于json
                    if newText not in list(KeyInfoDict["Init_SideChain"].keys()):
                        self.CreateColumn_ForTable(newText, tableObj)
                elif tableObj is self.tableWidget_Attenuation:
                    newText = "Att_" + newText
                    # 进一步判断是否已存在于json
                    if newText not in list(KeyInfoDict["Init_Attenuation"].keys()):
                        self.CreateColumn_ForTable(newText, tableObj)

                # 然后保存Json
                SaveJson(KeyInfoDict, global_curWwiseBaseJson)
                self.Table_Cell_Changed(tableObj)
                self.pushButton_WriteIntoWwise.setEnabled(False)
                self.lineEdit_AddColumnForTable.setReadOnly(True)
        except:
            traceback.print_exc()

    def RemoveColumn_FromTable(self, tableObj):
        LOG.debug("RemoveColumn_FromTable --> enter~~~")
        try:
            s_items = tableObj.selectedItems()
            LOG.debug(str(s_items))
            if len(s_items) != 0:
                selected_cols = []
                for i in s_items:  # 求出所选择的行数
                    col = i.column()
                    if col not in selected_cols:
                        # 先判断单元格颜色，如果有颜色，说明wwise里有，则不添加到删除列表
                        if tableObj.item(0, col).background().color().name() != key["DefaultColor_Gray"]:
                            selected_cols.append(col)
                LOG.debug(selected_cols)

                # 删除列
                selected_cols.sort(reverse=True)
                LOG.debug(selected_cols)
                for col in range(len(selected_cols)):
                    # 先判断单元格颜色，如果有颜色，说明wwise里有，则不删除
                    try:
                        if tableObj.item(0, selected_cols[col]).background().color().name() != key["DefaultColor_Gray"]:
                            tableObj.removeColumn(selected_cols[col])
                    except:
                        traceback.print_exc()

                # 重新整理jsonDict，并保存
                self.Table_Cell_Changed(tableObj)
        except:
            traceback.print_exc()

    def CheckBox_StateChanged_WriteJson(self, checkBoxObj):
        try:
            checkBoxDictRef = {
                self.checkbox_GenerateMultipleBanks: "GenerateMultipleBanks",
                self.checkbox_SoundBankGeneratePrintGUID: "SoundBankGeneratePrintGUID",
                self.checkbox_SoundBankGenerateMaxAttenuationInfo: "SoundBankGenerateMaxAttenuationInfo",
                self.checkBox_SoundBankGenerateEstimatedDuration: "SoundBankGenerateEstimatedDuration"
            }
            if checkBoxObj.isChecked():
                KeyInfoDict["Init_ProjectSettings"][checkBoxDictRef[checkBoxObj]] = "True"
            else:
                KeyInfoDict["Init_ProjectSettings"][checkBoxDictRef[checkBoxObj]] = "False"

            SaveJson(KeyInfoDict, global_curWwiseBaseJson)
        except:
            traceback.print_exc()

    def LineEdit_TextChanged_WriteJson(self):
        try:
            text_min = self.lineEdit_PitchRandom_Min.text()
            text_max = self.lineEdit_PitchRandom_Max.text()

            try:
                text_min = float(text_min)
                if text_min < 0:
                    KeyInfoDict["InitPitchRandomMin"] = text_min
                    self.SetTextColor(self.lineEdit_PitchRandom_Min, "black")
                    # LOG.debug(text_min)
                else:
                    KeyInfoDict["InitPitchRandomMin"] = -50
                    self.SetTextColor(self.lineEdit_PitchRandom_Min, "red")
            except:
                KeyInfoDict["InitPitchRandomMin"] = -50
                self.SetTextColor(self.lineEdit_PitchRandom_Min, "red")

            try:
                text_max = float(text_max)
                if text_max > 0:
                    KeyInfoDict["InitPitchRandomMax"] = text_max
                    self.SetTextColor(self.lineEdit_PitchRandom_Max, "black")
                    # LOG.debug(text_max)
                else:
                    KeyInfoDict["InitPitchRandomMax"] = 50
                    self.SetTextColor(self.lineEdit_PitchRandom_Max, "red")
            except:
                KeyInfoDict["InitPitchRandomMax"] = 50
                self.SetTextColor(self.lineEdit_PitchRandom_Max, "red")

            SaveJson(KeyInfoDict, global_curWwiseBaseJson)
        except:
            traceback.print_exc()

    def LocatePath_WriteIntoBaseJson(self, FileType):
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

    def LocatePath_UserDefined_ActualGeneratedSoundBank(self):
        BankPath = self.LocatePath_WriteIntoBaseJson("Folder")
        if BankPath is not None:
            self.lineEdit_ActualGeneratedBankPath.setText(BankPath)

    def LocatePath_UserDefined_SoundIDSTatusReportPath(self):
        Pathh = self.LocatePath_WriteIntoBaseJson("File")
        if Pathh is not None:
            self.lineEdit_SoundIDSTatusReportPath.setText(Pathh)

    def LineEditTextChanged_SoundIDSTatusReportPath(self, lineEditObj):
        try:
            currentText = lineEditObj.text()
            if os.path.exists(currentText):
                if currentText.endswith(".json"):
                    lineEditObj.setStyleSheet("color:black")
                    lineEditObj.setFont(QFont(key["DefaultFont_English"]))

                    LocalInfoDict["Path_SoundIDSTatusReport"] = currentText
                    SaveJson(LocalInfoDict, global_curWwiseLocalJson)
                    LOG.info(lan["LOG_Path_SoundIDSTatusReport"][L] + str(currentText))
                else:
                    lineEditObj.setStyleSheet("color:orange")
                    lineEditObj.setFont(QFont(key["DefaultFont_English"]))
            else:
                lineEditObj.setStyleSheet("color:red")
                lineEditObj.setFont(QFont(key["DefaultFont_English"]))
        except:
            traceback.print_exc()

    def LineEditTextChanged_ActualSoundBankPath(self, lineEditObj):
        try:
            currentText = lineEditObj.text()
            SoundBanksInfoXMLPath = os.path.join(currentText, "SoundbanksInfo.xml")
            if os.path.exists(SoundBanksInfoXMLPath):
                lineEditObj.setStyleSheet("color:black")
                lineEditObj.setFont(QFont(key["DefaultFont_English"]))

                LocalInfoDict["ActualGeneratedSoundBankPathOfOnePlatform"] = currentText
                SaveJson(LocalInfoDict, global_curWwiseLocalJson)
                LOG.info(lan["LOG_ActualGeneratedSoundBankPathOfOnePlatform"][L] + str(currentText))
            else:
                if os.path.exists(currentText):
                    lineEditObj.setStyleSheet("color:orange")
                    lineEditObj.setFont(QFont(key["DefaultFont_English"]))
                else:
                    lineEditObj.setStyleSheet("color:red")
                    lineEditObj.setFont(QFont(key["DefaultFont_English"]))
        except:
            traceback.print_exc()

    def LineEditTextChanged_AddNewName(self, lineEditObj):
        try:
            currentText = lineEditObj.text()
            if check_string(currentText):
                lineEditObj.setStyleSheet("color:black")
                lineEditObj.setFont(QFont(key["DefaultFont_English"]))
            else:
                lineEditObj.setStyleSheet("color:red")
                lineEditObj.setFont(QFont(key["DefaultFont_English"]))
        except:
            traceback.print_exc()

    def PreCheck_CheckDiff(self):
        self.MessageBox_NoArgs(lan["GUI_BTN_CheckDiff_Msg_Title"][L], lan["GUI_BTN_CheckDiff_Msg_Text"][L], self.CheckDiff)

    def CheckDiff(self):
        try:
            LOG.debug(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> 对比json/wwise关键信息差异")
            LOG.debug("[CheckDiff] 开始创建SW实例")
            self.initWwise = SimpleWaapi()

            LOG.debug("[CheckDiff] 调用SW.SessionStructure方法，获取差异Dict")
            ResultDict = self.initWwise.CheckDiff_SessionStructure()
            # LOG.debug("[CheckDiff] 获取到的Dict结果：")
            # LOG.debug(ResultDict)

            # BUS单独处理GUI显示
            if ResultDict["Result_Bus"]["compareResult"] == "False":
                self.treeWidget_Bus.setVisible(False)
                self.listWidget_CurrentBusStatus.clear()
                for busPath in ResultDict["Result_Bus"]["currentInfo"]:
                    self.listWidget_CurrentBusStatus.addItem(busPath)
                self.listWidget_CurrentBusStatus.setVisible(True)
            else:
                self.treeWidget_Bus.setVisible(True)
                self.listWidget_CurrentBusStatus.setVisible(False)

            # 根据ResultDict的结果，处理GUI显示
            WaapiStatusDict_Read = {
                "Init_ProjectSettings": "",
                "Init_BUS": "",
                "Init_Switch": "",
                "Init_State": "",
                "Init_RTPC": "",
                "Init_RTPC_Value": "",
                "Init_SideChain": "",
                "Init_Attenuation": "",
                "Init_Attenuation_Value": "",
                "Init_Conversion": "",
            }
            if ResultDict["Result_ProjectSettings"]["WaapiStatus"] == "False":
                self.label_ProjectSettings.setVisible(True)
                WaapiStatusDict_Read["Init_ProjectSettings"] = "False"
            if ResultDict["Result_Switch"]["WaapiStatus"] == "False":
                self.label_Switch.setVisible(True)
                WaapiStatusDict_Read["Init_Switch"] = "False"
            if ResultDict["Result_State"]["WaapiStatus"] == "False":
                self.label_State.setVisible(True)
                WaapiStatusDict_Read["Init_State"] = "False"
            if ResultDict["Result_RTPC_Value"]["WaapiStatus"] == "False":
                self.label_RTPC.setText(lan["GUI_InitSession_ThisVersionCanNotSync_Value"][L])
                self.label_RTPC.setVisible(True)
                WaapiStatusDict_Read["Result_RTPC_Value"] = "False"
            if ResultDict["Result_RTPC"]["WaapiStatus"] == "False":
                self.label_RTPC.setText(lan["GUI_InitSession_ThisVersionCanNotSync"][L])
                self.label_RTPC.setVisible(True)
                WaapiStatusDict_Read["Init_RTPC"] = "False"
            if ResultDict["Result_SideChain"]["WaapiStatus"] == "False":
                self.label_SideChain.setVisible(True)
                WaapiStatusDict_Read["Init_SideChain"] = "False"
            if ResultDict["Result_Conversion"]["WaapiStatus"] == "False":
                self.label_Conversion.setVisible(True)
                WaapiStatusDict_Read["Init_Conversion"] = "False"
            if ResultDict["Result_Attenuation_Value"]["WaapiStatus"] == "False":
                self.label_Attenuation.setText(lan["GUI_InitSession_ThisVersionCanNotSync_Value"][L])
                self.label_Attenuation.setVisible(True)
                WaapiStatusDict_Read["Init_Attenuation_Value"] = "False"
            if ResultDict["Result_Attenuation"]["WaapiStatus"] == "False":
                self.label_Attenuation.setText(lan["GUI_InitSession_ThisVersionCanNotSync"][L])
                self.label_Attenuation.setVisible(True)
                WaapiStatusDict_Read["Init_Attenuation"] = "False"

            # 将WaapiStatus存入KeyInfoDict
            KeyInfoDict["WaapiStatusDict_Read"] = WaapiStatusDict_Read

            # 保存base.json
            # LOG.debug("[CheckDiff] KeyInfoDict保存前的最终值：")
            # LOG.debug(KeyInfoDict)
            SaveJson(KeyInfoDict, global_curWwiseBaseJson)

            # 刷新GUI加载
            LOG.debug("[CheckDiff] 刷新GUI的显示结果 - 开始")
            self.Init_GUI_All()

            self.initWwise.__del__()
            LOG.debug("[CheckDiff] 手动断联SW")

            self.pushButton_WriteIntoWwise.setEnabled(True)
            self.lineEdit_AddColumnForTable.setReadOnly(False)

            LOG.debug("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< 对比json/wwise关键信息差异 [结束]\n")
            return ResultDict
        except:
            traceback.print_exc()
            return None

    def WriteIntoWwise(self):
        try:
            messageBox = QMessageBox(QMessageBox.Warning, lan["GUI_MessageBox_WriteIntoWwise_Title"][L],
                                     lan["GUI_MessageBox_WriteIntoWwise_Text"][L])
            messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
            Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
            Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
            messageBox.exec_()
            if messageBox.clickedButton() == Qyes:
                initWwise = SimpleWaapi()

                LOG.debug("[SW实例创建][InitSession][WriteIntoWwise]")
                WaapiStatusDict = initWwise.WriteIntoWwise_FromJson()
                LOG.debug("[WaapiStatusDict] Write into Wwise执行中的判断：")
                LOG.debug(WaapiStatusDict)

                initWwise.__del__()
                LOG.debug("[SW实例清除***][InitSession][WriteIntoWwise]")

                # 根据WaapiStatusDict的结果，处理GUI显示
                if WaapiStatusDict["Init_ProjectSettings"] == "False":
                    self.label_ProjectSettings_Write.setVisible(True)
                if WaapiStatusDict["Init_BUS"] == "False":
                    self.label_Bus_Write.setVisible(True)
                if WaapiStatusDict["Init_Switch"] == "False":
                    self.label_Switch_Write.setVisible(True)
                if WaapiStatusDict["Init_State"] == "False":
                    self.label_State_Write.setVisible(True)
                if WaapiStatusDict["Init_RTPC_Value"] == "False":
                    self.label_RTPC_Write.setText(lan["GUI_InitSession_ThisVersionCanNotWrite_Value"][L])
                    self.label_RTPC_Write.setVisible(True)
                if WaapiStatusDict["Init_RTPC"] == "False":
                    self.label_RTPC_Write.setText(lan["GUI_InitSession_ThisVersionCanNotWrite"][L])
                    self.label_RTPC_Write.setVisible(True)
                if WaapiStatusDict["Init_SideChain"] == "False":
                    self.label_SideChain_Write.setVisible(True)
                if WaapiStatusDict["Init_Attenuation_Value"] == "False":
                    self.label_Attenuation_Write.setText(lan["GUI_InitSession_ThisVersionCanNotWrite_Value"][L])
                    self.label_Attenuation_Write.setVisible(True)
                if WaapiStatusDict["Init_Attenuation"] == "False":
                    self.label_Attenuation_Write.setVisible(True)
                    self.label_Attenuation_Write.setText(lan["GUI_InitSession_ThisVersionCanNotWrite"][L])
                if WaapiStatusDict["Init_Conversion"] == "False":
                    self.label_Conversion_Write.setVisible(True)

                self.pushButton_WriteIntoWwise.setEnabled(False)
                self.lineEdit_AddColumnForTable.setReadOnly(True)
                self.ui.close()
        except:
            traceback.print_exc()

    @staticmethod
    def GetDefaultFont():
        if key["Language"] == "Chinese":
            Font_Def = key["DefaultFont_Chinese"]
        else:
            Font_Def = key["DefaultFont_English"]

        return Font_Def

    def SetTextColor(self, obj, color):
        if color == "red":
            obj.setStyleSheet("color:red")
            obj.setFont(QFont(key["DefaultFont_English"], key["DefaultFont_Size"]))
        elif color == "black":
            obj.setStyleSheet("color:black")
            obj.setFont(QFont(key["DefaultFont_English"], key["DefaultFont_Size"]))
        else:
            obj.setStyleSheet("color:black")
            obj.setFont(QFont(key["DefaultFont_English"], key["DefaultFont_Size"]))

    def SetTextColor_WithLanguageConsidered(self, obj, color, fontSize):
        if color == "red":
            obj.setStyleSheet("color:red")
            obj.setFont(QFont(self.GetDefaultFont(), fontSize))
        elif color == "black":
            obj.setStyleSheet("color:black")
            obj.setFont(QFont(self.GetDefaultFont(), fontSize))
        else:
            obj.setStyleSheet("color:black")
            obj.setFont(QFont(self.GetDefaultFont(), fontSize))

    def Table_Cell_Changed(self, tableObj):
        try:
            if tableObj is self.tableWidget_Switch:
                TotalRowNum = tableObj.rowCount()
                TotalColNum = tableObj.columnCount()

                # 先对每一个单元格的值属性，进行安全检查。不对的文字颜色变红。
                GUI_Init_Dict = {}
                for i in range(TotalColNum):
                    header_item = tableObj.horizontalHeaderItem(i)
                    header_text = header_item.text()
                    objlist = []
                    for g in range(TotalRowNum):
                        if tableObj.item(g, i) is not None:
                            text = tableObj.item(g, i).text()
                            if check_string(text):
                                if len(text) != 0:
                                    objlist.append(text)
                    GUI_Init_Dict[header_text] = objlist
                # LOG.debug(GUI_Init_Dict)
                KeyInfoDict["Init_Switch"] = GUI_Init_Dict

            elif tableObj is self.tableWidget_State:
                TotalRowNum = tableObj.rowCount()
                TotalColNum = tableObj.columnCount()

                # 先对每一个单元格的值属性，进行安全检查。不对的文字颜色变红。
                GUI_Init_Dict = {}
                for i in range(TotalColNum):
                    header_item = tableObj.horizontalHeaderItem(i)
                    header_text = header_item.text()
                    objlist = []
                    for g in range(TotalRowNum):
                        if tableObj.item(g, i) is not None:
                            text = tableObj.item(g, i).text()
                            if check_string(text):
                                if len(text) != 0:
                                    objlist.append(text)
                    GUI_Init_Dict[header_text] = objlist
                # LOG.debug(GUI_Init_Dict)
                KeyInfoDict["Init_State"] = GUI_Init_Dict

            elif tableObj is self.tableWidget_RTPC:
                TotalRowNum = tableObj.rowCount()
                TotalColNum = tableObj.columnCount()

                # 先对每一个单元格的值属性，进行安全检查。不对的文字颜色变红。
                GUI_Init_Dict = {}
                for i in range(TotalColNum):
                    header_item = tableObj.horizontalHeaderItem(i)
                    header_text = header_item.text()
                    objDict = {}
                    for g in range(TotalRowNum):
                        verder_item = tableObj.verticalHeaderItem(g)
                        verder_text = verder_item.text()
                        if tableObj.item(g, i) is not None:
                            text = tableObj.item(g, i).text()
                            if is_convertible_to_number(text):
                                if len(text) != 0:
                                    objDict[verder_text] = text
                                else:
                                    objDict[verder_text] = "0"
                            else:
                                objDict[verder_text] = "0"
                        else:
                            objDict[verder_text] = "0"

                    # 二次检查RTPC内部数据关系的合法性
                    value_min = float(objDict["Min"])
                    value_max = float(objDict["Max"])
                    value_initvalue = float(objDict["InitialValue"])
                    if value_min >= value_max or value_initvalue < value_min or value_initvalue > value_max:
                        objDict["Min"] = "0"
                        objDict["Max"] = "1"
                        objDict["InitialValue"] = "1"
                        GUI_Init_Dict[header_text] = objDict
                    else:
                        GUI_Init_Dict[header_text] = objDict

                # LOG.debug(GUI_Init_Dict)
                KeyInfoDict["Init_RTPC"] = GUI_Init_Dict

            elif tableObj is self.tableWidget_Conversion:
                TotalRowNum = tableObj.rowCount()
                TotalColNum = tableObj.columnCount()

                # 先对每一个单元格的值属性，进行安全检查。不对的文字颜色变红。
                GUI_Init_Dict = {}
                for i in range(TotalColNum):
                    header_item = tableObj.horizontalHeaderItem(i)
                    header_text = header_item.text()
                    objlist = []
                    for g in range(TotalRowNum):
                        if tableObj.item(g, i) is not None:
                            text = tableObj.item(g, i).text()
                            if check_string(text):
                                if len(text) != 0:
                                    objlist.append(text)
                    GUI_Init_Dict[header_text] = objlist
                # LOG.debug(GUI_Init_Dict)
                KeyInfoDict["Init_Conversion"] = GUI_Init_Dict

            elif tableObj is self.tableWidget_Attenuation:
                TotalRowNum = tableObj.rowCount()
                TotalColNum = tableObj.columnCount()

                # 先对每一个单元格的值属性，进行安全检查。不对的文字颜色变红。
                GUI_Init_Dict = {}
                for i in range(TotalColNum):
                    header_item = tableObj.horizontalHeaderItem(i)
                    header_text = header_item.text()
                    objDict = {}
                    for g in range(TotalRowNum):
                        verder_item = tableObj.verticalHeaderItem(g)
                        verder_text = verder_item.text()
                        if tableObj.item(g, i) is not None:
                            text = tableObj.item(g, i).text()
                            if is_convertible_to_number(text):
                                if len(text) != 0:
                                    objDict[verder_text] = text
                                else:
                                    objDict[verder_text] = "1"
                            else:
                                objDict[verder_text] = "1"
                        else:
                            objDict[verder_text] = "1"

                    # 二次检查RTPC内部数据关系的合法性
                    value = float(objDict["RadiusMax"])
                    if value <= 0:
                        objDict["RadiusMax"] = "1"
                        GUI_Init_Dict[header_text] = objDict
                    else:
                        GUI_Init_Dict[header_text] = objDict

                # LOG.debug(GUI_Init_Dict)
                KeyInfoDict["Init_Attenuation"] = GUI_Init_Dict

            elif tableObj is self.tableWidget_SideChain:
                TotalRowNum = tableObj.rowCount()
                TotalColNum = tableObj.columnCount()

                # 先对每一个单元格的值属性，进行安全检查。不对的文字颜色变红。
                GUI_Init_Dict = {}
                for i in range(TotalColNum):
                    header_item = tableObj.horizontalHeaderItem(i)
                    header_text = header_item.text()
                    objDict = {}
                    for g in range(TotalRowNum):
                        verder_item = tableObj.verticalHeaderItem(g)
                        verder_text = verder_item.text()
                        if tableObj.item(g, i) is not None:
                            text = tableObj.item(g, i).text()
                            if verder_text != "RTPC":
                                if is_convertible_to_number(text):
                                    if len(text) != 0:
                                        objDict[verder_text] = text
                                    else:
                                        objDict[verder_text] = "0"
                                else:
                                    objDict[verder_text] = "0"
                            else:
                                objDict[verder_text] = text
                        else:
                            objDict[verder_text] = "0"

                    # 二次检查RTPC内部数据关系的合法性
                    value_AttackTime = float(objDict["AttackTime"])
                    value_ReleaseTime = float(objDict["ReleaseTime"])
                    if value_AttackTime < 0 or value_AttackTime > 10 or value_ReleaseTime < 0 or value_ReleaseTime > 10:
                        objDict["AttackTime"] = "0"
                        objDict["ReleaseTime"] = "0.1"
                        GUI_Init_Dict[header_text] = objDict
                    else:
                        GUI_Init_Dict[header_text] = objDict

                # LOG.debug(GUI_Init_Dict)
                KeyInfoDict["Init_SideChain"] = GUI_Init_Dict

            SaveJson(KeyInfoDict, global_curWwiseBaseJson)
        except:
            traceback.print_exc()

    def TableCellChanged_Connect(self):
        self.tableWidget_Switch.cellChanged.connect(lambda: self.Table_Cell_Changed(self.tableWidget_Switch))
        self.tableWidget_State.cellChanged.connect(lambda: self.Table_Cell_Changed(self.tableWidget_State))
        self.tableWidget_RTPC.cellChanged.connect(lambda: self.Table_Cell_Changed(self.tableWidget_RTPC))
        self.tableWidget_Conversion.cellChanged.connect(lambda: self.Table_Cell_Changed(self.tableWidget_Conversion))
        self.tableWidget_Attenuation.cellChanged.connect(lambda: self.Table_Cell_Changed(self.tableWidget_Attenuation))
        self.tableWidget_SideChain.cellChanged.connect(lambda: self.Table_Cell_Changed(self.tableWidget_SideChain))

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