import logging
import os
import traceback

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QCursor, QColor
from PyQt5.QtWidgets import QWidget, QFileDialog, QMenu, QAction
from BasicTools import *
from globals import *
import globals
from Logs import *
from SimpleWaapi import *


class Window_KeyInfo(QWidget):
    def __init__(self):
        super().__init__()

        # Load GUI
        self.ui = uic.loadUi("cf\\gui\\KeyInfo.ui")
        self.ui.setWindowTitle(lan["GUI_KIG_WindowTitle"][L])

        # ------------------------------------------------------------------- Init Items ----- KeyStrList
        self.listWidget_KeyStrList = self.ui.listWidget_KeyStrList

        # ------------------------------------------------------------------- Init Items ----- Edit Zone
        self.lineEdit_EditKeyStr = self.ui.lineEdit_EditKeyStr
        self.pushButton_AddKey = self.ui.pushButton_AddKey
        self.pushButton_AddKeyByMirror = self.ui.pushButton_AddKeyByMirror
        self.label_Log = self.ui.label_Log
        self.pushButton_RefreshComboBox = self.ui.pushButton_RefreshComboBox
        self.groupBox_Description = self.ui.groupBox_Description
        self.label_decription = self.ui.label_decription
        self.label_statusMsg = self.ui.label_statusMsg

        # ------------------------------------------------------------------- Init Items ----- Charts
        self.groupBox_UserDefinedGroup = self.ui.groupBox_UserDefinedGroup

        self.label_StructureType = self.ui.label_StructureType
        self.comboBox_Structure_Type = self.ui.comboBox_Structure_Type

        self.label_Path_InWwise_UserDefinedTemplate = self.ui.label_Path_InWwise_UserDefinedTemplate
        self.lineEdit_Path_InWwise_UserDefinedTemplate = self.ui.lineEdit_Path_InWwise_UserDefinedTemplate

        self.label_Path_File_PlaceholderWAV = self.ui.label_Path_File_PlaceholderWAV
        self.lineEdit_Path_File_PlaceholderWAV = self.ui.lineEdit_Path_File_PlaceholderWAV
        self.pushButton_Browse_Path_File_PlaceholderWAV = self.ui.pushButton_Browse_Path_File_PlaceholderWAV

        self.label_Path_Folder_TargetWAV = self.ui.label_Path_Folder_TargetWAV
        self.lineEdit_Path_Folder_TargetWAV = self.ui.lineEdit_Path_Folder_TargetWAV
        self.pushButton_Browse_Path_Folder_TargetWAV = self.ui.pushButton_Browse_Path_Folder_TargetWAV

        self.label_Path_InWwise_TargetActorMixer = self.ui.label_Path_InWwise_TargetActorMixer
        self.lineEdit_Path_InWwise_TargetActorMixer = self.ui.lineEdit_Path_InWwise_TargetActorMixer

        self.label_Path_InWwise_TargetEvent = self.ui.label_Path_InWwise_TargetEvent
        self.lineEdit_Path_InWwise_TargetEvent = self.ui.lineEdit_Path_InWwise_TargetEvent

        self.label_Path_InWwise_TargetBank = self.ui.label_Path_InWwise_TargetBank
        self.lineEdit_Path_InWwise_TargetBank = self.ui.lineEdit_Path_InWwise_TargetBank

        self.label_Property_Bus = self.ui.label_Property_Bus
        self.lineEdit_Property_Bus = self.ui.lineEdit_Property_Bus
        self.comboBox_Property_Bus = self.ui.comboBox_Property_Bus

        self.label_Property_Bus_NPC = self.ui.label_Property_Bus_NPC
        self.lineEdit_Property_Bus_NPC = self.ui.lineEdit_Property_Bus_NPC
        self.comboBox_Property_Bus_NPC = self.ui.comboBox_Property_Bus_NPC

        self.label_Property_SwitchGroupName_PC_NPC = self.ui.label_Property_SwitchGroupName_PC_NPC
        self.lineEdit_Property_SwitchGroupName_PC_NPC = self.ui.lineEdit_Property_SwitchGroupName_PC_NPC
        self.comboBox_Property_SwitchGroupName_PC_NPC = self.ui.comboBox_Property_SwitchGroupName_PC_NPC

        self.label_Property_SwitchGroupName_Texture = self.ui.label_Property_SwitchGroupName_Texture
        self.lineEdit_Property_SwitchGroupName_Texture = self.ui.lineEdit_Property_SwitchGroupName_Texture
        self.comboBox_Property_SwitchGroupName_Texture = self.ui.comboBox_Property_SwitchGroupName_Texture

        self.label_Property_Conversion = self.ui.label_Property_Conversion
        self.lineEdit_Property_Conversion = self.ui.lineEdit_Property_Conversion
        self.comboBox_Property_Conversion = self.ui.comboBox_Property_Conversion

        self.label_Property_Positioning = self.ui.label_Property_Positioning
        self.lineEdit_Property_Positioning = self.ui.lineEdit_Property_Positioning
        self.comboBox_Property_Positioning = self.ui.comboBox_Property_Positioning

        self.label_Property_ifPitchRandom = self.ui.label_Property_ifPitchRandom
        self.comboBox_Property_ifPitchRandom = self.ui.comboBox_Property_ifPitchRandom

        self.label_Property_ifStream = self.ui.label_Property_ifStream
        self.comboBox_Property_ifStream = self.ui.comboBox_Property_ifStream

        # ------------------------------------------------------------------- Set Logic ----- Items
        self.pushButton_AddKeyByMirror.setStyleSheet("QPushButton{border-image: url(cf/gui/icon_buttons/btn_mirror.png)}"
                                                    "QPushButton:hover{border-image: url(cf/gui/icon_buttons/btn_mirror_hover.png)}"
                                                    "QPushButton:pressed{border-image: url(cf/gui/icon_buttons/btn_mirror_press.png)}")
        self.pushButton_AddKeyByMirror.clicked.connect(self.AddKeyByMirror)

        self.listWidget_KeyStrList.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
        self.listWidget_KeyStrList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.listWidget_KeyStrList.customContextMenuRequested.connect(self.RightClickMenu_listWidget_KeyStrList)
        self.listWidget_KeyStrList.currentItemChanged.connect(self.CheckIfInWwise)

        self.lineEdit_EditKeyStr.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
        self.pushButton_AddKey.clicked.connect(self.AddKey)
        self.pushButton_RefreshComboBox.setText(lan["GUI_KIG_PushButton_RefreshComboBox"][L])
        self.pushButton_RefreshComboBox.clicked.connect(self.RefreshAllComboBoxAndLineEdit)

        self.pushButton_Browse_Path_File_PlaceholderWAV.clicked.connect(
            lambda: self.WritePathIntoLineEdit(self.lineEdit_Path_File_PlaceholderWAV, self.LocatePath("File")))
        self.pushButton_Browse_Path_Folder_TargetWAV.clicked.connect(
            lambda: self.WritePathIntoLineEdit(self.lineEdit_Path_Folder_TargetWAV, self.LocatePath("Folder")))

        self.groupBox_UserDefinedGroup.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
        self.groupBox_UserDefinedGroup.setTitle(lan["GUI_KeyInfo_groupBox"][L])
        self.lineEdit_EditKeyStr.setPlaceholderText(lan["GUI_KeyInfo_lineEdit_Placeholder"][L])
        self.comboBox_Property_ifPitchRandom.setItemText(0, lan["GUI_RC_False"][L])
        self.comboBox_Property_ifPitchRandom.setItemText(1, lan["GUI_RC_True"][L])
        self.comboBox_Property_ifStream.setItemText(0, lan["GUI_RC_False"][L])
        self.comboBox_Property_ifStream.setItemText(1, lan["GUI_RC_True"][L])

        self.Init_ComboBox_By_ScanCurrentWwise()
        self.comboBox_Property_Bus.setStyleSheet("color:gray")
        self.comboBox_Property_Bus_NPC.setStyleSheet("color:gray")
        self.comboBox_Property_SwitchGroupName_PC_NPC.setStyleSheet("color:gray")
        self.comboBox_Property_SwitchGroupName_Texture.setStyleSheet("color:gray")
        self.comboBox_Property_Conversion.setStyleSheet("color:gray")
        self.comboBox_Property_Positioning.setStyleSheet("color:gray")
        self.comboBox_Property_Bus.currentIndexChanged.connect(lambda: self.Refresh_ComboBox_By_ScanCurrentWwise(self.lineEdit_Property_Bus, self.comboBox_Property_Bus))
        self.comboBox_Property_Bus_NPC.currentIndexChanged.connect(lambda: self.Refresh_ComboBox_By_ScanCurrentWwise(self.lineEdit_Property_Bus_NPC, self.comboBox_Property_Bus_NPC))
        self.comboBox_Property_SwitchGroupName_PC_NPC.currentIndexChanged.connect(lambda: self.Refresh_ComboBox_By_ScanCurrentWwise(self.lineEdit_Property_SwitchGroupName_PC_NPC, self.comboBox_Property_SwitchGroupName_PC_NPC))
        self.comboBox_Property_SwitchGroupName_Texture.currentIndexChanged.connect(lambda: self.Refresh_ComboBox_By_ScanCurrentWwise(self.lineEdit_Property_SwitchGroupName_Texture, self.comboBox_Property_SwitchGroupName_Texture))
        self.comboBox_Property_Conversion.currentIndexChanged.connect(lambda: self.Refresh_ComboBox_By_ScanCurrentWwise(self.lineEdit_Property_Conversion, self.comboBox_Property_Conversion))
        self.comboBox_Property_Positioning.currentIndexChanged.connect(lambda: self.Refresh_ComboBox_By_ScanCurrentWwise(self.lineEdit_Property_Positioning, self.comboBox_Property_Positioning))
        self.label_statusMsg.setStyleSheet("color:darkorange")

        self.groupBox_Description.setTitle(lan["GUI_KIG_GroupBox_Description_Title"][L])
        self.label_decription.setText(lan["GUI_KIG_Label_Description"][L])
        self.label_decription.setStyleSheet("color:black")
        self.label_decription.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
        self.label_StructureType.setText(lan["GUI_KIG_label_StructureType"][L])
        self.label_Path_InWwise_UserDefinedTemplate.setText(lan["GUI_KIG_label_Path_InWwise_UserDefinedTemplate"][L])
        self.label_Path_File_PlaceholderWAV.setText(lan["GUI_KIG_label_File_PlaceholderWAV"][L])
        self.pushButton_Browse_Path_File_PlaceholderWAV.setText(lan["GUI_pushButton_Locate"][L])
        self.label_Path_Folder_TargetWAV.setText(lan["GUI_KIG_label_Folder_TargetWAV"][L])
        self.pushButton_Browse_Path_Folder_TargetWAV.setText(lan["GUI_pushButton_Locate"][L])
        self.label_Path_InWwise_TargetActorMixer.setText(lan["GUI_KIG_label_InWwise_TargetActorMixer"][L])
        self.label_Path_InWwise_TargetEvent.setText(lan["GUI_KIG_label_InWwise_TargetEvent"][L])
        self.label_Path_InWwise_TargetBank.setText(lan["GUI_KIG_label_InWwise_TargetBank"][L])
        self.label_Property_Conversion.setText(lan["GUI_KIG_label_Conversion"][L])
        self.label_Property_Positioning.setText(lan["GUI_KIG_label_Positioning"][L])
        self.label_Property_Bus.setText(lan["GUI_KIG_label_Bus"][L])
        self.label_Property_Bus_NPC.setText(lan["GUI_KIG_label_Bus_NPC"][L])
        self.label_Property_SwitchGroupName_PC_NPC.setText(lan["GUI_KIG_label_SwitchGroupName_PC_NPC"][L])
        self.label_Property_SwitchGroupName_Texture.setText(lan["GUI_KIG_label_SwitchGroupName_Texture"][L])
        self.label_Property_ifPitchRandom.setText(lan["GUI_KIG_label_ifPitchRandom"][L])
        self.label_Property_ifStream.setText(lan["GUI_KIG_label_ifStream"][L])

        self.Init_PropertyChangedAction()

    # ------------------------------------------------------------------- Func ----- Init
    def Init_PanelDisplay(self):
        Data_KeyInfo = KeyInfoDict.get("Data_KeyInfo", "")
        if len(Data_KeyInfo) != 0:
            if len(KeyInfoDict["Data_KeyInfo"]) == 0:
                self.comboBox_Structure_Type.setCurrentIndex(0)
                self.IfShowHideGroup()
            else:
                for keyStr, valueDict in zip(Data_KeyInfo.keys(), Data_KeyInfo.values()):
                    self.listWidget_KeyStrList.addItem(keyStr)
                self.listWidget_KeyStrList.setCurrentRow(0)
                self.CheckIfInWwise()
                # LOG.debug("[ <-- REF][Init_PanelDisplay] --> [CheckIfInWwise]")

    def CheckIfInWwise(self):
        try:
            currentKeyStrCount = self.listWidget_KeyStrList.count()
            if currentKeyStrCount != 0:
                go = SimpleWaapi()
                LOG.debug("[SW实例创建][KeyInfo][CheckIfInWwise]")
                for i in range(currentKeyStrCount):
                    keystr = self.listWidget_KeyStrList.item(i).text()
                    result = go.Check_IfKeyStrWWUInWwise(keystr)
                    LOG.debug("[检查KeyStr结构是否已存在于Wwise] " + str(keystr) + " --> " + str(result))
                    if result is False:
                        self.listWidget_KeyStrList.item(i).setBackground(QColor("#ffeaff"))
                    else:
                        self.listWidget_KeyStrList.item(i).setBackground(QColor("#ffffff"))
                go.__del__()
                LOG.debug("[SW实例清除***][KeyInfo][CheckIfInWwise]\n")
        except:
            traceback.print_exc()

    def Init_PropertyChangedAction(self):
        self.label_statusMsg.setText("")
        self.listWidget_KeyStrList.itemSelectionChanged.connect(self.SelectKey)
        self.listWidget_KeyStrList.itemClicked.connect(self.SelectKey)
        self.lineEdit_EditKeyStr.textChanged.connect(self.TextChanged)

        self.comboBox_Structure_Type.currentIndexChanged.connect(
            lambda: self.SaveJson_ComboBox_CurrentIndexChanged(self.comboBox_Structure_Type))
        self.comboBox_Property_ifPitchRandom.currentIndexChanged.connect(
            lambda: self.SaveJson_ComboBox_CurrentIndexChanged(self.comboBox_Property_ifPitchRandom))
        self.comboBox_Property_ifStream.currentIndexChanged.connect(
            lambda: self.SaveJson_ComboBox_CurrentIndexChanged(self.comboBox_Property_ifStream))

        self.lineEdit_TextChanged_Connect()

    def lineEdit_TextChanged_Connect(self):
        self.lineEdit_Path_InWwise_UserDefinedTemplate.textChanged.connect(self.lineEdit_Path_InWwise_UserDefinedTemplate_ChangedHandler)
        self.lineEdit_Path_File_PlaceholderWAV.textChanged.connect(self.lineEdit_Path_File_PlaceholderWAV_ChangedHandler)
        self.lineEdit_Path_Folder_TargetWAV.textChanged.connect(self.lineEdit_Path_Folder_TargetWAV_ChangedHandler)
        self.lineEdit_Path_InWwise_TargetActorMixer.textChanged.connect(self.lineEdit_Path_InWwise_TargetActorMixer_ChangedHandler)
        self.lineEdit_Path_InWwise_TargetEvent.textChanged.connect(self.lineEdit_Path_InWwise_TargetEvent_ChangedHandler)
        self.lineEdit_Path_InWwise_TargetBank.textChanged.connect(self.lineEdit_Path_InWwise_TargetBank_ChangedHandler)
        self.lineEdit_Property_Conversion.textChanged.connect(self.lineEdit_Property_Conversion_ChangedHandler)
        self.lineEdit_Property_Positioning.textChanged.connect(self.lineEdit_Property_Positioning_ChangedHandler)
        self.lineEdit_Property_Bus.textChanged.connect(self.lineEdit_Property_Bus_ChangedHandler)
        self.lineEdit_Property_Bus_NPC.textChanged.connect(self.lineEdit_Property_Bus_NPC_ChangedHandler)
        self.lineEdit_Property_SwitchGroupName_PC_NPC.textChanged.connect(self.lineEdit_Property_SwitchGroupName_PC_NPC_ChangedHandler)
        self.lineEdit_Property_SwitchGroupName_Texture.textChanged.connect(self.lineEdit_Property_SwitchGroupName_Texture_ChangedHandler)

    def lineEdit_TextChanged_Disconnect(self):
        self.lineEdit_Path_InWwise_UserDefinedTemplate.textChanged.disconnect(self.lineEdit_Path_InWwise_UserDefinedTemplate_ChangedHandler)
        self.lineEdit_Path_File_PlaceholderWAV.textChanged.disconnect(self.lineEdit_Path_File_PlaceholderWAV_ChangedHandler)
        self.lineEdit_Path_Folder_TargetWAV.textChanged.disconnect(self.lineEdit_Path_Folder_TargetWAV_ChangedHandler)
        self.lineEdit_Path_InWwise_TargetActorMixer.textChanged.disconnect(self.lineEdit_Path_InWwise_TargetActorMixer_ChangedHandler)
        self.lineEdit_Path_InWwise_TargetEvent.textChanged.disconnect(self.lineEdit_Path_InWwise_TargetEvent_ChangedHandler)
        self.lineEdit_Path_InWwise_TargetBank.textChanged.disconnect(self.lineEdit_Path_InWwise_TargetBank_ChangedHandler)
        self.lineEdit_Property_Conversion.textChanged.disconnect(self.lineEdit_Property_Conversion_ChangedHandler)
        self.lineEdit_Property_Positioning.textChanged.disconnect(self.lineEdit_Property_Positioning_ChangedHandler)
        self.lineEdit_Property_Bus.textChanged.disconnect(self.lineEdit_Property_Bus_ChangedHandler)
        self.lineEdit_Property_Bus_NPC.textChanged.disconnect(self.lineEdit_Property_Bus_NPC_ChangedHandler)
        self.lineEdit_Property_SwitchGroupName_PC_NPC.textChanged.disconnect(self.lineEdit_Property_SwitchGroupName_PC_NPC_ChangedHandler)
        self.lineEdit_Property_SwitchGroupName_Texture.textChanged.disconnect(self.lineEdit_Property_SwitchGroupName_Texture_ChangedHandler)

    # ------------------------------------------------------------------- Func ----- Others
    def SelectKey(self):
        try:
            if KeyInfoDict.get("Data_KeyInfo", "") != "" and type(KeyInfoDict.get("Data_KeyInfo", "")) is dict:
                KeyStrDict = KeyInfoDict["Data_KeyInfo"]
                # 先判断当前list里的对象数量，如果对象数量为0，说明没东西了，则不执行下列动作，不然会报错
                countCurrentItemNum = self.listWidget_KeyStrList.count()
                currentItems = self.listWidget_KeyStrList.currentItem()
                if currentItems is None:
                    self.comboBox_Structure_Type.setCurrentIndex(0)
                    self.IfShowHideGroup()
                elif countCurrentItemNum != 0 and currentItems is not None:
                    selectedKeyStr = self.listWidget_KeyStrList.currentItem().text()
                    Structure_Type = KeyStrDict[selectedKeyStr]["Structure_Type"]
                    Path_InWwise_UserDefinedTemplate = KeyStrDict[selectedKeyStr]["Path_InWwise_UserDefinedTemplate"]
                    Path_File_PlaceholderWAV = KeyStrDict[selectedKeyStr]["Path_File_PlaceholderWAV"]
                    Path_Folder_TargetWAV = KeyStrDict[selectedKeyStr]["Path_Folder_TargetWAV"]
                    Path_InWwise_TargetActorMixer = KeyStrDict[selectedKeyStr]["Path_InWwise_TargetActorMixer"]
                    Path_InWwise_TargetEvent = KeyStrDict[selectedKeyStr]["Path_InWwise_TargetEvent"]
                    Path_InWwise_TargetBank = KeyStrDict[selectedKeyStr]["Path_InWwise_TargetBank"]
                    Property_Conversion = KeyStrDict[selectedKeyStr]["Property_Conversion"]
                    Property_Positioning = KeyStrDict[selectedKeyStr]["Property_Positioning"]
                    Property_Bus = KeyStrDict[selectedKeyStr]["Property_Bus"]
                    Property_Bus_NPC = KeyStrDict[selectedKeyStr]["Property_Bus_NPC"]
                    Property_SwitchGroupName_PC_NPC = KeyStrDict[selectedKeyStr]["Property_SwitchGroupName_PC_NPC"]
                    Property_SwitchGroupName_Texture = KeyStrDict[selectedKeyStr]["Property_SwitchGroupName_Texture"]
                    Property_ifPitchRandom = KeyStrDict[selectedKeyStr]["Property_ifPitchRandom"]
                    Property_ifStream = KeyStrDict[selectedKeyStr]["Property_ifStream"]

                    # --------------------------------------------------- Fill Init Info ----- comboBox
                    if len(Structure_Type) != 0:
                        if Structure_Type == "None":
                            self.comboBox_Structure_Type.setCurrentIndex(0)
                        elif Structure_Type == "type1d":
                            self.comboBox_Structure_Type.setCurrentIndex(1)
                        elif Structure_Type == "type2d":
                            self.comboBox_Structure_Type.setCurrentIndex(2)
                        elif Structure_Type == "type3d":
                            self.comboBox_Structure_Type.setCurrentIndex(3)
                        elif Structure_Type == "typet":
                            self.comboBox_Structure_Type.setCurrentIndex(4)
                        elif Structure_Type == "type1d_vo":
                            self.comboBox_Structure_Type.setCurrentIndex(5)
                        elif Structure_Type == "type2d_vo":
                            self.comboBox_Structure_Type.setCurrentIndex(6)
                        elif Structure_Type == "type2d_gun":
                            self.comboBox_Structure_Type.setCurrentIndex(7)
                        else:
                            self.comboBox_Structure_Type.setCurrentIndex(0)
                    else:
                        self.comboBox_Structure_Type.setCurrentIndex(0)

                    if Property_ifPitchRandom == "False":
                        self.comboBox_Property_ifPitchRandom.setCurrentIndex(0)
                    elif Property_ifPitchRandom == "True":
                        self.comboBox_Property_ifPitchRandom.setCurrentIndex(1)
                    else:
                        self.comboBox_Property_ifPitchRandom.setCurrentIndex(0)

                    if Property_ifStream == "False":
                        self.comboBox_Property_ifStream.setCurrentIndex(0)
                    elif Property_ifStream == "True":
                        self.comboBox_Property_ifStream.setCurrentIndex(1)
                    else:
                        self.comboBox_Property_ifStream.setCurrentIndex(0)

                    # --------------------------------------------------- Fill Init Info ----- lineEdit
                    # 在这里断联，确保批量写入时不要实例化SimpleWaapi
                    self.lineEdit_TextChanged_Disconnect()

                    # 写入lineEdit
                    self.lineEdit_Path_InWwise_UserDefinedTemplate.setText(Path_InWwise_UserDefinedTemplate)
                    self.lineEdit_Path_File_PlaceholderWAV.setText(Path_File_PlaceholderWAV)
                    self.lineEdit_Path_Folder_TargetWAV.setText(Path_Folder_TargetWAV)
                    self.lineEdit_Path_InWwise_TargetActorMixer.setText(Path_InWwise_TargetActorMixer)
                    self.lineEdit_Path_InWwise_TargetEvent.setText(Path_InWwise_TargetEvent)
                    self.lineEdit_Path_InWwise_TargetBank.setText(Path_InWwise_TargetBank)
                    self.lineEdit_Property_Conversion.setText(Property_Conversion)
                    self.lineEdit_Property_Positioning.setText(Property_Positioning)
                    self.lineEdit_Property_Bus.setText(Property_Bus)
                    self.lineEdit_Property_Bus_NPC.setText(Property_Bus_NPC)
                    self.lineEdit_Property_SwitchGroupName_PC_NPC.setText(Property_SwitchGroupName_PC_NPC)
                    self.lineEdit_Property_SwitchGroupName_Texture.setText(Property_SwitchGroupName_Texture)

                    # 在这里重联，确保逐条写入时可以正常实例化SimpleWaapi
                    self.lineEdit_TextChanged_Connect()
            else:
                self.label_statusMsg.setText(lan["GUI_LOG_InvalidKeyStrDict"][L])
                LOG.warning(lan["GUI_LOG_InvalidKeyStrDict"][L])
        except:
            traceback.print_exc()

    def TextChanged(self):
        try:
            # 顺便把msgLabel隐了
            self.label_statusMsg.setText("")

            # 先获取当前list中所有KeyStr字符串，给下一步安全检查提供比照参考，用于查重
            currentKeyStrCount = self.listWidget_KeyStrList.count()
            currentKeyStrList = []
            if currentKeyStrCount != 0:
                for i in range(currentKeyStrCount):
                    currentKeyStrList.append(self.listWidget_KeyStrList.item(i).text())

            # 获取lineEdit中用户填写的字符串
            newKeyStr = self.lineEdit_EditKeyStr.text()

            # 判断用户输入的字符串合法性（是否包含非法字符、是否数字开头、是否与已存在的有冲突等）
            if len(newKeyStr) != 0 and newKeyStr is not None:
                if CheckIfStringHasInvalidCharactor(newKeyStr) is False:
                    self.label_Log.setText(lan["GUI_LOG_InvalidCharInStr"][L])
                elif CheckIfStringStartsWithNotNum(newKeyStr) is False:
                    self.label_Log.setText(lan["GUI_LOG_InvalidFirstChar"][L])
                else:
                    if newKeyStr in currentKeyStrList:
                        self.label_Log.setText(lan["GUI_LOG_CharAlreadyExist"][L])
                    else:
                        self.label_Log.setText("")
            else:
                self.label_Log.setText("")
        except:
            traceback.print_exc()

    def SaveJson_LineEdit_TextChanged(self, lineEditObj):  # 当用户变更lineEdit内容时，改变后的值要自动存入info.json
        try:
            # 先确认当前KeyStrList中是否有对象
            if self.listWidget_KeyStrList.count() == 0:  # 如果左侧栏KeyStrList里面啥也没
                pass
            else:  # 如果左侧栏KeyStrList里面有东西
                # 获取当前lineEdit中的信息
                currentText = lineEditObj.text()
                # 获取左侧栏KeyStrList中被选中的对象的字符串
                currentKeyStr = self.listWidget_KeyStrList.currentItem().text()

                # 分类讨论。信息存入info.json
                if lineEditObj is self.lineEdit_Path_InWwise_UserDefinedTemplate:
                    keyIndexStr = "Path_InWwise_UserDefinedTemplate"
                elif lineEditObj is self.lineEdit_Path_File_PlaceholderWAV:
                    keyIndexStr = "Path_File_PlaceholderWAV"
                elif lineEditObj is self.lineEdit_Path_Folder_TargetWAV:
                    keyIndexStr = "Path_Folder_TargetWAV"
                elif lineEditObj is self.lineEdit_Path_InWwise_TargetActorMixer:
                    keyIndexStr = "Path_InWwise_TargetActorMixer"
                elif lineEditObj is self.lineEdit_Path_InWwise_TargetEvent:
                    keyIndexStr = "Path_InWwise_TargetEvent"
                elif lineEditObj is self.lineEdit_Path_InWwise_TargetBank:
                    keyIndexStr = "Path_InWwise_TargetBank"
                elif lineEditObj is self.lineEdit_Property_Conversion:
                    keyIndexStr = "Property_Conversion"
                elif lineEditObj is self.lineEdit_Property_Positioning:
                    keyIndexStr = "Property_Positioning"
                elif lineEditObj is self.lineEdit_Property_Bus:
                    keyIndexStr = "Property_Bus"
                elif lineEditObj is self.lineEdit_Property_Bus_NPC:
                    keyIndexStr = "Property_Bus_NPC"
                elif lineEditObj is self.lineEdit_Property_SwitchGroupName_PC_NPC:
                    keyIndexStr = "Property_SwitchGroupName_PC_NPC"
                elif lineEditObj is self.lineEdit_Property_SwitchGroupName_Texture:
                    keyIndexStr = "Property_SwitchGroupName_Texture"
                else:
                    keyIndexStr = "ErrorRecord"

                tempIndex = {
                    "Path_InWwise_UserDefinedTemplate": self.lineEdit_Path_InWwise_UserDefinedTemplate,
                    "Property_Conversion": self.lineEdit_Property_Conversion,
                    "Property_Positioning": self.lineEdit_Property_Positioning,
                    "Property_Bus": self.lineEdit_Property_Bus,
                    "Property_Bus_NPC": self.lineEdit_Property_Bus_NPC,
                    "Property_SwitchGroupName_PC_NPC": self.lineEdit_Property_SwitchGroupName_PC_NPC,
                    "Property_SwitchGroupName_Texture": self.lineEdit_Property_SwitchGroupName_Texture
                }

                # 先判断currentText的合法性，然后再保存，否则“字体变红+json维持原判”
                # 判断类是否处于实例化状态
                instanceStatus = str(is_instance_exist(SimpleWaapi))
                LOG.debug("")
                LOG.debug("[@@@] SimpleWaapi类实例化状态 --> " + instanceStatus + " --> " + str(currentKeyStr) + " --> " + str(keyIndexStr))
                GO = SimpleWaapi()
                LOG.debug("[SW实例创建][KeyInfo][SaveJson_LineEdit_TextChanged] --> " + str(currentKeyStr) + " --> " + str(keyIndexStr))
                if keyIndexStr in ["Path_InWwise_UserDefinedTemplate", "Property_Conversion", "Property_Positioning", "Property_Bus", "Property_Bus_NPC"]:
                    if len(currentText) == 0:
                        tempIndex[keyIndexStr].setStyleSheet("color:black")
                        tempIndex[keyIndexStr].setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
                        KeyInfoDict["Data_KeyInfo"][currentKeyStr][keyIndexStr] = currentText
                    else:
                        if GO.get_GUIDOfPath(currentText) is not None:
                            tempIndex[keyIndexStr].setStyleSheet("color:black")
                            tempIndex[keyIndexStr].setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
                            KeyInfoDict["Data_KeyInfo"][currentKeyStr][keyIndexStr] = currentText
                        else:
                            tempIndex[keyIndexStr].setStyleSheet("color:red")
                            tempIndex[keyIndexStr].setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))

                elif keyIndexStr in ["Property_SwitchGroupName_PC_NPC", "Property_SwitchGroupName_Texture"]:
                    if len(currentText) == 0:
                        tempIndex[keyIndexStr].setStyleSheet("color:black")
                        tempIndex[keyIndexStr].setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
                        KeyInfoDict["Data_KeyInfo"][currentKeyStr][keyIndexStr] = currentText
                    else:
                        if GO.get_Path_From_SwitchGroupName(currentText) is not None:
                            tempIndex[keyIndexStr].setStyleSheet("color:black")
                            tempIndex[keyIndexStr].setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
                            KeyInfoDict["Data_KeyInfo"][currentKeyStr][keyIndexStr] = currentText
                        else:
                            tempIndex[keyIndexStr].setStyleSheet("color:red")
                            tempIndex[keyIndexStr].setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
                else:
                    KeyInfoDict["Data_KeyInfo"][currentKeyStr][keyIndexStr] = currentText

                GO.__del__()
                LOG.debug("[SW实例清除***][KeyInfo][SaveJson_LineEdit_TextChanged] --> " + str(currentKeyStr) + " --> " + str(keyIndexStr))

                # 保存
                SaveJson(KeyInfoDict, global_curWwiseBaseJson)
        except:
            traceback.print_exc()

    def SaveJson_ComboBox_CurrentIndexChanged(self, comboBoxObj):  # 当用户变更comboBox下拉选项时，改变后的值要自动存入info.json
        try:
            # 先确认当前KeyStrList中是否有对象
            if self.listWidget_KeyStrList.count() == 0:  # 如果左侧栏KeyStrList里面啥也没
                pass
            else:  # 如果左侧栏KeyStrList里面有对象
                # 获取当前comboBox被选中的Index是几号位
                currentIndex = comboBoxObj.currentIndex()
                # 获取左侧栏KeyStrList中被选中的对象的字符串
                if self.listWidget_KeyStrList.currentItem() is not None:
                    currentKeyStr = self.listWidget_KeyStrList.currentItem().text()

                    # 分类讨论。信息存入info.json
                    if comboBoxObj is self.comboBox_Structure_Type:
                        keyIndexStr = "Structure_Type"
                        # 根据index推断得出当前合理的text值，预备下一步在info.json中保存该值
                        if currentIndex == 0:
                            currentText = "None"
                        elif currentIndex == 1:
                            currentText = "type1d"
                        elif currentIndex == 2:
                            currentText = "type2d"
                        elif currentIndex == 3:
                            currentText = "type3d"
                        elif currentIndex == 4:
                            currentText = "typet"
                        elif currentIndex == 5:
                            currentText = "type1d_vo"
                        elif currentIndex == 6:
                            currentText = "type2d_vo"
                        elif currentIndex == 7:
                            currentText = "type2d_gun"
                        else:
                            currentText = "None"

                        # 除了送出信息给info.json保存外，由于Structure_Type的值的变更，也决定其他元素显示与否，因此这里还需驱动相关元素的显示和隐藏
                        self.IfShowHideGroup()

                    elif comboBoxObj is self.comboBox_Property_ifPitchRandom:
                        keyIndexStr = "Property_ifPitchRandom"
                        if currentIndex == 0:
                            currentText = "False"
                        else:
                            currentText = "True"
                    elif comboBoxObj is self.comboBox_Property_ifStream:
                        keyIndexStr = "Property_ifStream"
                        if currentIndex == 0:
                            currentText = "False"
                        else:
                            currentText = "True"
                    else:
                        keyIndexStr = "ErrorRecord"
                        currentText = ""

                    KeyInfoDict["Data_KeyInfo"][currentKeyStr][keyIndexStr] = currentText

                    # 保存
                    SaveJson(KeyInfoDict, global_curWwiseBaseJson)
        except:
            traceback.print_exc()

    def RightClickMenu_listWidget_KeyStrList(self):
        Menu = QMenu(self)
        Menu.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))

        action_InsertStructureInWwise = QAction(lan["GUI_RC_InsertStructureInWwise"][L], self)
        Menu.addAction(action_InsertStructureInWwise)
        action_InsertStructureInWwise.triggered.connect(self.action_InsertStructureInWwise)

        Menu.addSeparator()

        action_RemoveKey = QAction(lan["GUI_RC_RemoveKey"][L], self)
        Menu.addAction(action_RemoveKey)
        action_RemoveKey.triggered.connect(self.DeleteKey)

        Menu.popup(QCursor.pos())

    def AddKey(self):
        try:
            if globals.LoadFlag is False:
                self.label_statusMsg.setText(lan["LOG_LoadAlert"][L])
                LOG.warning(lan["LOG_LoadAlert"][L])
            else:
                # 先获取当前list中所有KeyStr字符串，给下一步安全检查提供比照参考，用于查重
                currentKeyStrCount = self.listWidget_KeyStrList.count()
                currentKeyStrList = []
                if currentKeyStrCount != 0:
                    for i in range(currentKeyStrCount):
                        currentKeyStrList.append(self.listWidget_KeyStrList.item(i).text())

                # 获取lineEdit中用户填写的字符串
                newKeyStr = self.lineEdit_EditKeyStr.text()

                # 判断用户输入的字符串合法性（是否包含非法字符、是否数字开头、是否与已存在的有冲突等）
                if len(newKeyStr) != 0 and newKeyStr is not None:
                    if CheckIfStringHasInvalidCharactor(newKeyStr) is False:
                        # self.label_statusMsg.setText(lan["GUI_LOG_InvalidCharInStr"][L])
                        LOG.warning(lan["GUI_LOG_InvalidCharInStr"][L])
                    elif CheckIfStringStartsWithNotNum(newKeyStr) is False:
                        # self.label_statusMsg.setText(lan["GUI_LOG_InvalidFirstChar"][L])
                        LOG.warning(lan["GUI_LOG_InvalidFirstChar"][L])
                    else:
                        if newKeyStr in currentKeyStrList:
                            # self.label_statusMsg.setText(lan["GUI_LOG_CharAlreadyExist"][L])
                            LOG.warning(lan["GUI_LOG_CharAlreadyExist"][L])
                        else:  # 如果安全检查通过，生成空{}框架，加入总Dict
                            newDict = {
                                "Structure_Type": "None",
                                "Path_InWwise_UserDefinedTemplate": "",
                                "Path_File_PlaceholderWAV": global_wavSilencePath,
                                "Path_Folder_TargetWAV": "Originals\\SFX\\",
                                "Path_InWwise_TargetActorMixer": "\\Actor-Mixer Hierarchy\\Audio_" + newKeyStr + "\\" + newKeyStr,
                                "Path_InWwise_TargetEvent": "\\Events\\Event_" + newKeyStr,
                                "Path_InWwise_TargetBank": "\\SoundBanks\\Bank_" + newKeyStr + "\\Bank_" + newKeyStr,
                                "Property_Conversion": "",
                                "Property_Positioning": "",
                                "Property_Bus": "",
                                "Property_Bus_NPC": "",
                                "Property_SwitchGroupName_PC_NPC": "",
                                "Property_SwitchGroupName_Texture": "",
                                "Property_ifPitchRandom": "False",
                                "Property_ifStream": "False"
                            }
                            KeyInfoDict["Data_KeyInfo"][newKeyStr] = newDict
                            SaveJson(KeyInfoDict, global_curWwiseBaseJson)

                            # 重新加载listWidget_KeyStrList，刷新列表显示，并高亮到新增的对象上
                            self.listWidget_KeyStrList.clear()
                            for keyStr, valueDict in zip(KeyInfoDict["Data_KeyInfo"].keys(), KeyInfoDict["Data_KeyInfo"].values()):
                                self.listWidget_KeyStrList.addItem(keyStr)
                            self.listWidget_KeyStrList.setCurrentRow(currentKeyStrCount)
        except:
            traceback.print_exc()

    def AddKeyByMirror(self):
        try:
            if globals.LoadFlag is False:
                self.label_statusMsg.setText(lan["LOG_LoadAlert"][L])
                LOG.warning(lan["LOG_LoadAlert"][L])
            else:
                # 先获取当前list中所有KeyStr字符串，给下一步安全检查提供比照参考，用于查重
                currentKeyStrCount = self.listWidget_KeyStrList.count()
                currentKeyStrList = []
                if currentKeyStrCount != 0:
                    for i in range(currentKeyStrCount):
                        currentKeyStrList.append(self.listWidget_KeyStrList.item(i).text())

                # 获取lineEdit中用户填写的字符串
                newKeyStr = self.lineEdit_EditKeyStr.text()

                # 获取当前被选中待镜像的Key
                if self.listWidget_KeyStrList.currentItem() is not None:
                    selectedKeyStr = self.listWidget_KeyStrList.currentItem().text()
                    self.label_statusMsg.setText(lan["GUI_LOG_CurrentSelectKeyStr"][L] + str(selectedKeyStr))
                    # 判断用户输入的字符串合法性（是否包含非法字符、是否数字开头、是否与已存在的有冲突等）
                    if len(newKeyStr) != 0 and newKeyStr is not None:
                        if CheckIfStringHasInvalidCharactor(newKeyStr) is False:
                            # self.label_statusMsg.setText(lan["GUI_LOG_InvalidCharInStr"][L])
                            LOG.warning(lan["GUI_LOG_InvalidCharInStr"][L])
                        elif CheckIfStringStartsWithNotNum(newKeyStr) is False:
                            # self.label_statusMsg.setText(lan["GUI_LOG_InvalidFirstChar"][L])
                            LOG.warning(lan["GUI_LOG_InvalidFirstChar"][L])
                        else:
                            if newKeyStr in currentKeyStrList:
                                # self.label_statusMsg.setText(lan["GUI_LOG_CharAlreadyExist"][L])
                                LOG.warning(lan["GUI_LOG_CharAlreadyExist"][L])
                            else:  # 如果安全检查通过，生成空{}框架，加入总Dict
                                KeyInfoDict["Data_KeyInfo"][newKeyStr] = KeyInfoDict["Data_KeyInfo"][selectedKeyStr].copy()

                                # 将3个wwu路径替换为新的目标路径
                                KeyInfoDict["Data_KeyInfo"][newKeyStr]["Path_InWwise_TargetActorMixer"] = "\\Actor-Mixer Hierarchy\\Audio_" + newKeyStr + "\\" + newKeyStr
                                KeyInfoDict["Data_KeyInfo"][newKeyStr]["Path_InWwise_TargetEvent"] = "\\Events\\Event_" + newKeyStr
                                KeyInfoDict["Data_KeyInfo"][newKeyStr]["Path_InWwise_TargetBank"] = "\\SoundBanks\\Bank_" + newKeyStr + "\\Bank_" + newKeyStr

                                # 保存结果
                                SaveJson(KeyInfoDict, global_curWwiseBaseJson)

                                # 重新加载listWidget_KeyStrList，刷新列表显示，并高亮到新增的对象上
                                self.listWidget_KeyStrList.clear()
                                for keyStr, valueDict in zip(KeyInfoDict["Data_KeyInfo"].keys(), KeyInfoDict["Data_KeyInfo"].values()):
                                    self.listWidget_KeyStrList.addItem(keyStr)
                                self.listWidget_KeyStrList.setCurrentRow(currentKeyStrCount)
        except:
            traceback.print_exc()

    def DeleteKey(self):
        try:
            if globals.LoadFlag is False:
                self.label_statusMsg.setText(lan["LOG_LoadAlert"][L])
                LOG.warning(lan["LOG_LoadAlert"][L])
            else:
                if self.listWidget_KeyStrList.currentItem() is not None:
                    selectedKeyStr = self.listWidget_KeyStrList.currentItem().text()
                    currentRow = self.listWidget_KeyStrList.currentRow()
                    AllKeyStrList = []
                    for keyy, val in zip(SoundListDict["Data_SoundList"].keys(), SoundListDict["Data_SoundList"].values()):
                        AllKeyStrList.append(SoundListDict["Data_SoundList"][keyy]["KeyStr"]["text"])

                    if selectedKeyStr not in AllKeyStrList:
                        KeyInfoDict["Data_KeyInfo"].pop(selectedKeyStr)
                        SaveJson(KeyInfoDict, global_curWwiseBaseJson)
                        self.listWidget_KeyStrList.takeItem(currentRow)

                        # 清理完后，确认当前KeyStrList是否为空，如果是，则重置面板
                        if self.listWidget_KeyStrList.count() == 0:
                            self.comboBox_Structure_Type.setCurrentIndex(0)
                            self.IfShowHideGroup()
                    else:
                        self.label_statusMsg.setText(lan["GUI_LOG_InUsingAlert"][L] + selectedKeyStr)
                        LOG.warning(lan["GUI_LOG_InUsingAlert"][L] + selectedKeyStr)
        except:
            traceback.print_exc()

    def action_InsertStructureInWwise(self):
        try:
            if SafetyCheck_WwiseRunningStatus() is True:
                go = SimpleWaapi()
                LOG.debug("[SW实例创建][KeyInfo][action_InsertStructureInWwise]")
                projectFolderPath = go.get_FolderPath_WwiseCurrentProjectPath()
                if projectFolderPath is None:
                    self.label_statusMsg.setText(lan["LOG_LOG_WwiseStatusError_maynotload"][L])
                    LOG.warning(lan["LOG_LOG_WwiseStatusError_maynotload"][L])
                else:
                    curKeyStr = self.listWidget_KeyStrList.currentItem().text()
                    curKeyStr_Color = self.listWidget_KeyStrList.currentItem().background().color().name()
                    # 添加type选项判断
                    currentTypeIndex = self.comboBox_Structure_Type.currentIndex()
                    if currentTypeIndex == 0:
                        self.label_statusMsg.setText(lan["GUI_LOG_InvalidType"][L] + curKeyStr)
                        LOG.warning(lan["GUI_LOG_InvalidType"][L] + curKeyStr)
                    else:
                        if curKeyStr_Color == "#ffffff":
                            messageBox = QMessageBox(QMessageBox.Warning, lan["GUI_RC_InsertStructureInWwise_SafetyAlert_title"][L], lan["GUI_RC_InsertStructureInWwise_SafetyAlert_Text"][L])
                            messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
                            Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
                            Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
                            messageBox.exec_()
                            if messageBox.clickedButton() == Qyes:
                                go.CreateCleanBasic_ForTargetKeyStr(curKeyStr)
                                self.label_statusMsg.setText(lan["GUI_LOG_WriteIntoWwiseNotice"][L] + curKeyStr)
                        else:
                            go.CreateCleanBasic_ForTargetKeyStr(curKeyStr)
                            self.label_statusMsg.setText(lan["GUI_LOG_WriteIntoWwiseNotice"][L] + curKeyStr)
                go.__del__()
                LOG.debug("[SW实例清除***][KeyInfo][action_InsertStructureInWwise]")
            else:
                self.label_statusMsg.setText(lan["LOG_LOG_WwiseStatusError"][L])
                LOG.warning(lan["LOG_LOG_WwiseStatusError"][L])
        except:
            traceback.print_exc()

    def IfShowHideGroup(self):
        typeValue = self.comboBox_Structure_Type.currentText()

        if typeValue == "None":
            self.label_Path_InWwise_UserDefinedTemplate.setVisible(False)
            self.lineEdit_Path_InWwise_UserDefinedTemplate.setVisible(False)

            self.label_Path_File_PlaceholderWAV.setVisible(False)
            self.lineEdit_Path_File_PlaceholderWAV.setVisible(False)
            self.pushButton_Browse_Path_File_PlaceholderWAV.setVisible(False)

            self.label_Path_Folder_TargetWAV.setVisible(False)
            self.lineEdit_Path_Folder_TargetWAV.setVisible(False)
            self.pushButton_Browse_Path_Folder_TargetWAV.setVisible(False)

            self.label_Path_InWwise_TargetActorMixer.setVisible(False)
            self.lineEdit_Path_InWwise_TargetActorMixer.setVisible(False)

            self.label_Path_InWwise_TargetEvent.setVisible(False)
            self.lineEdit_Path_InWwise_TargetEvent.setVisible(False)

            self.label_Path_InWwise_TargetBank.setVisible(False)
            self.lineEdit_Path_InWwise_TargetBank.setVisible(False)

            self.label_Property_Conversion.setVisible(False)
            self.lineEdit_Property_Conversion.setVisible(False)
            self.comboBox_Property_Conversion.setVisible(False)

            self.label_Property_Positioning.setVisible(False)
            self.lineEdit_Property_Positioning.setVisible(False)
            self.comboBox_Property_Positioning.setVisible(False)

            self.label_Property_Bus.setVisible(False)
            self.lineEdit_Property_Bus.setVisible(False)
            self.comboBox_Property_Bus.setVisible(False)

            self.label_Property_Bus_NPC.setVisible(False)
            self.lineEdit_Property_Bus_NPC.setVisible(False)
            self.comboBox_Property_Bus_NPC.setVisible(False)

            self.label_Property_SwitchGroupName_PC_NPC.setVisible(False)
            self.lineEdit_Property_SwitchGroupName_PC_NPC.setVisible(False)
            self.comboBox_Property_SwitchGroupName_PC_NPC.setVisible(False)

            self.label_Property_SwitchGroupName_Texture.setVisible(False)
            self.lineEdit_Property_SwitchGroupName_Texture.setVisible(False)
            self.comboBox_Property_SwitchGroupName_Texture.setVisible(False)

            self.label_Property_ifPitchRandom.setVisible(False)
            self.comboBox_Property_ifPitchRandom.setVisible(False)

            self.label_Property_ifStream.setVisible(False)
            self.comboBox_Property_ifStream.setVisible(False)
        elif typeValue == "type1d":
            self.label_Path_InWwise_UserDefinedTemplate.setVisible(False)
            self.lineEdit_Path_InWwise_UserDefinedTemplate.setVisible(False)

            self.label_Path_File_PlaceholderWAV.setVisible(False)
            self.lineEdit_Path_File_PlaceholderWAV.setVisible(False)
            self.pushButton_Browse_Path_File_PlaceholderWAV.setVisible(False)

            self.label_Path_Folder_TargetWAV.setVisible(False)
            self.lineEdit_Path_Folder_TargetWAV.setVisible(False)
            self.pushButton_Browse_Path_Folder_TargetWAV.setVisible(False)

            self.label_Path_InWwise_TargetActorMixer.setVisible(False)
            self.lineEdit_Path_InWwise_TargetActorMixer.setVisible(False)

            self.label_Path_InWwise_TargetEvent.setVisible(False)
            self.lineEdit_Path_InWwise_TargetEvent.setVisible(False)

            self.label_Path_InWwise_TargetBank.setVisible(False)
            self.lineEdit_Path_InWwise_TargetBank.setVisible(False)

            self.label_Property_Conversion.setVisible(True)
            self.lineEdit_Property_Conversion.setVisible(True)
            self.comboBox_Property_Conversion.setVisible(True)

            self.label_Property_Positioning.setVisible(True)
            self.lineEdit_Property_Positioning.setVisible(True)
            self.comboBox_Property_Positioning.setVisible(True)

            self.label_Property_Bus.setVisible(True)
            self.lineEdit_Property_Bus.setVisible(True)
            self.comboBox_Property_Bus.setVisible(True)

            self.label_Property_Bus_NPC.setVisible(False)
            self.lineEdit_Property_Bus_NPC.setVisible(False)
            self.comboBox_Property_Bus_NPC.setVisible(False)

            self.label_Property_SwitchGroupName_PC_NPC.setVisible(False)
            self.lineEdit_Property_SwitchGroupName_PC_NPC.setVisible(False)
            self.comboBox_Property_SwitchGroupName_PC_NPC.setVisible(False)

            self.label_Property_SwitchGroupName_Texture.setVisible(False)
            self.lineEdit_Property_SwitchGroupName_Texture.setVisible(False)
            self.comboBox_Property_SwitchGroupName_Texture.setVisible(False)

            self.label_Property_ifPitchRandom.setVisible(True)
            self.comboBox_Property_ifPitchRandom.setVisible(True)

            self.label_Property_ifStream.setVisible(True)
            self.comboBox_Property_ifStream.setVisible(True)
        elif typeValue == "type2d":
            self.label_Path_InWwise_UserDefinedTemplate.setVisible(False)
            self.lineEdit_Path_InWwise_UserDefinedTemplate.setVisible(False)

            self.label_Path_File_PlaceholderWAV.setVisible(False)
            self.lineEdit_Path_File_PlaceholderWAV.setVisible(False)
            self.pushButton_Browse_Path_File_PlaceholderWAV.setVisible(False)

            self.label_Path_Folder_TargetWAV.setVisible(False)
            self.lineEdit_Path_Folder_TargetWAV.setVisible(False)
            self.pushButton_Browse_Path_Folder_TargetWAV.setVisible(False)

            self.label_Path_InWwise_TargetActorMixer.setVisible(False)
            self.lineEdit_Path_InWwise_TargetActorMixer.setVisible(False)

            self.label_Path_InWwise_TargetEvent.setVisible(False)
            self.lineEdit_Path_InWwise_TargetEvent.setVisible(False)

            self.label_Path_InWwise_TargetBank.setVisible(False)
            self.lineEdit_Path_InWwise_TargetBank.setVisible(False)

            self.label_Property_Conversion.setVisible(True)
            self.lineEdit_Property_Conversion.setVisible(True)
            self.comboBox_Property_Conversion.setVisible(True)

            self.label_Property_Positioning.setVisible(True)
            self.lineEdit_Property_Positioning.setVisible(True)
            self.comboBox_Property_Positioning.setVisible(True)

            self.label_Property_Bus.setVisible(True)
            self.lineEdit_Property_Bus.setVisible(True)
            self.comboBox_Property_Bus.setVisible(True)

            self.label_Property_Bus_NPC.setVisible(True)
            self.lineEdit_Property_Bus_NPC.setVisible(True)
            self.comboBox_Property_Bus_NPC.setVisible(True)

            self.label_Property_SwitchGroupName_PC_NPC.setVisible(True)
            self.lineEdit_Property_SwitchGroupName_PC_NPC.setVisible(True)
            self.comboBox_Property_SwitchGroupName_PC_NPC.setVisible(True)

            self.label_Property_SwitchGroupName_Texture.setVisible(False)
            self.lineEdit_Property_SwitchGroupName_Texture.setVisible(False)
            self.comboBox_Property_SwitchGroupName_Texture.setVisible(False)

            self.label_Property_ifPitchRandom.setVisible(True)
            self.comboBox_Property_ifPitchRandom.setVisible(True)

            self.label_Property_ifStream.setVisible(True)
            self.comboBox_Property_ifStream.setVisible(True)
        elif typeValue == "type3d":
            self.label_Path_InWwise_UserDefinedTemplate.setVisible(False)
            self.lineEdit_Path_InWwise_UserDefinedTemplate.setVisible(False)

            self.label_Path_File_PlaceholderWAV.setVisible(False)
            self.lineEdit_Path_File_PlaceholderWAV.setVisible(False)
            self.pushButton_Browse_Path_File_PlaceholderWAV.setVisible(False)

            self.label_Path_Folder_TargetWAV.setVisible(False)
            self.lineEdit_Path_Folder_TargetWAV.setVisible(False)
            self.pushButton_Browse_Path_Folder_TargetWAV.setVisible(False)

            self.label_Path_InWwise_TargetActorMixer.setVisible(False)
            self.lineEdit_Path_InWwise_TargetActorMixer.setVisible(False)

            self.label_Path_InWwise_TargetEvent.setVisible(False)
            self.lineEdit_Path_InWwise_TargetEvent.setVisible(False)

            self.label_Path_InWwise_TargetBank.setVisible(False)
            self.lineEdit_Path_InWwise_TargetBank.setVisible(False)

            self.label_Property_Conversion.setVisible(True)
            self.lineEdit_Property_Conversion.setVisible(True)
            self.comboBox_Property_Conversion.setVisible(True)

            self.label_Property_Positioning.setVisible(True)
            self.lineEdit_Property_Positioning.setVisible(True)
            self.comboBox_Property_Positioning.setVisible(True)

            self.label_Property_Bus.setVisible(True)
            self.lineEdit_Property_Bus.setVisible(True)
            self.comboBox_Property_Bus.setVisible(True)

            self.label_Property_Bus_NPC.setVisible(True)
            self.lineEdit_Property_Bus_NPC.setVisible(True)
            self.comboBox_Property_Bus_NPC.setVisible(True)

            self.label_Property_SwitchGroupName_PC_NPC.setVisible(True)
            self.lineEdit_Property_SwitchGroupName_PC_NPC.setVisible(True)
            self.comboBox_Property_SwitchGroupName_PC_NPC.setVisible(True)

            self.label_Property_SwitchGroupName_Texture.setVisible(True)
            self.lineEdit_Property_SwitchGroupName_Texture.setVisible(True)
            self.comboBox_Property_SwitchGroupName_Texture.setVisible(True)

            self.label_Property_ifPitchRandom.setVisible(True)
            self.comboBox_Property_ifPitchRandom.setVisible(True)

            self.label_Property_ifStream.setVisible(True)
            self.comboBox_Property_ifStream.setVisible(True)
        elif typeValue == "typet":
            self.label_Path_InWwise_UserDefinedTemplate.setVisible(True)
            self.lineEdit_Path_InWwise_UserDefinedTemplate.setVisible(True)

            self.label_Path_File_PlaceholderWAV.setVisible(False)
            self.lineEdit_Path_File_PlaceholderWAV.setVisible(False)
            self.pushButton_Browse_Path_File_PlaceholderWAV.setVisible(False)

            self.label_Path_Folder_TargetWAV.setVisible(False)
            self.lineEdit_Path_Folder_TargetWAV.setVisible(False)
            self.pushButton_Browse_Path_Folder_TargetWAV.setVisible(False)

            self.label_Path_InWwise_TargetActorMixer.setVisible(False)
            self.lineEdit_Path_InWwise_TargetActorMixer.setVisible(False)

            self.label_Path_InWwise_TargetEvent.setVisible(False)
            self.lineEdit_Path_InWwise_TargetEvent.setVisible(False)

            self.label_Path_InWwise_TargetBank.setVisible(False)
            self.lineEdit_Path_InWwise_TargetBank.setVisible(False)

            self.label_Property_Conversion.setVisible(False)
            self.lineEdit_Property_Conversion.setVisible(False)
            self.comboBox_Property_Conversion.setVisible(False)

            self.label_Property_Positioning.setVisible(False)
            self.lineEdit_Property_Positioning.setVisible(False)
            self.comboBox_Property_Positioning.setVisible(False)

            self.label_Property_Bus.setVisible(False)
            self.lineEdit_Property_Bus.setVisible(False)
            self.comboBox_Property_Bus.setVisible(False)

            self.label_Property_Bus_NPC.setVisible(False)
            self.lineEdit_Property_Bus_NPC.setVisible(False)
            self.comboBox_Property_Bus_NPC.setVisible(False)

            self.label_Property_SwitchGroupName_PC_NPC.setVisible(False)
            self.lineEdit_Property_SwitchGroupName_PC_NPC.setVisible(False)
            self.comboBox_Property_SwitchGroupName_PC_NPC.setVisible(False)

            self.label_Property_SwitchGroupName_Texture.setVisible(False)
            self.lineEdit_Property_SwitchGroupName_Texture.setVisible(False)
            self.comboBox_Property_SwitchGroupName_Texture.setVisible(False)

            self.label_Property_ifPitchRandom.setVisible(True)
            self.comboBox_Property_ifPitchRandom.setVisible(True)

            self.label_Property_ifStream.setVisible(True)
            self.comboBox_Property_ifStream.setVisible(True)
        elif typeValue == "type1d_vo":
            self.label_Path_InWwise_UserDefinedTemplate.setVisible(False)
            self.lineEdit_Path_InWwise_UserDefinedTemplate.setVisible(False)

            self.label_Path_File_PlaceholderWAV.setVisible(False)
            self.lineEdit_Path_File_PlaceholderWAV.setVisible(False)
            self.pushButton_Browse_Path_File_PlaceholderWAV.setVisible(False)

            self.label_Path_Folder_TargetWAV.setVisible(False)
            self.lineEdit_Path_Folder_TargetWAV.setVisible(False)
            self.pushButton_Browse_Path_Folder_TargetWAV.setVisible(False)

            self.label_Path_InWwise_TargetActorMixer.setVisible(False)
            self.lineEdit_Path_InWwise_TargetActorMixer.setVisible(False)

            self.label_Path_InWwise_TargetEvent.setVisible(False)
            self.lineEdit_Path_InWwise_TargetEvent.setVisible(False)

            self.label_Path_InWwise_TargetBank.setVisible(False)
            self.lineEdit_Path_InWwise_TargetBank.setVisible(False)

            self.label_Property_Conversion.setVisible(True)
            self.lineEdit_Property_Conversion.setVisible(True)
            self.comboBox_Property_Conversion.setVisible(True)

            self.label_Property_Positioning.setVisible(True)
            self.lineEdit_Property_Positioning.setVisible(True)
            self.comboBox_Property_Positioning.setVisible(True)

            self.label_Property_Bus.setVisible(True)
            self.lineEdit_Property_Bus.setVisible(True)
            self.comboBox_Property_Bus.setVisible(True)

            self.label_Property_Bus_NPC.setVisible(False)
            self.lineEdit_Property_Bus_NPC.setVisible(False)
            self.comboBox_Property_Bus_NPC.setVisible(False)

            self.label_Property_SwitchGroupName_PC_NPC.setVisible(False)
            self.lineEdit_Property_SwitchGroupName_PC_NPC.setVisible(False)
            self.comboBox_Property_SwitchGroupName_PC_NPC.setVisible(False)

            self.label_Property_SwitchGroupName_Texture.setVisible(False)
            self.lineEdit_Property_SwitchGroupName_Texture.setVisible(False)
            self.comboBox_Property_SwitchGroupName_Texture.setVisible(False)

            self.label_Property_ifPitchRandom.setVisible(True)
            self.comboBox_Property_ifPitchRandom.setVisible(True)

            self.label_Property_ifStream.setVisible(True)
            self.comboBox_Property_ifStream.setVisible(True)
        elif typeValue == "type2d_vo" or typeValue == "type2d_gun":
            self.label_Path_InWwise_UserDefinedTemplate.setVisible(False)
            self.lineEdit_Path_InWwise_UserDefinedTemplate.setVisible(False)

            self.label_Path_File_PlaceholderWAV.setVisible(False)
            self.lineEdit_Path_File_PlaceholderWAV.setVisible(False)
            self.pushButton_Browse_Path_File_PlaceholderWAV.setVisible(False)

            self.label_Path_Folder_TargetWAV.setVisible(False)
            self.lineEdit_Path_Folder_TargetWAV.setVisible(False)
            self.pushButton_Browse_Path_Folder_TargetWAV.setVisible(False)

            self.label_Path_InWwise_TargetActorMixer.setVisible(False)
            self.lineEdit_Path_InWwise_TargetActorMixer.setVisible(False)

            self.label_Path_InWwise_TargetEvent.setVisible(False)
            self.lineEdit_Path_InWwise_TargetEvent.setVisible(False)

            self.label_Path_InWwise_TargetBank.setVisible(False)
            self.lineEdit_Path_InWwise_TargetBank.setVisible(False)

            self.label_Property_Conversion.setVisible(True)
            self.lineEdit_Property_Conversion.setVisible(True)
            self.comboBox_Property_Conversion.setVisible(True)

            self.label_Property_Positioning.setVisible(True)
            self.lineEdit_Property_Positioning.setVisible(True)
            self.comboBox_Property_Positioning.setVisible(True)

            self.label_Property_Bus.setVisible(True)
            self.lineEdit_Property_Bus.setVisible(True)
            self.comboBox_Property_Bus.setVisible(True)

            self.label_Property_Bus_NPC.setVisible(True)
            self.lineEdit_Property_Bus_NPC.setVisible(True)
            self.comboBox_Property_Bus_NPC.setVisible(True)

            self.label_Property_SwitchGroupName_PC_NPC.setVisible(True)
            self.lineEdit_Property_SwitchGroupName_PC_NPC.setVisible(True)
            self.comboBox_Property_SwitchGroupName_PC_NPC.setVisible(True)

            self.label_Property_SwitchGroupName_Texture.setVisible(False)
            self.lineEdit_Property_SwitchGroupName_Texture.setVisible(False)
            self.comboBox_Property_SwitchGroupName_Texture.setVisible(False)

            self.label_Property_ifPitchRandom.setVisible(True)
            self.comboBox_Property_ifPitchRandom.setVisible(True)

            self.label_Property_ifStream.setVisible(True)
            self.comboBox_Property_ifStream.setVisible(True)
        else:
            self.label_Path_InWwise_UserDefinedTemplate.setVisible(False)
            self.lineEdit_Path_InWwise_UserDefinedTemplate.setVisible(False)

            self.label_Path_File_PlaceholderWAV.setVisible(False)
            self.lineEdit_Path_File_PlaceholderWAV.setVisible(False)
            self.pushButton_Browse_Path_File_PlaceholderWAV.setVisible(False)

            self.label_Path_Folder_TargetWAV.setVisible(False)
            self.lineEdit_Path_Folder_TargetWAV.setVisible(False)
            self.pushButton_Browse_Path_Folder_TargetWAV.setVisible(False)

            self.label_Path_InWwise_TargetActorMixer.setVisible(False)
            self.lineEdit_Path_InWwise_TargetActorMixer.setVisible(False)

            self.label_Path_InWwise_TargetEvent.setVisible(False)
            self.lineEdit_Path_InWwise_TargetEvent.setVisible(False)

            self.label_Path_InWwise_TargetBank.setVisible(False)
            self.lineEdit_Path_InWwise_TargetBank.setVisible(False)

            self.label_Property_Conversion.setVisible(False)
            self.lineEdit_Property_Conversion.setVisible(False)
            self.comboBox_Property_Conversion.setVisible(False)

            self.label_Property_Positioning.setVisible(False)
            self.lineEdit_Property_Positioning.setVisible(False)
            self.comboBox_Property_Positioning.setVisible(False)

            self.label_Property_Bus.setVisible(False)
            self.lineEdit_Property_Bus.setVisible(False)
            self.comboBox_Property_Bus.setVisible(False)

            self.label_Property_Bus_NPC.setVisible(False)
            self.lineEdit_Property_Bus_NPC.setVisible(False)
            self.comboBox_Property_Bus_NPC.setVisible(False)

            self.label_Property_SwitchGroupName_PC_NPC.setVisible(False)
            self.lineEdit_Property_SwitchGroupName_PC_NPC.setVisible(False)
            self.comboBox_Property_SwitchGroupName_PC_NPC.setVisible(False)

            self.label_Property_SwitchGroupName_Texture.setVisible(False)
            self.lineEdit_Property_SwitchGroupName_Texture.setVisible(False)
            self.comboBox_Property_SwitchGroupName_Texture.setVisible(False)

            self.label_Property_ifPitchRandom.setVisible(False)
            self.comboBox_Property_ifPitchRandom.setVisible(False)

            self.label_Property_ifStream.setVisible(False)
            self.comboBox_Property_ifStream.setVisible(False)

    # ------------------------------------------------------------------- Func ----- Global Utility
    @staticmethod
    def LocatePath(FileType):
        """
        :param FileType: File; Folder
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

    @staticmethod
    def WritePathIntoLineEdit(LineEdit, path):
        if path is not None and os.path.exists(path):
            LineEdit.setText(path)

    def ClearPanel(self):
        self.comboBox_Structure_Type.setCurrentIndex(0)

        self.lineEdit_Path_InWwise_UserDefinedTemplate.setText("")
        self.lineEdit_Path_File_PlaceholderWAV.setText("")
        self.lineEdit_Path_Folder_TargetWAV.setText("")
        self.lineEdit_Path_InWwise_TargetActorMixer.setText("")
        self.lineEdit_Path_InWwise_TargetEvent.setText("")
        self.lineEdit_Path_InWwise_TargetBank.setText("")
        self.lineEdit_Property_Conversion.setText("")
        self.lineEdit_Property_Positioning.setText("")
        self.lineEdit_Property_Bus.setText("")
        self.lineEdit_Property_Bus_NPC.setText("")
        self.lineEdit_Property_SwitchGroupName_PC_NPC.setText("")
        self.lineEdit_Property_SwitchGroupName_Texture.setText("")

        self.comboBox_Property_ifPitchRandom.setCurrentIndex(0)
        self.comboBox_Property_ifStream.setCurrentIndex(0)

        self.IfShowHideGroup()

    @staticmethod
    def GetDefaultFont():
        if key["Language"] == "Chinese":
            Font_Def = key["DefaultFont_Chinese"]
        else:
            Font_Def = key["DefaultFont_English"]

        return Font_Def

    def RefreshAllComboBoxAndLineEdit(self):
        messageBox = QMessageBox(QMessageBox.Warning, lan["GUI_KIG_SafetyCheck"][L], lan["GUI_KIG_PushButton_RefreshComboBox_SafetyCheckText"][L])
        messageBox.setFont(QFont(self.GetDefaultFont(), key["DefaultFont_Size"]))
        Qyes = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_READY"][L]), QMessageBox.YesRole)
        Qno = messageBox.addButton(self.tr(lan["GUI_SafetyAlert_CANCEL"][L]), QMessageBox.NoRole)
        messageBox.exec_()
        if messageBox.clickedButton() == Qyes:
            self.UpdateAndRefreshComboBoxList()

    def UpdateAndRefreshComboBoxList(self):
        try:
            # 先储存记录
            Text_Path_File_PlaceholderWAV = self.lineEdit_Path_File_PlaceholderWAV.text()
            Text_Path_Folder_TargetWAV = self.lineEdit_Path_Folder_TargetWAV.text()
            Text_Path_InWwise_UserDefinedTemplate = self.lineEdit_Path_InWwise_UserDefinedTemplate.text()
            Text_Path_InWwise_TargetActorMixer = self.lineEdit_Path_InWwise_TargetActorMixer.text()
            Text_Path_InWwise_TargetEvent = self.lineEdit_Path_InWwise_TargetEvent.text()
            Text_Path_InWwise_TargetBank = self.lineEdit_Path_InWwise_TargetBank.text()
            Text_Property_Bus = self.lineEdit_Property_Bus.text()
            Text_Property_Bus_NPC = self.lineEdit_Property_Bus_NPC.text()
            Text_Property_SwitchGroupName_PC_NPC = self.lineEdit_Property_SwitchGroupName_PC_NPC.text()
            Text_Property_SwitchGroupName_Texture = self.lineEdit_Property_SwitchGroupName_Texture.text()
            Text_Property_Conversion = self.lineEdit_Property_Conversion.text()
            Text_Property_Positioning = self.lineEdit_Property_Positioning.text()

            # 刷新CombBox
            self.Init_ComboBox_By_ScanCurrentWwise()

            # 刷新self.label_statusMsg
            self.label_statusMsg.setText("")

            # 恢复记录
            self.lineEdit_Path_File_PlaceholderWAV.setText(Text_Path_File_PlaceholderWAV)
            self.lineEdit_Path_Folder_TargetWAV.setText(Text_Path_Folder_TargetWAV)
            self.lineEdit_Path_InWwise_UserDefinedTemplate.setText(Text_Path_InWwise_UserDefinedTemplate)
            self.lineEdit_Path_InWwise_TargetActorMixer.setText(Text_Path_InWwise_TargetActorMixer)
            self.lineEdit_Path_InWwise_TargetEvent.setText(Text_Path_InWwise_TargetEvent)
            self.lineEdit_Path_InWwise_TargetBank.setText(Text_Path_InWwise_TargetBank)
            self.lineEdit_Property_Bus.setText(Text_Property_Bus)
            self.lineEdit_Property_Bus_NPC.setText(Text_Property_Bus_NPC)
            self.lineEdit_Property_SwitchGroupName_PC_NPC.setText(Text_Property_SwitchGroupName_PC_NPC)
            self.lineEdit_Property_SwitchGroupName_Texture.setText(Text_Property_SwitchGroupName_Texture)
            self.lineEdit_Property_Conversion.setText(Text_Property_Conversion)
            self.lineEdit_Property_Positioning.setText(Text_Property_Positioning)
        except:
            traceback.print_exc()

    def Init_ComboBox_By_ScanCurrentWwise(self):
        try:
            # ["BUS", "SWITCH", "STATE", "RTPC", "CONVERSION", "ATTENUATION"]
            # List_RTPC = GO.get_Paths_of_Descendants("RTPC")
            LOG.debug(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> 扫描Wwise，收集ComboBox下拉列表中的路径等选项")
            # 清空ComboBox
            self.comboBox_Property_Bus.clear()
            self.comboBox_Property_Bus_NPC.clear()
            self.comboBox_Property_SwitchGroupName_PC_NPC.clear()
            self.comboBox_Property_SwitchGroupName_Texture.clear()
            self.comboBox_Property_Conversion.clear()
            self.comboBox_Property_Positioning.clear()

            LOG.debug("[ScanCurrentWwise] 创建SW实例")
            GO = SimpleWaapi()

            tempPathListA = GO.get_Paths_of_Descendants("SWITCH")
            tempPathList = [""] + tempPathListA
            for eachPath in tempPathList:
                tarStr = os.path.basename(eachPath)
                self.comboBox_Property_SwitchGroupName_PC_NPC.addItem(tarStr)
                self.comboBox_Property_SwitchGroupName_Texture.addItem(tarStr)

            List_BUS = [""] + GO.get_Paths_of_Descendants("BUS")
            for eachPath in List_BUS:
                self.comboBox_Property_Bus.addItem(eachPath)
                self.comboBox_Property_Bus_NPC.addItem(eachPath)

            List_CONVERSION = [""] + GO.get_Paths_of_Descendants("CONVERSION")
            for eachPath in List_CONVERSION:
                self.comboBox_Property_Conversion.addItem(eachPath)

            List_ATTENUATION = [""] + GO.get_Paths_of_Descendants("ATTENUATION")
            for eachPath in List_ATTENUATION:
                self.comboBox_Property_Positioning.addItem(eachPath)

            GO.__del__()
            LOG.debug("[ScanCurrentWwise] 手动断联SW")
            LOG.debug("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< 扫描Wwise，收集ComboBox下拉列表中的路径等选项 [结束]\n")
        except:
            traceback.print_exc()

    def Refresh_ComboBox_By_ScanCurrentWwise(self, LineEdit, ComboBoxx):
        try:
            lineEditOldText = str(LineEdit.text())
            text = ComboBoxx.currentText()

            if text == lineEditOldText:
                pass
            else:
                ComboBoxx.setCurrentIndex(0)
                LineEdit.setText(text)
                self.label_statusMsg.setText(lan["GUI_LOG_LineEditChanged"][L])
        except:
            traceback.print_exc()

    def lineEdit_Path_InWwise_UserDefinedTemplate_ChangedHandler(self):
        self.SaveJson_LineEdit_TextChanged(self.lineEdit_Path_InWwise_UserDefinedTemplate)

    def lineEdit_Path_File_PlaceholderWAV_ChangedHandler(self):
        self.SaveJson_LineEdit_TextChanged(self.lineEdit_Path_File_PlaceholderWAV)

    def lineEdit_Path_Folder_TargetWAV_ChangedHandler(self):
        self.SaveJson_LineEdit_TextChanged(self.lineEdit_Path_Folder_TargetWAV)

    def lineEdit_Path_InWwise_TargetActorMixer_ChangedHandler(self):
        self.SaveJson_LineEdit_TextChanged(self.lineEdit_Path_InWwise_TargetActorMixer)

    def lineEdit_Path_InWwise_TargetEvent_ChangedHandler(self):
        self.SaveJson_LineEdit_TextChanged(self.lineEdit_Path_InWwise_TargetEvent)

    def lineEdit_Path_InWwise_TargetBank_ChangedHandler(self):
        self.SaveJson_LineEdit_TextChanged(self.lineEdit_Path_InWwise_TargetBank)

    def lineEdit_Property_Conversion_ChangedHandler(self):
        self.SaveJson_LineEdit_TextChanged(self.lineEdit_Property_Conversion)

    def lineEdit_Property_Positioning_ChangedHandler(self):
        self.SaveJson_LineEdit_TextChanged(self.lineEdit_Property_Positioning)

    def lineEdit_Property_Bus_ChangedHandler(self):
        self.SaveJson_LineEdit_TextChanged(self.lineEdit_Property_Bus)

    def lineEdit_Property_Bus_NPC_ChangedHandler(self):
        self.SaveJson_LineEdit_TextChanged(self.lineEdit_Property_Bus_NPC)

    def lineEdit_Property_SwitchGroupName_PC_NPC_ChangedHandler(self):
        self.SaveJson_LineEdit_TextChanged(self.lineEdit_Property_SwitchGroupName_PC_NPC)

    def lineEdit_Property_SwitchGroupName_Texture_ChangedHandler(self):
        self.SaveJson_LineEdit_TextChanged(self.lineEdit_Property_SwitchGroupName_Texture)

