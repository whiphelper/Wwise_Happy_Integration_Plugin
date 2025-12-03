import json
import os
import traceback
import psutil
import ujson as ujson
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QMessageBox
from pydub import AudioSegment
from pydub.generators import Sine
from waapi import *
from xml.etree import ElementTree as et
import logging
import queue
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton
from PyQt5.QtCore import QThread, pyqtSignal, QObject
import sys


Log = logging.getLogger('whipx_logger')
Log.setLevel(logging.DEBUG)
Log.propagate = False  # 避免WaapiClient的WampClientAutobahn.logger串扰Log

file_logger = logging.getLogger('file_logger')
file_logger.setLevel(logging.DEBUG)
file_logger.propagate = False  # 避免WaapiClient的WampClientAutobahn.logger串扰Log

# 将WAMP的Logger关掉，禁止输出到日志台
WampClientAutobahn.logger.disabled = True

global_logFormat = {
    "BLUE": [
        "[START]",
        "[开始]",
        "[Finished]",
        "[完结撒花]",
        "[Scanning]",
        "[扫描中]",
        "[Global Scanning]",
        "[全局扫描中]"
    ],
    "GREEN": [
        "[Connected]",
        "[已连接]",
        "[Ready]",
        "[就绪]"
        "[已就绪]",
        "[Done]",
        "[完成]",
        "[已完成]",
        "[Refreshed]",
        "[已刷新]",
        "[Created]",
        "[已生成]",
        "[Implemented]",
        "[已整合]",
        "[Imported]",
        "[已导入]",
        "[Exported]",
        "[已导出]",
        "[Removed]",
        "[已清理]",
        "[Replaced]",
        "[已更替]",
        "[Assigned]",
        "[已指派]",
        "[Refresh]",
        "[已还原]",
        "[WAV Imported]",
        "[WAV已导入]",
        "[BankAssigned]",
        "[Bank已指派]"
    ],
    "ORANGE": [
        "[Skipped]",
        "[跳过]",
        "[已跳过]",
        "[Notice]",
        "[提示]",
        "[Exist]",
        "[已存在]",
        "[DUPLICATED Actor]",
        "[已存在的Actor对象]",
        "[DUPLICATED Event]",
        "[已存在的Event对象]",
        "[UNUSED WAV]",
        "[闲置的WAV对象]"
    ],
    "RED": [
        "[Alert]",
        "[预警]",
        "[Warning]",
        "[警告]",
        "[UNFINISHED]",
        "[未能顺利完成]",
        "[Error]",
        "[报错]",
        "[Duplicated]",
        "[重复]",
        "[Invalid]",
        "[不合法]",
        "[Missing]",
        "[丢失]",
        "[Pause]",
        "[暂停]",
        "[温馨提示]",
        "[安全提示]",
        "[异常]",
        "[安全预警]",
        "[进程异常]",
        "[Progress Error]",
        "[FAIL]",
        "[失败]"
    ],
    "PURPLE": [
        "[Super Error]",
        "[严重错误]",
        "[Super Warning]",
        "[严重警告]",
        "[Super Crashed]",
        "[严重崩溃]"
    ]
}

global_SoundIDConfigStatusReport = {
    "ID_ExistInSoundList_NotExistInEngine": ["ID1"],
    "ID_ExistInEngine_NotExistInSoundList": ["ID2"],
    "ID_FoundDuplicate_InEngine": {
        "ID3": [
            "location1",
            "location2"
        ]
    },
    "Event_ExistInSoundList_NotExistInEngine": ["Play_01"],
    "Event_ExistInEngine_NotExistInSoundList": ["Play_02"],
    "Event_FoundDuplicate_InEngine": {
        "Play_03": [
            "location1",
            "location2"
        ]
    }
}


class LOG_DUAL:
    def __init__(self, logger1, logger2):
        super().__init__()
        self.log_Console = logger1
        self.log_file = logger2

    def debug(self, msg):
        if type(msg) is dict:
            msg = json.dumps(msg, ensure_ascii=False, indent=4)
            self.log_Console.debug(msg)
            self.log_file.debug(msg)
        elif type(msg) is list:
            for eachItem in msg:
                self.log_Console.debug(" --> " + str(eachItem))
                self.log_file.debug(" -->" + str(eachItem))
        else:
            msg = str(msg)
            self.log_Console.debug(msg)
            self.log_file.debug(msg)

    def info(self, msg):
        if type(msg) is dict:
            msg = json.dumps(msg, ensure_ascii=False, indent=4)
            self.log_Console.info(msg)
            self.log_file.info(msg)
        elif type(msg) is list:
            for eachItem in msg:
                self.log_Console.info(" --> " + str(eachItem))
                self.log_file.info(" --> " + str(eachItem))
        else:
            msg = str(msg)
            self.log_Console.info(msg)
            self.log_file.info(msg)

    def warning(self, msg):
        if type(msg) is dict:
            msg = json.dumps(msg, ensure_ascii=False, indent=4)
            self.log_Console.warning(msg)
            self.log_file.warning(msg)
        elif type(msg) is list:
            for eachItem in msg:
                self.log_Console.warning(" --> " + str(eachItem))
                self.log_file.warning(" --> " + str(eachItem))
        else:
            msg = str(msg)
            self.log_Console.warning(msg)
            self.log_file.warning(msg)

    def error(self, msg):
        if type(msg) is dict:
            msg = json.dumps(msg, ensure_ascii=False, indent=4)
            self.log_Console.error(msg)
            self.log_file.error(msg)
        elif type(msg) is list:
            for eachItem in msg:
                self.log_Console.error(" --> " + str(eachItem))
                self.log_file.error(" --> " + str(eachItem))
        else:
            msg = str(msg)
            self.log_Console.error(msg)
            self.log_file.error(msg)

    def critical(self, msg):
        if type(msg) is dict:
            msg = json.dumps(msg, ensure_ascii=False, indent=4)
            self.log_Console.critical(msg)
            self.log_file.critical(msg)
        elif type(msg) is list:
            for eachItem in msg:
                self.log_Console.critical(" --> " + str(eachItem))
                self.log_file.critical(" --> " + str(eachItem))
        else:
            msg = str(msg)
            self.log_Console.critical(msg)
            self.log_file.critical(msg)


class LoggerThread_WAMP(QThread):
    log_signal = pyqtSignal(str)

    def __init__(self, logger):
        super().__init__()
        self.logger = logger
        self.logFilePath = os.path.join(global_curWwisePath, "debug.log")

    def run(self):
        # 捕获 WampClientAutobahn 类中的日志消息
        handler = logging.StreamHandler(stream=self)
        # handler = logging.FileHandler(self.logFilePath, "a", encoding="gbk")
        handler.setLevel(logging.ERROR)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def write(self, message):
        # 发送日志消息到主线程
        self.log_signal.emit(message)

    def flush(self):
        pass


def list_top_level_folders_with_paths(path):
    folders_with_paths = []
    for folder in os.listdir(path):
        folder_path = os.path.join(path, folder)
        if os.path.isdir(folder_path):
            folders_with_paths.append({"folderName": folder, "folderPath": folder_path})
    return folders_with_paths


def check_process_count(process_name):  # 计算process运行数量
    count = 0
    for proc in psutil.process_iter():
        try:
            if proc.name().lower() == process_name.lower():
                count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return count


def CreateWAVPlaceholder_SineMono20Hz1s(wavPath):
    # 参数设置
    duration = 1000  # 音频时长,单位:毫秒
    sample_rate = 44100  # 采样率,单位:Hz
    frequency = 20  # 正弦波频率,单位:Hz
    volume = -20  # 音量,单位:dBFS

    # 生成正弦波
    sine_wave = Sine(frequency).to_audio_segment(duration=duration, volume=volume)

    # 设置采样率
    sine_wave = sine_wave.set_frame_rate(sample_rate)

    # 设置声道数为单声道
    sine_wave = sine_wave.set_channels(1)

    # 导出音频文件
    sine_wave.export(wavPath, format="wav")


def MessageBox_NoticeOnly(titleText, infoText):
    messageBox = QMessageBox(QMessageBox.Warning, titleText, infoText)
    messageBox.setFont(QFont("SimSun", 9))
    Qyes = messageBox.addButton("OK", QMessageBox.YesRole)
    messageBox.exec_()

    if messageBox.clickedButton() == Qyes:
        pass


SoundListDictFlag = False
LoadFlag = False
SafetyCheckLog = []
ColorGUIDPool = []
global_LanFolderInfoList = []
global_RootLayerList = []
SoundListDict = {}
KeyInfoDict = {}
LocalInfoDict = {}
key = {}
EventInfoDict = {}
global_curWwisePath = ""
global_debugLogPath = ""
LaunchTip_Title = "安全提示/Safety Tip"
LaunchTip_Text_NoWwise = "未检测到运行中的Wwise工程！\n\n请确保 有且仅有1个 Wwise工程在运行时，再尝试启动。\n\n\nWwise session is not running!\n\nPlease make sure there is ONLY ONE Wwise session running, then try to launch again."
LaunchTip_Text_MultiWwise = "检测到多个Wwise在运行！\n\n为了确保执行的安全性、避免混淆，请确保 有且仅有1个 Wwise工程在运行时，再尝试启动。\n\n\nMultiple Wwise running sessions have been detected!\n\nIn order to ensure safe execution and avoid confusion, please launch when there is ONLY ONE Wwise session running."
global_DiagnoseEvent_EventStructure = {
    "ifBeenAssignedToBank": {"Bool": "", "Items": []},  # 是否有所属的Bank指派
    "ifMultiAction": {"Bool": "", "Items": []},  # 是否包含多个Action
    "ifMultiType": {"Bool": "", "Items": []},  # 是否存在多个ActionType
    "ifSelfParadox": {"Bool": "", "Items": []},  # 是否存在自相矛盾的Action
    "ifBeenRemoteAffected_ByActions": {"Bool": "", "Items": []},  # 是否受到其他Event中Action的影响（全局总计）（例如：Stop或Break对Play的遥控、Resume对Pause的遥控）
    "ifBeenRemoteAffected_ByVariables": {"Bool": "", "Items": []},  # 是否受到任何变量的动态传参影响（全局总计）（例如：Switch、State、RTPC、Meter等对Property的遥控，或VoiceLimit、Threshold等其他类型）
    "EstimateTotalLoudnessRange": [],  # 响度值区间
    "ActionList": {}
}

global_DiagnoseEvent_ActionStructure = {
    "ifModified": {"Bool": "", "Property": []},  # 是否存在非默认值（Action框架）
    "ifBeenRemoteAffected": {"Bool": "", "Items": []},  # 是否受到其他Event中Action的影响（局部统计）（例如：Stop或Break对Play的遥控、Resume对Pause的遥控）
    "-------": "-------",
    "Type": "",
    "ObjectRef": {
        "ifModified": {"Bool": "", "Property": [], "Reference": []},  # 是否存在非默认值（ObjectRef框架）
        "ifBeenRemoteAffected": {"Bool": "", "Items": []},  # 是否受到任何变量的动态传参影响（局部统计）（例如：Switch、State、RTPC、Meter等对Property的遥控，或VoiceLimit、Threshold等其他类型）
        "-------": "-------",
        "Name": "",
        "Path": "",
        "ID": "",
        "Type": "",
        "ActorWWU": {"Path": "", "ID": ""},
        "Parents": [],
        "Children": []
    }
}

global_DiagnoseEvent_Sub_ObjectRefStructure = {
    "ifModified": {"Bool": "", "Property": [], "Reference": []},  # 是否存在非默认值（ObjectRef框架）
    "ifBeenRemoteAffected": {"Bool": "", "Items": []},  # 是否受到任何变量的动态传参影响（局部统计）（例如：Switch、State、RTPC、Meter等对Property的遥控，或VoiceLimit、Threshold等其他类型）
    "-------": "---------------------------------------",
    "Name": "",
    "Path": "",
    "ID": "",
    "Type": "",
    "ActorWWUInfo": {"Path": "", "ID": ""}
}

global_DiagnoseEvent_PropertyStructure = {
    "Name": "",
    "Type": "",
    "Value": ""
}

global_DiagnoseEvent_ReferenceStructure = {
    "Name": "",
    "ObjectRef": "",
    "ID": "",
    "WorkUnitID": ""
}

global_OverrideKeywordDict = {
    "OverrideOutput": "OverrideOutput",
    "OutputBus": "OverrideOutput",
    "OutputBusVolume": "OverrideOutput",
    "OutputBusLowpass": "OverrideOutput",
    "OutputBusHighpass": "OverrideOutput",

    "OverrideGameAuxSends": "OverrideGameAuxSends",
    "UseGameAuxSends": "OverrideGameAuxSends",
    "GameAuxSendVolume": "OverrideGameAuxSends",

    "OverrideUserAuxSends": "OverrideUserAuxSends",
    "UserAuxSend0": "OverrideUserAuxSends",
    "UserAuxSend1": "OverrideUserAuxSends",
    "UserAuxSend2": "OverrideUserAuxSends",
    "UserAuxSend3": "OverrideUserAuxSends",
    "UserAuxSendVolume0": "OverrideUserAuxSends",
    "UserAuxSendVolume1": "OverrideUserAuxSends",
    "UserAuxSendVolume2": "OverrideUserAuxSends",
    "UserAuxSendVolume3": "OverrideUserAuxSends",

    "OverrideEarlyReflections": "OverrideEarlyReflections",
    "ReflectionsAuxSend": "OverrideEarlyReflections",
    "ReflectionsVolume": "OverrideEarlyReflections",

    "OverrideConversion": "OverrideConversion",
    "Conversion": "OverrideConversion",

    "OverrideAnalysis": "OverrideAnalysis",
    "EnableLoudnessNormalization": "OverrideAnalysis",

    "OverrideEffect": "OverrideEffect",
    "Effect0": "OverrideEffect",
    "Effect1": "OverrideEffect",
    "Effect2": "OverrideEffect",
    "Effect3": "OverrideEffect",
    "BypassEffect": "OverrideEffect",

    "OverridePositioning": "OverridePositioning",
    "CenterPercentage": "OverridePositioning",
    "SpeakerPanning": "OverridePositioning",
    "3DSpatialization": "OverridePositioning",
    "SpeakerPanning3DSpatializationMix": "OverridePositioning",
    "EnableAttenuation": "OverridePositioning",
    "Attenuation": "OverridePositioning",
    "3DPosition": "OverridePositioning",
    "HoldEmitterPositionOrientation": "OverridePositioning",
    "EnableDiffraction": "OverridePositioning",
    "HoldListenerOrientation": "OverridePositioning",

    "OverrideHdrEnvelope": "OverrideHdrEnvelope",
    "HdrEnableEnvelope": "OverrideHdrEnvelope",
    "HdrEnvelopeSensitivity": "OverrideHdrEnvelope",
    "HdrActiveRange": "OverrideHdrEnvelope",

    "IgnoreParentMaxSoundInstance": "IgnoreParentMaxSoundInstance",
    "UseMaxSoundPerInstance": "IgnoreParentMaxSoundInstance",
    "MaxSoundPerInstance": "IgnoreParentMaxSoundInstance",
    "IsGlobalLimit": "IgnoreParentMaxSoundInstance",
    "OverLimitBehavior": "IgnoreParentMaxSoundInstance",
    "MaxReachedBehavior": "IgnoreParentMaxSoundInstance",

    "OverrideVirtualVoice": "OverrideVirtualVoice",
    "BelowThresholdBehavior": "OverrideVirtualVoice",
    "VirtualVoiceQueueBehavior": "OverrideVirtualVoice",

    "OverridePriority": "OverridePriority",
    "Priority": "OverridePriority",
    "PriorityDistanceFactor": "OverridePriority",
    "PriorityDistanceOffset": "OverridePriority"
}


def getSchemaVersionFromBusWWU():
    SchemaVersion = ""
    tree = et.parse(global_curWwisePath + "\\SoundBanks\\Default Work Unit.wwu")
    root = tree.getroot()

    for item in root.iter("WwiseDocument"):
        if len(item.attrib.get("SchemaVersion")) != 0:
            SchemaVersion = item.attrib.get("SchemaVersion")

    return SchemaVersion


wwiseProcessCount = check_process_count("Wwise.exe")
if wwiseProcessCount == 1:
    tGO = WaapiClient()
    # WampClientAutobahn.logger.setLevel(logging.CRITICAL)
    argss = {
        "from": {
            "ofType": ["Project"]
        },
        "options": {
            "return": ["filePath", "id"]
        }
    }
    ProjectPathh = tGO.call("ak.wwise.core.object.get", argss)
    if ProjectPathh is not None:
        if len(ProjectPathh["return"]) != 0:
            # 预备全局变量
            global_UserPreferenceJsonPath = "cf\\json\\UserPreference.json"
            global_curWwiseProjPath = ProjectPathh["return"][0]["filePath"]
            global_curWwiseProjID = ProjectPathh["return"][0]["id"]
            global_curWwiseProjName = os.path.basename(global_curWwiseProjPath)
            global_curWwisePath = os.path.dirname(global_curWwiseProjPath)
            global_curWwiseInfoJson = global_curWwisePath + "\\info.json"
            global_curWwiseBaseJson = global_curWwisePath + "\\base.json"
            global_curWwiseLocalJson = global_curWwisePath + "\\local.json"

            # 先判断schemaversion是否为2025以上版本，需要先明确buss和actormixer的字符串
            schemaVersionFlag = False

            curSchemaVersion = getSchemaVersionFromBusWWU()
            if curSchemaVersion is not None:
                if len(curSchemaVersion) == 0:
                    pass
                else:
                    if int(curSchemaVersion) >= 133:
                        schemaVersionFlag = True

            if schemaVersionFlag is True:
                global_actorPath = global_curWwisePath + "\\Containers\\"
                global_busPath = global_curWwisePath + "\\Busses\\"
                global_actorString = "Containers"
                global_busString = "Busses"
                global_RootBusString = "Main Audio Bus"
            else:
                global_actorPath = global_curWwisePath + "\\Actor-Mixer Hierarchy\\"
                global_busPath = global_curWwisePath + "\\Master-Mixer Hierarchy\\"
                global_actorString = "Actor-Mixer Hierarchy"
                global_busString = "Master-Mixer Hierarchy"
                global_RootBusString = "Master Audio Bus"

            global_eventPath = global_curWwisePath + "\\Events\\"
            global_banksPath = global_curWwisePath + "\\SoundBanks\\"
            global_switchPath = global_curWwisePath + "\\Switches\\"
            global_statePath = global_curWwisePath + "\\States\\"
            global_rtpcPath = global_curWwisePath + "\\Game Parameters\\"
            global_conversionPath = global_curWwisePath + "\\Conversion Settings\\"
            global_attenuationPath = global_curWwisePath + "\\Attenuations\\"
            global_interactivemusicPath = global_curWwisePath + "\\Interactive Music Hierarchy\\"
            global_OriginalsPath = global_curWwisePath + "\\Originals\\"
            global_sfxPath = global_curWwisePath + "\\Originals\\SFX\\"
            global_voicePath = global_curWwisePath + "\\Originals\\Voices\\"
            global_LanFolderInfoList = list_top_level_folders_with_paths(global_voicePath)
            global_wavSilencePath = "cf\\wavPlaceholder\\silence.wav"
            if not os.path.exists(global_wavSilencePath):
                # CreateWAVPlaceholder_SineMono20Hz1s(global_wavSilencePath)
                TempSound = AudioSegment.silent(duration=1000)
                TempSound.export(global_wavSilencePath, format="wav")

            # 获取SoundBankPaths路径
            treee = et.parse(global_curWwiseProjPath)
            roott = treee.getroot()

            global_SoundBankPathList = {}
            for itemm in roott.iter("Property"):
                if itemm.attrib.get("Name") == "SoundBankPaths":
                    for valuee in itemm.iter("Value"):
                        platform = valuee.attrib.get("Platform")
                        platform_path = valuee.text
                        global_SoundBankPathList[platform] = platform_path

            # 加载UserPreference.json (同时检查json是否有效)
            if os.path.exists(global_UserPreferenceJsonPath):
                try:
                    key = ujson.load(open(global_UserPreferenceJsonPath, "r", encoding="gbk"))
                except:
                    global_UserPreferenceJsonPath = str(global_UserPreferenceJsonPath) + " -------> [损坏/BROKEN]"

            # 加载info.json (同时检查json是否有效)
            if os.path.exists(global_curWwiseInfoJson):
                try:
                    SoundListDict = ujson.load(open(global_curWwiseInfoJson, "r", encoding="gbk"))
                    SoundListDictFlag = True
                except:
                    global_curWwiseInfoJson = str(global_curWwiseInfoJson) + " -------> [损坏/BROKEN]"
            else:
                SoundListDict_Clean = {
                    "$ProjectStr$": global_curWwiseProjName,
                    "$ProjectGUID$": global_curWwiseProjID,
                    "Data_SoundList": {}
                }
                try:
                    _ = dict(SoundListDict_Clean)
                    with open(global_curWwiseInfoJson, "w") as TempSoundDataDict:
                        ujson.dump(SoundListDict_Clean, TempSoundDataDict, ensure_ascii=False, indent=4)
                    SoundListDict = ujson.load(open(global_curWwiseInfoJson, "r", encoding="gbk"))
                    SoundListDictFlag = True
                except:
                    pass

            # 加载base.json (同时检查json是否有效)
            if os.path.exists(global_curWwiseBaseJson):
                try:
                    KeyInfoDict = ujson.load(open(global_curWwiseBaseJson, "r", encoding="gbk"))
                except:
                    global_curWwiseBaseJson = str(global_curWwiseBaseJson) + " -------> [损坏/BROKEN]"
                    traceback.print_exc()
            else:
                iniDict_Clean = {
                    "$ProjectStr$": global_curWwiseProjName,
                    "$ProjectGUID$": global_curWwiseProjID,
                    "--------------[Key Info]-------------": "----------------------",
                    "Data_KeyInfo": {},
                    "--------------[Init Wwise Structure]-------------": "----------------------",
                    "Init_ProjectSettings": {
                        "GenerateMultipleBanks": "True",
                        "SoundBankGeneratePrintGUID": "True",
                        "SoundBankGenerateMaxAttenuationInfo": "True",
                        "SoundBankGenerateEstimatedDuration": "True"
                    },
                    "Init_BUS": {
                        global_RootBusString: {
                            "SFX": {
                                "Action": {
                                    "PC": "",
                                    "NPC": ""
                                },
                                "Amb": "",
                                "UI": ""
                            },
                            "Music": "",
                            "VO": "",
                            "CG": ""
                        }
                    },
                    "Init_Switch": {
                        "Switch_PC_NPC": [
                            "PC",
                            "NPC"
                        ],
                        "Switch_Footsteps_Texture": [
                            "Dirt",
                            "Gravel",
                            "Grass",
                            "Muddy",
                            "Wood",
                            "Snow",
                            "Stone",
                            "Metal",
                            "Water_Puddle",
                            "Water_Ankle",
                            "Water_Knee"
                        ],
                        "Switch_Impact_Texture": [
                            "Flesh_Human",
                            "Flesh_Beast",
                            "Concrete",
                            "Water",
                            "Debris",
                            "Wood_Solid",
                            "Wood_Hollow",
                            "Metal_Solid",
                            "Metal_Hollow",
                            "Plant_Soft",
                            "Plant_Solid"
                        ]
                    },
                    "Init_State": {
                        "State_Alive_Dead": [
                            "Alive",
                            "Dead"
                        ],
                        "State_Playing_Pause": [
                            "Playing",
                            "Pause"
                        ]
                    },
                    "Init_RTPC": {
                        "RTPC_Volume_Master": {
                            "Min": "0.0",
                            "Max": "100.0",
                            "InitialValue": "100.0"
                        },
                        "RTPC_Volume_Music": {
                            "Min": "0.0",
                            "Max": "100.0",
                            "InitialValue": "100.0"
                        },
                        "RTPC_Volume_SFX": {
                            "Min": "0.0",
                            "Max": "100.0",
                            "InitialValue": "100.0"
                        },
                        "RTPC_Volume_VO": {
                            "Min": "0.0",
                            "Max": "100.0",
                            "InitialValue": "100.0"
                        },
                        "RTPC_Time": {
                            "Min": "0.0",
                            "Max": "24.0",
                            "InitialValue": "12.0"
                        },
                        "RTPC_HP": {
                            "Min": "0.0",
                            "Max": "100",
                            "InitialValue": "100.0"
                        },
                        "RTPC_SC_Hit_Cast": {
                            "Min": "-96.0",
                            "Max": "0.0",
                            "InitialValue": "0.0"
                        },
                        "RTPC_SC_PCBus_NPCBus": {
                            "Min": "-96.0",
                            "Max": "0.0",
                            "InitialValue": "0.0"
                        }
                    },
                    "Init_SideChain": {
                        "SC_Hit_Cast": {
                            "RTPC": "RTPC_SC_Hit_Cast",
                            "AttackTime": "0.0",
                            "ReleaseTime": "0.1"
                        },
                        "SC_PCBus_NPCBus": {
                            "RTPC": "RTPC_SC_PCBus_NPCBus",
                            "AttackTime": "0.0",
                            "ReleaseTime": "0.1"
                        }
                    },
                    "Init_Attenuation": {
                        "Att_Gen": {
                            "RadiusMax": "5000"
                        },
                        "Att_Ally": {
                            "RadiusMax": "5000"
                        },
                        "Att_Enemy": {
                            "RadiusMax": "5000"
                        }
                    },
                    "Init_Conversion": {
                        "Conversions": [
                            "Conv_VO_PC",
                            "Conv_VO_NPC",
                            "Conv_SFX_PC",
                            "Conv_SFX_NPC",
                            "Conv_Music",
                            "Conv_CG"
                        ]
                    },
                    "Init_Template": [
                        "Template_Sample"
                    ],
                    "InitPitchRandomMin": -50,
                    "InitPitchRandomMax": 50,
                    "Projects_SimpleBankName": [],
                    "WWISEColor": "24",
                    "WaapiStatusDict_Read": {
                        "Init_ProjectSettings": "",
                        "Init_BUS": "",
                        "Init_Switch": "",
                        "Init_State": "",
                        "Init_RTPC": "",
                        "Init_RTPC_Value": "",
                        "Init_SideChain": "",
                        "Init_Attenuation": "",
                        "Init_Attenuation_Value": "",
                        "Init_Conversion": ""
                    },
                    "WaapiStatusDict_Write": {
                        "Init_ProjectSettings": "",
                        "Init_BUS": "",
                        "Init_Switch": "",
                        "Init_State": "",
                        "Init_RTPC": "",
                        "Init_RTPC_Value": "",
                        "Init_SideChain": "",
                        "Init_Attenuation": "",
                        "Init_Attenuation_Value": "",
                        "Init_Conversion": ""
                    }
                }
                try:
                    _ = dict(iniDict_Clean)
                    with open(global_curWwiseBaseJson, "w") as TempInitDict:
                        ujson.dump(iniDict_Clean, TempInitDict, ensure_ascii=False, indent=4)
                    KeyInfoDict = ujson.load(open(global_curWwiseBaseJson, "r", encoding="gbk"))
                except:
                    traceback.print_exc()

            # 加载local.json (同时检查json是否有效)
            if os.path.exists(global_curWwiseLocalJson):
                try:
                    LocalInfoDict = ujson.load(open(global_curWwiseLocalJson, "r", encoding="gbk"))
                except:
                    global_curWwiseLocalJson = str(global_curWwiseLocalJson) + " -------> [BROKEN]"
                    traceback.print_exc()
            else:
                localDict_Clean = {
                    "$ProjectStr$": global_curWwiseProjName,
                    "$ProjectGUID$": global_curWwiseProjID,
                    "--------------[Local Path Info]-------------": "----------------------",
                    "ActualGeneratedSoundBankPathOfOnePlatform": global_curWwisePath + "\\" + list(global_SoundBankPathList.values())[0],
                    "Path_SoundIDSTatusReport": "",
                    "Path_DefaultSaveAsFolder": "",
                    "Path_SoundListXlsx": ""
                }
                try:
                    _ = dict(localDict_Clean)
                    with open(global_curWwiseLocalJson, "w") as TempInitDict:
                        ujson.dump(localDict_Clean, TempInitDict, ensure_ascii=False, indent=4)
                    LocalInfoDict = ujson.load(open(global_curWwiseLocalJson, "r", encoding="gbk"))
                except:
                    traceback.print_exc()

            # 定义L
            if key.get("Language", "@#") == "@#":
                L = "Chinese"
            else:
                if key["Language"] == "English":
                    L = "English"
                elif key["Language"] == "Chinese":
                    L = "Chinese"
                else:
                    L = "English"

            # 创建一个Dict，将所有的信息保存起来方便后续调用
            curWwiseInfo = {
                "global_UserPreferenceJsonPath": global_UserPreferenceJsonPath,
                "global_curWwiseProjPath": global_curWwiseProjPath,
                "global_curWwiseProjName": global_curWwiseProjName,
                "global_curWwisePath": global_curWwisePath,
                "global_curWwiseInfoJson": global_curWwiseInfoJson,
                "global_actorPath": global_actorPath,
                "global_eventPath": global_eventPath,
                "global_banksPath": global_banksPath,
                "global_switchPath": global_switchPath,
                "global_statePath": global_statePath,
                "global_rtpcPath": global_rtpcPath,
                "global_busPath": global_busPath,
                "global_conversionPath": global_conversionPath,
                "global_attenuationPath": global_attenuationPath,
                "global_interactivemusicPath": global_interactivemusicPath,
                "global_wavSilencePath": global_wavSilencePath,
                "global_sfxPath": global_sfxPath,
                "global_voicePath": global_voicePath,
                "global_LanFolderInfoList": global_LanFolderInfoList,
                "global_SoundBankPaths": global_SoundBankPathList
            }

            # 创建FileHandler来处理日志记录
            global_debugLogPath = "rec.log"

            file_handler = logging.FileHandler(global_debugLogPath)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            file_logger.addHandler(file_handler)

    tGO.disconnect()
elif wwiseProcessCount > 1:
    appp = QApplication(sys.argv)
    MessageBox_NoticeOnly(LaunchTip_Title, LaunchTip_Text_MultiWwise)
    sys.exit()
elif wwiseProcessCount == 0:
    appp = QApplication(sys.argv)
    MessageBox_NoticeOnly(LaunchTip_Title, LaunchTip_Text_NoWwise)
    sys.exit()
else:
    pass

# 创建LOG实例
LOG = LOG_DUAL(Log, file_logger)
