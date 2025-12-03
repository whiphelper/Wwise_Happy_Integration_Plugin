import ctypes
import gc
import os.path
import shutil
import subprocess
import time
import traceback
import uuid
import warnings
from datetime import datetime
import re
import xmltojson
import psutil
import winreg
from past.types import basestring
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from pydub.generators import Sine

from globals import *
from Logs import *
from pydub import AudioSegment

from SimpleXLSX import *


def flatten(listtt):
    for element in listtt:
        if hasattr(element, "__iter__") and not isinstance(element, basestring):
            for subElement in flatten(element):
                yield subElement
        else:
            yield element


def LoadJson(filePath, encodingType):  # 加载指定路径的.json文件。需要输入正确的编码。
    if os.path.exists(filePath):
        try:
            JsonDict = ujson.load(open(filePath, "r", encoding=encodingType))
            return JsonDict
        except:
            return "invalid encoding"
    else:
        return "invalid path"


def SaveJson(JsonDict, filePath):  # 将Json Dict保存到指定路径的.json文件
    # 检查JsonDict的合法性
    try:
        _ = dict(JsonDict)
        # 检查filePath的合法性
        # if os.path.exists(filePath):
        # 保存Json
        with open(filePath, "w") as TempObj:
            ujson.dump(JsonDict, TempObj, ensure_ascii=False, indent=4)
        return True
        # else:
        #     return "invalid Path"
    except:
        LOG.error(lan["GUIText_SaveJsonFailed_General"][L])
        return False


def XML_To_JSON(wwuPath, outputFilePath):
    with open(wwuPath, "r", encoding="utf-8") as f:
        my_xml = f.read()
    dictJson = xmltojson.parse(my_xml)
    finalJson = json.loads(dictJson)
    SaveJson(finalJson, outputFilePath)


def getCurrentTimeStr():  # 获取当前系统时间。输出为“年月日_时分秒”
    currentTimeStr = str(datetime.now())
    ValidNameStr = []
    for i in currentTimeStr:
        if i == " " or i == "-" or i == ":" or i == ".":
            i = "_"
            ValidNameStr.append(i)
        else:
            ValidNameStr.append(i)

    ValidStr = "".join(ValidNameStr)
    ValidStr = ValidStr.replace("_", "")
    ValidStr = ValidStr[0:14]
    FinalStr = ValidStr[0:8] + "_" + ValidStr[8:16]

    return FinalStr


def get_TargetTypeFile_FromTargetFolderPath(TargetFolderPath, TargetTypeFile):  # 在“指定路径”下统计所有“指定类型”的文件
    # 判断TargetFolderPath是否合法
    if os.path.exists(TargetFolderPath):
        # 执行搜索
        PathPool = []
        for maindir, subdir, file_name_list in os.walk(TargetFolderPath):
            for filename in file_name_list:
                path = os.path.join(maindir, filename)
                if str(path).endswith("." + TargetTypeFile) is True:
                    PathPool.append(path)
        return PathPool
    else:
        return "invalid path"


def SplitFilePath(file_path):  # 将文件路径中的 父级路径、文件名、文件类型 三个字符串解析出来
    if os.path.exists(file_path) and os.path.isfile(file_path):
        file_parentPath = os.path.dirname(file_path)
        file_name_withextension = os.path.basename(file_path)
        file_extension = os.path.splitext(file_path)[1][1:]
        file_name = file_name_withextension[0:-len(file_extension)-1]
        return {"file_parentPath": file_parentPath, "file_name": file_name, "file_extension": file_extension}
    else:
        return {}


def CreateNewFolder(TargetPath, NewFolderName):  # 在指定路径创建指定命名的文件夹
    # 判断合法性
    if CheckIfStringHasInvalidCharactor(NewFolderName) is True and os.path.exists(TargetPath) and os.path.isdir(TargetPath):
        NewFolderPath_Virtual = os.path.join(TargetPath, NewFolderName)
        if TargetPath.split(":")[1] == "":
            NewFolderPath_Virtual = NewFolderPath_Virtual.replace(":", ":\\")
        if not os.path.exists(NewFolderPath_Virtual):
            os.mkdir(NewFolderPath_Virtual)
            return NewFolderPath_Virtual
        else:
            return ""
    else:
        return ""


def CheckIfStringHasInvalidCharactor(StringToBeChecked):  # 检查字符串中是否包含非法字符
    invalidStr_SystemDefined = "\\/:*?\"<>|"
    invalidStr_UserDefined = " `~!@#$%^&*()-=+[{]}\\|;:\'\",<.>/?·￥…（）—、【】；‘’”“《》？！，。"
    String = str(StringToBeChecked)

    invalidcount = 0
    for eachChar in String:
        if eachChar in invalidStr_UserDefined:
            invalidcount += 1

    if invalidcount == 0:
        result = check_string(StringToBeChecked)
        if result is True:
            return True
        else:
            return False
    else:
        return False


def ifStrHasInvalidChar(string):
    invalidStr = " `~!@#$%^&*()-=+[{]}\\|;:\'\",<.>/?·￥…（）—、【】；‘’”“《》？！，。"
    invalidlog = []
    # 检查string里是否有非法字符
    for i in invalidStr:
        if i in string:
            invalidlog.append(i)

    return invalidlog

def ifValidID(SoundID):
    SoundID = str(SoundID)
    validList = ["1","2","3","4","5","6","7","8","9","0"]
    invalidcount = 0
    for eachChar in SoundID:
        if eachChar not in validList:
            invalidcount += 1

    if invalidcount == 0:
        return True
    else:
        return False

def CheckIfTargetObjectIsUnderTargetPath(TargetPath, TargetObjectName):  # 检查指定对象是否存在于指定路径下
    # 判断合法性
    if os.path.exists(TargetPath) and os.path.isdir(TargetPath):
        NewFolderPath_Virtual = os.path.join(TargetPath, TargetObjectName)
        if TargetPath.split(":")[1] == "":
            NewFolderPath_Virtual = NewFolderPath_Virtual.replace(":", ":\\")

        if os.path.exists(NewFolderPath_Virtual):
            return True
        else:
            return False


def CopyFile_ReplaceIfExist(sourceFullPathName, targetFullPathName):  # 复制文件到指定位置，重名时覆盖旧文件 (支持顺便重命名)
    ADVErrorLog = []

    # 先判断两个路径是否都为文件
    if not os.path.exists(sourceFullPathName):  # 判断sourceFullPathName是否存在
        ADVErrorLog.append(sourceFullPathName)
        warnings.warn("not exist")
    elif not os.path.isfile(sourceFullPathName):  # 判断sourceFullPathName是不是文件，而不是文件夹
        ADVErrorLog.append(sourceFullPathName)
        warnings.warn("is folder")
    else:
        # 判断新路径是否包含后缀
        count = targetFullPathName.rfind(".")
        if count == -1:
            ADVErrorLog.append(sourceFullPathName)
            warnings.warn("missing extension")
        else:
            extensionStr_Tar = targetFullPathName[count + 1:]
            extensionStr_Ori = SplitFilePath(sourceFullPathName).get("file_extension", "")
            # 检查两个路径的文件格式是否一致
            if extensionStr_Tar != extensionStr_Ori:
                ADVErrorLog.append(sourceFullPathName)
                warnings.warn("extension doesn't match")
            else:
                # 根据targetFullPathName推导目标父级路径
                targetPath = os.path.dirname(targetFullPathName)
                if not os.path.exists(targetPath):  # 如果目标父路径不存在
                    ADVErrorLog.append(targetPath)
                    warnings.warn("target folder path doesn't exist")
                else:
                    if os.path.exists(targetFullPathName):  # 如果目标全路径已存在
                        os.remove(targetFullPathName)
                        shutil.copy(sourceFullPathName, targetFullPathName)
                    else:
                        shutil.copy(sourceFullPathName, targetFullPathName)

    if len(ADVErrorLog) != 0:
        return False
    else:
        return True


def CopyFile_SkipIfExist(sourceFullPathName, targetFullPathName):  # 复制文件到指定位置，重名时跳过，啥也不干 (支持顺便重命名)
    ADVErrorLog = []

    # 先判断两个路径是否都为文件
    if not os.path.exists(sourceFullPathName):  # 判断sourceFullPathName是否存在
        ADVErrorLog.append(sourceFullPathName)
        warnings.warn("not exist")
    elif not os.path.isfile(sourceFullPathName):  # 判断sourceFullPathName是不是文件，而不是文件夹
        ADVErrorLog.append(sourceFullPathName)
        warnings.warn("is folder")
    else:
        # 判断新路径是否包含后缀
        count = targetFullPathName.rfind(".")
        if count == -1:
            ADVErrorLog.append(sourceFullPathName)
            warnings.warn("missing extension")
        else:
            extensionStr_Tar = targetFullPathName[count + 1:]
            extensionStr_Ori = SplitFilePath(sourceFullPathName).get("file_extension", "")
            # 检查两个路径的文件格式是否一致
            if extensionStr_Tar != extensionStr_Ori:
                ADVErrorLog.append(sourceFullPathName)
                warnings.warn("extension doesn't match")
            else:
                # 根据targetFullPathName推导目标父级路径
                targetPath = os.path.dirname(targetFullPathName)
                if not os.path.exists(targetPath):  # 如果目标父路径不存在
                    ADVErrorLog.append(targetPath)
                    warnings.warn("target folder path doesn't exist")
                else:
                    if os.path.exists(targetFullPathName):  # 如果目标全路径已存在
                        pass
                    else:
                        shutil.copy(sourceFullPathName, targetFullPathName)

    if len(ADVErrorLog) != 0:
        return False
    else:
        return True


def removeFile(file_path):  # 彻底删除文件（不进回收站）
    if os.path.exists(file_path):
        try:
            # 删除文件
            shutil.rmtree(file_path)
        except:
            LOG.error("[REMOVE FAILED]")


def GetDesktopPath():  # 获取桌面路径
    # return os.path.join(os.path.expanduser("~"), "Desktop")
    keyy = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders')
    return winreg.QueryValueEx(keyy, "Desktop")[0]


def is_process_running(process_name):  # 检查process是否正在运行中
    for proc in psutil.process_iter():
        try:
            if proc.name().lower() == process_name.lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def Kill_process(process_name):  # 终止process
    if is_process_running(process_name):
        for proc in psutil.process_iter():
            try:
                if proc.name().lower() == process_name.lower():
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass


def check_process_count(process_name):  # 计算process运行数量
    count = 0
    for proc in psutil.process_iter():
        try:
            if proc.name().lower() == process_name.lower():
                count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return count


def GenerateSmallestID(numList):  # 根据顺次，在已有的数字list中，生成一个最小的数字
    # 先将list转换为set，方便进行查找
    nums_set = set(numList)

    # 从1开始逐个查找正整数
    smallest_missing_integer = 10001
    while smallest_missing_integer in nums_set:
        smallest_missing_integer += 1

    return smallest_missing_integer


def CheckIfStringStartsWithNotNum(string):  # 判断字符串的第一个字符是不是数字
    if len(string) != 0:
        if string[0:1] not in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]:
            return True
        else:
            return False
    else:
        return None


def CheckIfJsonIsValidSoundSheet(jsonPath):  # 检查info.json的基本格式是否正确
    if not os.path.exists(jsonPath):
        return False
    else:
        SoundListDictt = LoadJson(jsonPath, "gbk")
        if SoundListDictt.get("$ProjectStr$", {}) == {} or len(SoundListDictt.get("$ProjectStr$", {})) == 0:
            return False
        elif SoundListDictt.get("$ProjectGUID$", {}) == {} or len(SoundListDictt.get("$ProjectGUID$", {})) == 0:
            return False
        elif SoundListDictt.get("Data_SoundList", "") == "" or type(SoundListDictt.get("Data_SoundList", "")) is not dict:
            return False
        else:
            return True


def getWWUPathFromLocal(WWUrootPath):  # 获取指定路径下所有的wwu文件路径
    wwuPathCups = []
    for p in Path(WWUrootPath).rglob("*.wwu"):
        wwuPathCups.append(p)

    return wwuPathCups


def SafetyCheck_WwiseRunningStatus():
    if not is_process_running("Wwise.exe"):
        return False
    else:
        if check_process_count("Wwise.exe") > 1:
            return False
        else:
            return True


def SafetyCheck_WwiseRunningStatus_Detailed():
    if not is_process_running("Wwise.exe"):
        return 0
    else:
        if check_process_count("Wwise.exe") > 1:
            return 2
        else:
            return 1


def CreateBasicStructure_SoundListDict():
    SoundListDictt = {
        "$ProjectStr$": global_curWwiseProjName,
        "$ProjectGUID$": global_curWwiseProjID,
        "Data_SoundList": {}
    }
    return SoundListDictt


def find_xml_files(path):
    xml_files = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.xml'):
                xml_files.append(os.path.abspath(os.path.join(root, file)))
    return xml_files


def Get_EventPropertyTypeString_From_ActionValueStr(ValueStr):
    if ValueStr == "1":
        return "Play"
    elif ValueStr == "2":
        return "Stop"
    elif ValueStr == "3":
        return "Stop All"
    elif ValueStr == "4":
        return "Mute"
    elif ValueStr == "5":
        return "UnMute"
    elif ValueStr == "6":
        return "UnMute All"
    elif ValueStr == "7":
        return "Pause"
    elif ValueStr == "8":
        return "Pause All"
    elif ValueStr == "9":
        return "Resume"
    elif ValueStr == "10":
        return "Resume All"
    elif ValueStr == "11":
        return "Set Bus Volume"
    elif ValueStr == "12":
        return "Set Voice Volume"
    elif ValueStr == "13":
        return "Set Voice Pitch"
    elif ValueStr == "14":
        return "Reset Bus Volume"
    elif ValueStr == "15":
        return "Reset Bus Volume All"
    elif ValueStr == "16":
        return "Reset Voice Volume"
    elif ValueStr == "17":
        return "Reset Voice Volume All"
    elif ValueStr == "18":
        return "Reset Pitch"
    elif ValueStr == "19":
        return "Reset Pitch All"
    elif ValueStr == "20":
        return "Enable State"
    elif ValueStr == "21":
        return "Disable State"
    elif ValueStr == "22":
        return "Set State"
    elif ValueStr == "23":
        return "Set Switch"
    elif ValueStr == "24":
        return "Enable Bypass"
    elif ValueStr == "25":
        return "Disable Bypass"
    elif ValueStr == "26":
        return "Set LPF"
    elif ValueStr == "27":
        return "Reset LPF"
    elif ValueStr == "28":
        return "Reset LPF All"
    elif ValueStr == "29":
        return "Set HPF"
    elif ValueStr == "30":
        return "Reset HPF"
    elif ValueStr == "31":
        return "Reset HPF All"
    elif ValueStr == "32":
        return "Reset Bypass Effect"
    elif ValueStr == "33":
        return "Reset Bypass Effect All"
    elif ValueStr == "34":
        return "Break"
    elif ValueStr == "35":
        return "Trigger"
    elif ValueStr == "36":
        return "Seek"
    elif ValueStr == "37":
        return "Seek All"
    elif ValueStr == "38":
        return "Set Game Parameter"
    elif ValueStr == "39":
        return "Reset Game Parameter"
    elif ValueStr == "40":
        return "Release Envelope"
    elif ValueStr == "41":
        return "Post Event"
    elif ValueStr == "42":
        return "Reset Playlist"
    else:
        return None


def Get_PropertyType_From_PropertyName(PropertyName):
    if PropertyName == "3DPosition":
        return "Value"
    elif PropertyName == "3DSpatialization":
        return "Value"
    elif PropertyName == "AttachableMixerInput":
        return "Reference"
    elif PropertyName == "Attenuation":
        return "Reference"
    elif PropertyName == "BelowThresholdBehavior":
        return "Value"
    elif PropertyName == "BypassEffect":
        return "bool"
    elif PropertyName == "BypassEffect0":
        return "bool"
    elif PropertyName == "BypassEffect1":
        return "bool"
    elif PropertyName == "BypassEffect2":
        return "bool"
    elif PropertyName == "BypassEffect3":
        return "bool"
    elif PropertyName == "CenterPercentage":
        return "Value"
    elif PropertyName == "Color":
        return "Value"
    elif PropertyName == "Conversion":
        return "Reference"
    elif PropertyName == "Effect0":
        return "Reference"
    elif PropertyName == "Effect1":
        return "Reference"
    elif PropertyName == "Effect2":
        return "Reference"
    elif PropertyName == "Effect3":
        return "Reference"
    elif PropertyName == "EnableAttenuation":
        return "bool"
    elif PropertyName == "EnableDiffraction":
        return "bool"
    elif PropertyName == "EnableLoudnessNormalization":
        return "bool"
    elif PropertyName == "EnableMidiNoteTracking":
        return "bool"
    elif PropertyName == "GameAuxSendHPF":
        return "Value"
    elif PropertyName == "GameAuxSendLPF":
        return "Value"
    elif PropertyName == "GameAuxSendVolume":
        return "Value"
    elif PropertyName == "GlobalOrPerObject":
        return "Value"
    elif PropertyName == "HdrActiveRange":
        return "Value"
    elif PropertyName == "HdrEnableEnvelope":
        return "bool"
    elif PropertyName == "HdrEnvelopeSensitivity":
        return "Value"
    elif PropertyName == "Highpass":
        return "Value"
    elif PropertyName == "HoldEmitterPositionOrientation":
        return "bool"
    elif PropertyName == "HoldListenerOrientation":
        return "bool"
    elif PropertyName == "IgnoreParentMaxSoundInstance":
        return "bool"
    elif PropertyName == "Inclusion":
        return "bool"
    elif PropertyName == "InitialDelay":
        return "Value"
    elif PropertyName == "IsGlobalLimit":
        return "Value"
    elif PropertyName == "ListenerRelativeRouting":
        return "bool"
    elif PropertyName == "Lowpass":
        return "Value"
    elif PropertyName == "MakeUpGain":
        return "Value"
    elif PropertyName == "MaxReachedBehavior":
        return "Value"
    elif PropertyName == "MaxSoundPerInstance":
        return "Value"
    elif PropertyName == "MidiBreakOnNoteOff":
        return "bool"
    elif PropertyName == "MidiChannelFilter":
        return "Value"
    elif PropertyName == "MidiKeyFilterMax":
        return "Value"
    elif PropertyName == "MidiKeyFilterMin":
        return "Value"
    elif PropertyName == "MidiPlayOnNoteType":
        return "Value"
    elif PropertyName == "MidiTrackingRootNote":
        return "Value"
    elif PropertyName == "MidiTransposition":
        return "Value"
    elif PropertyName == "MidiVelocityFilterMax":
        return "Value"
    elif PropertyName == "MidiVelocityFilterMin":
        return "Value"
    elif PropertyName == "MidiVelocityOffset":
        return "Value"
    elif PropertyName == "NormalOrShuffle":
        return "Value"
    elif PropertyName == "OutputBus":
        return "Reference"
    elif PropertyName == "OutputBusHighpass":
        return "Value"
    elif PropertyName == "OutputBusLowpass":
        return "Value"
    elif PropertyName == "OutputBusVolume":
        return "Value"
    elif PropertyName == "OverLimitBehavior":
        return "Value"
    elif PropertyName == "OverrideAnalysis":
        return "bool"
    elif PropertyName == "OverrideAttachableMixerInput":
        return "bool"
    elif PropertyName == "OverrideColor":
        return "bool"
    elif PropertyName == "OverrideConversion":
        return "bool"
    elif PropertyName == "OverrideEarlyReflections":
        return "bool"
    elif PropertyName == "OverrideEffect":
        return "bool"
    elif PropertyName == "OverrideGameAuxSends":
        return "bool"
    elif PropertyName == "OverrideHdrEnvelope":
        return "bool"
    elif PropertyName == "OverrideMetadata":
        return "bool"
    elif PropertyName == "OverrideMidiEventsBehavior":
        return "bool"
    elif PropertyName == "OverrideMidiNoteTracking":
        return "bool"
    elif PropertyName == "OverrideOutput":
        return "bool"
    elif PropertyName == "OverridePositioning":
        return "bool"
    elif PropertyName == "OverridePriority":
        return "bool"
    elif PropertyName == "OverrideUserAuxSends":
        return "bool"
    elif PropertyName == "OverrideVirtualVoice":
        return "bool"
    elif PropertyName == "Pitch":
        return "Value"
    elif PropertyName == "PlayMechanismInfiniteOrNumberOfLoops":
        return "Value"
    elif PropertyName == "PlayMechanismLoop":
        return "bool"
    elif PropertyName == "PlayMechanismLoopCount":
        return "Value"
    elif PropertyName == "PlayMechanismResetPlaylistEachPlay":
        return "bool"
    elif PropertyName == "PlayMechanismSpecialTransitions":
        return "bool"
    elif PropertyName == "PlayMechanismSpecialTransitionsType":
        return "Value"
    elif PropertyName == "PlayMechanismSpecialTransitionsValue":
        return "Value"
    elif PropertyName == "PlayMechanismStepOrContinuous":
        return "Value"
    elif PropertyName == "Priority":
        return "Value"
    elif PropertyName == "PriorityDistanceFactor":
        return "bool"
    elif PropertyName == "PriorityDistanceOffset":
        return "Value"
    elif PropertyName == "RandomAvoidRepeating":
        return "bool"
    elif PropertyName == "RandomAvoidRepeatingCount":
        return "Value"
    elif PropertyName == "RandomOrSequence":
        return "Value"
    elif PropertyName == "ReflectionsAuxSend":
        return "Reference"
    elif PropertyName == "ReflectionsVolume":
        return "Value"
    elif PropertyName == "RenderEffect0":
        return "bool"
    elif PropertyName == "RenderEffect1":
        return "bool"
    elif PropertyName == "RenderEffect2":
        return "bool"
    elif PropertyName == "RenderEffect3":
        return "bool"
    elif PropertyName == "RestartBeginningOrBackward":
        return "Value"
    elif PropertyName == "SpeakerPanning":
        return "Value"
    elif PropertyName == "SpeakerPanning3DSpatializationMix":
        return "Value"
    elif PropertyName == "UseGameAuxSends":
        return "bool"
    elif PropertyName == "UseMaxSoundPerInstance":
        return "bool"
    elif PropertyName == "UserAuxSend0":
        return "Reference"
    elif PropertyName == "UserAuxSend1":
        return "Reference"
    elif PropertyName == "UserAuxSend2":
        return "Reference"
    elif PropertyName == "UserAuxSend3":
        return "Reference"
    elif PropertyName == "UserAuxSendHPF0":
        return "Value"
    elif PropertyName == "UserAuxSendHPF1":
        return "Value"
    elif PropertyName == "UserAuxSendHPF2":
        return "Value"
    elif PropertyName == "UserAuxSendHPF3":
        return "Value"
    elif PropertyName == "UserAuxSendLPF0":
        return "Value"
    elif PropertyName == "UserAuxSendLPF1":
        return "Value"
    elif PropertyName == "UserAuxSendLPF2":
        return "Value"
    elif PropertyName == "UserAuxSendLPF3":
        return "Value"
    elif PropertyName == "UserAuxSendVolume0":
        return "Value"
    elif PropertyName == "UserAuxSendVolume1":
        return "Value"
    elif PropertyName == "UserAuxSendVolume2":
        return "Value"
    elif PropertyName == "UserAuxSendVolume3":
        return "Value"
    elif PropertyName == "VirtualVoiceQueueBehavior":
        return "Value"
    elif PropertyName == "Volume":
        return "Value"
    elif PropertyName == "Weight":
        return "Value"
    elif PropertyName == "SwitchGroupOrStateGroup":
        return "Reference"
    else:
        return None


def Get_EventInfos_FromAllEventWWUs(EventWWUFolderPath):  # 全量分析Event（不延伸到wav）
    EventRootCups = {}
    for wwuPath in getWWUPathFromLocal(EventWWUFolderPath):
        tree = ET.parse(wwuPath)
        root = tree.getroot()

        for EventName in root.iter("Event"):
            name = EventName.attrib.get("Name")
            guid = EventName.attrib.get("ID")
            tempDict = {"ID": guid, "Notes": "", "Action": {}}
            EventRootCups[name] = tempDict
            for comment in EventName.iter("Comment"):
                EventRootCups[name]["Notes"] = comment.text
            for action in EventName.iter("Action"):
                guid_action_id = action.attrib.get("ID")
                tempDict_Action = {"PropertyValue": "1", "PropertyName": "Play", "ObjectRef": {"ID": "", "Name": ""}}
                EventRootCups[name]["Action"][guid_action_id] = tempDict_Action
                for Property in action.iter("Property"):
                    PropertyValue = Property.attrib.get("Value")
                    PropertyName = Get_EventPropertyTypeString_From_ActionValueStr(PropertyValue)
                    EventRootCups[name]["Action"][guid_action_id]["PropertyValue"] = PropertyValue
                    EventRootCups[name]["Action"][guid_action_id]["PropertyName"] = PropertyName
                for ObjectRef in action.iter("ObjectRef"):
                    ObjectRef_Name = ObjectRef.attrib.get("Name")
                    ObjectRef_ID = ObjectRef.attrib.get("ID")
                    tempDict_Action["ObjectRef"]["Name"] = ObjectRef_Name
                    tempDict_Action["ObjectRef"]["ID"] = ObjectRef_ID
                EventRootCups[name]["Action"][guid_action_id] = tempDict_Action

    return EventRootCups


def Get_AllWAVPath_From_EventName(EventStr, WwiseProjectFolderPath):  # 通过Event名获取相关WAV路径（相同ObjectRef合并，不关注Action层级）
    EventWWUFolderPath = os.path.join(WwiseProjectFolderPath, "Events")
    ActorWWUFolderPath = os.path.join(WwiseProjectFolderPath, global_actorString)

    # 遍历，定位EventName区域
    ObjectRefList = []
    for wwuPath in getWWUPathFromLocal(EventWWUFolderPath):
        tree = ET.parse(wwuPath)
        root = tree.getroot()

        for EventName in root.iter("Event"):
            name = EventName.attrib.get("Name")
            if EventStr == name:
                for ObjectRef in EventName.iter("ObjectRef"):  # 在区域内，遍历每一个ObjectRef的GUID
                    ObjectRef_Name = ObjectRef.attrib.get("Name")
                    ObjectRef_ID = ObjectRef.attrib.get("ID")
                    ObjectRefList.append({"Name": ObjectRef_Name, "ID": ObjectRef_ID})

    # for循环。在ActorWWU路径中，定位每一个ObjectRef的GUID，获取类型，如果是容器类的类型，在该范围内，遍历所有的WAV路径
    ObjectRefWAVPairDict = {}
    for item in ObjectRefList:
        wavPathList = []

        for wwuPath in getWWUPathFromLocal(ActorWWUFolderPath):
            tree = ET.parse(wwuPath)
            root = tree.getroot()

            for elem in root.iter():
                if "ID" in elem.attrib and "Name" in elem.attrib:
                    if elem.attrib.get("Name") == item["Name"] and elem.attrib.get("ID") == item["ID"]:
                        for obj in elem.iter("AudioFileSource"):
                            for lann in obj.iter("Language"):
                                WavType = lann.text
                                if WavType != "SFX":
                                    WavType = "Voices\\" + WavType
                                for wavPath in obj.iter("AudioFile"):  # 路径拼接成完整的绝对路径
                                    WavPath = WwiseProjectFolderPath + "\\Originals\\" + WavType + "\\" + wavPath.text
                                    wavPathList.append(WavPath)
                        # 除重（switch复用）
                        wavPathList = sorted(list(set(wavPathList)))
                        ObjectRefWAVPairDict[item["ID"]] = {"Name": item["Name"], "Type": elem.tag, "wavPath": wavPathList}

    # 建立最终Dict
    FinalDict = {EventStr: ObjectRefWAVPairDict}

    return FinalDict


def Get_AllWAVPath_From_EventName_InActionLayer(EventStr, WwiseProjectFolderPath):  # 通过Event名获取相关WAV路径（关注Action层级，保留可能平级复用的相同ObjectRef）
    EventWWUFolderPath = os.path.join(WwiseProjectFolderPath, "Events")
    ActorWWUFolderPath = os.path.join(WwiseProjectFolderPath, global_actorString)

    EventRootCups = {}
    for wwuPath in getWWUPathFromLocal(EventWWUFolderPath):
        tree = ET.parse(wwuPath)
        root = tree.getroot()

        for EventName in root.iter("Event"):
            name = EventName.attrib.get("Name")
            if name == EventStr:
                guid = EventName.attrib.get("ID")
                tempDict = {"ID": guid, "Notes": "", "Action": {}}
                EventRootCups[name] = tempDict
                for comment in EventName.iter("Comment"):
                    EventRootCups[name]["Notes"] = comment.text
                for action in EventName.iter("Action"):
                    guid_action_id = action.attrib.get("ID")
                    tempDict_Action = {"PropertyValue": "1", "PropertyName": "Play", "ObjectRef": {"ID": "", "Name": "", "Type": "", "wavPath": []}}
                    EventRootCups[name]["Action"][guid_action_id] = tempDict_Action
                    for Property in action.iter("Property"):
                        if Property.attrib.get("Name") == "ActionType":
                            PropertyValue = Property.attrib.get("Value")
                            PropertyName = Get_EventPropertyTypeString_From_ActionValueStr(PropertyValue)
                            EventRootCups[name]["Action"][guid_action_id]["PropertyValue"] = PropertyValue
                            EventRootCups[name]["Action"][guid_action_id]["PropertyName"] = PropertyName
                    for ObjectRef in action.iter("ObjectRef"):
                        ObjectRef_Name = ObjectRef.attrib.get("Name")
                        ObjectRef_ID = ObjectRef.attrib.get("ID")
                        tempDict_Action["ObjectRef"]["Name"] = ObjectRef_Name
                        tempDict_Action["ObjectRef"]["ID"] = ObjectRef_ID
                        # 从这里遍历ActorWWU
                        wavPathList = []

                        for wwuPaths in getWWUPathFromLocal(ActorWWUFolderPath):
                            tree = ET.parse(wwuPaths)
                            root = tree.getroot()

                            for elem in root.iter():
                                if "ID" in elem.attrib and "Name" in elem.attrib:
                                    if elem.attrib.get("Name") == ObjectRef_Name and elem.attrib.get("ID") == ObjectRef_ID:
                                        for obj in elem.iter("AudioFileSource"):
                                            for lann in obj.iter("Language"):
                                                WavType = lann.text
                                                if WavType != "SFX":
                                                    WavType = "Voices\\" + WavType
                                                for wavPath in obj.iter("AudioFile"):  # 路径拼接成完整的绝对路径
                                                    WavPath = WwiseProjectFolderPath + "\\Originals\\" + WavType + "\\" + wavPath.text
                                                    wavPathList.append(WavPath)
                                        tempDict_Action["ObjectRef"]["Type"] = elem.tag
                        # 除重（switch复用）
                        wavPathList = sorted(list(set(wavPathList)))
                        tempDict_Action["ObjectRef"]["wavPath"] = wavPathList

                    EventRootCups[name]["Action"][guid_action_id] = tempDict_Action

    return EventRootCups


def Get_AllWAVPath_From_EventName_FlatWAVPath(EventStr, WwiseProjectFolderPath):
    result = Get_AllWAVPath_From_EventName(EventStr, WwiseProjectFolderPath)
    wavPathList = []
    dictInfo = result[EventStr]
    for keyy, value in zip(dictInfo.keys(), dictInfo.values()):
        wavList = value["wavPath"]
        if len(wavList) != 0:
            wavPathList += wavList

    # 集中
    wavFolderPath = []
    for path in wavPathList:
        wavFolderPath.append(path)

    return wavFolderPath


def Get_WavFolderPath_From_EventName(EventStr, WwiseProjectFolderPath):  # 通过Event名获取相关WAV路径所在的文件夹
    result = Get_AllWAVPath_From_EventName(EventStr, WwiseProjectFolderPath)  # 通过Event名获取相关WAV路径（相同ObjectRef合并，不关注Action层级）
    wavPathList = []
    dictInfo = result[EventStr]
    for keyy, value in zip(dictInfo.keys(), dictInfo.values()):
        wavList = value["wavPath"]
        if len(wavList) != 0:
            wavPathList += wavList

    # 除重
    wavFolderPath = []
    for path in wavPathList:
        wavFolderPath.append(os.path.dirname(path))
    wavFolderPath = list(set(wavFolderPath))

    return wavFolderPath


def DecorateSoundID(SoundID):
    NewSoundID = "#" + str(SoundID) + "#"
    return NewSoundID


def IfStringContainsSoundID(string):
    if str(string)[0:1] == "#" and str(string)[-1:] == "#" and len(str(string)[1:-1]) != 0:
        return True
    else:
        return False


def Get_SoundID_FromNotes(noteStr):
    noteStr = str(noteStr)
    tempList = []
    # 先判断是否有;
    if ";" in noteStr:
        groups = noteStr.split(";") if ";" in noteStr else noteStr.split(";")
        tempList = groups
    else:
        tempList = [noteStr]

    finalList = []
    if len(tempList) != 0:
        for item in tempList:
            # 再判断是否有,
            if "," in item or "，" in item:
                # 使用split()方法分割字符串
                segments = item.split(",") if "," in item else item.split("，")
                # 打印第一段
                strID = segments[0]
                if IfStringContainsSoundID(strID) is True:
                    cleanID = strID[1:-1]
                    finalList.append([cleanID, segments[1]])
                else:
                    finalList.append(["", segments[1]])
            else:
                strIDe = item
                if IfStringContainsSoundID(strIDe) is True:
                    cleanID = strIDe[1:-1]
                    finalList.append([cleanID, strIDe])
                else:
                    finalList.append(["", strIDe])
    # LOG.info(str(finalList))
    return finalList

def open_file_folder_highlight(file_path):  # 使用explorer命令打开文件夹并高亮文件
    folder_path = os.path.dirname(file_path)
    if os.path.exists(folder_path):  # 检查文件夹路径是否存在
        subprocess.Popen(['explorer', '/select,', file_path])


def openFile(filePath):
    tempStr = "start /B "
    os.system(tempStr + filePath)


def ColorConvert_Hex_to_ARGB(hexValue):
    if type(hexValue) is not str:
        return "ffffffff"
    else:
        if len(hexValue) != 7:
            return "ffffffff"
        else:
            head = hexValue[0:1]
            tail = hexValue[1:]
            if head != "#":
                return "ffffffff"
            else:
                ARGBValue = "ff" + tail
                return ARGBValue


def SafetyCheck_IfCharInStringAreAllNum(tarStr):
    tarStr = str(tarStr)
    count = 0
    for char in tarStr:
        if char not in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            count += 1

    if count == 0:
        return True
    else:
        return False


def getBNKXMLPathFromLocal(BNKXMLPath):
    BNKXMLCups = []
    AllXMLPathList = find_xml_files(BNKXMLPath)
    for p in AllXMLPathList:
        eList = ["Init.xml", "PluginInfo.xml", "SoundbanksInfo.xml"]
        if os.path.basename(p) not in eList:
            BNKXMLCups.append(p)

    return BNKXMLCups


def LocateEventBankLocation(EventStr, GeneratedSoundBanksPath):
    BankLocation = []
    for BNKXMLPath in getBNKXMLPathFromLocal(GeneratedSoundBanksPath):
        tree = ET.parse(BNKXMLPath)
        root = tree.getroot()
        for line in root.iter("Event"):
            name = line.attrib.get("Name")
            if EventStr == name:
                BankLocation.append(os.path.basename(BNKXMLPath)[:-4])

    BankLocation = list(set(BankLocation))
    return BankLocation


def find_targetType_files(path, fileType):
    fileList = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.' + fileType):
                fileList.append(os.path.abspath(os.path.join(root, file)))
    return fileList


def GetWAVMAXdBFS(WAVpath):
    obj = AudioSegment.from_file(WAVpath)
    MAXdBFS = str(obj.max_dBFS)
    # LOG.debug(MAXdBFS)
    return MAXdBFS


def FilterUniqueStrFromList(listName):
    listOri = listName
    Bad = []
    Good = []

    for i in listOri:
        ref = list(listOri)
        ref.remove(i)
        for j in ref:
            if i in j:
                Bad.append(i)

    for x in listOri:
        if x not in Bad:
            Good.append(x)

    return Good


# 全局唯一标识
unique_id = 1


# 遍历所有的节点
def walkData(root_node, level, result_list):  # 转载于https://blog.csdn.net/yiluochenwu/article/details/23515923  本内容依据“CC BY-SA 4.0”许可证进行授权。要查看该许可证，可访问https://creativecommons.org/licenses/by-sa/4.0/
    global unique_id
    temp_list = [unique_id, level, root_node.tag, root_node.attrib]
    result_list.append(temp_list)
    unique_id += 1

    # 遍历每个子节点
    children_node = list(root_node)
    if len(children_node) == 0:
        return
    for child in children_node:
        walkData(child, level + 1, result_list)
    return


def getXmlData(file_name):  # 转载于https://blog.csdn.net/yiluochenwu/article/details/23515923  本内容依据“CC BY-SA 4.0”许可证进行授权。要查看该许可证，可访问https://creativecommons.org/licenses/by-sa/4.0/
    level = 0  # 节点的深度从0开始
    result_list = []
    root = ET.parse(file_name).getroot()
    walkData(root, level, result_list)

    return result_list


def GetGUIDInfoPoolFromWWU(WWUPath):
    ContainerGUIDPool = {}

    # 设定深度位置检测范围
    checkNum = [6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40]
    R = getXmlData(WWUPath)
    for x in R:
        for n in checkNum:
            # 同时符合以下条件的ObjectRef路径，被全量筛选出来。以 {GUID:容器类型} 字典，通过ContainerGUIDPool传出
            if x[1] == n and len(x[3]) == 3 and list(x[3])[2] == "ShortID" and len(list(x[3].values())[0]) != 0:
                ContainerGUIDPool[list(x[3].values())[1]] = (x[2])
                # LOG.debug(x)
                # LOG.debug((x[2]))
                # LOG.debug(list(x[3].values())[1])

    return ContainerGUIDPool


def ADVCopy(sourcePath, sourceFileName, targetPath, targetFileName):
    sourceFullPathName = os.path.join(sourcePath, sourceFileName)
    targetFullPathName = os.path.join(targetPath, targetFileName)

    ADVErrorLog = []

    if not os.path.exists(sourceFullPathName):
        ADVErrorLog.append(
            lan["LOG_SC_HeadTip_Error"][L] + sourceFullPathName + lan["LOG_SC_def_PathsCheckPrintFunc"][L])
        LOG.warning(lan["LOG_SC_HeadTip_Error"][L] + sourceFullPathName + lan["LOG_SC_def_PathsCheckPrintFunc"][L])
    elif not os.path.exists(targetPath):
        ADVErrorLog.append(lan["LOG_SC_HeadTip_Error"][L] + targetPath + lan["LOG_SC_def_PathsCheckPrintFunc"][L])
        LOG.warning(lan["LOG_SC_HeadTip_Error"][L] + targetPath + lan["LOG_SC_def_PathsCheckPrintFunc"][L])
    elif os.path.exists(targetFullPathName):
        LOG.warning(lan["LOG_JKV_HeadTip_Hello"][L] + targetFullPathName + lan["LOG_JKV_AlreadyExist"][L])
    else:
        shutil.copy(sourceFullPathName, targetFullPathName)
        LOG.info(lan["LOG_WG_HeadTip_DONE"][L] + targetFullPathName + lan["LOG_JKV_WAVCreated"][L])

    return ADVErrorLog


def ADVQuickCopy(sourceFullPathName, targetPath, targetFileName):
    targetFullPathName = os.path.join(targetPath, targetFileName)

    ADVErrorLog = []

    if not os.path.exists(sourceFullPathName):
        ADVErrorLog.append(lan["LOG_SC_HeadTip_Error"][L] + sourceFullPathName + lan["LOG_SC_def_PathsCheckPrintFunc"][L])
        LOG.warning(lan["LOG_SC_HeadTip_Error"][L] + sourceFullPathName + lan["LOG_SC_def_PathsCheckPrintFunc"][L])
    elif not os.path.exists(targetPath):
        ADVErrorLog.append(lan["LOG_SC_HeadTip_Error"][L] + targetPath + lan["LOG_SC_def_PathsCheckPrintFunc"][L])
        LOG.warning(lan["LOG_SC_HeadTip_Error"][L] + targetPath + lan["LOG_SC_def_PathsCheckPrintFunc"][L])
    elif os.path.exists(targetFullPathName):
        LOG.warning(lan["LOG_JKV_HeadTip_Hello"][L] + targetFullPathName + lan["LOG_JKV_AlreadyExist"][L])
    else:
        shutil.copy(sourceFullPathName, targetFullPathName)
        LOG.info(lan["LOG_WG_HeadTip_DONE"][L] + targetFullPathName + lan["LOG_JKV_WAVCreated"][L])

    return ADVErrorLog


def getBankNameByEventInfo(EventName, EventID):
    BankNameList = []
    for wwuPath in getWWUPathFromLocal(global_curWwisePath + "\\SoundBanks"):
        tree = ET.parse(wwuPath)
        root = tree.getroot()

        for BankName in root.iter("SoundBank"):
            for obj in root.iter("ObjectRef"):
                if obj.attrib.get("Name") == EventName and obj.attrib.get("ID") == EventID:
                    BankName = BankName.attrib.get("Name")
                    BankNameList.append(BankName)

    return BankNameList


def list_top_level_folders_with_paths(path):
    folders_with_paths = []
    for folder in os.listdir(path):
        folder_path = os.path.join(path, folder)
        if os.path.isdir(folder_path):
            folders_with_paths.append({"folderName": folder, "folderPath": folder_path})
    return folders_with_paths


def wavGenForExpandSwitchFunc(PathWavPair, fName):
    Path_File_PlaceholderWAV = global_wavSilencePath
    Path_Folder_TargetWAV = os.path.join(global_curWwisePath, KeyInfoDict["Data_KeyInfo"][fName]["Path_Folder_TargetWAV"])

    wavGenError = []
    # 拉平wav数据
    flatWavPool = []
    if len(PathWavPair) != 0:
        for i in PathWavPair:
            flatWavPool.append(i.values())

    if len(flatWavPool) != 0:
        flatPathWavPair = [xx for xx in flatten(flatWavPool)]

        # 合并同类项
        flatPathWavPair = list(set(flatPathWavPair))

        # 在本地产生WAV
        for i in flatPathWavPair:
            i = i + ".wav"

            ADVErrorLog = ADVQuickCopy(Path_File_PlaceholderWAV, Path_Folder_TargetWAV, i)
            if len(ADVErrorLog) != 0:
                wavGenError.append(ADVErrorLog)

    return wavGenError


def KeyExistCheck(Str, Dict):
    if Str not in Dict:
        log = lan["LOG_SC_def_KeyExistCheck_HeadTip"][L] + str(Str) + lan["LOG_SC_def_KeyExistCheck"][L]
        return log
    else:
        return None


def PathsCheckPrintFunc(ObjPath):
    path = str(ObjPath)
    exist_path = os.path.exists(path)
    if exist_path is False:
        LOG.warning(lan["LOG_SC_HeadTip_Error"][L] + path + lan["LOG_SC_def_PathsCheckPrintFunc"][L])
        return False


def NewfNameSafetyCheck():
    newObjFound = []
    # LOG.debug(fName)
    # for i in list(KeyInfoDict["Data_KeyInfo"].keys()):
    #     if i not in KeyInfoDict["Data_KeyInfo"]:
    #         newObjFound.append(i)
    # LOG.debug(newObjFound)
    return newObjFound


def compareLists(listA, listB):
    differ = set(listA).difference(set(listB))
    return differ


def getAllSwitchGroupNamesFromSwitchWWU():
    SwitchNameList = []
    for wwuPath in getWWUPathFromLocal(global_curWwisePath + "\\Switches"):
        tree = ET.parse(wwuPath)
        root = tree.getroot()

        for SwitchGroupName in root.iter("SwitchGroup"):
            SwitchNameList.append(SwitchGroupName.attrib.get("Name"))

    return SwitchNameList


def getAllStateGroupNamesFromStateWWU():
    StateGroupNameList = []
    for wwuPath in getWWUPathFromLocal(global_curWwisePath + "\\States"):
        tree = ET.parse(wwuPath)
        root = tree.getroot()

        for StateGroupName in root.iter("StateGroup"):
            StateGroupNameList.append(StateGroupName.attrib.get("Name"))

    return StateGroupNameList


def getAllRTPCNamesFromRTPCWWU():
    RTPCNameList = []
    for wwuPath in getWWUPathFromLocal(global_curWwisePath + "\\Game Parameters"):
        tree = ET.parse(wwuPath)
        root = tree.getroot()

        for RTPCName in root.iter("GameParameter"):
            RTPCNameList.append(RTPCName.attrib.get("Name"))

    return RTPCNameList


def getSchemaVersionFromBusWWU():
    SchemaVersion = ""
    tree = ET.parse(global_curWwisePath + "\\SoundBanks\\Default Work Unit.wwu")
    root = tree.getroot()

    for item in root.iter("WwiseDocument"):
        if len(item.attrib.get("SchemaVersion")) != 0:
            SchemaVersion = item.attrib.get("SchemaVersion")

    return SchemaVersion


def ifWwiseVersionIsHigherThan2022():
    SchemaVersionStr = getSchemaVersionFromBusWWU()
    if len(SchemaVersionStr) == 0:
        return False
    else:
        if int(SchemaVersionStr) >= 110:
            return True
        else:
            return False


def getAllRTPCObjectRefNamesFromBUSWWU():
    AllRTPCObjectRefNames = []
    for wwuPath in getWWUPathFromLocal(global_curWwisePath + "\\" + global_busString):
        tree = ET.parse(wwuPath)
        root = tree.getroot()

        for RTPCObjectRefName in root.iter("ObjectRef"):
            AllRTPCObjectRefNames.append(RTPCObjectRefName.attrib.get("Name"))

    return AllRTPCObjectRefNames


def getAllAttenuationNamesFromAttenuationWWU():
    AttenuationNameList = []
    for wwuPath in getWWUPathFromLocal(global_curWwisePath + "\\Attenuations"):
        tree = ET.parse(wwuPath)
        root = tree.getroot()

        for AttenuationName in root.iter("Attenuation"):
            AttenuationNameList.append(AttenuationName.attrib.get("Name"))

    return AttenuationNameList


def compareDicts(dictA, dictB):
    differ = set(dictA.items()) - set(dictB.items())
    return differ


def SafetyCheckForGUI():
    try:
        findOutUnlinkedAudio()
        findOutLonelyActor()
        findUnusedEventGUI()
        findGhostEventGUI()
        FormatRuleCheck()
    except:
        traceback.print_exc()


def findOutUnlinkedAudio():
    obj = compareLists(getWAVPathFromAudioWWU(), getWAVPathFromLocal())
    for i in obj:
        SafetyCheckLog.append(lan["LOG_SC_def_findOutUnlinkedAudio"][L] + str(i))
        LOG.info(lan["LOG_SC_def_findOutUnlinkedAudio"][L] + str(i))
        time.sleep(0.01)


def findOutUnusedWAV():
    obj = compareLists(getWAVPathFromLocal(), getWAVPathFromAudioWWU())
    for i in obj:
        if i.find("Z_Temp") == -1:
            SafetyCheckLog.append(lan["LOG_SC_def_findOutUnusedWAV"][L] + str(i))
            LOG.info(lan["LOG_SC_def_findOutUnusedWAV"][L] + str(i))
            time.sleep(0.01)


def findOutLonelyActor():
    LA = compareDicts(getAudioContainersFromAudioWWU(), getObjectRefFromEventWWU())

    LA = dict(LA)
    for k in KeyInfoDict["Init_Template"]:
        LA.pop(k, None)

    for i, j in zip(LA.keys(), LA.values()):
        SafetyCheckLog.append(lan["LOG_SC_def_findOutLonelyActor"][L] + " " + str(i) + ": " + str(j))
        LOG.info(lan["LOG_SC_def_findOutLonelyActor"][L] + " " + str(i) + ": " + str(j))
        # ColorGUIDPool.append(j)
        time.sleep(0.01)


def findUnusedEventGUI():
    EventListWWU = []
    for keys in getEventNameFromEventWWU().items():
        EventListWWU.append(keys[0])

    obj = compareLists(EventListWWU, getEventsFromJson())
    # LOG.debug(obj)

    if len(obj) != 0:
        for i in obj:
            tempDict = {i: getEventNameFromEventWWU()[i]}
            SafetyCheckLog.append(lan["LOG_SC_def_findUnusedEvent"][L] + str(tempDict))
            LOG.info(lan["LOG_SC_def_findUnusedEvent"][L] + str(tempDict))
            # ColorGUIDPool.append(str(getEventNameFromEventWWU()[i]))
            time.sleep(0.01)


def findGhostEventGUI():
    EventListWWU = []
    for keys in getEventNameFromEventWWU().items():
        EventListWWU.append(keys[0])

    obj = compareLists(getEventsFromJson(), EventListWWU)
    for i in obj:
        SafetyCheckLog.append(lan["LOG_SC_def_findGhostEvent"][L] + str(i))
        LOG.info(lan["LOG_SC_def_findGhostEvent"][L] + str(i))
        time.sleep(0.01)
        # LOG.debug(i)


def FormatRuleCheck():
    InvalidGUIDPool = []

    # 遍历所有的EventWWU，检查是否有不符合格式规则的Event
    invalidEventGUIDPool = []
    allObjectRefGUIDPool = []
    for wwuPath in getWWUPathFromLocal(global_curWwisePath + "\\Events\\"):
        R = getXmlData(wwuPath)
        for x in R:
            if x[2] == "Event" and x[1] != 4:
                # LOG.warning(lan["LOG_SC_def_Warning"][L] + x[3]["Name"] + ": " + x[3]["ID"] + lan["LOG_SC_def_Warning_OutOfEventStructureRule"][L])
                LOG.info(lan["LOG_SC_def_Warning"][L] + x[3]["Name"] + ": " + x[3]["ID"] + lan["LOG_SC_def_Warning_OutOfEventStructureRule"][L])
                time.sleep(0.01)
                invalidEventGUIDPool.append(x[3]["ID"])

            # 获取所有ObjectRef的GUIDList，为后续筛选做准备
            if x[2] == "ObjectRef":
                allObjectRefGUIDPool.append(x[3]["ID"])

    # 如果发现不符合格式规则的Event，把相关的Event放到总池子里，占位[0]
    if len(invalidEventGUIDPool) != 0:
        InvalidGUIDPool.append(invalidEventGUIDPool)

    # 遍历所有的AudioWWU，检查是否有不符合格式规则的Event
    invalidObjectRefGUIDPool = []
    for wwuPath in getWWUPathFromLocal(global_curWwisePath + "\\" + global_actorString + "\\"):
        R = getXmlData(wwuPath)
        for x in R:
            if x[1] != 6 and len(x[3]) == 3 and list(x[3])[2] == "ShortID" and len(list(x[3].values())[0]) != 0 and x[3]["ID"] in allObjectRefGUIDPool:
                # LOG.warning(lan["LOG_SC_def_Warning"][L] + x[3]["Name"] + ": " + x[3]["ID"] + lan["LOG_SC_def_Warning_OutOfObjectRefStructureRule"][L])
                LOG.info(lan["LOG_SC_def_Warning"][L] + x[3]["Name"] + ": " + x[3]["ID"] + lan["LOG_SC_def_Warning_OutOfObjectRefStructureRule"][L])
                time.sleep(0.01)
                invalidObjectRefGUIDPool.append(x[3]["ID"])

    # 如果发现不符合格式规则的ObjectRef，把相关的ObjectRef放到总池子里，占位[1]
    if len(invalidObjectRefGUIDPool) != 0:
        InvalidGUIDPool.append(invalidObjectRefGUIDPool)

    # 展开InvalidGUIDPool
    flatInvalidGUIDPool = [x for x in flatten(InvalidGUIDPool)]

    return flatInvalidGUIDPool


def getWAVPathFromAudioWWU():
    WAVPathCups = []
    for wwuPath in getWWUPathFromLocal(global_curWwisePath + "\\" + global_actorString + "\\"):
        tree = ET.parse(wwuPath)
        root = tree.getroot()

        for AFS in root.iter("AudioFileSource"):
            a = AFS.find("Language").text
            b = AFS.find("AudioFile").text
            if a == "SFX":
                WAVPathCups.append(b)
            elif a != "SFX" and b is not None:
                b = a + "\\" + b
                WAVPathCups.append(b)

    for wwuPath in getWWUPathFromLocal(global_curWwisePath + "\\Interactive Music Hierarchy\\"):
        tree = ET.parse(wwuPath)
        root = tree.getroot()

        for AFS in root.iter("AudioFileSource"):
            a = AFS.find("Language").text
            b = AFS.find("AudioFile").text
            if a == "SFX":
                WAVPathCups.append(b)
            elif a != "SFX" and b is not None:
                b = a + "\\" + b
                WAVPathCups.append(b)

    WAVPathCups = set(WAVPathCups)
    return WAVPathCups


def getWAVPathFromLocal():
    wavPathCups = []

    for p in Path(global_curWwisePath + "\\Originals\\").iterdir():
        for s in p.rglob("*.wav"):
            s = str(s)
            s = s.replace(global_curWwisePath + "\\Originals\\SFX\\", "")
            s = s.replace(global_curWwisePath + "\\Originals\\Voices\\", "")
            wavPathCups.append(s)

    wavPathCups = set(wavPathCups)
    return wavPathCups


def getAudioContainersFromAudioWWU():
    AudioRootCups = {}

    for wwuPath in getWWUPathFromLocal(global_curWwisePath + "\\Interactive Music Hierarchy\\"):
        tree = ET.parse(wwuPath)
        root = tree.getroot()

        for a in root:
            for b in a:
                for c in b:
                    for d in c:
                        for e in d:
                            for f in e:
                                if f.attrib.get("ID") is not None:
                                    AudioRootCups[f.attrib.get("Name")] = f.attrib.get("ID")

    for wwuPath in getWWUPathFromLocal(global_curWwisePath + "\\Interactive Music Hierarchy\\"):
        tree = ET.parse(wwuPath)
        root = tree.getroot()

        for a in root:
            for b in a:
                for c in b:
                    for d in c:
                        if d.attrib.get("ID") is not None:
                            AudioRootCups[d.attrib.get("Name")] = d.attrib.get("ID")

    return AudioRootCups


def getObjectRefFromEventWWU():
    ObjectRefCups = {}
    for wwuPath in getWWUPathFromLocal(global_curWwisePath + "\\Events\\"):

        tree = ET.parse(wwuPath)
        root = tree.getroot()

        for ObjectRef in root.iter("ObjectRef"):
            ObjectRefCups[ObjectRef.attrib.get("Name")] = ObjectRef.attrib.get("ID")

    return ObjectRefCups


def getEventNameFromEventWWU():
    EventRootCups = {}
    for wwuPath in getWWUPathFromLocal(global_curWwisePath + "\\Events\\"):
        tree = ET.parse(wwuPath)
        root = tree.getroot()

        for EventName in root.iter("Event"):
            EventRootCups[EventName.attrib.get("Name")] = EventName.attrib.get("ID")

    return EventRootCups


def getEventsFromJson():
    EventListJson = []
    NameJsonObj = SoundListDict["Data_SoundList"]
    for i in NameJsonObj:
        if len(NameJsonObj[i]["EventName"]["text"]) != 0:
            text = NameJsonObj[i]["EventName"]["text"]
            EventListJson.append(text)

    EventListJson = set(EventListJson)
    # EventListJson = list(EventListJson)
    # LOG.debug(EventListJson)
    return EventListJson


def printDict(dictInfo):
    LOG.debug(json.dumps(dictInfo, ensure_ascii=False, indent=4))


def printList(listInfo):
    for eachItem in listInfo:
        LOG.debug(eachItem)


def get_paths(nested_dict, prefix=""):
    paths = []
    for keyy, value in nested_dict.items():
        current_path = prefix + "\\" + str(keyy) if prefix else str(keyy)
        paths.append(current_path)  # 添加当前路径到paths列表
        if isinstance(value, dict):
            paths.extend(get_paths(value, current_path))
    return paths


def Get_WwiseBus_From_Json(busDict):
    finalPathList = []
    resultList = get_paths(busDict)
    if len(resultList) != 0:
        for i in resultList:
            finalPathList.append("\\" + global_busString + "\\Default Work Unit\\" + i)
    return finalPathList


def QuickTest_HideFile(filePath):
    if os.path.exists(filePath):
        hide_file(filePath)


def check_string(input_string):
    pattern = r'^[a-zA-Z0-9_]+$'
    if re.match(pattern, input_string):
        return True
    elif len(input_string) == 0:
        return True
    else:
        return False


def is_convertible_to_number(string):
    try:
        int(string)
        return True
    except ValueError:
        try:
            float(string)
            return True
        except ValueError:
            return False


def is_instance_exist(cls):
    for obj in gc.get_objects():
        if isinstance(obj, cls):
            return True
    return False


def hide_file(file_path):
    # 设置文件属性为隐藏
    ctypes.windll.kernel32.SetFileAttributesW(file_path, 2)


def ConnectStr(InputList):
    sss = ""
    for strrrrr in InputList:
        sss = sss + ";" + strrrrr
    sss = sss[1:]
    return sss


def sort_dict_by_integer_keys(input_dict):
    # 将所有的键转换为整数,并按照数值大小排序
    sorted_keys = sorted(input_dict.keys(), key=int)

    # 创建一个新的字典,使用排序后的键的字符串表示作为新的键
    sorted_dictt = {str(keey): input_dict[keey] for keey in sorted_keys}

    return sorted_dictt


def process_object_ref_path(object_ref_path):
    result = []
    current_path = []

    for i, item in enumerate(object_ref_path):
        current_path.append(item)

        if item[0] == "ChildrenList":
            if i + 1 < len(object_ref_path):  # 确保有下一个元素
                new_path = current_path.copy()
                new_path.append(object_ref_path[i + 1])
                result.append(new_path)

    return result


def find_value_and_path(wwuPaths, target_type, target_value):
    tree = ET.parse(wwuPaths)
    root = tree.getroot()
    result = []
    listXX = []

    def dfs(element, path):
        nonlocal result, listXX

        # 检查当前元素的值是否为目标值
        if target_type in ["Name", "ID", "Type", "ShortID", "WorkUnitID", "Value"]:
            if element.attrib.get(target_type) == target_value:
                result = [element.tag, element.attrib.get('Name', '')]
                listXX = path + [result]
                return True

        # 递归遍历子元素
        for child in element:
            current_path = path + [[element.tag, element.attrib.get('Name', '')]]
            if dfs(child, current_path):
                return True

        return False

    dfs(root, [])
    return listXX


def find_element(element, listX, level=0):
    if level < len(listX):
        if listX[level][0] == element.tag and listX[level][1] == element.attrib.get("Name", "@#$"):
            global_RootLayerList.append(element)
        for child in element:
            find_element(child, listX, level + 1)


def merge_children(children):
    result = []
    stack = []

    for child in children:
        while stack and not child['path'].startswith(stack[-1]['path']):
            stack.pop()

        if stack:
            if 'Children' not in stack[-1]:
                stack[-1]['Children'] = []
            stack[-1]['Children'].append(child)
        else:
            result.append(child)

        stack.append(child)

    return result


def find_duplicates(input_list):
    # 使用字典来统计每个元素出现的次数
    count_dict = {}
    for item in input_list:
        if item in count_dict:
            count_dict[item] += 1
        else:
            count_dict[item] = 1

    # 创建一个新列表来存储重复的元素
    duplicates = [item for item, count in count_dict.items() if count > 1]

    return duplicates


def merge_identical_dicts(dict_list):
    # 创建一个空集合来存储唯一的字典
    unique_dicts = set()

    # 遍历原始列表中的每个字典
    for d in dict_list:
        # 将字典转换为JSON字符串
        dict_as_string = json.dumps(d, sort_keys=True)

        # 将JSON字符串添加到唯一集合中
        unique_dicts.add(dict_as_string)

    # 将唯一的JSON字符串转换回字典
    result = [json.loads(s) for s in unique_dicts]

    return result
