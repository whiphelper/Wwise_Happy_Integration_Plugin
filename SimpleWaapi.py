import os
from Logs import *
from globals import *
import psutil
from waapi import *
from xml.etree import ElementTree as ET
from BasicTools import *


class SimpleWaapi:
    def __init__(self):
        if check_process_count("Wwise.exe") == 1:
            self.GO = WaapiClient()
            # LOG.debug("[***]")
        else:
            self.GO = None
            LOG.debug("[SimpleWaapi - Init - FAILED]")

    def get_SelectedObjectsGUIDList(self):
        if self.GO is not None:
            args = {}
            Results = self.GO.call("ak.wwise.ui.getSelectedObjects", args)
            GUIDList = []
            for i in Results["objects"]:
                GUIDList.append(i["id"])
            return GUIDList

    def get_BasicInfoDict_From_GUID(self, GUID):
        args = {
            "from": {
                "id": [GUID]
            },
            "options": {
                "return": ["type", "path", "name", "filePath", "parent", "childrenCount"]
            }
        }
        Results = self.GO.call("ak.wwise.core.object.get", args)
        try:
            return Results["return"][0]
        except:
            return None

    def get_BasicInfoDictList_From_GUIDList(self, GUIDList):
        InfoList = []
        for GUID in GUIDList:
            Results = self.get_BasicInfoDict_From_GUID(GUID)
            InfoList.append(Results)

        return InfoList

    def get_parentGUID_From_GUID(self, GUID):
        ResultDict = self.get_BasicInfoDict_From_GUID(GUID)
        if "parent" in ResultDict:
            return ResultDict["parent"]["id"]
        else:
            return None

    def get_WwiseInfo(self):
        args = {}
        Results = self.GO.call("ak.wwise.core.getInfo", args)
        return Results

    def get_wwuPath_From_GUID(self, GUID):
        args = {
            "from": {
                "id": [GUID]
            },
            "options": {
                "return": ["filePath"]
            }
        }
        Results = self.GO.call("ak.wwise.core.object.get", args)
        try:
            return Results["return"][0]["filePath"]
        except:
            return None

    def get_wwuPath_From_EventName(self, EventName):
        EventStr = "Event:" + EventName
        args = {
            "from": {
                "name": [EventStr]
            },
            "options": {
                "return": ["filePath"]
            }
        }
        Results = self.GO.call("ak.wwise.core.object.get", args)
        try:
            return Results["return"][0]["filePath"]
        except:
            return None

    def Get_AllWAVPath_From_EventName_InActionLayer(self, EventStr):
        WwiseProjectFolderPath = global_curWwisePath
        EventRootCups = {}
        args = {
            "from": {
                "name": ["Event:" + EventStr]
            },
            "options": {
                "return": ["filePath"]
            }
        }
        Results = self.GO.call("ak.wwise.core.object.get", args)
        if Results is not None:
            EventWwuPath = Results["return"][0]["filePath"]
            if len(EventWwuPath) != 0:
                tree = ET.parse(EventWwuPath)
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
                            tempDict_Action = {"PropertyValue": "1", "PropertyName": "Play", "ObjectRef": {"ID": "", "Name": "", "Type": "", "WorkUnitID": "", "WorkUnitPath": "", "wavPath": []}}
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
                                ObjectRef_WorkUnitID = ObjectRef.attrib.get("WorkUnitID")
                                tempDict_Action["ObjectRef"]["Name"] = ObjectRef_Name
                                tempDict_Action["ObjectRef"]["ID"] = ObjectRef_ID
                                tempDict_Action["ObjectRef"]["WorkUnitID"] = ObjectRef_WorkUnitID
                                args = {
                                    "from": {
                                        "id": [ObjectRef_WorkUnitID]
                                    },
                                    "options": {
                                        "return": ["filePath"]
                                    }
                                }
                                Results = self.GO.call("ak.wwise.core.object.get", args)
                                ActorWwuPath = Results["return"][0]["filePath"]
                                tempDict_Action["ObjectRef"]["WorkUnitPath"] = ActorWwuPath

                                # 从这里遍历ActorWWU
                                wavPathList = []
                                tree = ET.parse(ActorWwuPath)
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

    def Get_ObjectRefInfo_From_EventName(self, EventStr):
        WwiseProjectFolderPath = global_curWwisePath
        EventRootCups = {}
        args = {
            "from": {
                "name": ["Event:" + EventStr]
            },
            "options": {
                "return": ["filePath"]
            }
        }
        Results = self.GO.call("ak.wwise.core.object.get", args)
        if Results is not None:
            EventWwuPath = Results["return"][0]["filePath"]
            if len(EventWwuPath) != 0:
                tree = ET.parse(EventWwuPath)
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
                            tempDict_Action = {"PropertyValue": "1", "PropertyName": "Play", "ObjectRef": {"ID": "", "Name": "", "Type": "", "WorkUnitID": "", "WorkUnitPath": "", "wavPath": []}}
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
                                ObjectRef_WorkUnitID = ObjectRef.attrib.get("WorkUnitID")
                                tempDict_Action["ObjectRef"]["Name"] = ObjectRef_Name
                                tempDict_Action["ObjectRef"]["ID"] = ObjectRef_ID
                                tempDict_Action["ObjectRef"]["WorkUnitID"] = ObjectRef_WorkUnitID
                                args = {
                                    "from": {
                                        "id": [ObjectRef_WorkUnitID]
                                    },
                                    "options": {
                                        "return": ["filePath"]
                                    }
                                }
                                Results = self.GO.call("ak.wwise.core.object.get", args)
                                ActorWwuPath = Results["return"][0]["filePath"]
                                tempDict_Action["ObjectRef"]["WorkUnitPath"] = ActorWwuPath

                            EventRootCups[name]["Action"][guid_action_id] = tempDict_Action

        return EventRootCups

    def getSchemaVersionFromBusWWU(self):
        SchemaVersion = ""
        path = self.get_FolderPath_WwiseCurrentProjectPath()
        if len(path) != 0:
            tree = ET.parse(path + "\\Master-Mixer Hierarchy\\Default Work Unit.wwu")
            root = tree.getroot()

            for item in root.iter("WwiseDocument"):
                if len(item.attrib.get("SchemaVersion")) != 0:
                    SchemaVersion = item.attrib.get("SchemaVersion")

        return SchemaVersion

    def ifWwiseVersionIsHigherThan2022(self):
        SchemaVersionStr = self.getSchemaVersionFromBusWWU()
        if len(SchemaVersionStr) == 0:
            return False
        else:
            if int(SchemaVersionStr) >= 110:
                return True
            else:
                return False

    def get_WwiseCurrentProjectPath(self):
        if self.GO is not None:
            args = {
                "from": {
                    "ofType": ["Project"]
                },
                "options": {
                    "return": ["filePath"]
                }
            }
            ProjectPath = self.GO.call("ak.wwise.core.object.get", args)
            if len(ProjectPath["return"]) != 0:
                return ProjectPath["return"][0]["filePath"]

    def get_WwiseCurrentProjectID(self):
        if self.GO is not None:
            args = {
                "from": {
                    "ofType": ["Project"]
                },
                "options": {
                    "return": ["id"]
                }
            }
            ProjectPath = self.GO.call("ak.wwise.core.object.get", args)
            if len(ProjectPath["return"]) != 0:
                return ProjectPath["return"][0]["id"]

    def get_FolderPath_WwiseCurrentProjectPath(self):
        if self.GO is not None:
            path = self.get_WwiseCurrentProjectPath()
            if path is None:
                return None
            else:
                if len(path) != 0:
                    folderPath = os.path.dirname(path)
                    return folderPath

    def get_GUIDOfPath(self, WwisePath):
        if self.GO is not None:
            args = {
                "from": {
                    "path": [WwisePath]
                },
                "options": {
                    "return": ["id"]
                }
            }
            Result = self.GO.call("ak.wwise.core.object.get", args)
            try:
                return Result["return"][0]["id"]
            except:
                return None

    def get_PathOfGUID(self, GUID):
        if self.GO is not None:
            args = {
                "from": {
                    "id": [GUID]
                },
                "options": {
                    "return": ["path"]
                }
            }
            Result = self.GO.call("ak.wwise.core.object.get", args)
            try:
                return Result["return"][0]["path"]
            except:
                return None

    def get_NameOfGUID(self, GUID):
        if self.GO is not None:
            args = {
                "from": {
                    "id": [GUID]
                },
                "options": {
                    "return": ["name"]
                }
            }
            Result = self.GO.call("ak.wwise.core.object.get", args)
            try:
                return Result["return"][0]["name"]
            except:
                return None

    def get_EventGUID_From_EventName(self, EventStr):
        if self.GO is not None:
            args = {
                "from": {
                    "name": ["Event:" + EventStr]
                },
                "options": {
                    "return": ["id"]
                }
            }
            Result = self.GO.call("ak.wwise.core.object.get", args)
            try:
                return Result["return"][0]["id"]
            except:
                return None

    def get_EventGUID_AndNotes_From_EventName(self, EventStr):
        if self.GO is not None:
            args = {
                "from": {
                    "name": ["Event:" + EventStr]
                },
                "options": {
                    "return": ["id", "notes"]
                }
            }
            Result = self.GO.call("ak.wwise.core.object.get", args)
            try:
                return [Result["return"][0]["id"], Result["return"][0]["notes"]]
            except:
                return None

    def get_Path_From_SwitchGroupName(self, SwitchGroupStr):
        if self.GO is not None:
            args = {
                "from": {
                    "name": ["SwitchGroup:" + SwitchGroupStr]
                },
                "options": {
                    "return": ["path"]
                }
            }
            Result = self.GO.call("ak.wwise.core.object.get", args)
            try:
                return Result["return"][0]["path"]
            except:
                return None

    def get_Path_From_StateGroupName(self, StateGroupStr):
        if self.GO is not None:
            args = {
                "from": {
                    "name": ["StateGroup:" + StateGroupStr]
                },
                "options": {
                    "return": ["path"]
                }
            }
            Result = self.GO.call("ak.wwise.core.object.get", args)
            try:
                return Result["return"][0]["path"]
            except:
                return None

    def get_Path_From_UniqueNameStr(self, typeStr, NameStr):
        if self.GO is not None:
            args = {
                "from": {
                    "name": [typeStr + ":" + NameStr]
                },
                "options": {
                    "return": ["path"]
                }
            }
            Result = self.GO.call("ak.wwise.core.object.get", args)
            try:
                return Result["return"][0]["path"]
            except:
                return None

    def PlayAnEvent(self, GUID):
        if self.GO is not None:
            args = {
                "action": "stop"
            }
            self.GO.call("ak.wwise.core.transport.executeAction", args)

            args = {
                "object": GUID
            }
            pID = self.GO.call("ak.wwise.core.transport.create", args)

            args = {
                "action": "play",
                "transport": pID["transport"]
            }
            self.GO.call("ak.wwise.core.transport.executeAction", args)

    def FocusOrPopUp(self, GUID):
        if self.GO is not None:
            args = {
                "command": "Inspect",
                "objects": [GUID]
            }
            self.GO.call("ak.wwise.ui.commands.execute", args)

    def StopAllEvent(self):
        if self.GO is not None:
            args = {
                "action": "stop"
            }
            self.GO.call("ak.wwise.core.transport.executeAction", args)

    def RenewNotesForGUID(self, GUID, Str):
        args = {
            "object": GUID,
            "value": Str
        }
        self.GO.call("ak.wwise.core.object.setNotes", args)

        # Save the Project
        args = {}
        self.GO.call("ak.wwise.core.project.save", args)

    def get_ObjectRefEventGUIDList(self, ObjectRefGUID):
        if self.GO is not None:
            GUIDList = []
            args = {
                "from": {
                    "id": [ObjectRefGUID]
                },
                "transform": [{
                    "select": ["referencesTo"]
                }],
                "options": {
                    "return": ["id"]
                }
            }
            result = self.GO.call("ak.wwise.core.object.get", args)

            try:
                for i in result["return"]:
                    GUIDList.append(i["id"])

                return GUIDList
            except:
                return None

    def get_Paths_of_Descendants(self, targetTypeStr):
        if self.GO is not None:
            # 定义合法的targetTypeStr
            if targetTypeStr == "BUS":
                tarRootPath = "\\Master-Mixer Hierarchy"
                validTypeStrList = ["Bus", "AuxBus"]
            elif targetTypeStr == "SWITCH":
                tarRootPath = "\\Switches"
                validTypeStrList = ["SwitchGroup"]
            elif targetTypeStr == "STATE":
                tarRootPath = "\\States"
                validTypeStrList = ["StateGroup"]
            elif targetTypeStr == "RTPC":
                tarRootPath = "\\Game Parameters"
                validTypeStrList = ["GameParameter"]
            elif targetTypeStr == "CONVERSION":
                tarRootPath = "\\Conversion Settings"
                validTypeStrList = ["Conversion"]
            elif targetTypeStr == "ATTENUATION":
                tarRootPath = "\\Attenuations"
                validTypeStrList = ["Attenuation"]
            elif targetTypeStr == "SIDECHAIN":
                tarRootPath = "\\Effects"
                validTypeStrList = ["Wwise Meter"]
            else:
                tarRootPath = ""
                validTypeStrList = []

            PATHList = []
            if targetTypeStr == "SIDECHAIN":
                args = {
                    "from": {
                        "path": [tarRootPath]
                    },
                    "transform": [{
                        "select": ["descendants"]
                    }],
                    "options": {
                        "return": ["path", "pluginName"]
                    }
                }
                result = self.GO.call("ak.wwise.core.object.get", args)
            else:
                args = {
                    "from": {
                        "path": [tarRootPath]
                    },
                    "transform": [{
                        "select": ["descendants"]
                    }],
                    "options": {
                        "return": ["path", "type"]
                    }
                }
                result = self.GO.call("ak.wwise.core.object.get", args)
            # LOG.debug(result)
            try:
                for i in result["return"]:
                    if targetTypeStr == "SIDECHAIN":
                        tarStr = i["pluginName"]
                    else:
                        tarStr = i["type"]
                    if tarStr in validTypeStrList:
                        PATHList.append(i["path"])
                        # LOG.debug(i["path"])
                return PATHList
            except:
                return None

    def get_Paths_of_Children_ForSwitchGroup(self, switchGroupPath):
        PATHList = []
        args = {
            "from": {
                "path": [switchGroupPath]
            },
            "transform": [{
                "select": ["children"]
            }],
            "options": {
                "return": ["path", "type"]
            }
        }
        result = self.GO.call("ak.wwise.core.object.get", args)
        try:
            for i in result["return"]:
                if i["type"] == "Switch":
                    PATHList.append(i["path"])
                    # LOG.debug(i["path"])
            return PATHList
        except:
            return None

    def get_Paths_of_Children_ForStateGroup(self, stateGroupPath):
        PATHList = []
        args = {
            "from": {
                "path": [stateGroupPath]
            },
            "transform": [{
                "select": ["children"]
            }],
            "options": {
                "return": ["path", "type"]
            }
        }
        result = self.GO.call("ak.wwise.core.object.get", args)
        try:
            for i in result["return"]:
                if i["type"] == "State":
                    PATHList.append(i["path"])
                    # LOG.debug(i["path"])
            return PATHList
        except:
            return None

    def get_Value_of_RTPC(self, RTPCPath):
        ValueDict = {
            "Min": "",
            "Max": "",
            "InitialValue": ""
        }
        args = {
            "from": {
                "path": [RTPCPath]
            },
            "options": {
                "return": ["Min", "Max", "InitialValue"]
            }
        }
        result = self.GO.call("ak.wwise.core.object.get", args)
        try:
            resultDict = result["return"][0]
            ValueDict["Min"] = str(resultDict["Min"])
            ValueDict["Max"] = str(resultDict["Max"])
            ValueDict["InitialValue"] = str(resultDict["InitialValue"])
            return ValueDict
        except:
            return None

    def get_value_of_WwiseMeter(self, MeterPath):
        MeterName = os.path.basename(MeterPath)
        ValidRTPCName = "RTPC_" + MeterName
        args = {
            "from": {
                "path": [MeterPath]
            },
            "options": {
                "return": ["AttackTime", "ReleaseTime"]
            }
        }
        result = self.GO.call("ak.wwise.core.object.get", args)

        try:
            AttackTime = float(result["return"][0]["AttackTime"])
            AttackTime = str(round(AttackTime, 1))
            ReleaseTime = float(result["return"][0]["ReleaseTime"])
            ReleaseTime = str(round(ReleaseTime, 1))
            SCDict = {
                "RTPC": ValidRTPCName,
                "AttackTime": AttackTime,
                "ReleaseTime": ReleaseTime
            }
            return SCDict
        except:
            return None

    def get_value_of_Attenuation(self, AttPath):
        args = {
            "from": {
                "path": [AttPath]
            },
            "options": {
                "return": ["RadiusMax"]
            }
        }
        result = self.GO.call("ak.wwise.core.object.get", args)
        try:
            RadiusMax = str(int(result["return"][0]["RadiusMax"]))
            return {"RadiusMax": RadiusMax}
        except:
            return None

    def get_ObjParentGUID(self, ObjGUID):
        if self.GO is not None:
            args = {
                "from": {
                    "id": [ObjGUID]
                },
                "transform": [{
                    "select": ["parent"]
                }],
                "options": {
                    "return": ["id"]
                }
            }
            Result = self.GO.call("ak.wwise.core.object.get", args)
            try:
                return Result["return"][0]["id"]
            except TypeError:
                return None

    def get_ObjChildrenGUID(self, ObjGUID):
        if self.GO is not None:
            GUIDList = []
            args = {
                "from": {
                    "id": [ObjGUID]
                },
                "transform": [{
                    "select": ["children"]
                }],
                "options": {
                    "return": ["id"]
                }
            }
            Result = self.GO.call("ak.wwise.core.object.get", args)

            try:
                for i in Result["return"]:
                    GUIDList.append(i["id"])
                return GUIDList
            except:
                return None

    def get_TypeOfGUID(self, GUID):
        if self.GO is not None:
            args = {
                "from": {
                    "id": [GUID]
                },
                "options": {
                    "return": ["type"]
                }
            }
            result = self.GO.call("ak.wwise.core.object.get", args)
            return result["return"][0]["type"]

    def get_TargetTypeInfo_From_Path(self, path, targetTypeStr):
        if self.GO is not None:
            args = {
                "from": {
                    "path": [path]
                },
                "options": {
                    "return": ["@@" + targetTypeStr]
                }
            }
            result = self.GO.call("ak.wwise.core.object.get", args)
            # LOG.debug("1 --> " + str(result))
            if result is not None:
                if Get_PropertyType_From_PropertyName(targetTypeStr) == "Reference":
                    TarName = result.get("return", {})[0].get("@@" + targetTypeStr, {}).get("name", "")
                    TarID = result.get("return", {})[0].get("@@" + targetTypeStr, {}).get("id", "")
                    # LOG.debug("2 --> " + str(TarName))
                    # LOG.debug("3 --> " + str(TarID))
                    if TarID != "{00000000-0000-0000-0000-000000000000}":
                        args2 = {
                            "from": {
                                "id": [TarID]
                            },
                            "options": {
                                "return": ["path"]
                            }
                        }
                        result2 = self.GO.call("ak.wwise.core.object.get", args2)
                        pathh = result2["return"][0]["path"]
                        # LOG.debug("4 --> " + str(result2))
                        # LOG.debug("5 --> " + str(pathh))
                        return {"ID": TarID, "Name": TarName, "Path": pathh}
                    else:
                        LOG.warning("[Warning] This \"" + result["return"][0]["type"] + "\" hasn't been assigned \"" + targetTypeStr + "\"")
                        return None
                else:
                    TarValue = result.get("return", {})[0].get("@@" + targetTypeStr, "")
                    if len(str(TarValue)) != 0:
                        # LOG.debug("6 --> " + str(TarValue))
                        return {"Value": TarValue}
                    else:
                        LOG.warning("[Warning] \"" + result["return"][0]["type"] + "\" doesn't have a property called \"" + targetTypeStr + "\"")
                        return None
            else:
                return None

    def create(self, parent, objtype, name, onNameConflict, noteStr):
        # 检查onNameConflict的合法性
        validOnNameConflictValueList = ["rename", "replace", "fail", "merge"]
        if onNameConflict not in validOnNameConflictValueList:
            onNameConflict = "merge"

        # 检查objtype的合法性
        if objtype == "RandomContainer":
            args = {
                "parent": parent,
                "type": "RandomSequenceContainer",
                "name": name,
                "@RandomOrSequence": 1,
                "onNameConflict": onNameConflict,
                "notes": noteStr
            }
            Results = self.GO.call("ak.wwise.core.object.create", args)
            return Results
        elif objtype == "SequenceContainer":
            args = {
                "parent": parent,
                "type": "RandomSequenceContainer",
                "name": name,
                "@RandomOrSequence": 0,
                "onNameConflict": onNameConflict,
                "notes": noteStr
            }
            Results = self.GO.call("ak.wwise.core.object.create", args)
            return Results
        elif objtype == "WorkUnit":
            args = {
                "parent": parent,
                "type": "WorkUnit",
                "name": name,
                "@RandomOrSequence": 0,
                "onNameConflict": "merge",
                "notes": noteStr
            }
            Results = self.GO.call("ak.wwise.core.object.create", args)
            return Results
        else:
            args = {
                "parent": parent,
                "type": objtype,
                "name": name,
                "onNameConflict": onNameConflict,
                "notes": noteStr
            }
            Results = self.GO.call("ak.wwise.core.object.create", args)
            return Results

    def create_RTPC(self, parentInfo, nameStr, noteStr, minValueIntOrStr, maxValueIntOrStr, initValueIntOrStr):
        args = {
            "parent": parentInfo,
            "type": "GameParameter",
            "name": nameStr,
            "onNameConflict": "merge",
            "notes": noteStr,
        }
        Result = self.GO.call("ak.wwise.core.object.create", args)

        args = {
            "object": Result["id"],
            "property": "Min",
            "value": minValueIntOrStr
        }
        self.GO.call("ak.wwise.core.object.setProperty", args)

        args = {
            "object": Result["id"],
            "property": "Max",
            "value": maxValueIntOrStr
        }
        self.GO.call("ak.wwise.core.object.setProperty", args)

        args = {
            "object": Result["id"],
            "property": "InitialValue",
            "value": initValueIntOrStr
        }
        self.GO.call("ak.wwise.core.object.setProperty", args)

        return Result

    def create_GenAttenuation(self, parentInfo, nameStr, noteStr, maxValueInt):
        # Create Gen Attenuation
        args = {
            "parent": parentInfo,
            "type": "Attenuation",
            "name": nameStr,
            "onNameConflict": "merge",
            "notes": noteStr
        }
        Result = self.GO.call("ak.wwise.core.object.create", args)

        # Set Init value for Gen Attenuation
        args = {
            "object": Result["id"],
            "property": "RadiusMax",
            "value": maxValueInt
        }
        self.GO.call("ak.wwise.core.object.setProperty", args)

        args = {
            "object": Result["id"],
            "curveType": "VolumeDryUsage",
            "use": "Custom",
            "points": [
                {
                    "x": 0,
                    "y": 0,
                    "shape": "SCurve"
                },
                {
                    "x": maxValueInt,
                    "y": -200,
                    "shape": "SCurve"
                }
            ]
        }
        self.GO.call("ak.wwise.core.object.setAttenuationCurve", args)

        args = {
            "object": Result["id"],
            "curveType": "SpreadUsage",
            "use": "Custom",
            "points": [
                {
                    "x": 0,
                    "y": 100,
                    "shape": "SCurve"
                },
                {
                    "x": maxValueInt,
                    "y": 0,
                    "shape": "SCurve"
                }
            ]
        }
        self.GO.call("ak.wwise.core.object.setAttenuationCurve", args)

        args = {
            "object": Result["id"],
            "curveType": "HighPassFilterUsage",
            "use": "Custom",
            "points": [
                {
                    "x": 0,
                    "y": 0,
                    "shape": "SCurve"
                },
                {
                    "x": maxValueInt,
                    "y": 100,
                    "shape": "SCurve"
                }
            ]
        }
        self.GO.call("ak.wwise.core.object.setAttenuationCurve", args)

        return Result

    def create_Bus(self, parentInfo, nameStr, noteStr):
        args = {
            "parent": parentInfo,
            "type": "Bus",
            "name": nameStr,
            "onNameConflict": "merge",
            "notes": noteStr,
        }
        Result = self.GO.call("ak.wwise.core.object.create", args)
        return Result

    def create_SoundBank(self, parentInfo, nameStr, noteStr):
        args = {
            "parent": parentInfo,
            "type": "SoundBank",
            "name": nameStr,
            "onNameConflict": "merge",
            "notes": noteStr
        }
        Result = self.GO.call("ak.wwise.core.object.create", args)
        return Result

    def create_SwitchGroup(self, parentInfo, nameStr, noteStr, childrenList: list):
        for childStr in childrenList:
            args = {
                "parent": parentInfo,
                "type": "SwitchGroup",
                "name": nameStr,
                "onNameConflict": "merge",
                "notes": noteStr,
                "children": [{
                    "type": "Switch",
                    "name": childStr,
                    "notes": ""
                }]
            }
            self.GO.call("ak.wwise.core.object.create", args)

    def create_WorkUnit(self, parentInfo, nameStr, noteStr):
        args = {
            "parent": parentInfo,
            "type": "WorkUnit",
            "name": nameStr,
            "onNameConflict": "merge",
            "notes": noteStr
        }
        result = self.GO.call("ak.wwise.core.object.create", args)
        return result

    def create_VirtualFolder(self, parentInfo, nameStr, noteStr):
        args = {
            "parent": parentInfo,
            "type": "Folder",
            "name": nameStr,
            "onNameConflict": "merge",
            "notes": noteStr
        }
        result = self.GO.call("ak.wwise.core.object.create", args)
        return result

    def create_ActorMixer(self, parentInfo, nameStr, noteStr):
        args = {
            "parent": parentInfo,
            "type": "ActorMixer",
            "name": nameStr,
            "onNameConflict": "merge",
            "notes": noteStr
        }
        result = self.GO.call("ak.wwise.core.object.create", args)
        return result

    def create_RandonContainer(self, parentInfo, nameStr, noteStr):
        args = {
            "parent": parentInfo,
            "type": "RandomSequenceContainer",
            "name": nameStr,
            "@RandomOrSequence": 1,
            "onNameConflict": "merge",
            "notes": noteStr
        }
        Results = self.GO.call("ak.wwise.core.object.create", args)
        return Results

    def create_SequenceContainer(self, parentInfo, nameStr, noteStr):
        args = {
            "parent": parentInfo,
            "type": "RandomSequenceContainer",
            "name": nameStr,
            "@RandomOrSequence": 0,
            "onNameConflict": "merge",
            "notes": noteStr
        }
        Results = self.GO.call("ak.wwise.core.object.create", args)
        return Results

    def create_BlendContainer(self, parentInfo, nameStr, noteStr):
        args = {
            "parent": parentInfo,
            "type": "BlendContainer",
            "name": nameStr,
            "onNameConflict": "merge",
            "notes": noteStr
        }
        Results = self.GO.call("ak.wwise.core.object.create", args)
        return Results

    def create_PlayEvent(self, parentInfo, nameStr, noteStr, TarRefInfo):
        args = {
            "parent": parentInfo,
            "type": "Event",
            "name": "Play_" + nameStr,
            "notes": noteStr,
            "onNameConflict": "merge",
            "children": [{
                "name": "",
                "type": "Action",
                "@ActionType": 1,
                "@Target": TarRefInfo
            }]
        }
        result = self.GO.call("ak.wwise.core.object.create", args)
        return result

    def create_StopEvent(self, parentInfo, nameStr, noteStr, TarRefInfo):
        args = {
            "parent": parentInfo,
            "type": "Event",
            "name": "Stop_" + nameStr,
            "notes": noteStr,
            "onNameConflict": "merge",
            "children": [{
                "name": "",
                "type": "Action",
                "@ActionType": 2,
                "@Target": TarRefInfo
            }]
        }
        result = self.GO.call("ak.wwise.core.object.create", args)
        return result

    def import_SFX(self, wavPath, TarGUID, nameStr):
        TarPath = self.get_PathOfGUID(TarGUID)
        args = {
            "importOperation": "useExisting",
            "default": {"importLanguage": "SFX"},
            "imports": [{
                "audioFile": wavPath,
                "objectPath": TarPath + "\\<Sound SFX>" + nameStr
            }]
        }
        Result = self.GO.call("ak.wwise.core.audio.import", args)
        try:
            for i in Result["objects"]:
                if i["name"] == nameStr:
                    return i["id"]
        except:
            return None

    def import_Voice(self, wavPath, TarGUID, nameStr, lanStr):
        TarPath = self.get_PathOfGUID(TarGUID)
        args = {
            "importOperation": "useExisting",
            "imports": [{
                "audioFile": wavPath,
                "objectPath": TarPath + "\\<Sound Voice>" + nameStr + "\\<AudioFileSource>" + nameStr + "_" + lanStr,
                "importLanguage": lanStr
            }]
        }
        Result = self.GO.call("ak.wwise.core.audio.import", args)
        try:
            for i in Result["objects"]:
                if i["name"] == nameStr:
                    return i["id"]
        except:
            return None

    def setInclusions_forBank(self, bankInfo, inclusionObjInfo):
        args = {
            "soundbank": bankInfo,
            "operation": "add",
            "inclusions": [
                {
                    "object": inclusionObjInfo,
                    "filter": [
                        "events",
                        "structures",
                        "media"
                    ]
                }
            ]
        }
        self.GO.call("ak.wwise.core.soundbank.setInclusions", args)

    def setReference(self, objInfo, referenceStr, tarInfo):
        args = {
            "object": objInfo,
            "reference": referenceStr,
            "value": tarInfo
        }
        self.GO.call("ak.wwise.core.object.setReference", args)

    def setReference_OutputBus(self, objInfo, tarInfo):
        args = {
            "object": objInfo,
            "reference": "OutputBus",
            "value": tarInfo
        }
        self.GO.call("ak.wwise.core.object.setReference", args)

    def setReference_Attenuation(self, objInfo, AttenObjInfo):
        args = {
            "object": objInfo,
            "property": "3DSpatialization",
            "value": "2"
        }
        self.GO.call("ak.wwise.core.object.setProperty", args)

        args = {
            "object": objInfo,
            "reference": "Attenuation",
            "value": AttenObjInfo
        }
        self.GO.call("ak.wwise.core.object.setReference", args)

    def setReference_Conversion(self, objInfo, RefInfo):
        args = {
            "object": objInfo,
            "property": "OverrideConversion",
            "value": True
        }
        self.GO.call("ak.wwise.core.object.setProperty", args)

        args = {
            "object": objInfo,
            "reference": "Conversion",
            "value": RefInfo
        }
        self.GO.call("ak.wwise.core.object.setReference", args)

    def setReference_SwitchOrStateGroup(self, objInfo, SwitchOrStateGroupInfo):
        args = {
            "object": objInfo,
            "reference": "SwitchGroupOrStateGroup",
            "value": SwitchOrStateGroupInfo
        }
        self.GO.call("ak.wwise.core.object.setReference", args)

    def setReference_EventActionAssignation(self, ActionGUID, ObjectRefGUID):
        args = {
            "object": ActionGUID,
            "reference": "Target",
            "value": ObjectRefGUID
        }
        self.GO.call("ak.wwise.core.object.setReference", args)

    def addAssignmentForSwitchOrState(self, objInfo, stateOrSwitchInfo):
        args = {
            "child": objInfo,
            "stateOrSwitch": stateOrSwitchInfo
        }
        self.GO.call("ak.wwise.core.switchContainer.addAssignment", args)

    def setProperty(self, objInfo, propertyStr, value):
        args = {
            "object": objInfo,
            "property": propertyStr,
            "value": value
        }
        self.GO.call("ak.wwise.core.object.setProperty", args)

    def setProperty_Volume(self, objInfo, value):
        args = {
            "object": objInfo,
            "property": "Volume",
            "value": value
        }
        self.GO.call("ak.wwise.core.object.setProperty", args)

    def setProperty_Pitch(self, objInfo, value):
        args = {
            "object": objInfo,
            "property": "Pitch",
            "value": value
        }
        result = self.GO.call("ak.wwise.core.object.setProperty", args)
        if result is None:
            LOG.info(lan["LOG_SM_PitchRandom_FAIL"][L])

    def setProperty_IsLoopingEnabled(self, objInfo):
        args = {
            "object": objInfo,
            "property": "IsLoopingEnabled",
            "value": "True"
        }
        self.GO.call("ak.wwise.core.object.setProperty", args)

    def setProperty_OverrideOutput(self, objInfo):
        args = {
            "object": objInfo,
            "property": "OverrideOutput",
            "value": "True"
        }
        self.GO.call("ak.wwise.core.object.setProperty", args)

    def setProperty_IsStreamingEnabled(self, objInfo):
        args = {
            "object": objInfo,
            "property": "IsStreamingEnabled",
            "value": "true"
        }
        self.GO.call("ak.wwise.core.object.setProperty", args)

    def setProperty_OverrideColor(self, objInfo, colorIntStr):
        args = {
            "object": objInfo,
            "property": "OverrideColor",
            "value": "true"
        }
        result = self.GO.call("ak.wwise.core.object.setProperty", args)
        if result is None:
            LOG.INFO(lan["LOG_SM_SetColor_FAIL"][L])

        args = {
            "object": objInfo,
            "property": "Color",
            "value": colorIntStr
        }
        result = self.GO.call("ak.wwise.core.object.setProperty", args)
        if result is None:
            LOG.INFO(lan["LOG_SM_SetColor_FAIL"][L])

    def setProperty_InitialDelay(self, objInfo, value):
        args = {
            "object": objInfo,
            "property": "InitialDelay",
            "value": value
        }
        self.GO.call("ak.wwise.core.object.setProperty", args)

    def setProperty_OverrideClockSettings(self, GUID):
        args = {
            "object": GUID,
            "property": "OverrideClockSettings",
            "value": "True"
        }
        self.GO.call("ak.wwise.core.object.setProperty", args)

    def setProperty_TempoAndTimeSignature(self, GUID, TempoValue, UpperValue, LowerValue):
        args = {
            "object": GUID,
            "property": "Tempo",
            "value": TempoValue
        }
        self.GO.call("ak.wwise.core.object.setProperty", args)

        args = {
            "object": GUID,
            "property": "TimeSignatureUpper",
            "value": UpperValue
        }
        self.GO.call("ak.wwise.core.object.setProperty", args)

        args = {
            "object": GUID,
            "property": "TimeSignatureLower",
            "value": LowerValue
        }
        self.GO.call("ak.wwise.core.object.setProperty", args)

    def setRandomizer(self, objInfo, propertyStr, enableBool, minFloat: float, maxFloat: float):
        args = {
            "object": objInfo,
            "property": propertyStr,
            "enabled": enableBool,
            "min": minFloat,
            "max": maxFloat
        }
        self.GO.call("ak.wwise.core.object.setRandomizer", args)

    def setRandomizer_Volume(self, objInfo, minFloat: float, maxFloat: float):
        args = {
            "object": objInfo,
            "property": "Volume",
            "enabled": True,
            "min": minFloat,
            "max": maxFloat
        }
        self.GO.call("ak.wwise.core.object.setRandomizer", args)

    def setRandomizer_Pitch(self, objInfo, minFloat: float, maxFloat: float):
        args = {
            "object": objInfo,
            "property": "Pitch",
            "enabled": True,
            "min": minFloat,
            "max": maxFloat
        }
        result = self.GO.call("ak.wwise.core.object.setRandomizer", args)
        if result is None:
            LOG.info(lan["LOG_SM_PitchRandom_FAIL"][L])

    def setRandomizer_InitialDelay(self, objInfo, minFloat: float, maxFloat: float):
        args = {
            "object": objInfo,
            "property": "InitialDelay",
            "enabled": True,
            "min": minFloat,
            "max": maxFloat
        }
        self.GO.call("ak.wwise.core.object.setRandomizer", args)

    def RenameEvent(self, OldEventNameStr, NewEventNameStr):
        args = {
            "from": {
                "name": ["Event:" + OldEventNameStr]
            },
            "options": {
                "return": ["id"]
            }
        }
        result = self.GO.call("ak.wwise.core.object.get", args)

        TarEventGUID = result["return"][0]["id"]
        args = {
            "object": TarEventGUID,
            "value": NewEventNameStr
        }
        Result = self.GO.call("ak.wwise.core.object.setName", args)
        return Result

    def move(self, objGUID, tarParentGUID):
        args = {
            "object": objGUID,
            "parent": tarParentGUID,
            "onNameConflict": "rename"
        }

        self.GO.call("ak.wwise.core.object.move", args)

    def rename(self, objGUID, newNameStr):
        args = {
            "object": objGUID,
            "value": newNameStr
        }
        self.GO.call("ak.wwise.core.object.setName", args)

    def uiCommand_FocusOrPopup(self, objInfo):
        args = {
            "command": "Inspect",
            "objects": [objInfo]
        }
        self.GO.call("ak.wwise.ui.commands.execute", args)

    def transport_PlayEvent(self, objInfo):
        args = {
            "action": "stop"
        }
        self.GO.call("ak.wwise.core.transport.executeAction", args)

        args = {
            "object": objInfo
        }
        pID = self.GO.call("ak.wwise.core.transport.create", args)

        args = {
            "action": "play",
            "transport": pID["transport"]
        }
        self.GO.call("ak.wwise.core.transport.executeAction", args)

        args = {
            "command": "Inspect",
            "objects": [objInfo]
        }
        self.GO.call("ak.wwise.ui.commands.execute", args)

    def transport_StopAllEvent(self):
        args = {
            "action": "stop"
        }
        self.GO.call("ak.wwise.core.transport.executeAction", args)

    def saveSession(self):
        args = {}
        self.GO.call("ak.wwise.core.project.save", args)

    def getAudioContainersFromAudioWWU(self):
        AudioRootCups = {}

        for wwuPath in getWWUPathFromLocal(self.get_CurrentWwiseSession_ActorMixerWWUPath()):
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

        for wwuPath in getWWUPathFromLocal(self.get_CurrentWwiseSession_InteractiveMusicWWUPath()):
            tree = ET.parse(wwuPath)
            root = tree.getroot()

            for a in root:
                for b in a:
                    for c in b:
                        for d in c:
                            if d.attrib.get("ID") is not None:
                                AudioRootCups[d.attrib.get("Name")] = d.attrib.get("ID")

        return AudioRootCups

    def get_CurrentWwiseSession_ActorMixerWWUPath(self):
        args = {
            "from": {
                "ofType": ["Project"]
            },
            "options": {
                "return": ["filePath"]
            }
        }
        ProjectPath = self.GO.call("ak.wwise.core.object.get", args)
        TargetPath = str(os.path.dirname(ProjectPath["return"][0]["filePath"])) + "\\Actor-Mixer Hierarchy"
        return TargetPath

    def get_CurrentWwiseSession_EventsWWUPath(self):
        args = {
            "from": {
                "ofType": ["Project"]
            },
            "options": {
                "return": ["filePath"]
            }
        }
        ProjectPath = self.GO.call("ak.wwise.core.object.get", args)
        TargetPath = str(os.path.dirname(ProjectPath["return"][0]["filePath"])) + "\\Events"
        return TargetPath

    def get_CurrentWwiseSession_SoundBankWWUPath(self):
        args = {
            "from": {
                "ofType": ["Project"]
            },
            "options": {
                "return": ["filePath"]
            }
        }
        ProjectPath = self.GO.call("ak.wwise.core.object.get", args)
        TargetPath = str(os.path.dirname(ProjectPath["return"][0]["filePath"])) + "\\SoundBanks"
        return TargetPath

    def get_CurrentWwiseSession_InteractiveMusicWWUPath(self):
        args = {
            "from": {
                "ofType": ["Project"]
            },
            "options": {
                "return": ["filePath"]
            }
        }
        ProjectPath = self.GO.call("ak.wwise.core.object.get", args)
        TargetPath = str(os.path.dirname(ProjectPath["return"][0]["filePath"])) + "\\Interactive Music Hierarchy"
        return TargetPath

    def get_CurrentWwiseSession_SwitchesWWUPath(self):
        args = {
            "from": {
                "ofType": ["Project"]
            },
            "options": {
                "return": ["filePath"]
            }
        }
        ProjectPath = self.GO.call("ak.wwise.core.object.get", args)
        TargetPath = str(os.path.dirname(ProjectPath["return"][0]["filePath"])) + "\\Switches"
        return TargetPath

    def get_CurrentWwiseSession_OriginalsSFXFolderPath(self):
        args = {
            "from": {
                "ofType": ["Project"]
            },
            "options": {
                "return": ["filePath"]
            }
        }
        ProjectPath = self.GO.call("ak.wwise.core.object.get", args)
        TargetPath = str(os.path.dirname(ProjectPath["return"][0]["filePath"])) + "\\Originals\\SFX"
        return TargetPath

    def get_CurrentWwiseSession_OriginalsFolderPath(self):
        args = {
            "from": {
                "ofType": ["Project"]
            },
            "options": {
                "return": ["filePath"]
            }
        }
        ProjectPath = self.GO.call("ak.wwise.core.object.get", args)
        TargetPath = str(os.path.dirname(ProjectPath["return"][0]["filePath"])) + "\\Originals"
        return TargetPath

    def getEventNameFromEventWWU(self):
        EventRootCups = {}
        for wwuPath in getWWUPathFromLocal(self.get_CurrentWwiseSession_EventsWWUPath()):
            tree = ET.parse(wwuPath)
            root = tree.getroot()

            for EventName in root.iter("Event"):
                EventRootCups[EventName.attrib.get("Name")] = EventName.attrib.get("ID")

        return EventRootCups

    def GetWWUPath(self, wwuPath):
        args = {
            "from": {
                "path": [wwuPath]
            },
            "options": {
                "return": [
                    "filePath"
                ]
            }
        }
        Result = self.GO.call("ak.wwise.core.object.get", args)
        typeResult = Result["return"][0]["filePath"]

        return typeResult

    def FilterValidContainerPaths(self, TemplatePath):
        # 遍历TemplateWWU中所有可能是合法容器、Folder、ActorMixer、3M、Sound的数据
        WWUPath = self.GetWWUPath(TemplatePath)
        GUIDDICTResult = GetGUIDInfoPoolFromWWU(WWUPath)
        # for i in GUIDDICTResult:
        #     LOG.debug(i)

        # 获取以上所有数据的路径
        Results = self.GetPathsFromGUID(GUIDDICTResult)
        # for ii in Results:
        #     LOG.debug(ii)

        # 排查是否存在禁用对象（"Folder"、"ActorMixer"、"Sound"、"MusicSwitchContainer"、"MusicPlaylistContainer"、"MusicSegment"）
        ForbiddenTypeList = ["Folder", "ActorMixer", "Sound", "MusicSwitchContainer", "MusicPlaylistContainer", "MusicSegment"]
        ForbiddenPaths = []

        # 先检查Template本身的容器类型，禁用对象（"Folder"、"ActorMixer"、"Sound"、"MusicSwitchContainer"、"MusicPlaylistContainer"、"MusicSegment"）
        TemplateType = self.GetPathType(TemplatePath)
        if TemplateType in ForbiddenTypeList:
            ForbiddenPaths.append(TemplateType)

        # 再检查子集对象中是否包含禁用对象（"Folder"、"ActorMixer"、"Sound"、"MusicSwitchContainer"、"MusicPlaylistContainer"、"MusicSegment"）
        # 准备好比对用的Template路径，补充路径格式
        TemplatePath = TemplatePath + "\\"

        # 把包含Template路径的路径筛选出来(加"\\"，是为了排除Template本身的路径，确保只取子集)
        TargetResults = []
        for obj in Results:
            if obj.find(TemplatePath) != -1:
                TargetResults.append(obj)
                # LOG.debug(obj)

        # 检查TargetResults中是否存在禁用对象
        if len(TargetResults) != 0:
            for obj in TargetResults:
                CheckTypeResult = self.GetPathType(obj)
                if CheckTypeResult in ForbiddenTypeList:
                    ForbiddenPaths.append(CheckTypeResult)
                    # LOG.debug(CheckTypeResult)

        # 不论是否找到了禁用对象，将ForbiddenPaths传出，继续向后执行

        # 找出处于最末端的对象
        # 预备两个List，待后续筛查用
        checkStrs = []
        tarPaths = []

        # 开始筛查合法对象
        for i in Results:
            rootPath = TemplatePath  # rootPath是带着\\的TemplatePath
            if i.find(rootPath) != -1:
                x = i.replace(rootPath, "")  # 如果找到带有rootPath的行，把前面的路径字符去除
                y = os.path.split(x)[1]  # 再把尾部的元素取出
                # LOG.debug(y)
                # LOG.debug(i)
                tarStr = "\\" + y + "\\"
                checkStrs.append(tarStr)
                # LOG.debug(tarStr)
                tarPaths.append(rootPath + x)
                # LOG.debug(rootPath + x)
        # # LOG.debug(tarPaths)

        ValidPaths = FilterUniqueStrFromList(tarPaths)
        # for kkk in ValidPaths:
        #     LOG.debug(kkk)

        # # 把代表"非最底层"的“字符串证例”筛选出来
        # invalidStrs = []
        # for k in checkStrs:
        #     # LOG.debug(k)
        #     for ee in tarPaths:
        #         # LOG.debug(ee)
        #         if ee.find(k) != -1:
        #             # 前后都有\\的字符串如果出现在路径中，说明这个字符串所在的位置并不是最末端
        #             # 从而，如果一个路径的尾部却以这个字符串结尾，则说明这个路径并不是最末端，而是某个中间父级
        #             invalidStrs.append(k)
        #             # LOG.debug("k --> " + k)
        #
        # # 合并“字符串证例”同类项
        # invalidStrs = list(set(invalidStrs))
        # # for ooo in invalidStrs:
        #     # LOG.debug("invalid candidates: " + ooo)
        #
        # # 将“字符串证例”中的\\去除，准备用来检验“每个路径的尾部是不是这个字符串”，如果是，说明这个路径是中间路径！
        # for x, y in enumerate(invalidStrs):
        #     invalidStrs[x] = y.replace("\\", "")
        # # LOG.debug(invalidStrs)
        # PathsNeedToBeDeleted = []
        # # LOG.debug("------------------------------------------------")
        # for path in tarPaths:
        #     for badStr in invalidStrs:
        #         if os.path.split(path)[1] == badStr:
        #             # LOG.debug(badStr)
        #             # LOG.debug(os.path.split(path)[1])
        #             PathsNeedToBeDeleted.append(path)
        #             # LOG.debug(path)

        # 将“中间路径”从所有路径中排除，剩下的就都是“最末端路径”了
        # ValidPaths = []
        # for j in tarPaths:
        #     if j not in PathsNeedToBeDeleted:
        #         ValidPaths.append(j)
        #         # LOG.debug(j)

        # 检查ValidPaths中是否包含SwitchContainer，如果是的话，发送到ForbiddenPaths
        if len(ValidPaths) != 0:
            for obj in ValidPaths:
                # LOG.debug(ValidPaths)
                CheckTypeResult = self.GetPathType(obj)
                if CheckTypeResult == "SwitchContainer":
                    ForbiddenPaths.append(CheckTypeResult)

        return ValidPaths, ForbiddenPaths

    def GetPathType(self, cPath):
        args = {
            "from": {
                "path": [cPath]
            },
            "options": {
                "return": [
                    "type"
                ]
            }
        }
        Result = self.GO.call("ak.wwise.core.object.get", args)
        typeResult = Result["return"][0]["type"]

        return typeResult

    def getSwitchFromSwitchWWU(self, SwitchGroupName):
        SwitchCups = []

        for wwuPath in getWWUPathFromLocal(self.get_CurrentWwiseSession_SwitchesWWUPath()):
            tree = ET.parse(wwuPath)
            root = tree.getroot()

            for a in root.iter("SwitchGroup"):
                if a.attrib.get("Name") == SwitchGroupName:
                    for b in a:
                        for c in b:
                            SwitchCups.append(c.attrib.get("Name"))
        return SwitchCups

    def GetPathsFromGUID(self, guiddict: dict):
        GUIDPathPool = []
        for GUID in guiddict:
            args = {
                "from": {
                    "id": [GUID]
                },
                "options": {
                    "return": [
                        "path"
                    ]
                }
            }
            Result = self.GO.call("ak.wwise.core.object.get", args)
            GUIDPathPool.append(Result["return"][0]["path"])

        return GUIDPathPool

    def getSingleEventGUIDFromEventWWU(self, EventNameStr):
        EventGUID = ""
        for wwuPath in getWWUPathFromLocal(self.get_CurrentWwiseSession_EventsWWUPath()):
            tree = ET.parse(wwuPath)
            root = tree.getroot()

            for EventName in root.iter("Event"):
                if EventName.attrib.get("Name") == str(EventNameStr):
                    EventGUID = EventName.attrib.get("ID")

        return EventGUID

    def setNotesForGUID(self, GUID, Str):
        args = {
            "object": GUID,
            "value": Str
        }
        self.GO.call("ak.wwise.core.object.setNotes", args)

        # Save the Project
        args = {}
        self.GO.call("ak.wwise.core.project.save", args)

    def getObjectRefFromEventStr(self, EventStr):
        ObjectRefCups = {}
        resultDict = self.Get_ObjectRefInfo_From_EventName(EventStr)
        if len(resultDict) != 0:
            actionDict = resultDict[EventStr].get("Action", {})
            if len(actionDict) != 0:
                for keyy, valueee in zip(actionDict.keys(), actionDict.values()):
                    ObjectRefCups[valueee["ObjectRef"]["ID"]] = valueee["ObjectRef"]["Name"]
        # LOG.debug(ObjectRefCups)
        return ObjectRefCups

    def GetBNKNameFromEventStr(self, EventStr):
        FinalList = []
        result = self.get_EventGUID_From_EventName(EventStr)
        if result is not None:
            args = {
                "from": {
                    "name": ["Event:" + EventStr]
                },
                "options": {
                    "return": ["workunit"]
                }
            }
            result = self.GO.call("ak.wwise.core.object.get", args)
            EventWWU_Name = result["return"][0]["workunit"]["name"]
            EventWWU_GUID = result["return"][0]["workunit"]["id"]
            List_BankA = getBankNameByEventInfo(EventWWU_Name, EventWWU_GUID)

            args = {
                "from": {
                    "name": ["Event:" + EventStr]
                },
                "options": {
                    "return": ["id"]
                }
            }
            result = self.GO.call("ak.wwise.core.object.get", args)
            Event_GUID = result["return"][0]["id"]
            List_BankB = getBankNameByEventInfo(EventStr, Event_GUID)

            List = List_BankA + List_BankB
            return List
        else:
            return FinalList

    def GenerateOneBNK(self, BNKName):
        args = {
            "soundbanks": [
                {
                    "name": BNKName,
                    "rebuild": True
                }
            ],
            # "clearAudioFileCache": True,
            "writeToDisk": True
        }
        result = self.GO.call("ak.wwise.core.soundbank.generate", args)
        if result is None:
            LOG.info(lan["LOG_SM_AutoGenerateBank_FAIL"][L])
            return False
        else:
            return True

    def getSwitchGroupNamePathFromSwitchWWU(self, SwitchGroupName):
        SwitchGroupNamePath = ""
        for wwuPath in getWWUPathFromLocal(self.get_CurrentWwiseSession_SwitchesWWUPath()):
            tree = ET.parse(wwuPath)
            root = tree.getroot()

            for a in root.iter("SwitchGroup"):
                if a.attrib.get("Name") == SwitchGroupName:
                    tempPath = str(wwuPath)
                    index = tempPath.find("Switches")
                    SwitchGroupNamePath = "\\" + tempPath[index:-4] + "\\" + SwitchGroupName

        return SwitchGroupNamePath

    def type1d(self, Id, Fname, Sname, Tname, Rannum):
        NamePool = self.nameStrGen(Id, Fname, Sname, Tname, Rannum)
        SourceWAVPath = os.path.join(global_curWwisePath, KeyInfoDict["Data_KeyInfo"][Fname]["Path_Folder_TargetWAV"])
        TarActorPath = KeyInfoDict["Data_KeyInfo"][Fname]["Path_InWwise_TargetActorMixer"]
        TarEventPath = KeyInfoDict["Data_KeyInfo"][Fname]["Path_InWwise_TargetEvent"]
        ifPitchRandom = KeyInfoDict["Data_KeyInfo"][Fname]["Property_ifPitchRandom"]
        ifStream = KeyInfoDict["Data_KeyInfo"][Fname]["Property_ifStream"]

        # Create A Simple Random Container
        args = {
            "parent": TarActorPath,
            "type": "RandomSequenceContainer",
            "@RandomOrSequence": 1,
            "name": NamePool[1][1],
            "onNameConflict": "merge",
            "notes": NamePool[1][0]
        }
        self.GO.call("ak.wwise.core.object.create", args)

        # Import audio files for Random Container
        for i in range(len(NamePool[2])):
            args = {
                "importOperation": "useExisting",
                "default": {"importLanguage": "SFX"},
                "imports": [{
                    "audioFile": SourceWAVPath + NamePool[2][i] + ".wav",
                    "objectPath": TarActorPath + "\\" + NamePool[1][1] + "\\<Sound SFX>" + NamePool[2][i]
                }]
            }
            self.GO.call("ak.wwise.core.audio.import", args)
            LOG.info(lan["LOG_WG_HeadTip_DONE"][L] + str(NamePool[2][i]) + lan["LOG_WG_def_ImportWAVForContainer"][L])

            # Set Randomizer for RandomContainer
            if ifPitchRandom == "True":
                args = {
                    "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + NamePool[2][i],
                    "property": "Pitch",
                    "enabled": True,
                    "min": KeyInfoDict["InitPitchRandomMin"],
                    "max": KeyInfoDict["InitPitchRandomMax"]
                }
                result = self.GO.call("ak.wwise.core.object.setRandomizer", args)
                if result is None:
                    LOG.info(lan["LOG_SM_PitchRandom_FAIL"][L])

            # Set Loop for SFX
            if NamePool[1][1][-3:] == "_LP":
                args = {
                    "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + NamePool[2][i],
                    "property": "IsLoopingEnabled",
                    "value": "True"
                }
                self.GO.call("ak.wwise.core.object.setProperty", args)

        # Create the Event for Random Container
        args = {
            "parent": TarEventPath,
            "type": "Event",
            "name": NamePool[1][2],
            "notes": NamePool[1][0],
            "onNameConflict": "merge",
            "children": [{
                "name": "",
                "type": "Action",
                "@ActionType": 1,
                "@Target": TarActorPath + "\\" + NamePool[1][1]
            }]
        }
        self.GO.call("ak.wwise.core.object.create", args)

        # 给Loop的对象生成Stop事件
        if NamePool[1][1][-3:] == "_LP":
            args = {
                "parent": TarEventPath,
                "type": "Event",
                "name": "Stop_" + NamePool[1][1],
                "notes": NamePool[1][0] + "s",
                "onNameConflict": "merge",
                "children": [{
                    "name": "",
                    "type": "Action",
                    "@ActionType": 2,
                    "@Target": TarActorPath + "\\" + NamePool[1][1],
                    "@FadeTime": 0.5
                }]
            }
            self.GO.call("ak.wwise.core.object.create", args)

        # Set WAV Stream
        if ifStream == "True":
            for i in range(len(NamePool[2])):
                args = {
                    "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + NamePool[2][i],
                    "property": "IsStreamingEnabled",
                    "value": "true"
                }
                self.GO.call("ak.wwise.core.object.setProperty", args)

        # Save the Project
        args = {}
        self.GO.call("ak.wwise.core.project.save", args)

    def type1d_vo(self, Id, Fname, Sname, Tname, Rannum):
        NamePool = self.nameStrGen(Id, Fname, Sname, Tname, Rannum)
        TarActorPath = KeyInfoDict["Data_KeyInfo"][Fname]["Path_InWwise_TargetActorMixer"]
        TarEventPath = KeyInfoDict["Data_KeyInfo"][Fname]["Path_InWwise_TargetEvent"]
        ifPitchRandom = KeyInfoDict["Data_KeyInfo"][Fname]["Property_ifPitchRandom"]
        ifStream = KeyInfoDict["Data_KeyInfo"][Fname]["Property_ifStream"]
        global_LanFolderInfoList_refresh = list_top_level_folders_with_paths(global_voicePath)

        # Create A Simple Random Container
        args = {
            "parent": TarActorPath,
            "type": "RandomSequenceContainer",
            "@RandomOrSequence": 1,
            "name": NamePool[1][1],
            "onNameConflict": "merge",
            "notes": NamePool[1][0]
        }
        self.GO.call("ak.wwise.core.object.create", args)

        # Import audio files for Random Container
        for LangFolderinfo in global_LanFolderInfoList_refresh:
            for i in range(len(NamePool[2])):
                args = {
                    "importOperation": "useExisting",
                    "imports": [{
                        "audioFile": LangFolderinfo["folderPath"] + "\\" + NamePool[2][i] + ".wav",
                        "objectPath": TarActorPath + "\\<Random Container>" + NamePool[1][1] + "\\<Sound Voice>" + NamePool[2][i] + "\\<AudioFileSource>" + NamePool[2][i] + "_" + LangFolderinfo["folderName"],
                        "importLanguage": LangFolderinfo["folderName"]
                    }]
                }
                result = self.GO.call("ak.wwise.core.audio.import", args)
                LOG.info(lan["LOG_WG_HeadTip_DONE"][L] + str(result))

                # Set Randomizer for RandomContainer
                if ifPitchRandom == "True":
                    args = {
                        "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + NamePool[2][i],
                        "property": "Pitch",
                        "enabled": True,
                        "min": KeyInfoDict["InitPitchRandomMin"],
                        "max": KeyInfoDict["InitPitchRandomMax"]
                    }
                    result = self.GO.call("ak.wwise.core.object.setRandomizer", args)
                    if result is None:
                        LOG.info(lan["LOG_SM_PitchRandom_FAIL"][L])

                # Set Loop for SFX
                if NamePool[1][1][-3:] == "_LP":
                    args = {
                        "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + NamePool[2][i],
                        "property": "IsLoopingEnabled",
                        "value": "True"
                    }
                    self.GO.call("ak.wwise.core.object.setProperty", args)

        # Create the Event for Random Container
        args = {
            "parent": TarEventPath,
            "type": "Event",
            "name": NamePool[1][2],
            "notes": NamePool[1][0],
            "onNameConflict": "merge",
            "children": [{
                "name": "",
                "type": "Action",
                "@ActionType": 1,
                "@Target": TarActorPath + "\\" + NamePool[1][1]
            }]
        }
        self.GO.call("ak.wwise.core.object.create", args)

        # 给Loop的对象生成Stop事件
        if NamePool[1][1][-3:] == "_LP":
            args = {
                "parent": TarEventPath,
                "type": "Event",
                "name": "Stop_" + NamePool[1][1],
                "notes": NamePool[1][0] + "s",
                "onNameConflict": "merge",
                "children": [{
                    "name": "",
                    "type": "Action",
                    "@ActionType": 2,
                    "@Target": TarActorPath + "\\" + NamePool[1][1],
                    "@FadeTime": 0.5
                }]
            }
            self.GO.call("ak.wwise.core.object.create", args)

        # Set WAV Stream
        if ifStream == "True":
            for i in range(len(NamePool[2])):
                args = {
                    "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + NamePool[2][i],
                    "property": "IsStreamingEnabled",
                    "value": "true"
                }
                self.GO.call("ak.wwise.core.object.setProperty", args)

        # Save the Project
        args = {}
        self.GO.call("ak.wwise.core.project.save", args)

    def type2d(self, Id, Fname, Sname, Tname, Rannum):
        NamePool = self.nameStrGen(Id, Fname, Sname, Tname, Rannum)

        MPSwitchGroupName = KeyInfoDict["Data_KeyInfo"][Fname]["Property_SwitchGroupName_PC_NPC"]
        MPSwitchGroupPath = self.get_Path_From_SwitchGroupName(MPSwitchGroupName)
        MPSwitchList = self.getSwitchFromSwitchWWU(MPSwitchGroupName)

        SourceWAVPath = os.path.join(global_curWwisePath, KeyInfoDict["Data_KeyInfo"][Fname]["Path_Folder_TargetWAV"])
        TarActorPath = KeyInfoDict["Data_KeyInfo"][Fname]["Path_InWwise_TargetActorMixer"]
        NPCBusPath = KeyInfoDict["Data_KeyInfo"][Fname]["Property_Bus_NPC"]
        TarEventPath = KeyInfoDict["Data_KeyInfo"][Fname]["Path_InWwise_TargetEvent"]
        AttenuationPath = KeyInfoDict["Data_KeyInfo"][Fname]["Property_Positioning"]
        ifPitchRandom = KeyInfoDict["Data_KeyInfo"][Fname]["Property_ifPitchRandom"]
        ifStream = KeyInfoDict["Data_KeyInfo"][Fname]["Property_ifStream"]

        #  Create the SwitchContainer
        args = {
            "parent": TarActorPath,
            "type": "SwitchContainer",
            "name": NamePool[1][1],
            "onNameConflict": "merge",
            "notes": NamePool[1][0]
        }
        self.GO.call("ak.wwise.core.object.create", args)

        # Set the SwitchGroup Assign for the SwitchContainer
        args = {
            "object": TarActorPath + "\\" + NamePool[1][1],
            "reference": "SwitchGroupOrStateGroup",
            "value": MPSwitchGroupPath
        }
        self.GO.call("ak.wwise.core.object.setReference", args)

        # Import RandomContainer and assign switch
        for i in range(len(MPSwitchList)):
            args = {
                "importOperation": "useExisting",
                "default": {},
                "imports": [{
                    "importLanguage": "SFX",
                    "@Volume": "0",
                    "objectPath": TarActorPath + "\\<Switch Container>" + NamePool[1][1] + "\\<Random Container>" + MPSwitchList[i],
                    "switchAssignation": MPSwitchList[i]
                }]
            }
            self.GO.call("ak.wwise.core.audio.import", args)
            LOG.info(lan["LOG_WG_HeadTip_DONE"][L] + str(MPSwitchList[i]) + lan["LOG_WG_def_ImportContainerAndAssignSwitch"][L])

        # Import audio files for RandomContainer
        for j in range(len(MPSwitchList)):
            for i in range(len(NamePool[2])):
                args = {
                    "importOperation": "useExisting",
                    "default": {"importLanguage": "SFX"},
                    "imports": [{
                        "audioFile": SourceWAVPath + NamePool[2][i] + ".wav",
                        "objectPath": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[j] + "\\<Sound SFX>" + NamePool[2][i]
                    }]
                }
                self.GO.call("ak.wwise.core.audio.import", args)
                LOG.info(lan["LOG_WG_HeadTip_DONE"][L] + str(NamePool[2][i]) + lan["LOG_WG_def_ImportWAVForContainer"][L])

                # Set Randomizer for RandomContainer
                if ifPitchRandom == "True":
                    args = {
                        "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[j] + "\\" + NamePool[2][i],
                        "property": "Pitch",
                        "enabled": True,
                        "min": KeyInfoDict["InitPitchRandomMin"],
                        "max": KeyInfoDict["InitPitchRandomMax"]
                    }
                    result = self.GO.call("ak.wwise.core.object.setRandomizer", args)
                    if result is None:
                        LOG.info(lan["LOG_SM_PitchRandom_FAIL"][L])

                # Set WAV Stream
                if ifStream == "True":
                    args = {
                        "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[j] + "\\" + NamePool[2][i],
                        "property": "IsStreamingEnabled",
                        "value": "true"
                    }
                    self.GO.call("ak.wwise.core.object.setProperty", args)

                # Set Loop for SFX
                if NamePool[1][1][-3:] == "_LP":
                    args = {
                        "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[j] + "\\" + NamePool[2][i],
                        "property": "IsLoopingEnabled",
                        "value": "True"
                    }
                    self.GO.call("ak.wwise.core.object.setProperty", args)

        # Set the OverrideOutPutBus for NPC RandomContainer
        # Check Exist First
        existResult = self.get_GUIDOfPath(NPCBusPath)
        if existResult is None:
            LOG.warning(lan["LOG_WG_def_CreateBasic_ObjectNotExist"][L] + NPCBusPath)
        else:
            args = {
                "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                "property": "OverrideOutput",
                "value": "True"
            }
            self.GO.call("ak.wwise.core.object.setProperty", args)

            # Set the OutputBUS for NPC RandomContainer
            args = {
                "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                "reference": "OutputBus",
                "value": NPCBusPath
            }
            self.GO.call("ak.wwise.core.object.setReference", args)

        # Set Gen 3D Attenuation for All Parents
        if len(AttenuationPath) == 0:
            pass
        else:
            # Check Exist First
            existResult = self.get_GUIDOfPath(AttenuationPath)
            if existResult is None:
                LOG.warning(lan["LOG_WG_def_CreateBasic_ObjectNotExist"][L] + AttenuationPath)
            else:
                args = {
                    "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                    "property": "OverridePositioning",
                    "value": "True"
                }
                self.GO.call("ak.wwise.core.object.setProperty", args)

                args = {
                    "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                    "property": "3DSpatialization",
                    "value": "2"
                }
                self.GO.call("ak.wwise.core.object.setProperty", args)

                args = {
                    "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                    "reference": "Attenuation",
                    "value": AttenuationPath
                }
                self.GO.call("ak.wwise.core.object.setReference", args)

        # Create the Event for SwitchContainer
        args = {
            "parent": TarEventPath,
            "type": "Event",
            "name": NamePool[1][2],
            "notes": NamePool[1][0],
            "onNameConflict": "merge",
            "children": [{
                "name": "",
                "type": "Action",
                "@ActionType": 1,
                "@Target": TarActorPath + "\\" + NamePool[1][1]
            }]
        }
        self.GO.call("ak.wwise.core.object.create", args)

        # 给Loop的对象生成Stop事件
        if NamePool[1][1][-3:] == "_LP":
            args = {
                "parent": TarEventPath,
                "type": "Event",
                "name": "Stop_" + NamePool[1][1],
                "notes": NamePool[1][0] + "s",
                "onNameConflict": "merge",
                "children": [{
                    "name": "",
                    "type": "Action",
                    "@ActionType": 2,
                    "@Target": TarActorPath + "\\" + NamePool[1][1],
                    "@FadeTime": 0.5
                }]
            }
            self.GO.call("ak.wwise.core.object.create", args)

        # Save the Project
        args = {}
        self.GO.call("ak.wwise.core.project.save", args)

    def type2d_gun(self, Id, Fname, Sname, Tname, Rannum):
        NamePool = self.nameStrGen(Id, Fname, Sname, Tname, Rannum)

        MPSwitchGroupName = KeyInfoDict["Data_KeyInfo"][Fname]["Property_SwitchGroupName_PC_NPC"]
        MPSwitchGroupPath = self.get_Path_From_SwitchGroupName(MPSwitchGroupName)
        MPSwitchList = self.getSwitchFromSwitchWWU(MPSwitchGroupName)

        SourceWAVPath = os.path.join(global_curWwisePath, KeyInfoDict["Data_KeyInfo"][Fname]["Path_Folder_TargetWAV"])
        TarActorPath = KeyInfoDict["Data_KeyInfo"][Fname]["Path_InWwise_TargetActorMixer"]
        NPCBusPath = KeyInfoDict["Data_KeyInfo"][Fname]["Property_Bus_NPC"]
        TarEventPath = KeyInfoDict["Data_KeyInfo"][Fname]["Path_InWwise_TargetEvent"]
        AttenuationPath = KeyInfoDict["Data_KeyInfo"][Fname]["Property_Positioning"]
        ifPitchRandom = KeyInfoDict["Data_KeyInfo"][Fname]["Property_ifPitchRandom"]
        ifStream = KeyInfoDict["Data_KeyInfo"][Fname]["Property_ifStream"]

        FireName_PC = key["ValidGunLayer"]["PC"]
        FireName_NPC = key["ValidGunLayer"]["NPC"]

        # Create the Switch Container For TAIL
        args = {
            "parent": TarActorPath,
            "type": "SwitchContainer",
            "name": NamePool[1][3],
            "onNameConflict": "merge",
            "notes": NamePool[1][0]
        }
        result = self.GO.call("ak.wwise.core.object.create", args)
        SwitchContainerGUID_Tail = result.get("id", None)

        if SwitchContainerGUID_Tail is not None:
            # Set Property
            args = {
                "object": SwitchContainerGUID_Tail,
                "reference": "SwitchGroupOrStateGroup",
                "value": MPSwitchGroupPath
            }
            self.GO.call("ak.wwise.core.object.setReference", args)

            # Import Switch Container and Assign Switch
            for i in range(len(MPSwitchList)):
                args = {
                    "importOperation": "useExisting",
                    "default": {},
                    "imports": [{
                        "importLanguage": "SFX",
                        "@Volume": "0",
                        "objectPath": TarActorPath + "\\" + NamePool[1][3] + "\\<Random Container>" + MPSwitchList[i],
                        "switchAssignation": MPSwitchList[i]
                    }]
                }
                self.GO.call("ak.wwise.core.audio.import", args)

            # Set the OverrideOutPutBus for NPC RandomContainer
            args = {
                "object": TarActorPath + "\\" + NamePool[1][3] + "\\" + MPSwitchList[1],
                "property": "OverrideOutput",
                "value": "True"
            }
            self.GO.call("ak.wwise.core.object.setProperty", args)

            # Set the OutputBUS for NPC RandomContainer
            args = {
                "object": TarActorPath + "\\" + NamePool[1][3] + "\\" + MPSwitchList[1],
                "reference": "OutputBus",
                "value": NPCBusPath
            }
            self.GO.call("ak.wwise.core.object.setReference", args)

            # Set Gen 3D Attenuation for All Parents
            args = {
                "object": TarActorPath + "\\" + NamePool[1][3] + "\\" + MPSwitchList[1],
                "property": "OverridePositioning",
                "value": "True"
            }
            self.GO.call("ak.wwise.core.object.setProperty", args)

            args = {
                "object": TarActorPath + "\\" + NamePool[1][3] + "\\" + MPSwitchList[1],
                "property": "3DSpatialization",
                "value": "2"
            }
            self.GO.call("ak.wwise.core.object.setProperty", args)

            args = {
                "object": TarActorPath + "\\" + NamePool[1][3] + "\\" + MPSwitchList[1],
                "reference": "Attenuation",
                "value": AttenuationPath
            }
            self.GO.call("ak.wwise.core.object.setReference", args)

            # Import audio files for RandomContainer
            for j in range(len(MPSwitchList)):
                for i in range(len(NamePool[2]["Tail"])):
                    args = {
                        "importOperation": "useExisting",
                        "default": {"importLanguage": "SFX"},
                        "imports": [{
                            "audioFile": SourceWAVPath + NamePool[2]["Tail"][i] + ".wav",
                            "objectPath": TarActorPath + "\\" + NamePool[1][3] + "\\" + MPSwitchList[j] + "\\<Sound SFX>" + NamePool[2]["Tail"][i]
                        }]
                    }
                    self.GO.call("ak.wwise.core.audio.import", args)
                    LOG.info(
                        lan["LOG_WG_HeadTip_DONE"][L] + str(NamePool[2]["Tail"][i]) + lan["LOG_WG_def_ImportWAVForContainer"][L])

                    # Set Randomizer for RandomContainer
                    if ifPitchRandom == "True":
                        args = {
                            "object": TarActorPath + "\\" + NamePool[1][3] + "\\" + MPSwitchList[j] + "\\" + NamePool[2]["Tail"][i],
                            "property": "Pitch",
                            "enabled": True,
                            "min": KeyInfoDict["InitPitchRandomMin"],
                            "max": KeyInfoDict["InitPitchRandomMax"]
                        }
                        result = self.GO.call("ak.wwise.core.object.setRandomizer", args)
                        if result is None:
                            LOG.info(lan["LOG_SM_PitchRandom_FAIL"][L])

                    # Set WAV Stream
                    if ifStream == "True":
                        args = {
                            "object": TarActorPath + "\\" + NamePool[1][3] + "\\" + MPSwitchList[j] + "\\" + NamePool[2]["Tail"][i],
                            "property": "IsStreamingEnabled",
                            "value": "true"
                        }
                        self.GO.call("ak.wwise.core.object.setProperty", args)

        # Create a RandomContainer
        args = {
            "parent": TarActorPath,
            "type": "RandomSequenceContainer",
            "name": NamePool[1][1] + "_LP",
            "onNameConflict": "merge",
            "notes": NamePool[1][0]
        }
        result = self.GO.call("ak.wwise.core.object.create", args)
        RandomContainerGUID = result.get("id", None)

        if RandomContainerGUID is not None:
            args = {
                "object": RandomContainerGUID,
                "property": "PlayMechanismStepOrContinuous",
                "value": 0
            }
            self.GO.call("ak.wwise.core.object.setProperty", args)

            args = {
                "object": RandomContainerGUID,
                "property": "PlayMechanismLoop",
                "value": "true"
            }
            self.GO.call("ak.wwise.core.object.setProperty", args)

            args = {
                "object": RandomContainerGUID,
                "property": "PlayMechanismSpecialTransitions",
                "value": "true"
            }
            self.GO.call("ak.wwise.core.object.setProperty", args)

            args = {
                "object": RandomContainerGUID,
                "property": "PlayMechanismSpecialTransitionsType",
                "value": "3"
            }
            self.GO.call("ak.wwise.core.object.setProperty", args)

            args = {
                "object": RandomContainerGUID,
                "property": "PlayMechanismSpecialTransitionsValue",
                "value": "0.07"
            }
            self.GO.call("ak.wwise.core.object.setProperty", args)

            # Create the Switch Container A
            args = {
                "parent": RandomContainerGUID,
                "type": "SwitchContainer",
                "name": NamePool[1][1],
                "onNameConflict": "merge",
                "notes": "GAGAGA"
            }
            result = self.GO.call("ak.wwise.core.object.create", args)
            SwitchContainerGUID = result.get("id", None)

            # Create Events
            args = {
                "parent": TarEventPath,
                "type": "Event",
                "name": NamePool[1][2] + "_LP",
                "notes": NamePool[1][0],
                "onNameConflict": "merge",
                "children": [{
                    "name": "",
                    "type": "Action",
                    "@ActionType": 1,
                    "@Target": RandomContainerGUID
                }]
            }
            self.GO.call("ak.wwise.core.object.create", args)

            if SwitchContainerGUID is not None:
                # Create Events
                args = {
                    "parent": TarEventPath,
                    "type": "Event",
                    "name": NamePool[1][2],
                    "notes": NamePool[1][0],
                    "onNameConflict": "merge",
                    "children": [
                        {
                            "name": NamePool[1][2],
                            "type": "Action",
                            "@ActionType": 1,
                            "@Target": SwitchContainerGUID
                        },
                        {
                            "name": Fname + "_Tail",
                            "type": "Action",
                            "@ActionType": 1,
                            "@Target": SwitchContainerGUID_Tail
                        }
                    ]
                }
                self.GO.call("ak.wwise.core.object.create", args)

                # Set Property
                args = {
                    "object": SwitchContainerGUID,
                    "reference": "SwitchGroupOrStateGroup",
                    "value": MPSwitchGroupPath
                }
                self.GO.call("ak.wwise.core.object.setReference", args)

                # Import Switch Container and Assign Switch
                for i in range(len(MPSwitchList)):
                    args = {
                        "importOperation": "useExisting",
                        "default": {},
                        "imports": [{
                            "importLanguage": "SFX",
                            "@Volume": "0",
                            "objectPath": TarActorPath + "\\" + NamePool[1][1] + "_LP\\" + NamePool[1][1] + "\\<Blend Container>" + MPSwitchList[i],
                            "switchAssignation": MPSwitchList[i]
                        }]
                    }
                    self.GO.call("ak.wwise.core.audio.import", args)

                # Set the OverrideOutPutBus for NPC RandomContainer
                args = {
                    "object": TarActorPath + "\\" + NamePool[1][1] + "_LP\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                    "property": "OverrideOutput",
                    "value": "True"
                }
                self.GO.call("ak.wwise.core.object.setProperty", args)

                # Set the OutputBUS for NPC RandomContainer
                args = {
                    "object": TarActorPath + "\\" + NamePool[1][1] + "_LP\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                    "reference": "OutputBus",
                    "value": NPCBusPath
                }
                self.GO.call("ak.wwise.core.object.setReference", args)

                # Set Gen 3D Attenuation for All Parents
                args = {
                    "object": TarActorPath + "\\" + NamePool[1][1] + "_LP\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                    "property": "OverridePositioning",
                    "value": "True"
                }
                self.GO.call("ak.wwise.core.object.setProperty", args)

                args = {
                    "object": TarActorPath + "\\" + NamePool[1][1] + "_LP\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                    "property": "3DSpatialization",
                    "value": "2"
                }
                self.GO.call("ak.wwise.core.object.setProperty", args)

                args = {
                    "object": TarActorPath + "\\" + NamePool[1][1] + "_LP\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                    "reference": "Attenuation",
                    "value": AttenuationPath
                }
                self.GO.call("ak.wwise.core.object.setReference", args)

                args = {
                    "parent": TarEventPath,
                    "type": "Event",
                    "name": "Stop_" + NamePool[1][1] + "_LP",
                    "notes": "Stop_" + NamePool[1][1] + "_LP",
                    "onNameConflict": "merge",
                    "children": [
                        {
                            "name": "Stop_" + NamePool[1][1] + "_LP",
                            "type": "Action",
                            "@ActionType": 34,
                            "@Target": RandomContainerGUID
                        },
                        {
                            "name": NamePool[1][3],
                            "type": "Action",
                            "@ActionType": 1,
                            "@Target": SwitchContainerGUID_Tail
                        }
                    ]
                }
                self.GO.call("ak.wwise.core.object.create", args)

                # Create Random Containers
                for name in FireName_PC:
                    args = {
                        "parent": TarActorPath + "\\" + NamePool[1][1] + "_LP\\" + NamePool[1][1] + "\\" + MPSwitchList[0],
                        "type": "RandomSequenceContainer",
                        "name": name,
                        "onNameConflict": "merge",
                        "notes": ""
                    }
                    self.GO.call("ak.wwise.core.object.create", args)

                    for i in NamePool[2][name]:
                        args = {
                            "importOperation": "useExisting",
                            "default": {"importLanguage": "SFX"},
                            "imports": [{
                                "audioFile": SourceWAVPath + i + ".wav",
                                "objectPath": TarActorPath + "\\" + NamePool[1][1] + "_LP\\" + NamePool[1][1] + "\\" + MPSwitchList[0] + "\\" + name + "\\<Sound SFX>" + i
                            }]
                        }
                        self.GO.call("ak.wwise.core.audio.import", args)
                        LOG.info(lan["LOG_WG_HeadTip_DONE"][L] + str(NamePool[2][name]) + lan["LOG_WG_def_ImportWAVForContainer"][L])

                        # Set Randomizer for RandomContainer
                        if ifPitchRandom == "True":
                            args = {
                                "object": TarActorPath + "\\" + NamePool[1][1] + "_LP\\" + NamePool[1][1] + "\\" + MPSwitchList[0] + "\\" + name + "\\" + i,
                                "property": "Pitch",
                                "enabled": True,
                                "min": KeyInfoDict["InitPitchRandomMin"],
                                "max": KeyInfoDict["InitPitchRandomMax"]
                            }
                            result = self.GO.call("ak.wwise.core.object.setRandomizer", args)
                            if result is None:
                                LOG.info(lan["LOG_SM_PitchRandom_FAIL"][L])

                        # Set WAV Stream
                        if ifStream == "True":
                            args = {
                                "object": TarActorPath + "\\" + NamePool[1][1] + "_LP\\" + NamePool[1][1] + "\\" + MPSwitchList[0] + "\\" + name + "\\" + i,
                                "property": "IsStreamingEnabled",
                                "value": "true"
                            }
                            self.GO.call("ak.wwise.core.object.setProperty", args)

                for name in FireName_NPC:
                    args = {
                        "parent": TarActorPath + "\\" + NamePool[1][1] + "_LP\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                        "type": "RandomSequenceContainer",
                        "name": name,
                        "onNameConflict": "merge",
                        "notes": ""
                    }
                    self.GO.call("ak.wwise.core.object.create", args)

                    for i in NamePool[2][name]:
                        args = {
                            "importOperation": "useExisting",
                            "default": {"importLanguage": "SFX"},
                            "imports": [{
                                "audioFile": SourceWAVPath + i + ".wav",
                                "objectPath": TarActorPath + "\\" + NamePool[1][1] + "_LP\\" + NamePool[1][1] + "\\" + MPSwitchList[1] + "\\" + name + "\\<Sound SFX>" + i
                            }]
                        }
                        self.GO.call("ak.wwise.core.audio.import", args)
                        LOG.info(lan["LOG_WG_HeadTip_DONE"][L] + str(NamePool[2][name]) + lan["LOG_WG_def_ImportWAVForContainer"][L])

                        # Set Randomizer for RandomContainer
                        if ifPitchRandom == "True":
                            args = {
                                "object": TarActorPath + "\\" + NamePool[1][1] + "_LP\\" + NamePool[1][1] + "\\" + MPSwitchList[1] + "\\" + name + "\\" + i,
                                "property": "Pitch",
                                "enabled": True,
                                "min": KeyInfoDict["InitPitchRandomMin"],
                                "max": KeyInfoDict["InitPitchRandomMax"]
                            }
                            result = self.GO.call("ak.wwise.core.object.setRandomizer", args)
                            if result is None:
                                LOG.info(lan["LOG_SM_PitchRandom_FAIL"][L])

                        # Set WAV Stream
                        if ifStream == "True":
                            args = {
                                "object": TarActorPath + "\\" + NamePool[1][1] + "_LP\\" + NamePool[1][1] + "\\" + MPSwitchList[1] + "\\" + name + "\\" + i,
                                "property": "IsStreamingEnabled",
                                "value": "true"
                            }
                            self.GO.call("ak.wwise.core.object.setProperty", args)

        # Save the Project
        args = {}
        self.GO.call("ak.wwise.core.project.save", args)

    def type2d_vo(self, Id, Fname, Sname, Tname, Rannum):
        NamePool = self.nameStrGen(Id, Fname, Sname, Tname, Rannum)
        MPSwitchGroupName = KeyInfoDict["Data_KeyInfo"][Fname]["Property_SwitchGroupName_PC_NPC"]
        # MPSwitchGroupPath = self.getSwitchGroupNamePathFromSwitchWWU(MPSwitchGroupName)
        MPSwitchGroupPath = self.get_Path_From_SwitchGroupName(MPSwitchGroupName)
        MPSwitchList = self.getSwitchFromSwitchWWU(MPSwitchGroupName)

        TarActorPath = KeyInfoDict["Data_KeyInfo"][Fname]["Path_InWwise_TargetActorMixer"]
        NPCBusPath = KeyInfoDict["Data_KeyInfo"][Fname]["Property_Bus_NPC"]
        TarEventPath = KeyInfoDict["Data_KeyInfo"][Fname]["Path_InWwise_TargetEvent"]
        ifPitchRandom = KeyInfoDict["Data_KeyInfo"][Fname]["Property_ifPitchRandom"]
        ifStream = KeyInfoDict["Data_KeyInfo"][Fname]["Property_ifStream"]
        AttenuationPath = KeyInfoDict["Data_KeyInfo"][Fname]["Property_Positioning"]

        global_LanFolderInfoList_refresh = list_top_level_folders_with_paths(global_voicePath)

        #  Create the SwitchContainer
        args = {
            "parent": TarActorPath,
            "type": "SwitchContainer",
            "name": NamePool[1][1],
            "onNameConflict": "merge",
            "notes": NamePool[1][0]
        }
        self.GO.call("ak.wwise.core.object.create", args)

        # Set the SwitchGroup Assign for the SwitchContainer
        args = {
            "object": TarActorPath + "\\" + NamePool[1][1],
            "reference": "SwitchGroupOrStateGroup",
            "value": MPSwitchGroupPath
        }
        self.GO.call("ak.wwise.core.object.setReference", args)

        # Import RandomContainer and assign switch
        for i in range(len(MPSwitchList)):
            args = {
                "importOperation": "useExisting",
                "default": {},
                "imports": [{
                    "importLanguage": "SFX",
                    "@Volume": "0",
                    "objectPath": TarActorPath + "\\<Switch Container>" + NamePool[1][1] + "\\<Random Container>" + MPSwitchList[i],
                    "switchAssignation": MPSwitchList[i]
                }]
            }
            self.GO.call("ak.wwise.core.audio.import", args)
            LOG.info(lan["LOG_WG_HeadTip_DONE"][L] + str(MPSwitchList[i]) + lan["LOG_WG_def_ImportContainerAndAssignSwitch"][L])

        # Import audio files for RandomContainer
        for LangFolderinfo in global_LanFolderInfoList_refresh:
            for j in range(len(MPSwitchList)):
                for i in range(len(NamePool[2])):
                    args = {
                        "importOperation": "useExisting",
                        "imports": [{
                            "objectPath": TarActorPath + "\\" + NamePool[1][1] + "\\<Random Container>" + MPSwitchList[j] + "\\<Sound Voice>" + NamePool[2][i] + "\\<AudioFileSource>" + NamePool[2][i] + "_" + LangFolderinfo["folderName"],
                            "audioFile": LangFolderinfo["folderPath"] + "\\" + NamePool[2][i] + ".wav",
                            "importLanguage": LangFolderinfo["folderName"]
                        }]
                    }
                    self.GO.call("ak.wwise.core.audio.import", args)
                    LOG.info(lan["LOG_WG_HeadTip_DONE"][L] + str(NamePool[2][i]) + lan["LOG_WG_def_ImportWAVForContainer"][L])

                    # Set Randomizer for RandomContainer
                    if ifPitchRandom == "True":
                        args = {
                            "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[j] + "\\" + NamePool[2][i],
                            "property": "Pitch",
                            "enabled": True,
                            "min": KeyInfoDict["InitPitchRandomMin"],
                            "max": KeyInfoDict["InitPitchRandomMax"]
                        }
                        result = self.GO.call("ak.wwise.core.object.setRandomizer", args)
                        if result is None:
                            LOG.info(lan["LOG_SM_PitchRandom_FAIL"][L])

                    # Set WAV Stream
                    if ifStream == "True":
                        args = {
                            "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[j] + "\\" + NamePool[2][i],
                            "property": "IsStreamingEnabled",
                            "value": "true"
                        }
                        self.GO.call("ak.wwise.core.object.setProperty", args)

                    # Set Loop for SFX
                    if NamePool[1][1][-3:] == "_LP":
                        args = {
                            "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[j] + "\\" + NamePool[2][i],
                            "property": "IsLoopingEnabled",
                            "value": "True"
                        }
                        self.GO.call("ak.wwise.core.object.setProperty", args)

        # Set the OverrideOutPutBus for NPC RandomContainer
        # Check Exist First
        existResult = self.get_GUIDOfPath(NPCBusPath)
        if existResult is None:
            LOG.warning(lan["LOG_WG_def_CreateBasic_ObjectNotExist"][L] + NPCBusPath)
        else:
            args = {
                "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                "property": "OverrideOutput",
                "value": "True"
            }
            self.GO.call("ak.wwise.core.object.setProperty", args)

            # Set the OutputBUS for NPC RandomContainer
            args = {
                "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                "reference": "OutputBus",
                "value": NPCBusPath
            }
            self.GO.call("ak.wwise.core.object.setReference", args)

        # Set Gen 3D Attenuation for All Parents
        if len(AttenuationPath) == 0:
            pass
        else:
            # Check Exist First
            existResult = self.get_GUIDOfPath(AttenuationPath)
            if existResult is None:
                LOG.warning(lan["LOG_WG_def_CreateBasic_ObjectNotExist"][L] + AttenuationPath)
            else:
                args = {
                    "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                    "property": "OverridePositioning",
                    "value": "True"
                }
                self.GO.call("ak.wwise.core.object.setProperty", args)

                args = {
                    "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                    "property": "3DSpatialization",
                    "value": "2"
                }
                self.GO.call("ak.wwise.core.object.setProperty", args)

                args = {
                    "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                    "reference": "Attenuation",
                    "value": AttenuationPath
                }
                self.GO.call("ak.wwise.core.object.setReference", args)

        # Create the Event for SwitchContainer
        args = {
            "parent": TarEventPath,
            "type": "Event",
            "name": NamePool[1][2],
            "notes": NamePool[1][0],
            "onNameConflict": "merge",
            "children": [{
                "name": "",
                "type": "Action",
                "@ActionType": 1,
                "@Target": TarActorPath + "\\" + NamePool[1][1]
            }]
        }
        self.GO.call("ak.wwise.core.object.create", args)

        # 给Loop的对象生成Stop事件
        if NamePool[1][1][-3:] == "_LP":
            args = {
                "parent": TarEventPath,
                "type": "Event",
                "name": "Stop_" + NamePool[1][1],
                "notes": NamePool[1][0] + "s",
                "onNameConflict": "merge",
                "children": [{
                    "name": "",
                    "type": "Action",
                    "@ActionType": 2,
                    "@Target": TarActorPath + "\\" + NamePool[1][1],
                    "@FadeTime": 0.5
                }]
            }
            self.GO.call("ak.wwise.core.object.create", args)

        # Save the Project
        args = {}
        self.GO.call("ak.wwise.core.project.save", args)

    def type3d(self, Id, Fname, Sname, Tname, Rannum):
        NamePool = self.nameStrGen(Id, Fname, Sname, Tname, Rannum)

        MPSwitchGroupName = KeyInfoDict["Data_KeyInfo"][Fname]["Property_SwitchGroupName_PC_NPC"]
        # MPSwitchGroupPath = self.getSwitchGroupNamePathFromSwitchWWU(MPSwitchGroupName)
        MPSwitchGroupPath = self.get_Path_From_SwitchGroupName(MPSwitchGroupName)
        MPSwitchList = self.getSwitchFromSwitchWWU(MPSwitchGroupName)

        TextureSwitchGroupName = KeyInfoDict["Data_KeyInfo"][Fname]["Property_SwitchGroupName_Texture"]
        # TextureSwitchGroupPath = self.getSwitchGroupNamePathFromSwitchWWU(TextureSwitchGroupName)
        TextureSwitchGroupPath = self.get_Path_From_SwitchGroupName(TextureSwitchGroupName)
        TextureSwitchList = self.getSwitchFromSwitchWWU(TextureSwitchGroupName)

        SourceWAVPath = os.path.join(global_curWwisePath, KeyInfoDict["Data_KeyInfo"][Fname]["Path_Folder_TargetWAV"])
        TarActorPath = KeyInfoDict["Data_KeyInfo"][Fname]["Path_InWwise_TargetActorMixer"]
        NPCBusPath = KeyInfoDict["Data_KeyInfo"][Fname]["Property_Bus_NPC"]
        TarEventPath = KeyInfoDict["Data_KeyInfo"][Fname]["Path_InWwise_TargetEvent"]

        ifPitchRandom = KeyInfoDict["Data_KeyInfo"][Fname]["Property_ifPitchRandom"]
        ifStream = KeyInfoDict["Data_KeyInfo"][Fname]["Property_ifStream"]
        AttenuationPath = KeyInfoDict["Data_KeyInfo"][Fname]["Property_Positioning"]

        # Create the Switch Container
        args = {
            "parent": TarActorPath,
            "type": "SwitchContainer",
            "name": NamePool[1][1],
            "onNameConflict": "merge",
            "notes": NamePool[1][0]
        }
        self.GO.call("ak.wwise.core.object.create", args)

        # Set the SwitchGroup Assign for the SwitchContainer
        args = {
            "object": TarActorPath + "\\" + NamePool[1][1],
            "reference": "SwitchGroupOrStateGroup",
            "value": MPSwitchGroupPath
        }
        self.GO.call("ak.wwise.core.object.setReference", args)

        # Import Switch Container and Assign Switch
        for i in range(len(MPSwitchList)):
            args = {
                "importOperation": "useExisting",
                "default": {},
                "imports": [{
                    "importLanguage": "SFX",
                    "@Volume": "0",
                    "objectPath": TarActorPath + "\\<Switch Container>" + NamePool[1][1] + "\\<Switch Container>" + MPSwitchList[i],
                    "switchAssignation": MPSwitchList[i]
                }]
            }
            self.GO.call("ak.wwise.core.audio.import", args)
            LOG.info(lan["LOG_WG_HeadTip_DONE"][L] + str(MPSwitchList[i]) + lan["LOG_WG_def_ImportAndAssignSwitch"][L])

        # Set the SwitchGroup Assign for the 2nd Layer SwitchContainer
        for i in range(len(MPSwitchList)):
            args = {
                "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[i],
                "reference": "SwitchGroupOrStateGroup",
                "value": TextureSwitchGroupPath
            }
            self.GO.call("ak.wwise.core.object.setReference", args)
            LOG.info(lan["LOG_WG_HeadTip_DONE"][L] + str(MPSwitchList[i]) + lan["LOG_WG_def_SetSwitchGroup"][L])

        # Import RandomContainer and Assign Switch
        for j in range(len(MPSwitchList)):
            for i in range(len(TextureSwitchList)):
                args = {
                    "importOperation": "useExisting",
                    "default": {},
                    "imports": [{
                        "importLanguage": "SFX",
                        "@Volume": "0",
                        "objectPath": TarActorPath + "\\<Switch Container>" + NamePool[1][1] + "\\<Switch Container>" +
                                      MPSwitchList[j] + "\\<Random Container>" + TextureSwitchList[i],
                        "switchAssignation": TextureSwitchList[i]
                    }]
                }
                self.GO.call("ak.wwise.core.audio.import", args)
                LOG.info(lan["LOG_WG_HeadTip_DONE"][L] + str(TextureSwitchList[i]) +
                      lan["LOG_WG_def_ImportContainerAndAssignSwitch"][L])

        # Import WAV for RandomContainer
        for k in range(len(MPSwitchList)):
            for j in range(len(TextureSwitchList)):
                for i in range(len(NamePool[2][j])):
                    args = {
                        "importOperation": "useExisting",
                        "default": {"importLanguage": "SFX"},
                        "imports": [{
                            "audioFile": SourceWAVPath + NamePool[2][j][i] + ".wav",
                            "objectPath": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[k] + "\\" +
                                          TextureSwitchList[j] + "\\<Sound SFX>" + NamePool[2][j][i]
                        }]
                    }
                    self.GO.call("ak.wwise.core.audio.import", args)
                    LOG.info(lan["LOG_WG_HeadTip_DONE"][L] + str(NamePool[2][j][i]) +
                          lan["LOG_WG_def_ImportWAVForContainer"][L])

                    # Set Randomizer for SFX
                    try:
                        if ifPitchRandom == "True":
                            args = {
                                "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[k] + "\\" +
                                          TextureSwitchList[j] + "\\" + NamePool[2][j][i],
                                "property": "Pitch",
                                "enabled": True,
                                "min": KeyInfoDict["InitPitchRandomMin"],
                                "max": KeyInfoDict["InitPitchRandomMax"]
                            }
                            result = self.GO.call("ak.wwise.core.object.setRandomizer", args)
                            if result is None:
                                LOG.info(lan["LOG_SM_PitchRandom_FAIL"][L])
                    except:
                        LOG.error(lan["LOG_SM_PitchRandom_FAIL"][L])

                    # Set WAV Stream
                    if ifStream == "True":
                        args = {
                            "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[k] + "\\" +
                                      TextureSwitchList[j] + "\\" + NamePool[2][j][i],
                            "property": "IsStreamingEnabled",
                            "value": "true"
                        }
                        self.GO.call("ak.wwise.core.object.setProperty", args)

                    # Set Loop for SFX
                    if NamePool[1][1][-3:] == "_LP":
                        args = {
                            "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[k] + "\\" +
                                      TextureSwitchList[j] + "\\" + NamePool[2][j][i],
                            "property": "IsLoopingEnabled",
                            "value": "True"
                        }
                        self.GO.call("ak.wwise.core.object.setProperty", args)

        # Set the OverrideOutPutBus for NPC RandomContainer
        # Check Exist First
        existResult = self.get_GUIDOfPath(NPCBusPath)
        if existResult is None:
            LOG.warning(lan["LOG_WG_def_CreateBasic_ObjectNotExist"][L] + NPCBusPath)
        else:
            args = {
                "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                "property": "OverrideOutput",
                "value": "True"
            }
            self.GO.call("ak.wwise.core.object.setProperty", args)

            # Set the OutputBUS for NPC RandomContainer
            args = {
                "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                "reference": "OutputBus",
                "value": NPCBusPath
            }
            self.GO.call("ak.wwise.core.object.setReference", args)

        # Set Gen 3D Attenuation for All Parents
        if len(AttenuationPath) == 0:
            pass
        else:
            # Check Exist First
            existResult = self.get_GUIDOfPath(AttenuationPath)
            if existResult is None:
                LOG.warning(lan["LOG_WG_def_CreateBasic_ObjectNotExist"][L] + AttenuationPath)
            else:
                args = {
                    "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                    "property": "OverridePositioning",
                    "value": "True"
                }
                self.GO.call("ak.wwise.core.object.setProperty", args)

                args = {
                    "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                    "property": "3DSpatialization",
                    "value": "2"
                }
                self.GO.call("ak.wwise.core.object.setProperty", args)

                args = {
                    "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + MPSwitchList[1],
                    "reference": "Attenuation",
                    "value": AttenuationPath
                }
                self.GO.call("ak.wwise.core.object.setReference", args)

        # Create Event for SwitchContainer
        args = {
            "parent": TarEventPath,
            "type": "Event",
            "name": NamePool[1][2],
            "notes": NamePool[1][0],
            "onNameConflict": "merge",
            "children": [{
                "name": "",
                "type": "Action",
                "@ActionType": 1,
                "@Target": TarActorPath + "\\" + NamePool[1][1]
            }]
        }
        self.GO.call("ak.wwise.core.object.create", args)

        # 给Loop的对象生成Stop事件
        if NamePool[1][1][-3:] == "_LP":
            args = {
                "parent": TarEventPath,
                "type": "Event",
                "name": "Stop_" + NamePool[1][1],
                "notes": NamePool[1][0] + "s",
                "onNameConflict": "merge",
                "children": [{
                    "name": "",
                    "type": "Action",
                    "@ActionType": 2,
                    "@Target": TarActorPath + "\\" + NamePool[1][1],
                    "@FadeTime": 0.5
                }]
            }
            self.GO.call("ak.wwise.core.object.create", args)

        # Save the Project
        args = {}
        self.GO.call("ak.wwise.core.project.save", args)

    def typet(self, Id, Fname, Sname, Tname, Rannum):
        NamePool = self.nameStrGen(Id, Fname, Sname, Tname, Rannum)
        SourceWAVPath = os.path.join(global_curWwisePath, KeyInfoDict["Data_KeyInfo"][Fname]["Path_Folder_TargetWAV"])
        TarActorPath = KeyInfoDict["Data_KeyInfo"][Fname]["Path_InWwise_TargetActorMixer"]
        TarEventPath = KeyInfoDict["Data_KeyInfo"][Fname]["Path_InWwise_TargetEvent"]
        TemplatePath = KeyInfoDict["Data_KeyInfo"][Fname]["Path_InWwise_UserDefinedTemplate"]
        TemplateName = os.path.basename(TemplatePath)

        ifPitchRandom = KeyInfoDict["Data_KeyInfo"][Fname]["Property_ifPitchRandom"]
        ifStream = KeyInfoDict["Data_KeyInfo"][Fname]["Property_ifStream"]
        AttenuationPath = KeyInfoDict["Data_KeyInfo"][Fname]["Property_Positioning"]

        # 先检查模板路径是否存在, 如果不存在，直接结束进程并打印报告！
        existcheck = self.GetWWUPath(TemplatePath)
        if existcheck is None:
            LOG.warning(lan["LOG_WG_def_typet_TemplateNotExist"][L])
        else:
            # 检查模板内部结构！通过后再进行执行！
            PathResults = self.FilterValidContainerPaths(TemplatePath)

            # 判断PathResults[1]是否为空（包含禁用对象）, 如果不为空，结束进程并打印报告
            if len(PathResults[1]) != 0:
                LOG.warning(lan["LOG_WG_def_typet_FoundForbiddenObj"][L])
            else:
                # 判断PathResults[0]是否为空，空的话，说明该模板是一个单一容器
                if len(PathResults[0]) == 0:
                    # Copy A Template
                    args = {
                        "object": TemplatePath,
                        "parent": TarActorPath,
                        "onNameConflict": "rename"
                    }
                    self.GO.call("ak.wwise.core.object.copy", args)

                    # Rename the Template
                    args = {
                        "object": TarActorPath + "\\" + TemplateName,
                        "value": NamePool[1][1]
                    }
                    self.GO.call("ak.wwise.core.object.setName", args)

                    # Add Note for the new Container
                    args = {
                        "object": TarActorPath + "\\" + NamePool[1][1],
                        "value": NamePool[1][0]
                    }
                    self.GO.call("ak.wwise.core.object.setNotes", args)

                    # Import audio files for Random Container
                    for i in range(len(NamePool[2])):
                        args = {
                            "importOperation": "useExisting",
                            "default": {"importLanguage": "SFX"},
                            "imports": [{
                                "audioFile": SourceWAVPath + NamePool[2][i] + ".wav",
                                "objectPath": TarActorPath + "\\" + NamePool[1][1] + "\\<Sound SFX>" + NamePool[2][i]
                            }]
                        }
                        self.GO.call("ak.wwise.core.audio.import", args)
                        LOG.info(lan["LOG_WG_HeadTip_DONE"][L] + str(NamePool[2][i]) +
                              lan["LOG_WG_def_ImportWAVIntoUserDefinedContainer"][L])

                        # Set Loop for SFX
                        if NamePool[1][1][-3:] == "_LP":
                            args = {
                                "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + NamePool[2][i],
                                "property": "IsLoopingEnabled",
                                "value": "True"
                            }
                            self.GO.call("ak.wwise.core.object.setProperty", args)

                    # Set WAV Stream
                    if ifStream == "True":
                        for i in range(len(NamePool[2])):
                            args = {
                                "object": TarActorPath + "\\" + NamePool[1][1] + "\\" + NamePool[2][i],
                                "property": "IsStreamingEnabled",
                                "value": "true"
                            }
                            self.GO.call("ak.wwise.core.object.setProperty", args)

                    # Create the Event for Random Container
                    args = {
                        "parent": TarEventPath,
                        "type": "Event",
                        "name": NamePool[1][2],
                        "notes": NamePool[1][0],
                        "onNameConflict": "merge",
                        "children": [{
                            "name": "",
                            "type": "Action",
                            "@ActionType": 1,
                            "@Target": TarActorPath + "\\" + NamePool[1][1]
                        }]
                    }
                    self.GO.call("ak.wwise.core.object.create", args)

                    # 给Loop的对象生成Stop事件
                    if NamePool[1][1][-3:] == "_LP":
                        args = {
                            "parent": TarEventPath,
                            "type": "Event",
                            "name": "Stop_" + NamePool[1][1],
                            "notes": NamePool[1][0] + "s",
                            "onNameConflict": "merge",
                            "children": [{
                                "name": "",
                                "type": "Action",
                                "@ActionType": 2,
                                "@Target": TarActorPath + "\\" + NamePool[1][1],
                                "@FadeTime": 0.5
                            }]
                        }
                        self.GO.call("ak.wwise.core.object.create", args)

                    # Save the Project
                    args = {}
                    self.GO.call("ak.wwise.core.project.save", args)

                    # LOG.debug("单一容器模板")
                else:
                    # PathResults[0]不为空，说明该模板有其下属子容器

                    # 把旧的模板路径置换成新的目标路径
                    NewPaths = PathResults[0]
                    for x, y in enumerate(NewPaths):
                        NewPaths[x] = y.replace(TemplatePath, TarActorPath + "\\" + NamePool[1][1])

                    # Copy A Template
                    args = {
                        "object": TemplatePath,
                        "parent": TarActorPath,
                        "onNameConflict": "rename"
                    }
                    self.GO.call("ak.wwise.core.object.copy", args)

                    # Rename the Template
                    args = {
                        "object": TarActorPath + "\\" + TemplateName,
                        "value": NamePool[1][1]
                    }
                    self.GO.call("ak.wwise.core.object.setName", args)

                    # Add Note for the new Container
                    args = {
                        "object": TarActorPath + "\\" + NamePool[1][1],
                        "value": NamePool[1][0]
                    }
                    self.GO.call("ak.wwise.core.object.setNotes", args)

                    # LOG.debug(NewPaths)
                    # LOG.debug(NamePool[2])

                    # Import audio files for RandomContainer
                    for j in range(len(NewPaths)):
                        for i in range(len(NamePool[2][j])):
                            args = {
                                "importOperation": "useExisting",
                                "default": {"importLanguage": "SFX"},
                                "imports": [{
                                    "audioFile": SourceWAVPath + "\\" + NamePool[2][j][i] + ".wav",
                                    "objectPath": NewPaths[j] + "\\<Sound SFX>" + NamePool[2][j][i]
                                }]
                            }
                            self.GO.call("ak.wwise.core.audio.import", args)
                            LOG.info(lan["LOG_WG_HeadTip_DONE"][L] + str(NamePool[2][j][i]) +
                                  lan["LOG_WG_def_ImportWAVForContainer"][L])

                            # Set Randomizer for RandomContainer
                            if ifPitchRandom == "True":
                                args = {
                                    "object": NewPaths[j] + "\\" + NamePool[2][j][i],
                                    "property": "Pitch",
                                    "enabled": True,
                                    "min": KeyInfoDict["InitPitchRandomMin"],
                                    "max": KeyInfoDict["InitPitchRandomMax"]
                                }
                                result = self.GO.call("ak.wwise.core.object.setRandomizer", args)
                                if result is None:
                                    LOG.info(lan["LOG_SM_PitchRandom_FAIL"][L])

                            # Set WAV Stream
                            if ifStream == "True":
                                args = {
                                    "object": NewPaths[j] + "\\" + NamePool[2][j][i],
                                    "property": "IsStreamingEnabled",
                                    "value": "true"
                                }
                                self.GO.call("ak.wwise.core.object.setProperty", args)

                            # Set Loop for SFX
                            if NamePool[1][1][-3:] == "_LP":
                                args = {
                                    "object": NewPaths[j] + "\\" + NamePool[2][j][i],
                                    "property": "IsLoopingEnabled",
                                    "value": "True"
                                }
                                self.GO.call("ak.wwise.core.object.setProperty", args)

                    # Create the Event for Random Container
                    args = {
                        "parent": TarEventPath,
                        "type": "Event",
                        "name": NamePool[1][2],
                        "notes": NamePool[1][0],
                        "onNameConflict": "merge",
                        "children": [{
                            "name": "",
                            "type": "Action",
                            "@ActionType": 1,
                            "@Target": TarActorPath + "\\" + NamePool[1][1]
                        }]
                    }
                    self.GO.call("ak.wwise.core.object.create", args)

                    # 给Loop的对象生成Stop事件
                    if NamePool[1][1][-3:] == "_LP":
                        args = {
                            "parent": TarEventPath,
                            "type": "Event",
                            "name": "Stop_" + NamePool[1][1],
                            "notes": NamePool[1][0] + "s",
                            "onNameConflict": "merge",
                            "children": [{
                                "name": "",
                                "type": "Action",
                                "@ActionType": 2,
                                "@Target": TarActorPath + "\\" + NamePool[1][1],
                                "@FadeTime": 0.5
                            }]
                        }
                        self.GO.call("ak.wwise.core.object.create", args)

                    # Save the Project
                    args = {}
                    self.GO.call("ak.wwise.core.project.save", args)

    def CreateCleanBasic_AllInOnce(self):
        LOG.info(lan["LOG_WG_def_CreateBasic_Start"][L])

        currentKeyStrList = list(KeyInfoDict["Data_KeyInfo"].keys())
        KeyDict = KeyInfoDict["Data_KeyInfo"]

        # Create WWUs
        for i in currentKeyStrList:
            args = {
                "parent": "\\Actor-Mixer Hierarchy",
                "type": "WorkUnit",
                "name": "Audio_" + i,
                "onNameConflict": "merge",
                "notes": ""
            }
            self.GO.call("ak.wwise.core.object.create", args)

            args = {
                "parent": "\\Events",
                "type": "WorkUnit",
                "name": "Event_" + i,
                "onNameConflict": "merge",
                "notes": ""
            }
            self.GO.call("ak.wwise.core.object.create", args)

            args = {
                "parent": "\\SoundBanks",
                "type": "WorkUnit",
                "name": "Bank_" + i,
                "onNameConflict": "merge",
                "notes": ""
            }
            self.GO.call("ak.wwise.core.object.create", args)
        LOG.info(lan["LOG_WG_def_CreateBasic_CreateWWUs"][L])

        # Create Actor-Mixer
        for i in currentKeyStrList:
            if i == "Music":
                ContainerType = "MusicSwitchContainer"
            else:
                ContainerType = "ActorMixer"

            args = {
                "parent": "\\Actor-Mixer Hierarchy" + "\\Audio_" + i,
                "type": ContainerType,
                "name": i,
                "onNameConflict": "merge",
                "notes": ""
            }
            self.GO.call("ak.wwise.core.object.create", args)
        LOG.info(lan["LOG_WG_def_CreateBasic_CreateActor-Mixers"][L])

        # Set BUS
        for i in currentKeyStrList:
            if len(KeyDict[i]["Property_Bus"]) != 0:
                args = {
                    "object": KeyDict[i]["Path_InWwise_TargetActorMixer"],
                    "reference": "OutputBus",
                    "value": KeyDict[i]["Property_Bus"]
                }
                self.GO.call("ak.wwise.core.object.setReference", args)
        LOG.info(lan["LOG_WG_def_CreateBasic_SetBuses"][L])

        if KeyInfoDict["$ProjectStr$"] in KeyInfoDict["Projects_SimpleBankName"]:
            # Create SoundBank
            for i in currentKeyStrList:
                args = {
                    "parent": "\\SoundBanks\\Bank_" + i,
                    "type": "SoundBank",
                    "name": i,
                    "onNameConflict": "merge",
                    "notes": ""
                }
                self.GO.call("ak.wwise.core.object.create", args)
            LOG.info(lan["LOG_WG_def_CreateBasic_CreateSoundBanks"][L])

            # Add Event WWU into SoundBank
            for i in currentKeyStrList:
                args = {
                    "soundbank": "\\SoundBanks\\Bank_" + i + "\\" + i,
                    "operation": "add",
                    "inclusions": [
                        {
                            "object": "\\Events" + "\\Event_" + i,
                            "filter": [
                                "events",
                                "structures",
                                "media"
                            ]
                        }
                    ]
                }
                self.GO.call("ak.wwise.core.soundbank.setInclusions", args)
            LOG.info(lan["LOG_WG_def_CreateBasic_AssignSoundBanks"][L])
        else:
            # Create SoundBank
            for i in currentKeyStrList:
                args = {
                    "parent": "\\SoundBanks\\Bank_" + i,
                    "type": "SoundBank",
                    "name": "Bank_" + i,
                    "onNameConflict": "merge",
                    "notes": ""
                }
                self.GO.call("ak.wwise.core.object.create", args)
            LOG.info(lan["LOG_WG_def_CreateBasic_CreateSoundBanks"][L])

            # Add Event WWU into SoundBank
            for i in currentKeyStrList:
                args = {
                    "soundbank": "\\SoundBanks\\Bank_" + i + "\\Bank_" + i,
                    "operation": "add",
                    "inclusions": [
                        {
                            "object": "\\Events" + "\\Event_" + i,
                            "filter": [
                                "events",
                                "structures",
                                "media"
                            ]
                        }
                    ]
                }
                self.GO.call("ak.wwise.core.soundbank.setInclusions", args)
            LOG.info(lan["LOG_WG_def_CreateBasic_AssignSoundBanks"][L])

        # Set InitConversion for All Parents
        for i in currentKeyStrList:
            if len(KeyDict[i]["Property_Conversion"]) == 0:
                pass
            else:
                args = {
                    "object": "\\Actor-Mixer Hierarchy\\Audio_" + i + "\\" + i,
                    "reference": "Conversion",
                    "value": KeyDict[i]["Property_Conversion"]
                }
                self.GO.call("ak.wwise.core.object.setReference", args)
        LOG.info(lan["LOG_WG_def_SetInitConversion"][L])

        # Set Gen 3D Attenuation for All Parents
        for i in currentKeyStrList:
            if KeyDict[i]["Structure_Type"] not in ["type2d", "type3d", "type2d_vo"]:  # 这三类的主ActorMixer上不可以设置衰减，衰减需要安排在必要的子分支上
                if len(KeyDict[i]["Property_Positioning"]) == 0:
                    pass
                else:
                    args = {
                        "object": "\\Actor-Mixer Hierarchy\\Audio_" + i + "\\" + i,
                        "property": "3DSpatialization",
                        "value": "2"
                    }
                    self.GO.call("ak.wwise.core.object.setProperty", args)

                    args = {
                        "object": "\\Actor-Mixer Hierarchy\\Audio_" + i + "\\" + i,
                        "reference": "Attenuation",
                        "value": KeyDict[i]["Property_Positioning"]
                    }
                    self.GO.call("ak.wwise.core.object.setReference", args)
        LOG.info(lan["LOG_WG_def_SetGenAttenforParents"][L])

        args = {}
        self.GO.call("ak.wwise.core.project.save", args)

        LOG.info("-----------------------------------------------------------------------------")
        LOG.info(lan["LOG_WG_def_WWISESessionCreated"][L])

    def CreateCleanBasic_ForTargetKeyStr(self, keyStr):  # 要补充对每一个路径是否实际存在的安全检查
        LOG.info(lan["LOG_WG_def_CreateBasic_Start"][L])

        i = keyStr
        KeyDict = KeyInfoDict["Data_KeyInfo"][keyStr]

        # Create WWUs
        args = {
            "parent": "\\Actor-Mixer Hierarchy",
            "type": "WorkUnit",
            "name": "Audio_" + i,
            "onNameConflict": "merge",
            "notes": ""
        }
        self.GO.call("ak.wwise.core.object.create", args)

        args = {
            "parent": "\\Events",
            "type": "WorkUnit",
            "name": "Event_" + i,
            "onNameConflict": "merge",
            "notes": ""
        }
        self.GO.call("ak.wwise.core.object.create", args)

        args = {
            "parent": "\\SoundBanks",
            "type": "WorkUnit",
            "name": "Bank_" + i,
            "onNameConflict": "merge",
            "notes": ""
        }
        self.GO.call("ak.wwise.core.object.create", args)
        LOG.info(lan["LOG_WG_def_CreateBasic_CreateWWUs"][L])

        # Create Actor-Mixer
        if i == "Music":
            ContainerType = "MusicSwitchContainer"
        else:
            ContainerType = "ActorMixer"

        args = {
            "parent": "\\Actor-Mixer Hierarchy" + "\\Audio_" + i,
            "type": ContainerType,
            "name": i,
            "onNameConflict": "merge",
            "notes": ""
        }
        self.GO.call("ak.wwise.core.object.create", args)
        LOG.info(lan["LOG_WG_def_CreateBasic_CreateActor-Mixers"][L])

        # Set BUS
        if len(KeyDict["Property_Bus"]) != 0:
            # Check Exist First
            existResult = self.get_GUIDOfPath(KeyDict["Property_Bus"])
            if existResult is None:
                LOG.info(lan["LOG_WG_def_CreateBasic_ObjectNotExist"][L] + KeyDict["Property_Bus"])
            else:
                args = {
                    "object": KeyDict["Path_InWwise_TargetActorMixer"],
                    "reference": "OutputBus",
                    "value": KeyDict["Property_Bus"]
                }
                self.GO.call("ak.wwise.core.object.setReference", args)
                LOG.info(lan["LOG_WG_def_CreateBasic_SetBuses"][L])

        if KeyInfoDict["$ProjectStr$"] in KeyInfoDict["Projects_SimpleBankName"]:
            # Create SoundBank
            args = {
                "parent": "\\SoundBanks\\Bank_" + i,
                "type": "SoundBank",
                "name": i,
                "onNameConflict": "merge",
                "notes": ""
            }
            self.GO.call("ak.wwise.core.object.create", args)
            LOG.info(lan["LOG_WG_def_CreateBasic_CreateSoundBanks"][L])

            # Add Event WWU into SoundBank
            args = {
                "soundbank": "\\SoundBanks\\Bank_" + i + "\\" + i,
                "operation": "add",
                "inclusions": [
                    {
                        "object": "\\Events" + "\\Event_" + i,
                        "filter": [
                            "events",
                            "structures",
                            "media"
                        ]
                    }
                ]
            }
            self.GO.call("ak.wwise.core.soundbank.setInclusions", args)
            LOG.info(lan["LOG_WG_def_CreateBasic_AssignSoundBanks"][L])
        else:
            # Create SoundBank
            args = {
                "parent": "\\SoundBanks\\Bank_" + i,
                "type": "SoundBank",
                "name": "Bank_" + i,
                "onNameConflict": "merge",
                "notes": ""
            }
            self.GO.call("ak.wwise.core.object.create", args)
            LOG.info(lan["LOG_WG_def_CreateBasic_CreateSoundBanks"][L])

            # Add Event WWU into SoundBank
            args = {
                "soundbank": "\\SoundBanks\\Bank_" + i + "\\Bank_" + i,
                "operation": "add",
                "inclusions": [
                    {
                        "object": "\\Events" + "\\Event_" + i,
                        "filter": [
                            "events",
                            "structures",
                            "media"
                        ]
                    }
                ]
            }
            self.GO.call("ak.wwise.core.soundbank.setInclusions", args)
            LOG.info(lan["LOG_WG_def_CreateBasic_AssignSoundBanks"][L])

        # Set InitConversion for All Parents
        if len(KeyDict["Property_Conversion"]) == 0:
            pass
        else:
            # Check Exist First
            existResult = self.get_GUIDOfPath(KeyDict["Property_Conversion"])
            if existResult is None:
                LOG.warning(lan["LOG_WG_def_CreateBasic_ObjectNotExist"][L] + KeyDict["Property_Conversion"])
            else:
                args = {
                    "object": "\\Actor-Mixer Hierarchy\\Audio_" + i + "\\" + i,
                    "reference": "Conversion",
                    "value": KeyDict["Property_Conversion"]
                }
                self.GO.call("ak.wwise.core.object.setReference", args)
                LOG.info(lan["LOG_WG_def_SetInitConversion"][L])

        # Set Gen 3D Attenuation for All Parents
        if KeyDict["Structure_Type"] not in ["type2d", "type3d", "type2d_vo", "type2d_gun"]:  # 这三类的主ActorMixer上不可以设置衰减，衰减需要安排在必要的子分支上
            if len(KeyDict["Property_Positioning"]) == 0:
                pass
            else:
                # Check Exist First
                existResult = self.get_GUIDOfPath(KeyDict["Property_Positioning"])
                if existResult is None:
                    LOG.warning(lan["LOG_WG_def_CreateBasic_ObjectNotExist"][L] + KeyDict["Property_Positioning"])
                else:
                    args = {
                        "object": "\\Actor-Mixer Hierarchy\\Audio_" + i + "\\" + i,
                        "property": "3DSpatialization",
                        "value": "2"
                    }
                    self.GO.call("ak.wwise.core.object.setProperty", args)

                    args = {
                        "object": "\\Actor-Mixer Hierarchy\\Audio_" + i + "\\" + i,
                        "reference": "Attenuation",
                        "value": KeyDict["Property_Positioning"]
                    }
                    self.GO.call("ak.wwise.core.object.setReference", args)
                    LOG.info(lan["LOG_WG_def_SetGenAttenforParents"][L])

        args = {}
        self.GO.call("ak.wwise.core.project.save", args)

        LOG.info("-----------------------------------------------------------------------------")
        LOG.info(lan["LOG_WG_def_WWISESessionCreated"][L])

    def CreateBus_From_DictStructure(self):
        WaapiStatus = ""
        # 创建基础BUS："SFX", "Music", "VO", "CG"
        RootBus = ["SFX", "Music", "VO", "CG"]
        for i in range(len(RootBus)):
            args = {
                "parent": "\\Master-Mixer Hierarchy\\Default Work Unit\\Master Audio Bus",
                "type": "Bus",
                "name": RootBus[i],
                "onNameConflict": "merge",
                "notes": "",
            }
            result = self.GO.call("ak.wwise.core.object.create", args)
            LOG.debug("[写入结果-BUS] --> " + str(RootBus[i]))
            LOG.debug(result)

            # Waapi Status检查
            if result is None:
                WaapiStatus = "False"

        # SFX --> Action:PC/NPC BUS
        args = {
            "parent": "\\Master-Mixer Hierarchy\\Default Work Unit\\Master Audio Bus\\SFX",
            "type": "Bus",
            "name": "Action",
            "onNameConflict": "merge",
            "notes": "",
            "children": [
                {
                    "type": "Bus",
                    "name": "PC",
                    "notes": ""
                },
                {
                    "type": "Bus",
                    "name": "NPC",
                    "notes": ""
                }
            ]
        }
        result = self.GO.call("ak.wwise.core.object.create", args)
        LOG.debug("[写入结果-BUS] --> " + "PC/NPC BUS")
        LOG.debug(result)

        # Waapi Status检查
        if result is None:
            WaapiStatus = "False"

        # SFX --> Amb BUS
        args = {
            "parent": "\\Master-Mixer Hierarchy\\Default Work Unit\\Master Audio Bus\\SFX",
            "type": "Bus",
            "name": "Amb",
            "onNameConflict": "merge",
            "notes": "",
        }
        result = self.GO.call("ak.wwise.core.object.create", args)
        LOG.debug("[写入结果-BUS] --> " + "Amb BUS")
        LOG.debug(result)

        # Waapi Status检查
        if result is None:
            WaapiStatus = "False"

        # SFX --> UI BUS
        args = {
            "parent": "\\Master-Mixer Hierarchy\\Default Work Unit\\Master Audio Bus\\SFX",
            "type": "Bus",
            "name": "UI",
            "onNameConflict": "merge",
            "notes": "",
        }
        result = self.GO.call("ak.wwise.core.object.create", args)
        LOG.debug("[写入结果-BUS] --> " + "UI BUS")
        LOG.debug(result)

        # Waapi Status检查
        if result is None:
            WaapiStatus = "False"

        return WaapiStatus

    def WriteIntoWwise_FromJson(self):
        WaapiStatusDict = {
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
            "Init_Template": ""
        }
        # 设置ProjectSettings -------------------------------------------------------------------------
        args = {
            "from": {
                "ofType": ["Project"]
            },
            "options": {
                "return": ["id"]
            }
        }
        ProjectGUID = self.GO.call("ak.wwise.core.object.get", args)

        ProjectSettingItemList = KeyInfoDict["Init_ProjectSettings"]
        for keey, vaalue in zip(ProjectSettingItemList.keys(), ProjectSettingItemList.values()):
            if vaalue == "True":
                value = "true"
            else:
                value = "false"
            args = {
                "object": ProjectGUID["return"][0]["id"],
                "property": keey,
                "value": value
            }
            result = self.GO.call("ak.wwise.core.object.setProperty", args)
            LOG.debug("[写入结果-ProjectSettings] --> " + str(keey))
            LOG.debug(result)

            # 检查并写入WaapiStatus状态标记
            if result is None:
                WaapiStatusDict["Init_ProjectSettings"] = "False"

        LOG.info(lan["LOG_WG_def_CreateBasic_ProjectSettingItemList"][L])

        # 创建Bus -------------------------------------------------------------------------
        # 先判断Wwise工程中是否已存在自定义Bus，如果没有，再写入
        currentBusList = self.get_Paths_of_Descendants("BUS")
        if len(currentBusList) == 1 and currentBusList[0] == "\\Master-Mixer Hierarchy\\Default Work Unit\\Master Audio Bus":
            waapiStatusResult = self.CreateBus_From_DictStructure()

            # 检查并写入WaapiStatus状态标记
            if waapiStatusResult == "False":
                WaapiStatusDict["Init_BUS"] = "False"

            LOG.info(lan["LOG_WG_def_CreateBasic_CreateBuses"][L])
        else:
            LOG.warning(lan["LOG_WG_def_CreateBasic_CreateBuses_Cancel"][L])
            LOG.warning(lan["LOG_WG_def_CreateBasic_CreateBuses"][L])

        # Create Switches -------------------------------------------------------------------------
        for switchGroupName, switchList in zip(KeyInfoDict["Init_Switch"].keys(), KeyInfoDict["Init_Switch"].values()):
            possiblePath = self.get_Path_From_SwitchGroupName(switchGroupName)
            if possiblePath is not None and len(possiblePath) != 0:  # 说明Wwise里有
                LOG.warning(lan["LOG_WG_def_CreateBasic_ExistObject"][L] + switchGroupName)
            else:
                for switch in switchList:
                    args = {
                        "parent": "\\Switches\\Default Work Unit",
                        "type": "SwitchGroup",
                        "name": switchGroupName,
                        "onNameConflict": "merge",
                        "notes": "",
                        "children": [{
                            "type": "Switch",
                            "name": switch,
                            "notes": ""
                        }]
                    }
                    result = self.GO.call("ak.wwise.core.object.create", args)
                    LOG.debug("[写入结果-Switch] --> " + str(switchGroupName) + " --> " + str(switch))
                    LOG.debug(result)

                    # 检查并写入WaapiStatus状态标记
                    if result is None:
                        WaapiStatusDict["Init_Switch"] = "False"

        LOG.info(lan["LOG_WG_def_CreateBasic_CreateSwitches"][L])

        # Create States -------------------------------------------------------------------------
        for stateGroupName, stateList in zip(KeyInfoDict["Init_State"].keys(), KeyInfoDict["Init_State"].values()):
            possiblePath = self.get_Path_From_StateGroupName(stateGroupName)
            if possiblePath is not None and len(possiblePath) != 0:  # 说明Wwise里有
                LOG.warning(lan["LOG_WG_def_CreateBasic_ExistObject"][L] + stateGroupName)
            else:
                for state in stateList:
                    args = {
                        "parent": "\\States\\Default Work Unit",
                        "type": "StateGroup",
                        "name": stateGroupName,
                        "onNameConflict": "merge",
                        "notes": "",
                        "children": [{
                            "type": "State",
                            "name": state,
                            "notes": ""
                        }]
                    }
                    result = self.GO.call("ak.wwise.core.object.create", args)
                    LOG.debug("[写入结果-State] --> " + str(stateGroupName) + " --> " + str(state))
                    LOG.debug(result)

                    # 检查并写入WaapiStatus状态标记
                    if result is None:
                        WaapiStatusDict["Init_State"] = "False"

        LOG.info(lan["LOG_WG_def_CreateBasic_CreateStates"][L])

        # Create RTPCs -------------------------------------------------------------------------
        for RTPCName, RTPCValueDict in zip(KeyInfoDict["Init_RTPC"].keys(), KeyInfoDict["Init_RTPC"].values()):
            possiblePath = self.get_Path_From_UniqueNameStr("GameParameter", RTPCName)
            if possiblePath is not None and len(possiblePath) != 0:  # 说明Wwise里有
                LOG.warning(lan["LOG_WG_def_CreateBasic_ExistObject"][L] + RTPCName)
            else:
                args = {
                    "parent": "\\Game Parameters\\Default Work Unit",
                    "type": "GameParameter",
                    "name": RTPCName,
                    "onNameConflict": "merge",
                    "notes": "",
                }
                result = self.GO.call("ak.wwise.core.object.create", args)
                LOG.debug("[写入结果-RTPC] --> " + str(RTPCName))
                LOG.debug(result)

                # 检查并写入WaapiStatus状态标记
                if result is None:
                    WaapiStatusDict["Init_RTPC"] = "False"

                args = {
                    "object": "\\Game Parameters\\Default Work Unit" + "\\" + RTPCName,
                    "property": "Min",
                    "value": RTPCValueDict["Min"]
                }
                result = self.GO.call("ak.wwise.core.object.setProperty", args)
                LOG.debug("[写入结果-RTPC Value] --> " + str(RTPCValueDict["Min"]))
                LOG.debug(result)

                # 检查并写入WaapiStatus状态标记
                if result is None:
                    WaapiStatusDict["Init_RTPC_Value"] = "False"

                args = {
                    "object": "\\Game Parameters\\Default Work Unit" + "\\" + RTPCName,
                    "property": "Max",
                    "value": RTPCValueDict["Max"]
                }
                result = self.GO.call("ak.wwise.core.object.setProperty", args)
                LOG.debug("[写入结果-RTPC Value] --> " + str(RTPCValueDict["Max"]))
                LOG.debug(result)

                # 检查并写入WaapiStatus状态标记
                if result is None:
                    WaapiStatusDict["Init_RTPC_Value"] = "False"

                args = {
                    "object": "\\Game Parameters\\Default Work Unit" + "\\" + RTPCName,
                    "property": "InitialValue",
                    "value": RTPCValueDict["InitialValue"]
                }
                result = self.GO.call("ak.wwise.core.object.setProperty", args)
                LOG.debug("[写入结果-RTPC Value] --> " + str(RTPCValueDict["InitialValue"]))
                LOG.debug(result)

                # 检查并写入WaapiStatus状态标记
                if result is None:
                    WaapiStatusDict["Init_RTPC_Value"] = "False"

        LOG.info(lan["LOG_WG_def_CreateBasic_CreateRTPCs"][L])

        if ifWwiseVersionIsHigherThan2022() is True:
            # Set RTPC to BUS
            AllRTPCObjectRefNames = getAllRTPCObjectRefNamesFromBUSWWU()
            if "RTPC_Volume_Master" in AllRTPCObjectRefNames:
                LOG.warning(lan["LOG_WG_def_CreateBasic_ExistRTPCRef"][L] + "RTPC_Volume_Master")
            else:
                args = {
                    "objects": [
                        {
                            "object": "\\Master-Mixer Hierarchy\\Default Work Unit\\Master Audio Bus",
                            "@RTPC": [
                                {
                                    "type": "RTPC",
                                    "name": "",
                                    "@Curve": {
                                        "type": "Curve",
                                        "points": [
                                            {
                                                "x": 0.0,
                                                "y": -200,
                                                "shape": "Linear"

                                            },
                                            {
                                                "x": 100,
                                                "y": 0,
                                                "shape": "Linear"

                                            }
                                        ]
                                    },
                                    "notes": "",
                                    "@PropertyName": "OutputBusVolume",
                                    "@ControlInput": "\\Game Parameters\\Default Work Unit\\RTPC_Volume_Master"
                                }
                            ]
                        }
                    ],
                    "onNameConflict": "merge"
                }
                self.GO.call("ak.wwise.core.object.set", args)
                LOG.info(lan["LOG_WG_def_SetRTPCToBUS"][L])

            if "RTPC_Volume_Music" in AllRTPCObjectRefNames:
                LOG.warning(lan["LOG_WG_def_CreateBasic_ExistRTPCRef"][L] + "RTPC_Volume_Music")
            else:
                args = {
                    "objects": [
                        {
                            "object": "\\Master-Mixer Hierarchy\\Default Work Unit\\Master Audio Bus\\Music",
                            "@RTPC": [
                                {
                                    "type": "RTPC",
                                    "name": "",
                                    "@Curve": {
                                        "type": "Curve",
                                        "points": [
                                            {
                                                "x": 0.0,
                                                "y": -200,
                                                "shape": "Linear"

                                            },
                                            {
                                                "x": 100,
                                                "y": 0,
                                                "shape": "Linear"

                                            }
                                        ]
                                    },
                                    "notes": "",
                                    "@PropertyName": "OutputBusVolume",
                                    "@ControlInput": "\\Game Parameters\\Default Work Unit\\RTPC_Volume_Music"
                                }
                            ]
                        }
                    ],
                    "onNameConflict": "merge"
                }
                self.GO.call("ak.wwise.core.object.set", args)
                LOG.info(lan["LOG_WG_def_SetRTPCToBUS"][L])

            if "RTPC_Volume_SFX" in AllRTPCObjectRefNames:
                LOG.warning(lan["LOG_WG_def_CreateBasic_ExistRTPCRef"][L] + "RTPC_Volume_SFX")
            else:
                args = {
                    "objects": [
                        {
                            "object": "\\Master-Mixer Hierarchy\\Default Work Unit\\Master Audio Bus\\SFX",
                            "@RTPC": [
                                {
                                    "type": "RTPC",
                                    "name": "",
                                    "@Curve": {
                                        "type": "Curve",
                                        "points": [
                                            {
                                                "x": 0.0,
                                                "y": -200,
                                                "shape": "Linear"

                                            },
                                            {
                                                "x": 100,
                                                "y": 0,
                                                "shape": "Linear"

                                            }
                                        ]
                                    },
                                    "notes": "",
                                    "@PropertyName": "OutputBusVolume",
                                    "@ControlInput": "\\Game Parameters\\Default Work Unit\\RTPC_Volume_SFX"
                                }
                            ]
                        }
                    ],
                    "onNameConflict": "merge"
                }
                self.GO.call("ak.wwise.core.object.set", args)
                LOG.info(lan["LOG_WG_def_SetRTPCToBUS"][L])

            if "RTPC_Volume_VO" in AllRTPCObjectRefNames:
                LOG.warning(lan["LOG_WG_def_CreateBasic_ExistRTPCRef"][L] + "RTPC_Volume_VO")
            else:
                args = {
                    "objects": [
                        {
                            "object": "\\Master-Mixer Hierarchy\\Default Work Unit\\Master Audio Bus\\VO",
                            "@RTPC": [
                                {
                                    "type": "RTPC",
                                    "name": "",
                                    "@Curve": {
                                        "type": "Curve",
                                        "points": [
                                            {
                                                "x": 0.0,
                                                "y": -200,
                                                "shape": "Linear"

                                            },
                                            {
                                                "x": 100,
                                                "y": 0,
                                                "shape": "Linear"

                                            }
                                        ]
                                    },
                                    "notes": "",
                                    "@PropertyName": "OutputBusVolume",
                                    "@ControlInput": "\\Game Parameters\\Default Work Unit\\RTPC_Volume_VO"
                                }
                            ]
                        }
                    ],
                    "onNameConflict": "merge"
                }
                self.GO.call("ak.wwise.core.object.set", args)
                LOG.info(lan["LOG_WG_def_SetRTPCToBUS"][L])
        else:
            # WaapiStatusDict["Init_RTPC_Value"] = "False"
            LOG.warning(lan["LOG_WG_def_CreateBasic_WwiseVersionIsLowerThan2022"][L])

        # 创建Conversion -------------------------------------------------------------------------
        for ConvName in KeyInfoDict["Init_Conversion"]["Conversions"]:
            possiblePath = self.get_Path_From_UniqueNameStr("Conversion", ConvName)
            if possiblePath is not None and len(possiblePath) != 0:  # 说明Wwise里有
                LOG.warning(lan["LOG_WG_def_CreateBasic_ExistObject"][L] + ConvName)
            else:
                args = {
                    "parent": "\\Conversion Settings\\Default Work Unit",
                    "type": "Conversion",
                    "name": ConvName,
                    "onNameConflict": "merge",
                    "notes": "",
                }
                result = self.GO.call("ak.wwise.core.object.create", args)
                LOG.debug("[写入结果-Conversion] --> " + str(ConvName))
                LOG.debug(result)

                # 检查并写入WaapiStatus状态标记
                if result is None:
                    WaapiStatusDict["Init_Conversion"] = "False"

        LOG.info(lan["LOG_WG_def_CreateBasic_CreateConversion"][L])

        # 创建基础Attenuation -------------------------------------------------------------------------
        for AttName, AttValueDict in zip(KeyInfoDict["Init_Attenuation"].keys(), KeyInfoDict["Init_Attenuation"].values()):
            possiblePath = self.get_Path_From_UniqueNameStr("Attenuation", AttName)
            if possiblePath is not None and len(possiblePath) != 0:  # 说明Wwise里有
                LOG.warning(lan["LOG_WG_def_CreateBasic_ExistObject"][L] + AttName)
            else:
                args = {
                    "parent": "\\Attenuations\\Default Work Unit",
                    "type": "Attenuation",
                    "name": AttName,
                    "onNameConflict": "merge",
                    "notes": "",
                }
                result = self.GO.call("ak.wwise.core.object.create", args)
                LOG.debug("[写入结果-Attenuation] --> " + str(AttName))
                LOG.debug(result)

                # 检查并写入WaapiStatus状态标记
                if result is None:
                    WaapiStatusDict["Init_Attenuation"] = "False"

                LOG.info(lan["LOG_WG_def_CreateBasic_CreateGenAttenuation"][L])

                # Set Init value for Gen Attenuation
                args = {
                    "object": "\\Attenuations\\Default Work Unit\\" + AttName,
                    "property": "RadiusMax",
                    "value": str(AttValueDict["RadiusMax"])
                }
                result = self.GO.call("ak.wwise.core.object.setProperty", args)
                LOG.debug("[写入结果-Attenuation Value] --> " + str(AttValueDict["RadiusMax"]))
                LOG.debug(result)

                # 检查并写入WaapiStatus状态标记
                if result is None:
                    WaapiStatusDict["Init_Attenuation_Value"] = "False"

                args = {
                    "object": "\\Attenuations\\Default Work Unit\\" + AttName,
                    "curveType": "VolumeDryUsage",
                    "use": "Custom",
                    "points": [
                        {
                            "x": 0,
                            "y": 0,
                            "shape": "SCurve"
                        },
                        {
                            "x": int(AttValueDict["RadiusMax"]),
                            "y": -200,
                            "shape": "SCurve"
                        }
                    ]
                }
                result = self.GO.call("ak.wwise.core.object.setAttenuationCurve", args)
                LOG.debug("[写入结果-Attenuation Value] --> VolumeDryUsage")
                LOG.debug(result)

                # 检查并写入WaapiStatus状态标记
                if result is None:
                    WaapiStatusDict["Init_Attenuation_Value"] = "False"

                args = {
                    "object": "\\Attenuations\\Default Work Unit\\" + AttName,
                    "curveType": "SpreadUsage",
                    "use": "Custom",
                    "points": [
                        {
                            "x": 0,
                            "y": 100,
                            "shape": "SCurve"
                        },
                        {
                            "x": int(AttValueDict["RadiusMax"]),
                            "y": 0,
                            "shape": "SCurve"
                        }
                    ]
                }
                result = self.GO.call("ak.wwise.core.object.setAttenuationCurve", args)
                LOG.debug("[写入结果-Attenuation Value] --> SpreadUsage")
                LOG.debug(result)

                # 检查并写入WaapiStatus状态标记
                if result is None:
                    WaapiStatusDict["Init_Attenuation_Value"] = "False"

                args = {
                    "object": "\\Attenuations\\Default Work Unit\\" + AttName,
                    "curveType": "HighPassFilterUsage",
                    "use": "Custom",
                    "points": [
                        {
                            "x": 0,
                            "y": 0,
                            "shape": "SCurve"
                        },
                        {
                            "x": int(AttValueDict["RadiusMax"]),
                            "y": 100,
                            "shape": "SCurve"
                        }
                    ]
                }
                result = self.GO.call("ak.wwise.core.object.setAttenuationCurve", args)
                LOG.debug("[写入结果-Attenuation Value] --> HighPassFilterUsage")
                LOG.debug(result)

                # 检查并写入WaapiStatus状态标记
                if result is None:
                    WaapiStatusDict["Init_Attenuation_Value"] = "False"

            LOG.info(lan["LOG_WG_def_SetGenAttenuation"][L])

        # Create SideChain -------------------------------------------------------------------------
        if ifWwiseVersionIsHigherThan2022() is not True:
            WaapiStatusDict["Init_SideChain"] = "False"
            LOG.warning(lan["LOG_WG_def_CreateBasic_WwiseVersionIsLowerThan2022_CanNotSetPlgin"][L])
        else:
            for SCName, SCValueDict in zip(KeyInfoDict["Init_SideChain"].keys(), KeyInfoDict["Init_SideChain"].values()):
                possiblePath = self.get_Path_From_UniqueNameStr("Effect", SCName)
                if possiblePath is not None and len(possiblePath) != 0:  # 说明Wwise里有
                    LOG.warning(lan["LOG_WG_def_CreateBasic_ExistObject"][L] + SCName)
                else:
                    args = {
                        "objects": [
                            {
                                "object": "\\Effects\\Default Work Unit",
                                "onNameConflict": "merge",
                                "children": [
                                    {
                                        "type": "Effect",
                                        "name": SCName,
                                        "classId": 8454147,
                                        "@AttackTime": float(SCValueDict["AttackTime"]),
                                        "@ReleaseTime": float(SCValueDict["ReleaseTime"])
                                    }
                                ]
                            }
                        ]
                    }
                    result = self.GO.call("ak.wwise.core.object.set", args)
                    LOG.debug("[写入结果-SideChain] --> " + str(SCName))
                    LOG.debug(result)

                    # 检查并写入WaapiStatus状态标记
                    if result is None:
                        WaapiStatusDict["Init_SideChain"] = "False"

        LOG.info(lan["LOG_WG_def_CreateBasic_CreateMeter"][L])

        # 创建模板路径
        resetPath = "\\Actor-Mixer Hierarchy\\Default Work Unit\\UserDefinedTemplate"
        result = self.get_GUIDOfPath(resetPath)
        if result is not None and len(result) != 0:
            LOG.info(lan["LOG_WG_def_CreateBasic_ExistObject"][L] + resetPath)
            LOG.info(lan["LOG_WG_def_CreateBasic_UserDefinedTemplate"][L])
        else:
            args = {
                "parent": "\\Actor-Mixer Hierarchy\\Default Work Unit",
                "type": "ActorMixer",
                "name": "UserDefinedTemplate",
                "onNameConflict": "merge",
                "notes": ""
            }
            result = self.GO.call("ak.wwise.core.object.create", args)
            LOG.debug("[写入结果-Template] --> UserDefinedTemplate")
            LOG.debug(result)

            # 检查并写入WaapiStatus状态标记
            if result is None:
                WaapiStatusDict["Init_Template"] = "False"

            LOG.info(lan["LOG_WG_def_CreateBasic_UserDefinedTemplate"][L])

        # Save the Project
        args = {}
        self.GO.call("ak.wwise.core.project.save", args)
        LOG.info(lan["LOG_WG_def_WWISESessionCreated"][L])

        # 立即将WaapiStatusDict写入KeyInfoDict
        KeyInfoDict["WaapiStatusDict_Write"] = WaapiStatusDict
        SaveJson(KeyInfoDict, global_curWwiseBaseJson)

        return WaapiStatusDict

    def CheckDiff_SessionStructure(self):
        # 先扫描、统计当前工程里的对象，和base.json中预设的做对比 --------------------------------------------------------------
        diffCount = {
            "Result_ProjectSettings": {
                "compareResult": "",
                "WaapiStatus": "",
                "currentInfo": {},
                "jsonInfo": {},
                "diffInfo": {}
            },
            "Result_Bus": {
                "compareResult": "",
                "WaapiStatus": "",
                "currentInfo": [],
                "jsonInfo": [],
                "diffInfo": []
            },
            "Result_Switch": {
                "compareResult": "",
                "WaapiStatus": "",
                "currentInfo": {},
                "jsonInfo": {},
                "diffInfo": {}
            },
            "Result_State": {
                "compareResult": "",
                "WaapiStatus": "",
                "currentInfo": {},
                "jsonInfo": {},
                "diffInfo": {}
            },
            "Result_RTPC": {
                "compareResult": "",
                "WaapiStatus": "",
                "currentInfo": {},
                "jsonInfo": {},
                "diffInfo": {}
            },
            "Result_RTPC_Value": {
                "compareResult": "",
                "WaapiStatus": "",
                "currentInfo": {},
                "jsonInfo": {},
                "diffInfo": {}
            },
            "Result_SideChain": {
                "compareResult": "",
                "WaapiStatus": "",
                "currentInfo": {},
                "jsonInfo": {},
                "diffInfo": {}
            },
            "Result_Conversion": {
                "compareResult": "",
                "WaapiStatus": "",
                "currentInfo": [],
                "jsonInfo": [],
                "diffInfo": []
            },
            "Result_Attenuation": {
                "compareResult": "",
                "WaapiStatus": "",
                "currentInfo": {},
                "jsonInfo": {},
                "diffInfo": {}
            },
            "Result_Attenuation_Value": {
                "compareResult": "",
                "WaapiStatus": "",
                "currentInfo": {},
                "jsonInfo": {},
                "diffInfo": {}
            }
        }

        # 获取当前工程ID -------------------------------------------------------------------------------------------
        args = {
            "from": {
                "ofType": ["Project"]
            },
            "options": {
                "return": ["id"]
            }
        }
        ProjectGUID = self.GO.call("ak.wwise.core.object.get", args)
        LOG.debug("[工程ID查询结果]" + str(ProjectGUID))
        ProjectGUID = ProjectGUID["return"][0]["id"]

        # 获取当前ProjectSettings信息，和json中的预设做对比，记录差异 -------------------------------------------------------
        Init_ProjectSettings = KeyInfoDict["Init_ProjectSettings"]
        NoneValueCount = 0
        objLenCount = len(Init_ProjectSettings)
        for keyy, valueee in zip(Init_ProjectSettings.keys(), Init_ProjectSettings.values()):
            args = {
                "from": {
                    "id": [ProjectGUID]
                },
                "options": {
                    "return": [keyy]
                }
            }
            result = self.GO.call("ak.wwise.core.object.get", args)
            LOG.debug("[ProjectSettings对象查询结果] --> " + str(keyy) + " --> " + str(result))

            if result is not None:
                # 如果获取到的值全部为空，说明Waapi不支持，打标签；如果获取值正常，则进行正常记录
                currentValueInWwise = str(result["return"][0].get(keyy, "@#$"))
                if currentValueInWwise == "@#$":
                    NoneValueCount += 1
                else:
                    diffCount["Result_ProjectSettings"]["currentInfo"][keyy] = currentValueInWwise
                    if valueee != currentValueInWwise:
                        diffCount["Result_ProjectSettings"]["compareResult"] = "False"
            else:
                diffCount["Result_ProjectSettings"]["WaapiStatus"] = "False"

        # 查看NoneValueCount情况，判断Waapi支持状态
        if diffCount["Result_ProjectSettings"]["WaapiStatus"] == "False" or NoneValueCount == objLenCount:  # 说明取值均失败，Waapi不支持获取该对象的信息
            diffCount["Result_ProjectSettings"]["WaapiStatus"] = "False"
        else:
            # Init_ProjectSettings可以直接用wwise实际值覆盖json (如果前面因为版本过低原因，全部都没获取到值，这里就不覆盖，否则就正常覆盖。)
            KeyInfoDict["Init_ProjectSettings"] = diffCount["Result_ProjectSettings"]["currentInfo"]

        # # 比照得出diffInfo差异记录
        # if Init_ProjectSettings != diffCount["Result_ProjectSettings"]["currentInfo"]:
        #     diffResultDict = find_differences_between_SingleKeyValuePairDict(Init_ProjectSettings, diffCount["Result_ProjectSettings"]["currentInfo"])
        #     diffCount["Result_ProjectSettings"]["diffInfo"] = diffResultDict

        # 将KeyInfoDict的最终值，同步记录到diffCount中
        diffCount["Result_ProjectSettings"]["jsonInfo"] = Init_ProjectSettings

        # 获取当前BUS信息，和json中的预设做对比，记录差异 ---------------------------------------------------------------------
        currentBusList_From_Wwise = self.get_Paths_of_Descendants("BUS")
        currentBusList_From_Json = Get_WwiseBus_From_Json(KeyInfoDict["Init_BUS"])
        diffCount["Result_Bus"]["jsonInfo"] = currentBusList_From_Json

        try:
            # 立即确认Waapi支持状态
            if len(currentBusList_From_Wwise) != 0:
                # 比照得出diffInfo差异记录
                if currentBusList_From_Json != currentBusList_From_Wwise:
                    difference_list = list(set(currentBusList_From_Wwise) ^ set(currentBusList_From_Json))
                    diffCount["Result_Bus"]["compareResult"] = "False"
                    diffCount["Result_Bus"]["diffInfo"] = difference_list

                # 正常记录当前实际数据
                diffCount["Result_Bus"]["currentInfo"] = currentBusList_From_Wwise
            else:
                diffCount["Result_Bus"]["WaapiStatus"] = "False"
        except:
            diffCount["Result_Bus"]["WaapiStatus"] = "False"

        # 获取当前Switch信息，转换为json ----------------------------------------------------------------------------------
        # 扫描Wwise工程，获取当前实际的数据组
        currentSwitchGroupPathList_From_Wwise = self.get_Paths_of_Descendants("SWITCH")
        CurrentSwitchInfo_From_Wwise = {}
        LOG.debug("[Switch查询结果]: ")
        LOG.debug(currentSwitchGroupPathList_From_Wwise)

        try:
            # 立即确认Waapi支持状态
            if len(currentSwitchGroupPathList_From_Wwise) != 0:
                invalidWaapiCount = 0
                SwitchPathCount = len(currentSwitchGroupPathList_From_Wwise)
                for switchGroupPath in currentSwitchGroupPathList_From_Wwise:
                    resultList = self.get_Paths_of_Children_ForSwitchGroup(switchGroupPath)
                    LOG.debug("获取到的Switch对象List：")
                    LOG.debug(resultList)
                    SwitchGroupName = os.path.basename(switchGroupPath)
                    switchList = []
                    if resultList is not None:
                        for switchPath in resultList:
                            switchList.append(os.path.basename(switchPath))
                        CurrentSwitchInfo_From_Wwise[SwitchGroupName] = switchList
                    else:
                        invalidWaapiCount += 1
                        CurrentSwitchInfo_From_Wwise[SwitchGroupName] = ["@A", "@B"]

                # 以json为参考系。如果Wwise里有了，就用wwise的覆盖json的预设值，待后续重新加载GUI显示
                json_SwitchGroupList = list(KeyInfoDict["Init_Switch"].keys())
                for SGName in json_SwitchGroupList:
                    if CurrentSwitchInfo_From_Wwise.get(SGName, "@#$") != "@#$":  # 说明Wwise里有
                        if CurrentSwitchInfo_From_Wwise[SGName] != ["@A", "@B"]:  # 确保不要让莫须有的内容覆盖掉正常内容
                            KeyInfoDict["Init_Switch"][SGName] = CurrentSwitchInfo_From_Wwise[SGName]

                # 以Wwise为参考系。如果json中没有，就添加到json中，待后续重新加载GUI显示
                wwise_SwitchGroupList = list(CurrentSwitchInfo_From_Wwise.keys())
                for SGName in wwise_SwitchGroupList:
                    if KeyInfoDict["Init_Switch"].get(SGName, "@#$") == "@#$":  # 说明Json里没
                        if CurrentSwitchInfo_From_Wwise[SGName] != ["@A", "@B"]:  # 确保不要让莫须有的内容覆盖掉正常内容
                            KeyInfoDict["Init_Switch"][SGName] = CurrentSwitchInfo_From_Wwise[SGName]

                # 比照得出diffInfo差异记录
                if CurrentSwitchInfo_From_Wwise != KeyInfoDict["Init_Switch"]:
                    # diffResultDict = Diff_Dict_For_KeyListPair(CurrentSwitchInfo_From_Wwise, KeyInfoDict["Init_Switch"])
                    diffCount["Result_Switch"]["compareResult"] = "False"
                    diffCount["Result_Switch"]["currentInfo"] = CurrentSwitchInfo_From_Wwise
                    # diffCount["Result_Switch"]["diffInfo"] = diffResultDict
                    # LOG.debug(CurrentSwitchInfo_From_Wwise)

                # 将KeyInfoDict的最终值，同步记录到diffCount中
                diffCount["Result_Switch"]["jsonInfo"] = KeyInfoDict["Init_Switch"]

                # 判断WaapiStatus，如果状态不对，打标记
                if invalidWaapiCount == SwitchPathCount:
                    diffCount["Result_Switch"]["WaapiStatus"] = "False"
            else:
                # 将KeyInfoDict的最终值，同步记录到diffCount中
                diffCount["Result_Switch"]["jsonInfo"] = KeyInfoDict["Init_Switch"]
        except:
            diffCount["Result_Switch"]["WaapiStatus"] = "False"

        # 获取当前State信息，转换为json ----------------------------------------------------------------------------------
        # 扫描Wwise工程，获取当前实际的数据组
        currentStateGroupPathList_From_Wwise = self.get_Paths_of_Descendants("STATE")
        CurrentStateInfo_From_Wwise = {}
        LOG.debug("[State查询结果]: ")
        LOG.debug(currentStateGroupPathList_From_Wwise)

        try:
            # 立即确认Waapi支持状态
            if len(currentStateGroupPathList_From_Wwise) != 0:
                invalidWaapiCount = 0
                StatePathCount = len(currentStateGroupPathList_From_Wwise)
                for stateGroupPath in currentStateGroupPathList_From_Wwise:
                    resultList = self.get_Paths_of_Children_ForStateGroup(stateGroupPath)
                    LOG.debug("获取到的State对象List：")
                    LOG.debug(resultList)
                    StateGroupName = os.path.basename(stateGroupPath)
                    stateList = []
                    if resultList is not None:
                        for statePath in resultList:
                            state = os.path.basename(statePath)
                            if state != "None":
                                stateList.append(state)
                        CurrentStateInfo_From_Wwise[StateGroupName] = stateList
                    else:
                        invalidWaapiCount += 1
                        CurrentStateInfo_From_Wwise[StateGroupName] = ["@A", "@B"]

                # 以json为参考系。如果Wwise里有了，就用wwise的覆盖json的预设值，待后续重新加载GUI显示
                json_StateGroupList = list(KeyInfoDict["Init_State"].keys())
                for SGName in json_StateGroupList:
                    if CurrentStateInfo_From_Wwise.get(SGName, "@#$") != "@#$":  # 说明Wwise里有
                        if CurrentStateInfo_From_Wwise[SGName] != ["@A", "@B"]:
                            KeyInfoDict["Init_State"][SGName] = CurrentStateInfo_From_Wwise[SGName]

                # 以Wwise为参考系。如果json中没有，就添加到json中，待后续重新加载GUI显示
                wwise_StateGroupList = list(CurrentStateInfo_From_Wwise.keys())
                for SGName in wwise_StateGroupList:
                    if KeyInfoDict["Init_State"].get(SGName, "@#$") == "@#$":  # 说明Json里没
                        if CurrentStateInfo_From_Wwise[SGName] != ["@A", "@B"]:
                            KeyInfoDict["Init_State"][SGName] = CurrentStateInfo_From_Wwise[SGName]

                # 比照得出diffInfo差异记录
                if CurrentStateInfo_From_Wwise != KeyInfoDict["Init_State"]:
                    # diffResultDict = Diff_Dict_For_KeyListPair(CurrentStateInfo_From_Wwise, KeyInfoDict["Init_State"])
                    diffCount["Result_State"]["compareResult"] = "False"
                    diffCount["Result_State"]["currentInfo"] = CurrentStateInfo_From_Wwise
                    # diffCount["Result_State"]["diffInfo"] = diffResultDict

                # 将KeyInfoDict的最终值，同步记录到diffCount中
                diffCount["Result_State"]["jsonInfo"] = KeyInfoDict["Init_State"]

                # 判断WaapiStatus，如果状态不对，打标记
                if invalidWaapiCount == StatePathCount:
                    diffCount["Result_State"]["WaapiStatus"] = "False"
            else:
                # 将KeyInfoDict的最终值，同步记录到diffCount中
                diffCount["Result_State"]["jsonInfo"] = KeyInfoDict["Init_State"]
        except:
            diffCount["Result_State"]["WaapiStatus"] = "False"

        # 获取当前RTPC信息，转换为json ----------------------------------------------------------------------------------
        # 扫描Wwise工程，获取当前实际的数据组
        currentRTPCPathList_From_Wwise = self.get_Paths_of_Descendants("RTPC")
        currentRTPCDict = {}
        LOG.debug("[RTPC查询结果]: ")
        LOG.debug(currentRTPCPathList_From_Wwise)

        try:
            if len(currentRTPCPathList_From_Wwise) != 0:
                invalidWaapiCount = 0
                rtpcPathCount = len(currentRTPCPathList_From_Wwise)
                for RTPCPath in currentRTPCPathList_From_Wwise:
                    rtpcValueDictResult = self.get_Value_of_RTPC(RTPCPath)
                    LOG.debug("获取到的RTPC属性Dict：")
                    LOG.debug(rtpcValueDictResult)
                    rtpcName = os.path.basename(RTPCPath)
                    # 立即查询WaapiStatus
                    if rtpcValueDictResult is not None:
                        currentRTPCDict[rtpcName] = rtpcValueDictResult
                    else:
                        # 添加Waapi不支持标记
                        invalidWaapiCount += 1
                        currentRTPCDict[rtpcName] = {
                            "Min": "@0",
                            "Max": "@1",
                            "InitialValue": "@1"
                        }

                # 以json为参考系。如果Wwise里有了，就用wwise的覆盖json的预设值，待后续重新加载GUI显示
                json_RTPCList = list(KeyInfoDict["Init_RTPC"].keys())
                for RTPCName in json_RTPCList:
                    if currentRTPCDict.get(RTPCName, "@#$") != "@#$":  # 说明Wwise里有
                        if currentRTPCDict[RTPCName] != {
                            "Min": "@0",
                            "Max": "@1",
                            "InitialValue": "@1"
                        }:
                            KeyInfoDict["Init_RTPC"][RTPCName] = currentRTPCDict[RTPCName]

                # 以Wwise为参考系。如果json中没有，就添加到json中，待后续重新加载GUI显示
                wwise_RTPCList = list(currentRTPCDict.keys())
                for RTPCName in wwise_RTPCList:
                    if KeyInfoDict["Init_RTPC"].get(RTPCName, "@#$") == "@#$":  # 说明Json里没
                        if currentRTPCDict[RTPCName] != {
                            "Min": "@0",
                            "Max": "@1",
                            "InitialValue": "@1"
                        }:
                            KeyInfoDict["Init_RTPC"][RTPCName] = currentRTPCDict[RTPCName]

                # 比照得出diffInfo差异记录
                if currentRTPCDict != KeyInfoDict["Init_RTPC"]:
                    # diffResultDict = Diff_Dict_For_KeySubkeyValuePair(currentRTPCDict, KeyInfoDict["Init_RTPC"])
                    diffCount["Result_RTPC"]["compareResult"] = "False"
                    diffCount["Result_RTPC"]["currentInfo"] = currentRTPCDict
                    # diffCount["Result_RTPC"]["diffInfo"] = diffResultDict

                # 将KeyInfoDict的最终值，同步记录到diffCount中
                diffCount["Result_RTPC"]["jsonInfo"] = KeyInfoDict["Init_RTPC"]

                # 判断WaapiStatus，如果状态不对，打标记
                if invalidWaapiCount == rtpcPathCount:
                    diffCount["Result_RTPC_Value"]["WaapiStatus"] = "False"
            else:
                # 将KeyInfoDict的最终值，同步记录到diffCount中
                diffCount["Result_RTPC"]["jsonInfo"] = KeyInfoDict["Init_RTPC"]
        except:
            diffCount["Result_RTPC"]["WaapiStatus"] = "False"

        # 获取当前SideChain信息，转换为json -----------------------------------------------------------------------------
        # 扫描Wwise工程，获取当前实际的数据组
        currentSideChainPathList_From_Wwise = self.get_Paths_of_Descendants("SIDECHAIN")
        currentSideChainDict = {}
        LOG.debug("[SIDECHAIN查询结果]: ")
        LOG.debug(currentSideChainPathList_From_Wwise)

        try:
            if len(currentSideChainPathList_From_Wwise) != 0:  # 这里2019不支持查询SIDECHAIN
                invalidWaapiCount = 0
                SIDECHAINPathCount = len(currentSideChainPathList_From_Wwise)
                for SCPath in currentSideChainPathList_From_Wwise:
                    scValueDictResult = self.get_value_of_WwiseMeter(SCPath)
                    LOG.debug("获取到的SIDECHAIN属性Dict：")
                    LOG.debug(scValueDictResult)
                    scName = os.path.basename(SCPath)
                    if scValueDictResult is not None:
                        currentSideChainDict[scName] = scValueDictResult
                    else:
                        invalidWaapiCount += 1
                        currentSideChainDict[scName] = {
                            "RTPC": "@RTPC_SC_NameStr",
                            "AttackTime": "@0",
                            "ReleaseTime": "@1"
                        }

                # 以json为参考系。如果Wwise里有了，就用wwise的覆盖json的预设值，待后续重新加载GUI显示
                json_SideChainList = list(KeyInfoDict["Init_SideChain"].keys())
                for SideChainName in json_SideChainList:
                    if currentSideChainDict.get(SideChainName, "@#$") != "@#$":  # 说明Wwise里有
                        if currentSideChainDict[SideChainName] != {
                            "RTPC": "@RTPC_SC_NameStr",
                            "AttackTime": "@0",
                            "ReleaseTime": "@1"
                        }:
                            KeyInfoDict["Init_SideChain"][SideChainName] = currentSideChainDict[SideChainName]

                # 以Wwise为参考系。如果json中没有，就添加到json中，待后续重新加载GUI显示
                wwise_SideChainList = list(currentSideChainDict.keys())
                for SideChainName in wwise_SideChainList:
                    if KeyInfoDict["Init_SideChain"].get(SideChainName, "@#$") == "@#$":  # 说明Json里没
                        if currentSideChainDict[SideChainName] != {
                            "RTPC": "@RTPC_SC_NameStr",
                            "AttackTime": "@0",
                            "ReleaseTime": "@1"
                        }:
                            KeyInfoDict["Init_SideChain"][SideChainName] = currentSideChainDict[SideChainName]

                # 比照得出diffInfo差异记录
                if currentSideChainDict != KeyInfoDict["Init_SideChain"]:
                    # diffResultDict = Diff_Dict_For_KeySubkeyValuePair(currentSideChainDict, KeyInfoDict["Init_SideChain"])
                    diffCount["Result_SideChain"]["compareResult"] = "False"
                    diffCount["Result_SideChain"]["currentInfo"] = currentSideChainDict
                    # diffCount["Result_SideChain"]["diffInfo"] = diffResultDict

                # 将KeyInfoDict的最终值，同步记录到diffCount中
                diffCount["Result_SideChain"]["jsonInfo"] = KeyInfoDict["Init_SideChain"]

                # 判断WaapiStatus，如果状态不对，打标记
                if invalidWaapiCount == SIDECHAINPathCount:
                    diffCount["Result_SideChain"]["WaapiStatus"] = "False"
            else:
                # 将KeyInfoDict的最终值，同步记录到diffCount中
                diffCount["Result_SideChain"]["jsonInfo"] = KeyInfoDict["Init_SideChain"]
        except:
            diffCount["Result_SideChain"]["WaapiStatus"] = "False"

        # 获取当前Conversion信息，转换为json ----------------------------------------------------------------------------
        # 扫描Wwise工程，获取当前实际的数据组
        currentConversionPathList_From_Wwise = self.get_Paths_of_Descendants("CONVERSION")
        JsonConversionNameList = KeyInfoDict["Init_Conversion"]["Conversions"]
        LOG.debug("[CONVERSION查询结果]: ")
        LOG.debug(currentConversionPathList_From_Wwise)

        try:
            if len(currentConversionPathList_From_Wwise) != 0:
                currentConversionNameList = []
                for convPath in currentConversionPathList_From_Wwise:
                    currentConversionNameList.append(os.path.basename(convPath))

                # 以json为参考系。如果Wwise里有了，就用wwise的覆盖json的预设值，待后续重新加载GUI显示
                for ConvName in JsonConversionNameList:
                    if ConvName in currentConversionNameList:  # 说明Wwise里有
                        KeyInfoDict["Init_Conversion"]["Conversions"].remove(ConvName)

                # 以Wwise为参考系。如果json中没有，就添加到json中，待后续重新加载GUI显示
                for ConvName in currentConversionNameList:
                    if ConvName in JsonConversionNameList:
                        KeyInfoDict["Init_Conversion"]["Conversions"].remove(ConvName)

                # 比照得出diffInfo差异记录
                if currentConversionNameList != JsonConversionNameList:
                    # diffResultlist = find_differences_from_lists(JsonConversionNameList, currentConversionNameList)
                    diffCount["Result_Conversion"]["compareResult"] = "False"
                    diffCount["Result_Conversion"]["currentInfo"] = currentConversionNameList
                    # diffCount["Result_Conversion"]["diffInfo"] = diffResultlist

                # 将KeyInfoDict的最终值，同步记录到diffCount中
                diffCount["Result_Conversion"]["jsonInfo"] = JsonConversionNameList
            else:
                # 将KeyInfoDict的最终值，同步记录到diffCount中
                diffCount["Result_Conversion"]["jsonInfo"] = JsonConversionNameList
        except:
            diffCount["Result_Conversion"]["WaapiStatus"] = "False"

        # 获取当前Attenuation信息，转换为json ---------------------------------------------------------------------------
        # 扫描Wwise工程，获取当前实际的数据组
        currentAttenuationPathList_From_Wwise = self.get_Paths_of_Descendants("ATTENUATION")
        currentAttenuationDict = {}
        LOG.debug("[ATTENUATION查询结果]: ")
        LOG.debug(currentAttenuationPathList_From_Wwise)

        try:
            if len(currentAttenuationPathList_From_Wwise) != 0:
                invalidWaapiCount = 0
                ATTENUATIONPathCount = len(currentAttenuationPathList_From_Wwise)
                for attPath in currentAttenuationPathList_From_Wwise:
                    attName = os.path.basename(attPath)
                    maxDistanceDict = self.get_value_of_Attenuation(attPath)
                    LOG.debug("获取到的Attenuation属性Dict：")
                    LOG.debug(maxDistanceDict)
                    if maxDistanceDict is not None:
                        currentAttenuationDict[attName] = maxDistanceDict
                    else:
                        invalidWaapiCount += 1
                        currentAttenuationDict[attName] = {
                            "RadiusMax": "@5000"
                        }

                # 以json为参考系。如果Wwise里有了，就用wwise的覆盖json的预设值，待后续重新加载GUI显示
                json_AttNameList = list(KeyInfoDict["Init_Attenuation"].keys())
                for AttName in json_AttNameList:
                    if currentAttenuationDict.get(AttName, "@#$") != "@#$":  # 说明Wwise里有
                        if currentAttenuationDict[AttName] != {
                            "RadiusMax": "@5000"
                        }:
                            KeyInfoDict["Init_Attenuation"][AttName] = currentAttenuationDict[AttName]

                # 以Wwise为参考系。如果json中没有，就添加到json中，待后续重新加载GUI显示
                wwise_AttNameList = list(currentAttenuationDict.keys())
                for AttName in wwise_AttNameList:
                    if KeyInfoDict["Init_Attenuation"].get(AttName, "@#$") == "@#$":  # 说明Json里没
                        if currentAttenuationDict[AttName] != {
                            "RadiusMax": "@5000"
                        }:
                            KeyInfoDict["Init_Attenuation"][AttName] = currentAttenuationDict[AttName]

                # 比照得出diffInfo差异记录
                if currentAttenuationDict != KeyInfoDict["Init_Attenuation"]:
                    # diffResultDict = Diff_Dict_For_KeySubkeyValuePair(currentAttenuationDict, KeyInfoDict["Init_Attenuation"])
                    diffCount["Result_Attenuation"]["compareResult"] = "False"
                    diffCount["Result_Attenuation"]["currentInfo"] = currentAttenuationDict
                    # diffCount["Result_Attenuation"]["diffInfo"] = diffResultDict

                # 将KeyInfoDict的最终值，同步记录到diffCount中
                diffCount["Result_Attenuation"]["jsonInfo"] = KeyInfoDict["Init_Attenuation"]

                # 判断WaapiStatus，如果状态不对，打标记
                if invalidWaapiCount == ATTENUATIONPathCount:
                    diffCount["Result_Attenuation_Value"]["WaapiStatus"] = "False"
            else:
                # 将KeyInfoDict的最终值，同步记录到diffCount中
                diffCount["Result_Attenuation"]["jsonInfo"] = KeyInfoDict["Init_Attenuation"]
        except:
            diffCount["Result_Attenuation"]["WaapiStatus"] = "False"

        # 返回最终的Dict结果
        return diffCount

    def PathsCheckLog(self):
        PathsCheckLogs = []

        # info.json检查
        InfoJsonPath = os.path.exists(global_curWwisePath + "\\info.json")
        if InfoJsonPath is False:
            PathsCheckLogs.append(lan["LOG_SC_def_PathsCheckLog_FAIL"][L])
            # LOG.debug("1")
        else:
            ErrorPrintPool = []
            if len(ErrorPrintPool) != 0:
                for t in ErrorPrintPool:
                    PathsCheckLogs.append(t)
                    # LOG.debug("2")
            else:
                # fName对象的相关Key检查
                newfname = NewfNameSafetyCheck()
                currentfNameList = list(KeyInfoDict["Data_KeyInfo"].keys())

                # 如果fName里存在尚未生成Value组的新对象，先跳过这些新对象，只检查已存在Value的fName
                if len(newfname) != 0:
                    PathsCheckLogs.append(lan["LOG_SC_HeadTip_Error"][L] + str(newfname) + lan["LOG_SC_def_PathsCheckLog_KeyNameGroup"][L])
                    # LOG.debug("4")
                    validfnamelist = []
                    for j in currentfNameList:
                        if j not in newfname:
                            validfnamelist.append(j)

                    # 先检查KeyInfoDict[fname[i]]相应的子key是否存在
                    for y in validfnamelist:
                        SubKeyStrNeedToBeChecked = key["validKeyInfoItems"]
                        SubKeyStrError = []
                        for o in SubKeyStrNeedToBeChecked:
                            log = KeyExistCheck(o, KeyInfoDict["Data_KeyInfo"][y])
                            if log is not None:
                                SubKeyStrError.append(log)
                        if len(SubKeyStrError) != 0:
                            for p in SubKeyStrError:
                                PathsCheckLogs.append(p)
                                # LOG.debug("5")

                        # fName的Value组相关路径检查
                        else:
                            OriWAVFilePath = KeyInfoDict["Data_KeyInfo"][y]["Path_File_PlaceholderWAV"]
                            TarWAVPath = global_curWwisePath + "\\" + KeyInfoDict["Data_KeyInfo"][y]["Path_Folder_TargetWAV"]

                            if PathsCheckPrintFunc(OriWAVFilePath) is False:
                                PathsCheckLogs.append("error")
                                # LOG.debug("7")
                            if PathsCheckPrintFunc(TarWAVPath) is False:
                                PathsCheckLogs.append("error")
                                # LOG.debug("8")

                            TypeStr = KeyInfoDict["Data_KeyInfo"][y]["Structure_Type"]
                            MultiPlayerSwitchGroupName = KeyInfoDict["Data_KeyInfo"][y]["Property_SwitchGroupName_PC_NPC"]
                            TextureSwitchGroupName = KeyInfoDict["Data_KeyInfo"][y]["Property_SwitchGroupName_Texture"]
                            NPCBusPath = KeyInfoDict["Data_KeyInfo"][y]["Property_Bus_NPC"]
                            TemplatePath = KeyInfoDict["Data_KeyInfo"][y]["Path_InWwise_UserDefinedTemplate"]
                            TemplateName = ""
                            if len(TemplatePath) != 0:
                                TemplateName = os.path.basename(TemplatePath)
                            WAVStream = KeyInfoDict["Data_KeyInfo"][y]["Property_ifStream"]

                            # 检查TypeStr是否合法
                            validType = key["ValidTypeStr"]
                            if TypeStr not in validType:
                                PathsCheckLogs.append(lan["LOG_SC_HeadTip_Unacceptable"][L] + str(y) + lan["LOG_SC_def_PathsCheckLog_InvalidTypeString"][L])
                                # LOG.debug("9")
                            # 检查Type相关Info是否合法
                            if TypeStr == "type1d":
                                if len(MultiPlayerSwitchGroupName) != 0 or len(TextureSwitchGroupName) != 0:
                                    pass
                                    # PathsCheckLogs.append(lan["LOG_SC_HeadTip_Unacceptable"][L] + str(y) + lan["LOG_SC_def_PathsCheckLog_InvalidType1DPath"][L])
                            elif TypeStr == "type2d":
                                if len(MultiPlayerSwitchGroupName) == 0:
                                    PathsCheckLogs.append(lan["LOG_SC_HeadTip_Unacceptable"][L] + str(y) + lan["LOG_SC_def_PathsCheckLog_InvalidType2DSwitchPath"][L])
                                    # LOG.debug("10")
                                if len(NPCBusPath) == 0:
                                    PathsCheckLogs.append(lan["LOG_SC_HeadTip_Unacceptable"][L] + str(y) + lan["LOG_SC_def_PathsCheckLog_InvalidType2DBUSPath"][L])
                                    # LOG.debug("11")
                            elif TypeStr == "type3d":
                                if len(MultiPlayerSwitchGroupName) == 0 or len(TextureSwitchGroupName) == 0:
                                    PathsCheckLogs.append(lan["LOG_SC_HeadTip_Unacceptable"][L] + str(y) + lan["LOG_SC_def_PathsCheckLog_InvalidType3DSwitchPath"][L])
                                    # LOG.debug("12")
                                if len(NPCBusPath) == 0:
                                    PathsCheckLogs.append(lan["LOG_SC_HeadTip_Unacceptable"][L] + str(y) + lan["LOG_SC_def_PathsCheckLog_InvalidType3DBUSPath"][L])
                                    # LOG.debug("13")
                            elif TypeStr == "typet":
                                if len(TemplatePath) == 0 or len(TemplateName) == 0:
                                    PathsCheckLogs.append(lan["LOG_SC_HeadTip_Unacceptable"][L] + str(y) + lan["LOG_SC_def_PathsCheckLog_InvalidTypeSAmbPath"][L])
                                    # LOG.debug("14")
                                if len(WAVStream) == 0:
                                    PathsCheckLogs.append(lan["LOG_SC_HeadTip_Unacceptable"][L] + str(y) + lan["LOG_SC_def_PathsCheckLog_InvalidTypeSAmbStream"][L])
                                    # LOG.debug("15")

                # 否则说明fName里的对象都有Value组，就全部检查一遍
                else:
                    # 先检查fName里每一个对象的子key是否存在
                    for a in currentfNameList:
                        SubKeyStrNeedToBeChecked = key["validKeyInfoItems"]
                        SubKeyStrError = []
                        for b in SubKeyStrNeedToBeChecked:
                            log = KeyExistCheck(b, KeyInfoDict["Data_KeyInfo"][a])
                            if log is not None:
                                SubKeyStrError.append(log)
                        if len(SubKeyStrError) != 0:
                            for c in SubKeyStrError:
                                PathsCheckLogs.append(c)
                                # LOG.debug("16")
                        # fName的Value组相关路径检查
                        else:
                            OriWAVFilePath = KeyInfoDict["Data_KeyInfo"][a]["Path_File_PlaceholderWAV"]
                            TarWAVPath = global_curWwisePath + "\\" + KeyInfoDict["Data_KeyInfo"][a]["Path_Folder_TargetWAV"]

                            if PathsCheckPrintFunc(OriWAVFilePath) is False:
                                PathsCheckLogs.append("error")
                                # LOG.debug("7")
                            if PathsCheckPrintFunc(TarWAVPath) is False:
                                PathsCheckLogs.append("error")
                                # LOG.debug("8")

                            TypeStr = KeyInfoDict["Data_KeyInfo"][a]["Structure_Type"]
                            MultiPlayerSwitchGroupName = KeyInfoDict["Data_KeyInfo"][a]["Property_SwitchGroupName_PC_NPC"]
                            TextureSwitchGroupName = KeyInfoDict["Data_KeyInfo"][a]["Property_SwitchGroupName_Texture"]
                            NPCBusPath = KeyInfoDict["Data_KeyInfo"][a]["Property_Bus_NPC"]
                            TemplatePath = KeyInfoDict["Data_KeyInfo"][a]["Path_InWwise_UserDefinedTemplate"]
                            TemplateName = ""
                            if len(TemplatePath) != 0:
                                TemplateName = os.path.basename(TemplatePath)
                            WAVStream = KeyInfoDict["Data_KeyInfo"][a]["Property_ifStream"]

                            # 检查TypeStr是否合法
                            validType = key["ValidTypeStr"]
                            if TypeStr not in validType:
                                PathsCheckLogs.append(lan["LOG_SC_HeadTip_Unacceptable"][L] + str(a) + lan["LOG_SC_def_PathsCheckLog_InvalidTypeString"][L])

                            if TypeStr == "type1d":
                                if len(MultiPlayerSwitchGroupName) != 0 or len(TextureSwitchGroupName) != 0:
                                    pass
                                    # PathsCheckLogs.append(lan["LOG_SC_HeadTip_Unacceptable"][L] + str(a) + lan["LOG_SC_def_PathsCheckLog_InvalidType1DPath"][L])
                            elif TypeStr == "type2d":
                                if len(MultiPlayerSwitchGroupName) == 0:
                                    PathsCheckLogs.append(lan["LOG_SC_HeadTip_Unacceptable"][L] + str(a) + lan["LOG_SC_def_PathsCheckLog_InvalidType2DSwitchPath"][L])
                                if len(NPCBusPath) == 0:
                                    PathsCheckLogs.append(lan["LOG_SC_HeadTip_Unacceptable"][L] + str(a) + lan["LOG_SC_def_PathsCheckLog_InvalidType2DBUSPath"][L])
                            elif TypeStr == "type3d":
                                if len(MultiPlayerSwitchGroupName) == 0 or len(TextureSwitchGroupName) == 0:
                                    PathsCheckLogs.append(lan["LOG_SC_HeadTip_Unacceptable"][L] + str(a) + lan["LOG_SC_def_PathsCheckLog_InvalidType3DSwitchPath"][L])
                                if len(NPCBusPath) == 0:
                                    PathsCheckLogs.append(lan["LOG_SC_HeadTip_Unacceptable"][L] + str(a) + lan["LOG_SC_def_PathsCheckLog_InvalidType3DBUSPath"][L])
                            elif TypeStr == "typet":
                                if len(TemplatePath) == 0 or len(TemplateName) == 0:
                                    PathsCheckLogs.append(lan["LOG_SC_HeadTip_Unacceptable"][L] + str(a) + lan["LOG_SC_def_PathsCheckLog_InvalidTypeSAmbPath"][L])
                                if len(WAVStream) == 0:
                                    PathsCheckLogs.append(lan["LOG_SC_HeadTip_Unacceptable"][L] + str(a) + " --> TypeSAmb structure WAVStream would better be \"True\".")
        return PathsCheckLogs

    def nameStrGen(self, ID, fName, sName, tName, ranNum):
        namingError = []
        finalNameStr = []
        sfxContainerStr = []

        # AudioWWUPath = self.get_CurrentWwiseSession_ActorMixerWWUPath()
        # MusicWWUPath = self.get_CurrentWwiseSession_InteractiveMusicWWUPath()
        # EventWWUPath = self.get_CurrentWwiseSession_EventsWWUPath()

        # 先确认值是否为None
        if ID == "None":
            ID = ""
        if fName == "None":
            fName = ""
        if sName == "None":
            sName = ""
        if tName == "None":
            tName = ""
        if ranNum == "None":
            ranNum = ""

        # 检查fName是否合法（存在、属于合法范围内对象）
        if len(fName) == 0:
            # LOG.debug(lan["LOG_NSG_def_nameStrGen_KeyNameIsMissing"][L])
            namingError.append(lan["LOG_NSG_def_nameStrGen_KeyNameIsMissing"][L])
        if fName not in list(KeyInfoDict["Data_KeyInfo"].keys()):
            # LOG.debug(lan["LOG_NSG_def_nameStrGen_fnameInvalid"][L])
            namingError.append(lan["LOG_NSG_def_nameStrGen_fnameInvalid"][L])

        # 检查sName是否合法（无非法字符）
        if len(ifStrHasInvalidChar(sName)) != 0:
            # LOG.debug("sName: " + lan["LOG_NSG_def_nameStrGen_StrHasInvalidChar"][L])
            namingError.append(lan["LOG_NSG_def_nameStrGen_StrHasInvalidChar"][L])

        # 检查tName是否合法（无非法字符）
        if len(ifStrHasInvalidChar(tName)) != 0:
            # LOG.debug("tName: " + lan["LOG_NSG_def_nameStrGen_StrHasInvalidChar"][L])
            namingError.append(lan["LOG_NSG_def_nameStrGen_StrHasInvalidChar"][L])

        # 检查ranNum是否合法（存在、属于合法范围内对象）
        if len(ranNum) == 0:
            # LOG.debug(lan["LOG_NSG_def_nameStrGen_RDMisMissing"][L])
            namingError.append(lan["LOG_NSG_def_nameStrGen_RDMisMissing"][L])
        if ranNum not in key["validRanNum"]:
            # LOG.debug(lan["LOG_NSG_def_nameStrGen_RanNumInvalid"][L])
            namingError.append(lan["LOG_NSG_def_nameStrGen_RanNumInvalid"][L])

        # 查看namingError是否有报错信息，如果没有，则开始生成ObjRefStr和EventStr
        if len(namingError) == 0:
            tempNameList = [ID, fName, sName, tName, ranNum]

            # 把ID放入finalNameStr中
            finalNameStr.append(ID)

            # 生成ObjRefStr (Container Name)----------------------
            ObjRefStr = ""
            for i in range(1, len(tempNameList) - 1):
                if tempNameList[i] != "":
                    ObjRefStr += (tempNameList[i] + "_")
                else:
                    continue
            ObjRefStr = ObjRefStr[:-1]

            # 判断ObjectRef是否已存在
            AudioContainerDict = self.getAudioContainersFromAudioWWU()
            if ObjRefStr in AudioContainerDict.keys():
                tempDictA = {ObjRefStr: AudioContainerDict[ObjRefStr]}
                LOG.warning(lan["LOG_NSG_def_nameStrGen_DuplicatedActor"][L] + str(tempDictA))
                namingError.append(lan["LOG_NSG_def_nameStrGen_DuplicatedActor"][L] + str(tempDictA))
            else:
                finalNameStr.append(ObjRefStr)

            # 生成EventStr (Event Name)----------------------------
            EventStr = "Play_" + ObjRefStr

            # 判断EventStr是否已存在
            EventDict = self.getEventNameFromEventWWU()
            if EventStr in EventDict.keys():
                tempDictB = {EventStr: EventDict[EventStr]}
                LOG.warning(lan["LOG_NSG_def_nameStrGen_DuplicatedEvent"][L] + str(tempDictB))
                namingError.append(lan["LOG_NSG_def_nameStrGen_DuplicatedEvent"][L] + str(tempDictB))
            else:
                finalNameStr.append(EventStr)

            # 判断type类型是否为gun，如果是，则安排Tail命名组
            ObjRefStr_Tail = ObjRefStr + "_Tail"
            TypeValue = KeyInfoDict["Data_KeyInfo"][fName]["Structure_Type"]
            if TypeValue in key["ValidTypeStr"] and TypeValue == "type2d_gun":
                # 不允许type2d_gun的命名末尾有“_LP”，在这里做一个安全检查
                if ObjRefStr[-3:] == "_LP":
                    namingError.append(lan["LOG_NSG_def_nameStrGen_LPnotallowed"][L] + " --> " + str(ObjRefStr))
                    # LOG.info(lan["LOG_NSG_def_nameStrGen_LPnotallowed"][L] + " --> " + str(ObjRefStr))
                else:
                    finalNameStr.append(ObjRefStr_Tail)

            # 查看namingError是否有报错信息，如果没有，则继续进一步检查类型，准备生成sfx大礼包
            if len(namingError) == 0:
                # 获取type值，检查type值是否在合法范围内，如果在，继续下一步sfx生成
                TypeValue = KeyInfoDict["Data_KeyInfo"][fName]["Structure_Type"]
                ValidTypeList = key["ValidTypeStr"]
                if TypeValue in ValidTypeList:
                    # typet类型生成SFX命名大礼包
                    if TypeValue == "typet":
                        try:
                            # 先判断Template路径是否存在
                            # 先检查模板路径是否存在, 如果不存在，直接结束进程并打印报告！
                            TemplatePathInWwise = KeyInfoDict["Data_KeyInfo"][fName]["Path_InWwise_UserDefinedTemplate"]
                            existcheck = self.GetWWUPath(TemplatePathInWwise)
                            if existcheck is None:
                                # LOG.debug(lan["LOG_WG_def_typet_TemplateNotExist"][L])
                                namingError.append(lan["LOG_WG_def_typet_TemplateNotExist"][L])
                            else:
                                # 检查模板内部结构！通过后再进行执行！
                                PathResults = self.FilterValidContainerPaths(TemplatePathInWwise)
                                # 判断PathResults[1]是否为空, 如果不为空（说明包含禁用的容器对象），结束进程并打印报告
                                if len(PathResults[1]) != 0:
                                    # LOG.debug(lan["LOG_WG_def_typet_FoundForbiddenObj"][L])
                                    namingError.append(lan["LOG_WG_def_typet_FoundForbiddenObj"][L])
                                else:
                                    # 判断PathResults[0]是否为空，空的话，说明该模板是一个单一容器
                                    if len(PathResults[0]) == 0:
                                        # 生成WAV小礼包
                                        for i in range(1, int(ranNum) + 1):
                                            if 0 < int(ranNum) < 9:
                                                ObjRefStr = ObjRefStr + "_0" + str(i)
                                                sfxContainerStr.append(ObjRefStr)
                                                ObjRefStr = ObjRefStr[:-3]
                                    else:
                                        # PathResults[0]不为空，说明该模板有其下属子容器
                                        # 先将Template的Path移除模板框架部分的字符串，仅保留对生成新命名有用的部分，然后将路径中"\\"替换为"_"
                                        CleanStr = []
                                        for i in PathResults[0]:
                                            cut = i.replace(TemplatePathInWwise + "\\", "")
                                            newStr = cut.replace("\\", "_")
                                            CleanStr.append(newStr)
                                        if 0 < int(ranNum) < 9:
                                            for obj in CleanStr:
                                                sub_sfxContainerStr = []
                                                for i in range(1, int(ranNum) + 1):
                                                    ObjRefStr = ObjRefStr + "_" + obj + "_0" + str(i)
                                                    sub_sfxContainerStr.append(ObjRefStr)
                                                    ObjRefStr = ObjRefStr[: -len(obj) - 1 - 3]
                                                sfxContainerStr.append(sub_sfxContainerStr)
                        except:
                            # LOG.debug(lan["LOG_NSG_def_nameStrGen_typetNeedWaapi"][L])
                            namingError.append(lan["LOG_NSG_def_nameStrGen_typetNeedWaapi"][L])

                    # type3d类型生成SFX命名大礼包
                    elif TypeValue == "type3d":
                        SwitchGroupName_Texture = KeyInfoDict["Data_KeyInfo"][fName]["Property_SwitchGroupName_Texture"]
                        switchObjList = self.getSwitchFromSwitchWWU(SwitchGroupName_Texture)
                        # 先判断是否在WWU中成功取到了SwitchObjList
                        if len(switchObjList) != 0:
                            # 随机数大于1的情况
                            if 0 < int(ranNum) < 9:
                                for obj in switchObjList:
                                    sub_sfxContainerStr = []
                                    for i in range(1, int(ranNum) + 1):
                                        ObjRefStr = ObjRefStr + "_" + obj + "_0" + str(i)
                                        sub_sfxContainerStr.append(ObjRefStr)
                                        ObjRefStr = ObjRefStr[: -len(obj) - 1 - 3]
                                    sfxContainerStr.append(sub_sfxContainerStr)

                    # type1d、type2d类型生成SFX命名大礼包
                    elif TypeValue in ["type1d", "type2d", "type1d_vo", "type2d_vo"]:
                        for i in range(1, int(ranNum) + 1):
                            # 随机数大于1的情况
                            if 0 < int(ranNum) < 9:
                                ObjRefStr = ObjRefStr + "_0" + str(i)
                                sfxContainerStr.append(ObjRefStr)
                                ObjRefStr = ObjRefStr[:-3]

                    # type2d_gun类型生成SFX命名大礼包
                    elif TypeValue == "type2d_gun":
                        sfxContainerStr = {"Tail":[]}
                        for obj in key["ValidGunLayer"]["PC"]:
                            sfxContainerStr[obj] = []
                            # sfxContainerStr = {
                            #     "Fire": [],
                            #     "Mech": [],
                            #     "Sub": [],
                            #     "Sweetener": [],
                            #     "Transient": [],
                            #     "Tail": []
                            # }
                        # 添加判断，如果type类型是type2d_gun，则移除命名末尾的“LP”
                        TypeValue = KeyInfoDict["Data_KeyInfo"][fName]["Structure_Type"]
                        if TypeValue in key["ValidTypeStr"] and TypeValue == "type2d_gun":
                            if ObjRefStr[-3:] == "_LP":
                                ObjRefStr = ObjRefStr[:-3]

                        subStrList = list(sfxContainerStr.keys())
                        for subStr in subStrList:
                            for i in range(1, int(ranNum) + 1):
                                # 随机数大于1的情况
                                if 0 < int(ranNum) < 9:
                                    ObjRefStr = ObjRefStr + "_" + subStr + "_0" + str(i)
                                    sfxContainerStr[subStr].append(ObjRefStr)
                                    ObjRefStr = ObjRefStr[:-(4 + len(subStr))]

                    # Value --> ValidTypeList --> WaapiGoFunc 不匹配提示
                    else:
                        LOG.error(lan["LOG_NSG_def_nameStrGen_ValidTypeListOutOfDate"][L])
                        namingError.append(lan["LOG_NSG_def_nameStrGen_ValidTypeListOutOfDate"][L])

        return namingError, finalNameStr, sfxContainerStr

    def nameStrGenWithoutCheckDuplicate(self, ID, fName, sName, tName, ranNum):
        namingError = []
        finalNameStr = []
        sfxContainerStr = []

        # AudioWWUPath = self.get_CurrentWwiseSession_ActorMixerWWUPath()
        # MusicWWUPath = self.get_CurrentWwiseSession_InteractiveMusicWWUPath()
        # EventWWUPath = self.get_CurrentWwiseSession_EventsWWUPath()

        # 先确认值是否为None
        if ID == "None":
            ID = ""
        if fName == "None":
            fName = ""
        if sName == "None":
            sName = ""
        if tName == "None":
            tName = ""
        if ranNum == "None":
            ranNum = ""

        # 检查fName是否合法（存在、属于合法范围内对象）
        if len(fName) == 0:
            # LOG.debug(lan["LOG_NSG_def_nameStrGen_KeyNameIsMissing"][L])
            namingError.append(lan["LOG_NSG_def_nameStrGen_KeyNameIsMissing"][L])
        if fName not in list(KeyInfoDict["Data_KeyInfo"].keys()):
            # LOG.debug(lan["LOG_NSG_def_nameStrGen_fnameInvalid"][L])
            namingError.append(lan["LOG_NSG_def_nameStrGen_fnameInvalid"][L])

        # 检查sName是否合法（无非法字符）
        if len(ifStrHasInvalidChar(sName)) != 0:
            # LOG.debug("sName: " + lan["LOG_NSG_def_nameStrGen_StrHasInvalidChar"][L])
            namingError.append(lan["LOG_NSG_def_nameStrGen_StrHasInvalidChar"][L])

        # 检查tName是否合法（无非法字符）
        if len(ifStrHasInvalidChar(tName)) != 0:
            # LOG.debug("tName: " + lan["LOG_NSG_def_nameStrGen_StrHasInvalidChar"][L])
            namingError.append(lan["LOG_NSG_def_nameStrGen_StrHasInvalidChar"][L])

        # 检查ranNum是否合法（存在、属于合法范围内对象）
        if len(ranNum) == 0:
            # LOG.debug(lan["LOG_NSG_def_nameStrGen_RDMisMissing"][L])
            namingError.append(lan["LOG_NSG_def_nameStrGen_RDMisMissing"][L])
        if ranNum not in key["validRanNum"]:
            # LOG.debug(lan["LOG_NSG_def_nameStrGen_RanNumInvalid"][L])
            namingError.append(lan["LOG_NSG_def_nameStrGen_RanNumInvalid"][L])

        # 查看namingError是否有报错信息，如果没有，则开始生成ObjRefStr和EventStr
        if len(namingError) == 0:
            tempNameList = [ID, fName, sName, tName, ranNum]

            # 把ID放入finalNameStr中
            finalNameStr.append(ID)

            # 生成ObjRefStr (Container Name)----------------------
            ObjRefStr = ""
            for i in range(1, len(tempNameList) - 1):
                if tempNameList[i] != "":
                    ObjRefStr += (tempNameList[i] + "_")
                else:
                    continue
            ObjRefStr = ObjRefStr[:-1]
            finalNameStr.append(ObjRefStr)

            # 生成EventStr (Event Name)----------------------------
            EventStr = "Play_" + ObjRefStr
            finalNameStr.append(EventStr)

            # 查看namingError是否有报错信息，如果没有，则继续进一步检查类型，准备生成sfx大礼包
            if len(namingError) == 0:
                # 获取type值，检查type值是否在合法范围内，如果在，继续下一步sfx生成
                TypeValue = KeyInfoDict["Data_KeyInfo"][fName]["Structure_Type"]
                WwiseTemplate = KeyInfoDict["Data_KeyInfo"][fName]["Path_InWwise_UserDefinedTemplate"]
                TextureSwitchGroupName = KeyInfoDict["Data_KeyInfo"][fName]["Property_SwitchGroupName_Texture"]

                ValidTypeList = key["ValidTypeStr"]
                if TypeValue in ValidTypeList:
                    # typet类型生成SFX命名大礼包
                    if TypeValue == "typet":
                        try:
                            # 先判断Template路径是否存在
                            # 先检查模板路径是否存在, 如果不存在，直接结束进程并打印报告！
                            existcheck = self.GetWWUPath(WwiseTemplate)
                            if existcheck is None:
                                # LOG.debug(lan["LOG_WG_def_typet_TemplateNotExist"][L])
                                namingError.append(lan["LOG_WG_def_typet_TemplateNotExist"][L])
                            else:
                                # 检查模板内部结构！通过后再进行执行！
                                PathResults = self.FilterValidContainerPaths(WwiseTemplate)

                                # 判断PathResults[1]是否为空, 如果不为空（说明包含禁用的容器对象），结束进程并打印报告
                                if len(PathResults[1]) != 0:
                                    # LOG.debug(lan["LOG_WG_def_typet_FoundForbiddenObj"][L])
                                    namingError.append(lan["LOG_WG_def_typet_FoundForbiddenObj"][L])
                                else:
                                    # 判断PathResults[0]是否为空，空的话，说明该模板是一个单一容器
                                    if len(PathResults[0]) == 0:
                                        # 生成WAV小礼包
                                        for i in range(1, int(ranNum) + 1):
                                            # if ranNum == "1" or ranNum == 1:
                                            #     sfxContainerStr.append(ObjRefStr)
                                            if 0 < int(ranNum) < 9:
                                                ObjRefStr = ObjRefStr + "_0" + str(i)
                                                sfxContainerStr.append(ObjRefStr)
                                                ObjRefStr = ObjRefStr[:-3]
                                    else:
                                        # PathResults[0]不为空，说明该模板有其下属子容器
                                        # 先将Template的Path移除模板框架部分的字符串，仅保留对生成新命名有用的部分，然后将路径中"\\"替换为"_"
                                        CleanStr = []
                                        for i in PathResults[0]:
                                            cut = i.replace(WwiseTemplate + "\\", "")
                                            newStr = cut.replace("\\", "_")
                                            CleanStr.append(newStr)
                                        # 生成大礼包
                                        # if ranNum == "1" or ranNum == 1:
                                        #     sub_sfxContainerStr = []
                                        #     for obj in CleanStr:
                                        #         ObjRefStr = ObjRefStr + "_" + obj
                                        #         tempList = [ObjRefStr]
                                        #         sub_sfxContainerStr.append(tempList)
                                        #         ObjRefStr = ObjRefStr[: -len(obj) - 1]
                                        #     sfxContainerStr = sub_sfxContainerStr
                                        if 0 < int(ranNum) < 9:
                                            for obj in CleanStr:
                                                sub_sfxContainerStr = []
                                                for i in range(1, int(ranNum) + 1):
                                                    ObjRefStr = ObjRefStr + "_" + obj + "_0" + str(i)
                                                    sub_sfxContainerStr.append(ObjRefStr)
                                                    ObjRefStr = ObjRefStr[: -len(obj) - 1 - 3]
                                                sfxContainerStr.append(sub_sfxContainerStr)

                        except:
                            # LOG.debug(lan["LOG_NSG_def_nameStrGen_typetNeedWaapi"][L])
                            namingError.append(lan["LOG_NSG_def_nameStrGen_typetNeedWaapi"][L])

                    # type3d类型生成SFX命名大礼包
                    elif TypeValue == "type3d":
                        switchObjList = self.getSwitchFromSwitchWWU(TextureSwitchGroupName)
                        # 先判断是否在WWU中成功取到了SwitchObjList
                        if len(switchObjList) != 0:
                            # # 随机数等于1的情况
                            # if ranNum == "1" or ranNum == 1:
                            #     sub_sfxContainerStr = []
                            #     for obj in switchObjList:
                            #         ObjRefStr = ObjRefStr + "_" + obj
                            #         tempList = [ObjRefStr]
                            #         sub_sfxContainerStr.append(tempList)
                            #         ObjRefStr = ObjRefStr[: -len(obj) - 1]
                            #     sfxContainerStr = sub_sfxContainerStr
                            # 随机数大于1的情况
                            if 0 < int(ranNum) < 9:
                                for obj in switchObjList:
                                    sub_sfxContainerStr = []
                                    for i in range(1, int(ranNum) + 1):
                                        ObjRefStr = ObjRefStr + "_" + obj + "_0" + str(i)
                                        sub_sfxContainerStr.append(ObjRefStr)
                                        ObjRefStr = ObjRefStr[: -len(obj) - 1 - 3]
                                    sfxContainerStr.append(sub_sfxContainerStr)

                    # type1d、type2d类型生成SFX命名大礼包
                    elif TypeValue in ["type1d", "type2d", "type1d_vo", "type2d_vo"]:
                        for i in range(1, int(ranNum) + 1):
                            # # 随机数等于1的情况
                            # if ranNum == "1" or ranNum == 1:
                            #     sfxContainerStr.append(ObjRefStr)
                            # 随机数大于1的情况
                            if 0 < int(ranNum) < 9:
                                ObjRefStr = ObjRefStr + "_0" + str(i)
                                sfxContainerStr.append(ObjRefStr)
                                ObjRefStr = ObjRefStr[:-3]

                    # type2d_gun类型生成SFX命名大礼包
                    elif TypeValue == "type2d_gun":
                        sfxContainerStr = {"Tail":[]}
                        for obj in key["ValidGunLayer"]["PC"]:
                            sfxContainerStr[obj] = []
                            # sfxContainerStr = {
                            #     "Fire": [],
                            #     "Mech": [],
                            #     "Sub": [],
                            #     "Sweetener": [],
                            #     "Transient": [],
                            #     "Tail": []
                            # }
                        # 添加判断，如果type类型是type2d_gun，则移除命名末尾的“LP”
                        TypeValue = KeyInfoDict["Data_KeyInfo"][fName]["Structure_Type"]
                        if TypeValue in key["ValidTypeStr"] and TypeValue == "type2d_gun":
                            if ObjRefStr[-3:] == "_LP":
                                ObjRefStr = ObjRefStr[:-3]

                        subStrList = list(sfxContainerStr.keys())
                        for subStr in subStrList:
                            for i in range(1, int(ranNum) + 1):
                                # 随机数大于1的情况
                                if 0 < int(ranNum) < 9:
                                    ObjRefStr = ObjRefStr + "_" + subStr + "_0" + str(i)
                                    sfxContainerStr[subStr].append(ObjRefStr)
                                    ObjRefStr = ObjRefStr[:-(4 + len(subStr))]

                    # Value --> ValidTypeList --> WaapiGoFunc 不匹配提示
                    else:
                        LOG.warning(lan["LOG_NSG_def_nameStrGen_ValidTypeListOutOfDate"][L])
                        namingError.append(lan["LOG_NSG_def_nameStrGen_ValidTypeListOutOfDate"][L])

        return namingError, finalNameStr, sfxContainerStr

    def wavGen(self, ID, fName, sName, tName, ranNum):
        qq = self.nameStrGen(ID, fName, sName, tName, ranNum)
        wavGenError = []

        # 如果命名池没有报错、存在ObjectRefStr和EventStr、存在wav大礼包
        if len(qq[0]) == 0 and len(qq[1]) != 0 and len(qq[2]) != 0:
            LOG.info(lan["LOG_NSG_def_wavGen_START"][L])
            # 先判断Type是否为typet，或type3d，或type1d、type2d
            typeStr = KeyInfoDict["Data_KeyInfo"][fName]["Structure_Type"]
            Path_File_PlaceholderWAV = global_wavSilencePath
            Path_Folder_TargetWAV = os.path.join(global_curWwisePath, KeyInfoDict["Data_KeyInfo"][fName]["Path_Folder_TargetWAV"])

            if typeStr == "typet":
                for obj in qq[2]:
                    if type(obj) is str:
                        for i in qq[2]:
                            i = i + ".wav"
                            ADVErrorLogA = ADVQuickCopy(Path_File_PlaceholderWAV, Path_Folder_TargetWAV, i)
                            if len(ADVErrorLogA) != 0:
                                wavGenError.append(ADVErrorLogA)
                        break  # 大循环只能一遍
                    elif type(obj) is list:
                        for i in qq[2]:
                            for j in i:
                                j = j + ".wav"
                                ADVErrorLogB = ADVQuickCopy(Path_File_PlaceholderWAV, Path_Folder_TargetWAV, j)
                                if len(ADVErrorLogB) != 0:
                                    wavGenError.append(ADVErrorLogB)
                        break  # 大循环只能一遍
            elif typeStr == "type3d":
                for i in qq[2]:
                    for j in i:
                        j = j + ".wav"
                        ADVErrorLogB = ADVQuickCopy(Path_File_PlaceholderWAV, Path_Folder_TargetWAV, j)
                        if len(ADVErrorLogB) != 0:
                            wavGenError.append(ADVErrorLogB)
            elif typeStr == "type1d_vo" or typeStr == "type2d_vo":
                global_LanFolderInfoList_refresh = list_top_level_folders_with_paths(global_voicePath)
                if len(global_LanFolderInfoList_refresh) != 0:
                    for langInfo in global_LanFolderInfoList_refresh:
                        for i in qq[2]:
                            i = i + ".wav"
                            ADVErrorLogA = ADVQuickCopy(Path_File_PlaceholderWAV, langInfo["folderPath"], i)
                            if len(ADVErrorLogA) != 0:
                                wavGenError.append(ADVErrorLogA)
            elif typeStr == "type2d_gun":
                for sublist in qq[2].values():
                    for i in sublist:
                        i = i + ".wav"
                        ADVErrorLogA = ADVQuickCopy(Path_File_PlaceholderWAV, Path_Folder_TargetWAV, i)
                        if len(ADVErrorLogA) != 0:
                            wavGenError.append(ADVErrorLogA)
            else:
                for i in qq[2]:
                    i = i + ".wav"
                    ADVErrorLogA = ADVQuickCopy(Path_File_PlaceholderWAV, Path_Folder_TargetWAV, i)
                    if len(ADVErrorLogA) != 0:
                        wavGenError.append(ADVErrorLogA)

        # 否则，意味着命名池有报错，提示停止产生WAV
        else:
            LOG.info(lan["LOG_NSG_def_wavGen_STOPPED"][L])
            wavGenError.append(lan["LOG_NSG_def_wavGen_STOPPED"][L])

        return wavGenError

    def getObjectRefFromEventStr_ReturnDict(self, EventStr):
        ObjectRefCups = {}

        for wwuPath in getWWUPathFromLocal(self.get_CurrentWwiseSession_EventsWWUPath()):
            tree = ET.parse(wwuPath)
            root = tree.getroot()

            for a in root:
                for b in a:
                    for c in b:
                        for d in c:
                            if d.attrib.get("Name") == EventStr:
                                for e in d:
                                    for f in e:
                                        for g in f:
                                            for h in g:
                                                for i in h:
                                                    if i.attrib.get("ID") is not None:
                                                        ObjectRefCups[i.attrib.get("Name")] = i.attrib.get("ID")
        return ObjectRefCups

    def CreateAndGetNewPathsOfNewGUIDs(self, ObjectRefGUID):
        # 获取SwitchInfo大包
        SB = self.getAllContainerInfoFromObjectRefGUID(ObjectRefGUID)
        ERLog = []
        TotalNewGUIDPaths = []
        for i in SB:
            if i["SwitchGroupName"] == 0:
                ERLog.append("SwitchGroupName can not be empty!")
                LOG.warning(i["SwitchContainerName"] + lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_NoSwitchGroupName"][L])

            if len(i["CurrentChildType"]) == 0:
                ERLog.append("CurrentChildType can not be empty!")
                LOG.warning(i["SwitchContainerName"] + lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_NoCurrentChild"][L])
            if i["CurrentChildType"] == "Multi":
                ERLog.append("CurrentChildType can not be Multi! 说明当前SwitchContainer子集的类型存在多种，程序无法判断将要生成的目标类型")
                LOG.warning(i["SwitchContainerName"] + lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_MultiCurrentChild"][L])

            if i["CurrentChildType"] == "SwitchContainer":
                if len(i["CurrentChildSwitchGroupName"]) == 0:
                    ERLog.append("CurrentChildSwitchGroupName can not be empty!")
                    LOG.warning(i["SwitchContainerName"] + lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_SubLayerObj"][L] +
                          lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_NoSwitchGroupName"][L])
                if i["CurrentChildSwitchGroupName"] == "Multi":
                    ERLog.append("CurrentChildSwitchGroupName can not be Multi!")
                    LOG.warning(i["SwitchContainerName"] + lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_SubLayerObj"][L] +
                          lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_MultiCurrentChildSwitchGroupName"][L])

                if i["SwitchTargetContainerType"] == "SwitchContainer":
                    ERLog.append("SwitchTargetContainerType can not be SwitchContainer AGAIN!")
                    LOG.warning(i["SwitchContainerName"] + lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_SubLayerObj"][L] +
                          lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_TooManySwitchContainer"][L])
                if i["SwitchTargetContainerType"] == "Multi":
                    ERLog.append("SwitchTargetContainerType can not be Multi!")
                    LOG.warning(i["SwitchContainerName"] + lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_SubLayerObj"][L] +
                          lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_MultiCurrentChild"][L])

        # 检查ERLog内容
        if len(ERLog) != 0:
            LOG.warning(lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_FoundError"][L])
        else:
            LOG.warning(lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_SafetyCheckPASS"][L])
            # 检查通过，就继续下一步。
            NewGUIDsPool = []  # 路径池，将以下产生的新容器的GUID，全部保存在这里，待后续转换成路径！
            for i in SB:
                # 如果Diff中有内容，说明有差异，则开始逐个遍历处理
                if len(i["Diff"]) != 0:
                    LOG.warning(i["SwitchContainerName"] + lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_FoundDiff"][L])
                    for j, k in zip(i["Diff"].keys(), i["Diff"].values()):
                        # 在SC父级下，生成一个对象
                        args = {
                            "parent": i["SwitchContainerGUID"],
                            "type": i["CurrentChildType"],
                            "name": j,
                            "onNameConflict": "merge",
                            "notes": ""
                        }
                        newObjInfo = self.GO.call("ak.wwise.core.object.create", args)
                        NewGUIDsPool.append(newObjInfo["id"])
                        LOG.info(j + lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_CreatedNew"][L])

                        # 将新生成的容器，指派到Diff对象上，建立关联
                        args = {
                            "child": newObjInfo["id"],
                            "stateOrSwitch": k
                        }
                        self.GO.call("ak.wwise.core.switchContainer.addAssignment", args)
                        LOG.info(newObjInfo["name"] + lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_AssignNew"][L])

                        # 在这里分流：
                        # 如果刚才新增的容器是SwitchContainer
                        if i["CurrentChildType"] == "SwitchContainer":
                            # LOG.debug(lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_CreateNewSwitchContainer"][L])
                            # 先给刚才新增的SwitchContainer上，指派主干SwitchGroup
                            args = {
                                "object": newObjInfo["id"],
                                "reference": "SwitchGroupOrStateGroup",
                                "value": i["CurrentChildSwitchGroupPath"]
                            }
                            self.GO.call("ak.wwise.core.object.setReference", args)
                            LOG.info(newObjInfo["name"] + lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_AssignNewSwitchGroup"][L])

                            # 再继续批量产生下属容器，并安排指派
                            for m, n in zip(i["CurrentChildSwitchGroupGUID"].keys(),
                                            i["CurrentChildSwitchGroupGUID"].values()):
                                # 产生容器
                                args = {
                                    "parent": newObjInfo["id"],
                                    "type": i["SwitchTargetContainerType"],
                                    "name": m,
                                    "onNameConflict": "merge",
                                    "notes": ""
                                }
                                secNewObjInfo = self.GO.call("ak.wwise.core.object.create", args)
                                LOG.warning(m + lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_CreatedNew"][L])

                                NewGUIDsPool.append(secNewObjInfo["id"])
                                # 安排指派
                                args = {
                                    "child": secNewObjInfo["id"],
                                    "stateOrSwitch": n
                                }
                                self.GO.call("ak.wwise.core.switchContainer.addAssignment", args)
                                LOG.warning(
                                    secNewObjInfo["name"] + lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_AssignNew"][
                                        L])

                            # 准备导入Sound、WAV
                            LOG.info(lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_ReadyToCreateWAV"][L])

                        # 如果刚才新增的容器是BlendContainer，提示将直接产生Sound
                        elif i["CurrentChildType"] == "BlendContainer":
                            # LOG.debug(lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_CreateNewBlendContainer"][L])
                            LOG.warning(lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_ReadyToCreateWAV"][L])

                        # 如果刚才新增的容器是RandomSequenceContainer
                        else:
                            # LOG.debug(lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_CreateNewRanSeqContainer"][L])
                            LOG.warning(lan["LOG_SC_def_CreateAndGetNewPathsOfNewGUIDs_ReadyToCreateWAV"][L])

            # 过滤新增对象中的SwitchContainer，仅保留其他类型的容器，并转换为路径
            NewGUIDsPaths = []
            if len(NewGUIDsPool) != 0:  # NewGUIDsPool是以上新增过的所有容器对象的GUID（通过ak.wwise.core.object.create返回值获取到的）
                for gg in NewGUIDsPool:
                    typeResult = self.GetGUIDCategory(gg)
                    if typeResult != "SwitchContainer":  # 把SwitchContainer的类型排除掉（因为要导入WAV的容器对象不能是Switch类型的容器）
                        pathResult = self.GetGUIDPath(gg)
                        NewGUIDsPaths.append(pathResult)

            # 保存、传出新增GUID对象的路径字符串，作为生成WAV的依据
            if len(NewGUIDsPaths) != 0:
                for pp in NewGUIDsPaths:
                    TotalNewGUIDPaths.append(pp)

        return TotalNewGUIDPaths

    def GetGUIDPath(self, GUID):
        args = {
            "from": {
                "id": [GUID]
            },
            "options": {
                "return": [
                    "path"
                ]
            }
        }
        Result = self.GO.call("ak.wwise.core.object.get", args)
        ObjPath = Result["return"][0]["path"]

        return ObjPath

    def GetGUIDCategory(self, GUID):
        args = {
            "from": {
                "id": [GUID]
            },
            "options": {
                "return": [
                    "type"
                ]
            }
        }
        Result = self.GO.call("ak.wwise.core.object.get", args)
        ObjCategory = Result["return"][0]["type"]

        return ObjCategory

    def getAllContainerInfoFromObjectRefGUID(self, ObjectRefGUID):
        # 初始化待return的对象
        TotalSwitchContainerInfo = []
        ActorMixerPath = self.get_CurrentWwiseSession_ActorMixerWWUPath()

        # 获取SwitchContainerName和SwitchContainerGUID
        getInfoPool = []
        for wwuPath in getWWUPathFromLocal(ActorMixerPath):
            R = getXmlData(wwuPath)
            for x in R:
                # LOG.debug(x)
                if len(x) == 4 and len(x[3]) == 3 and list(x[3])[2] == "ShortID":
                    if x[1] >= 6 and x[2] != "Sound":
                        getInfoPool.append(x)
                        # LOG.warning(x)

        # 预备两个包，一个存纯SwitchContainer的数据，另一个存整体关系的数据
        SwitchRelatedLines = []
        CompContainerLines = []
        wwuFlag = 0
        for line in range(len(getInfoPool)):
            if getInfoPool[line][3]["ID"] == ObjectRefGUID and getInfoPool[line][1] != 6:
                LOG.info(lan["LOG_SC_def_getAllContainerInfoFromObjectRefGUID_InvalidSwitchLayer"][L])
            elif getInfoPool[line][1] == 6 and getInfoPool[line][3]["ID"] == ObjectRefGUID:
                while line < len(getInfoPool) and wwuFlag == 0:
                    # 获取纯SwitchContainer数据包
                    if getInfoPool[line][2] == "SwitchContainer":
                        SwitchRelatedLines.append(getInfoPool[line])
                        # LOG.debug(getInfoPool[line])

                    # 获取整体关系的数据包
                    CompContainerLines.append(getInfoPool[line])
                    # LOG.debug(getInfoPool[line])
                    line += 1
                    if line < len(getInfoPool):
                        if getInfoPool[line][1] == 6:
                            wwuFlag = 1

        # 通过SwitchRelatedLines数据包，首次生成数据框架，先将Name和GUID存起来
        for i in SwitchRelatedLines:
            OneSwitchContainerInfo = {"SwitchContainerName": i[3]["Name"], "SwitchContainerGUID": i[3]["ID"],
                                      "SwitchGroupName": "", "SwitchGroupGUID": "", "SwitchGroupSwitchInfo": [],
                                      "CurUseSwitchAssign": [], "Diff": {}, "CurrentChildType": "",
                                      "CurrentChildSwitchGroupName": "", "CurrentChildSwitchGroupPath": "",
                                      "CurrentChildSwitchGroupGUID": "", "SwitchTargetContainerType": ""}
            TotalSwitchContainerInfo.append(OneSwitchContainerInfo)

        # 重新获取所有行信息，将每个SwitchGUID的SwitchGroup信息筛出来
        getAllReferenceLine = []
        for wwuPath in getWWUPathFromLocal(ActorMixerPath):
            R = getXmlData(wwuPath)
            for x in R:
                # LOG.debug(x)
                if len(x) == 4 and (len(x[3]) == 1 or len(x[3]) == 3):
                    if x[1] >= 6 and x[2] != "Sound" and x[2] != "MediaID" and x[2] != "ActiveSource" and x[2] != "Property":
                        getAllReferenceLine.append(x)
                        # LOG.debug(x)

        # 将每个SwitchGUID的SwitchGroup信息筛出来
        for i in TotalSwitchContainerInfo:
            eachGUID = i["SwitchContainerGUID"]
            # LOG.debug(eachGUID)

            for line in range(len(getAllReferenceLine)):
                # LOG.debug(getAllReferenceLine[line])
                if eachGUID in str(getAllReferenceLine[line]):
                    # LOG.debug(getAllReferenceLine[line])
                    rType = getAllReferenceLine[line][2]
                    # LOG.debug(rType)

                    # 先分离小包！
                    sBro = []
                    refFlag = 0
                    while line < len(getAllReferenceLine) and refFlag == 0:
                        sBro.append(getAllReferenceLine[line])
                        # NameStr = getAllReferenceLine[line][3]["Name"]
                        line += 1
                        if line < len(getAllReferenceLine):
                            if getAllReferenceLine[line][2] == rType:
                                refFlag = 1

                    # 在各自的小包中寻找目标，并分别写入
                    for kk in range(len(sBro)):
                        # LOG.debug(sBro[kk])
                        if "SwitchGroupOrStateGroup" in str(sBro[kk]):
                            i["SwitchGroupName"] = sBro[kk + 1][3]["Name"]
                            i["SwitchGroupGUID"] = sBro[kk + 1][3]["ID"]

                            # 获取SwitchGroup的Switch的信息
                            i["SwitchGroupSwitchInfo"] = self.getSwitchInfoFromSwitchWWU(sBro[kk + 1][3]["Name"])

        # 判断Switch对象下属的容器类型是否统一。先获取信息：SwitchContainerGUID:[Container1, Container2...]
        BigGroup = {}
        for x in range(len(CompContainerLines)):
            secflag = 0
            smallGroup = []
            if CompContainerLines[x][2] == "SwitchContainer":
                iNum = CompContainerLines[x][1]
                rGUID = CompContainerLines[x][3]["ID"]
                while x < len(CompContainerLines) and secflag == 0:
                    if CompContainerLines[x][1] == iNum + 2:
                        # LOG.debug(CompContainerLines[x])
                        smallGroup.append(CompContainerLines[x][2])
                    x += 1
                    if x < len(CompContainerLines):
                        if CompContainerLines[x][1] == iNum:
                            secflag = 1
                BigGroup[rGUID] = smallGroup
        # LOG.debug(BigGroup)

        # 检查每一组中，Container的类型是否唯一
        SameTypeCheckResult = []
        for p, t in zip(list(BigGroup.keys()), list(BigGroup.values())):
            typeList = []
            # LOG.debug(p)
            # LOG.debug(t)
            for count in range(len(t)):
                typeList.append(t[count])

            if len(typeList) != 0:
                # 实际的检查步骤在这里
                sameCheck = typeList.count(typeList[0]) == len(typeList)
                if sameCheck is True:
                    # LOG.debug({p: typeList[0]})
                    # 写入大礼包
                    for i in TotalSwitchContainerInfo:
                        if i["SwitchContainerGUID"] == p:
                            i["CurrentChildType"] = typeList[0]
                else:
                    # LOG.debug({p: "Multi"})
                    # 写入大礼包
                    for i in TotalSwitchContainerInfo:
                        if i["SwitchContainerGUID"] == p:
                            i["CurrentChildType"] = "Multi"

        # 如果SwitchContainer的子集不存在“空”、“Multi”的情况，且也正好是一个SwitchContainer，那么需要分析“所有同层级子集身上的SwitchGroup是否为同一个”
        SCNeedToGetSG = []
        for i in TotalSwitchContainerInfo:
            if i["CurrentChildType"] == "SwitchContainer":
                SCNeedToGetSG.append(i["SwitchContainerGUID"])

        # LOG.debug(SCNeedToGetSG)
        # SCNeedToGetSG中的对象，是子集也是SwitchContainer的SwitchContainer

        # 重新获取所有行信息
        getInfo = []
        for wwuPath in getWWUPathFromLocal(ActorMixerPath):
            R = getXmlData(wwuPath)
            for x in R:
                if len(x) == 4 and len(x[3]) == 3 and list(x[3])[2] == "ShortID":
                    if x[1] >= 6 and x[2] != "Sound":
                        getInfo.append(x)
                        # LOG.debug(x)

        # 获取以每个满足合法条件的Switch为小组的所有二级成员，为下一步抽取纯二级SwitchContainer做准备
        childPool = []
        if len(SCNeedToGetSG) != 0:
            for i in SCNeedToGetSG:
                sBro = []
                for line in range(len(getInfo)):
                    if i in str(getInfo[line]):
                        refNum = getInfo[line][1]

                        quaFlag = 0
                        while line < len(getInfo) and quaFlag == 0:
                            sBro.append(getInfo[line])
                            line += 1
                            if line < len(getInfo):
                                if getInfo[line][1] == refNum:
                                    quaFlag = 1

                childPool.append(sBro)

        # for i in childPool:
        #     for k in i:
        #         LOG.debug(k)

        # 开始抽取二级SwitchContainerGUID
        # SCNeedToGetSG中的GUID --> LayerNum --> LayerNum + 2
        bigBro = {}
        if len(SCNeedToGetSG) != 0 and len(childPool) != 0:
            for i, j in zip(SCNeedToGetSG, childPool):
                # LOG.debug(i)
                sBro = []
                for k in j:
                    if k[1] == j[0][1] + 2:
                        sBro.append(k)
                bigBro[i] = sBro

        # 通过bigBro.values()，获取各自的SwitchGroup。重新获取所有行信息，将每个SwitchGUID的SwitchGroup信息筛出来
        getAllReferenceLine = []
        for wwuPath in getWWUPathFromLocal(ActorMixerPath):
            R = getXmlData(wwuPath)
            for x in R:
                # LOG.debug(x)
                if len(x) == 4 and (len(x[3]) == 1 or len(x[3]) == 3):
                    if x[1] >= 6 and x[2] != "Sound" and x[2] != "MediaID" and x[2] != "ActiveSource" and x[2] != "Property":
                        getAllReferenceLine.append(x)
                        # LOG.debug(x)

        for i, j in zip(bigBro.keys(), bigBro.values()):
            # LOG.debug("----------------")
            tempStore = []
            # LOG.debug(i)
            # LOG.debug(len(j))
            for k in j:
                eachGUID = k[3]["ID"]

                # LOG.debug(eachGUID)  # 需要获取SwitchGroup信息的GUID
                # bBro = []
                for line in range(len(getAllReferenceLine)):  # 逐行遍历大包
                    # LOG.debug(getAllReferenceLine[line])
                    if eachGUID in str(getAllReferenceLine[line]):  # 如果发现了包含目标GUID的行
                        # LOG.debug(getAllReferenceLine[line])
                        rType = getAllReferenceLine[line][2]
                        # LOG.debug(eachGUID)

                        # 先分离小包！
                        sBro = []
                        refFlag = 0
                        while line < len(getAllReferenceLine) and refFlag == 0:
                            sBro.append(getAllReferenceLine[line])
                            line += 1
                            if line < len(getAllReferenceLine):
                                if getAllReferenceLine[line][2] == rType:
                                    refFlag = 1

                        # LOG.debug("sBro:")
                        # LOG.debug(sBro)
                        # 放入待分析的小包！
                        for ee in range(len(sBro)):
                            if sBro[ee][3].get("Name", "") == "SwitchGroupOrStateGroup":
                                tempStore.append(sBro[ee + 1][3]["Name"])
                                # LOG.debug(sBro[ee + 1][3]["Name"])

            # LOG.debug(tempStore)
            if len(tempStore) != 0:
                # 实际的检查步骤在这里
                sameCheck = tempStore.count(tempStore[0]) == len(tempStore)
                if sameCheck is True:
                    # LOG.debug({i: tempStore[0]})
                    # 写入大礼包
                    for qq in TotalSwitchContainerInfo:
                        if qq["SwitchContainerGUID"] == i:
                            qq["CurrentChildSwitchGroupName"] = tempStore[0]
                            # SGPath = self.getSwitchGroupNamePathFromSwitchWWU(tempStore[0])
                            SGPath = self.get_Path_From_SwitchGroupName(tempStore[0])
                            qq["CurrentChildSwitchGroupPath"] = SGPath

                            # 获取SwitchGroup的Switch的信息
                            qq["CurrentChildSwitchGroupGUID"] = self.getSwitchInfoNGFromSwitchWWU(tempStore[0])
                else:
                    # 写入大礼包
                    for qq in TotalSwitchContainerInfo:
                        if qq["SwitchContainerGUID"] == i:
                            qq["CurrentChildSwitchGroupName"] = "Multi"

        # 获取当前SwitchAssign的指派GUID，并添加在大包里
        for i in TotalSwitchContainerInfo:
            GUIDLists = self.getCurUseSwitchAssign(i["SwitchContainerGUID"])
            i["CurUseSwitchAssign"] = GUIDLists

        # 如果"CurrentChildType"是SwitchContainer，分析同层级所有子集的容器类型是否统一，并将结果填充到"SwitchTargetContainerType"
        for i in TotalSwitchContainerInfo:
            # LOG.debug("----------------")
            if len(i["SwitchContainerGUID"]) != 0 and i["CurrentChildType"] == "SwitchContainer":
                # 再次重新获取SwitchContainerName和SwitchContainerGUID
                getInfoPool = []
                for wwuPath in getWWUPathFromLocal(ActorMixerPath):
                    R = getXmlData(wwuPath)
                    for x in R:
                        # LOG.debug(x)
                        if len(x) == 4 and len(x[3]) == 3 and list(x[3])[2] == "ShortID":
                            if x[1] >= 6 and x[2] != "Sound":
                                getInfoPool.append(x)
                                # LOG.debug(x)

                # 将属于当前i["SwitchContainerGUID"]的区间行单独筛选出来
                for line in range(len(getInfoPool)):
                    if i["SwitchContainerGUID"] in str(getInfoPool[line]):
                        # LOG.debug(getInfoPool[line])
                        rNum = getInfoPool[line][1]
                        # LOG.debug(rNum)
                        sBro = []
                        flag = 0
                        while line < len(getInfoPool) and flag == 0:
                            sBro.append(getInfoPool[line])
                            line += 1
                            if line < len(getInfoPool):
                                if getInfoPool[line][1] == rNum:
                                    flag = 1

                        # 抽取第三级容器的行，将容器类型放入list中，待进一步内部对比
                        ThirdLayerContainerTypeList = []
                        for ii in sBro:
                            if ii[1] == rNum + 4:
                                ThirdLayerContainerTypeList.append(ii[2])
                        # LOG.debug(ThirdLayerContainerTypeList)

                        # 对比内部对象差异
                        if len(ThirdLayerContainerTypeList) != 0:
                            sameCheck = ThirdLayerContainerTypeList.count(ThirdLayerContainerTypeList[0]) == len(ThirdLayerContainerTypeList)
                            if sameCheck is True:
                                i["SwitchTargetContainerType"] = ThirdLayerContainerTypeList[0]
                            else:
                                i["SwitchTargetContainerType"] = "Multi"

        # 直接将SwitchAssignDiff信息存入"Diff"
        for i in TotalSwitchContainerInfo:
            diffListResult = self.ShowDiffSwitchObjGUIDForExpandSwitch(i)
            if len(diffListResult) != 0:
                i["Diff"] = diffListResult

        return TotalSwitchContainerInfo

    def ShowDiffSwitchObjGUIDForExpandSwitch(self, SwitchInfoDict: dict):
        if len(SwitchInfoDict["SwitchGroupSwitchInfo"]) != 0:
            aList = list(SwitchInfoDict["SwitchGroupSwitchInfo"].keys())
            bList = SwitchInfoDict["CurUseSwitchAssign"]
            CompareResult = compareLists(aList, bList)
        else:
            CompareResult = []

        CompResult = {}
        if len(CompareResult) != 0:
            # 将GUID变为GUID：Name
            for i, j in zip(SwitchInfoDict["SwitchGroupSwitchInfo"].keys(),
                            SwitchInfoDict["SwitchGroupSwitchInfo"].values()):
                if i in CompareResult:
                    CompResult[j] = i

            return CompResult
        else:
            return {}

    def getCurUseSwitchAssign(self, SwitchContainerGUID):
        args = {
            "id": SwitchContainerGUID
        }
        Results = self.GO.call("ak.wwise.core.switchContainer.getAssignments", args)

        CurSwitchAssignGUIDList = []
        for ii in Results["return"]:
            CurSwitchAssignGUIDList.append(ii["stateOrSwitch"])

        return CurSwitchAssignGUIDList

    def getSwitchInfoNGFromSwitchWWU(self, SwitchGroupName):
        SwitchCups = {}

        for wwuPath in getWWUPathFromLocal(self.get_CurrentWwiseSession_SwitchesWWUPath()):
            tree = ET.parse(wwuPath)
            root = tree.getroot()

            for a in root.iter("SwitchGroup"):
                if a.attrib.get("Name") == SwitchGroupName:
                    for b in a:
                        for c in b:
                            SwitchCups[c.attrib.get("Name")] = c.attrib.get("ID")
        return SwitchCups

    def getSwitchInfoFromSwitchWWU(self, SwitchGroupName):
        SwitchCups = {}

        for wwuPath in getWWUPathFromLocal(self.get_CurrentWwiseSession_SwitchesWWUPath()):
            tree = ET.parse(wwuPath)
            root = tree.getroot()

            for a in root.iter("SwitchGroup"):
                if a.attrib.get("Name") == SwitchGroupName:
                    for b in a:
                        for c in b:
                            SwitchCups[c.attrib.get("ID")] = c.attrib.get("Name")
        return SwitchCups

    def GetNewInfoForIndiExpandSwitchFunc(self, Fname, RDM, NewPaths: list):
        # 获取一级SwitchGroup的所有Switch对象名，用于移除type2d、type3d字符串中的局部部分
        MultiPlayerSwitchGroupName = KeyInfoDict["Data_KeyInfo"][Fname]["Property_SwitchGroupName_PC_NPC"]
        MPSwitchList = self.getSwitchFromSwitchWWU(MultiPlayerSwitchGroupName)
        typeStr = KeyInfoDict["Data_KeyInfo"][Fname]["Structure_Type"]
        PathAndWAVPair = []

        if typeStr == "type2d":
            LOG.info(lan["LOG_SM_def_WaapiGo_type2dDetected"][L])
            # 剪裁新路径字符串
            NewPathsCut = []
            if len(NewPaths) != 0:
                for i in NewPaths:
                    for j in MPSwitchList:
                        if ("\\" + j) in str(i):
                            if str(i)[-(len("\\" + j)):] == "\\" + j:
                                k = str(i).replace("\\" + j, "")
                                # LOG.debug(k)
                                NewPathsCut.append(k)

            # 安全检查，检查对比TarActorPath，没问题的话，去除TarActorPath字符串，获得WAV根字符串
            TarActorPath = KeyInfoDict["Data_KeyInfo"][Fname]["Path_InWwise_TargetActorMixer"]
            PathERLog = []
            for i in NewPathsCut:
                if (TarActorPath + "\\") not in i:
                    PathERLog.append(i)
                    LOG.warning(lan["LOG_SM_def_WaapiGo_CanNotFindTarActorPath"][L] + i)

            # LOG.debug(PathERLog)
            # RootWAVStr
            RootWAVStr = []
            if len(PathERLog) == 0:
                for i in NewPathsCut:
                    ii = i.replace(TarActorPath + "\\", "")
                    jj = ii.replace("\\", "_")
                    RootWAVStr.append(jj)
                    # LOG.debug(jj)

            # 目标路径和WAV配对
            if len(RootWAVStr) != 0:
                for i, kk in zip(NewPaths, RootWAVStr):
                    # LOG.debug(i)
                    # LOG.debug(kk)
                    wavList = []
                    for rdm in range(1, int(RDM) + 1):
                        wavList.append(kk + "_0" + str(rdm))
                    PathAndWAVPair.append({i: wavList})

        elif typeStr == "type3d":
            LOG.info(lan["LOG_SM_def_WaapiGo_type3dDetected"][L])
            # 剪裁新路径字符串
            NewPathsCut = []
            if len(NewPaths) != 0:
                for i in NewPaths:
                    for j in MPSwitchList:
                        if ("\\" + j + "\\") in str(i):
                            k = str(i).replace("\\" + j, "")
                            # LOG.debug(k)
                            NewPathsCut.append(k)

            # 安全检查，检查对比TarActorPath，没问题的话，去除TarActorPath字符串，获得WAV根字符串
            TarActorPath = KeyInfoDict["Data_KeyInfo"][Fname]["Path_InWwise_TargetActorMixer"]
            PathERLog = []
            for i in NewPathsCut:
                if (TarActorPath + "\\") not in i:
                    PathERLog.append(i)
                    LOG.warning(lan["LOG_SM_def_WaapiGo_CanNotFindTarActorPath"][L] + i)

            # LOG.debug(PathERLog)
            # RootWAVStr
            RootWAVStr = []
            if len(PathERLog) == 0:
                for i in NewPathsCut:
                    ii = i.replace(TarActorPath + "\\", "")
                    jj = ii.replace("\\", "_")
                    RootWAVStr.append(jj)
                    # LOG.debug(jj)

            # 目标路径和WAV配对
            if len(RootWAVStr) != 0:
                for i, kk in zip(NewPaths, RootWAVStr):
                    # LOG.debug(i)
                    # LOG.debug(kk)
                    wavList = []
                    for rdm in range(1, int(RDM) + 1):
                        wavList.append(kk + "_0" + str(rdm))
                    PathAndWAVPair.append({i: wavList})

        elif typeStr == "typet":
            LOG.info(lan["LOG_SM_def_WaapiGo_typetDetected"][L])
            # 安全检查，检查对比TarActorPath，没问题的话，去除TarActorPath字符串，获得WAV根字符串
            TarActorPath = KeyInfoDict["Data_KeyInfo"][Fname]["Path_InWwise_TargetActorMixer"]
            PathERLog = []
            for i in NewPaths:
                if (TarActorPath + "\\") not in i:
                    PathERLog.append(i)
                    LOG.warning(lan["LOG_SM_def_WaapiGo_CanNotFindTarActorPath"][L] + i)

            # LOG.debug(PathERLog)
            # RootWAVStr
            RootWAVStr = []
            if len(PathERLog) == 0:
                for i in NewPaths:
                    ii = i.replace(TarActorPath + "\\", "")  # 移除模板路径字符串部分
                    jj = ii.replace("\\", "_")  # 将路径分隔符替换为下划线
                    RootWAVStr.append(jj)
                    # LOG.debug(jj)
                    # LOG.debug(i)

            # 目标路径和WAV配对
            if len(RootWAVStr) != 0:
                # LOG.debug("len of NewPaths: " + str(len(NewPaths)))
                # LOG.debug("len of RootWAVStr: " + str(len(RootWAVStr)))
                for i, kk in zip(NewPaths, RootWAVStr):
                    # LOG.debug(i)
                    # LOG.debug(kk)
                    wavList = []
                    for rdm in range(1, int(RDM) + 1):
                        wavList.append(kk + "_0" + str(rdm))
                    PathAndWAVPair.append({i: wavList})
        else:
            LOG.warning(lan["LOG_SC_def_ExpandSwitchInvalidType_FAIL"][L])

        return PathAndWAVPair

    def ImportNewObjsForExpandSwitchFunc(self, Id, Fname, Sname, Tname, Rannum, PathWavPair: list):
        NamePool = self.nameStrGenWithoutCheckDuplicate(Id, Fname, Sname, Tname, Rannum)
        if len(PathWavPair) != 0:
            SourceWAVPath = os.path.join(global_curWwisePath, KeyInfoDict["Data_KeyInfo"][Fname]["Path_Folder_TargetWAV"])
            ifPitchRandom = KeyInfoDict["Data_KeyInfo"][Fname]["Property_ifPitchRandom"]
            ifStream = KeyInfoDict["Data_KeyInfo"][Fname]["Property_ifStream"]
            for i in PathWavPair:
                for path, wavStrList in zip(i.keys(), i.values()):
                    for s in wavStrList:
                        # import WAV
                        args = {
                            "importOperation": "useExisting",
                            "default": {"importLanguage": "SFX"},
                            "imports": [{
                                "audioFile": SourceWAVPath + s + ".wav",
                                "objectPath": path + "\\<Sound SFX>" + s
                            }]
                        }
                        self.GO.call("ak.wwise.core.audio.import", args)
                        LOG.info(s + lan["LOG_SC_def_ImportNewObjsForExpandSwitchFunc_WAVImported"][L])

                        # Set Randomizer for RandomContainer
                        if ifPitchRandom == "True":
                            args = {
                                "object": path + "\\" + s,
                                "property": "Pitch",
                                "enabled": True,
                                "min": KeyInfoDict["InitPitchRandomMin"],
                                "max": KeyInfoDict["InitPitchRandomMax"]
                            }
                            result = self.GO.call("ak.wwise.core.object.setRandomizer", args)
                            if result is None:
                                LOG.info(lan["LOG_SM_PitchRandom_FAIL"][L])

                        # Set WAV Stream
                        if ifStream == "True":
                            args = {
                                "object": path + "\\" + s,
                                "property": "IsStreamingEnabled",
                                "value": "true"
                            }
                            self.GO.call("ak.wwise.core.object.setProperty", args)

                        # Set Loop for SFX
                        if NamePool[1][1][-3:] == "_LP":
                            args = {
                                "object": path + "\\" + s,
                                "property": "IsLoopingEnabled",
                                "value": "True"
                            }
                            self.GO.call("ak.wwise.core.object.setProperty", args)

                        # Save the Project
                        args = {}
                        self.GO.call("ak.wwise.core.project.save", args)

    def getObjectRefGUIDFromEventStr(self, EventStr):
        ObjectRefGUIDList = []

        for wwuPath in getWWUPathFromLocal(self.get_CurrentWwiseSession_EventsWWUPath()):
            tree = ET.parse(wwuPath)
            root = tree.getroot()

            for a in root:
                for b in a:
                    for c in b:
                        for d in c:
                            if d.attrib.get("Name") == EventStr:
                                for e in d:
                                    for f in e:
                                        for g in f:
                                            for h in g:
                                                for i in h:
                                                    if i.attrib.get("ID") is not None:
                                                        ObjectRefGUIDList.append(i.attrib.get("ID"))
        return ObjectRefGUIDList

    def getWAVPathsFromObjectRefGUID(self, GUID):
        WavPathList = []
        for wwuPath in getWWUPathFromLocal(self.get_CurrentWwiseSession_ActorMixerWWUPath()):
            tree = ET.parse(wwuPath)
            root = tree.getroot()

            for a in root.iter("ChildrenList"):
                for b in a:
                    if b.attrib.get("ID") == GUID:
                        # LOG.debug(b.attrib.get("Name"))
                        for c in b.iter("AudioFileSource"):
                            for d in c.iter("Language"):
                                wavType = d.text
                                for e in c.iter("AudioFile"):
                                    # LOG.debug(wavType + "\\" + e.text)
                                    WavPathList.append(wavType + "\\" + e.text)
        return WavPathList

    def RenameEventToDisuse(self, OldNameStr):
        errorLog = []

        args = {
            "from": {
                "name": ["Event:" + OldNameStr]
            },
            "options": {
                "return": ["id"]
            }
        }
        result = self.GO.call("ak.wwise.core.object.get", args)

        TarEventGUID = result["return"][0]["id"]
        args = {
            "object": TarEventGUID,
            "value": OldNameStr + "_disuse"
        }
        status = self.GO.call("ak.wwise.core.object.setName", args)

        # Save the Project
        args = {}
        self.GO.call("ak.wwise.core.project.save", args)

        if len(str(status)) != 0:
            errorLog.append(str(status))
            return errorLog

    def RenameObjNameToDisuseByGUID(self, GUID):
        errorLog = []
        try:
            args = {
                "from": {
                    "id": [GUID]
                }
            }
            NameStrResult = self.GO.call("ak.wwise.core.object.get", args)

            args = {
                "object": GUID,
                "value": NameStrResult["return"][0]["name"] + "_disuse"
            }
            status = self.GO.call("ak.wwise.core.object.setName", args)

            # Save the Project
            args = {}
            self.GO.call("ak.wwise.core.project.save", args)

            if len(str(status)) != 0:
                errorLog.append(str(status))
                return errorLog

        except:
            LOG.error(lan["LOG_WG_def_RenameObjNameToDisuseByGUID_FAIL"][L])

    def ColorGUID(self, guid):
        args = {
            "object": guid,
            "property": "OverrideColor",
            "value": "true"
        }
        result = self.GO.call("ak.wwise.core.object.setProperty", args)
        if result is None:
            LOG.INFO(lan["LOG_SM_SetColor_FAIL"][L])

        args = {
            "object": guid,
            "property": "Color",
            "value": KeyInfoDict["WWISEColor"]
        }
        result = self.GO.call("ak.wwise.core.object.setProperty", args)
        if result is None:
            LOG.INFO(lan["LOG_SM_SetColor_FAIL"][L])

    def Check_IfKeyStrWWUInWwise(self, keystr):
        if len(keystr) != 0:
            possiblePath_Actor = "\\Actor-Mixer Hierarchy\\Audio_" + keystr + "\\" + keystr
            possiblePath_Event = "\\Events\\Event_" + keystr
            possiblePath_Bank = "\\SoundBanks\\Bank_" + keystr + "\\" + "Bank_" + keystr
            possiblePathList = [possiblePath_Actor, possiblePath_Event, possiblePath_Bank]

            if self.GO is not None:
                checkResultCount = 0
                for iPath in possiblePathList:
                    args = {
                        "from": {
                            "path": [iPath]
                        },
                        "options": {
                            "return": ["id"]
                        }
                    }
                    Result = self.GO.call("ak.wwise.core.object.get", args)
                    # LOG.debug(Result)
                    if Result is None:
                        checkResultCount += 1

                if checkResultCount == 0:
                    return True
                else:
                    return False
            else:
                return False

    def Check_IfPathsOfKeyStrExistInWwise(self, keystr):
        text_Structure_Type = KeyInfoDict["Data_KeyInfo"][keystr]["Structure_Type"]
        text_Path_InWwise_UserDefinedTemplate = KeyInfoDict["Data_KeyInfo"][keystr]["Path_InWwise_UserDefinedTemplate"]
        text_Path_InWwise_TargetActorMixer = KeyInfoDict["Data_KeyInfo"][keystr]["Path_InWwise_TargetActorMixer"]
        text_Path_InWwise_TargetEvent = KeyInfoDict["Data_KeyInfo"][keystr]["Path_InWwise_TargetEvent"]
        text_Path_InWwise_TargetBank = KeyInfoDict["Data_KeyInfo"][keystr]["Path_InWwise_TargetBank"]
        text_Property_Conversion = KeyInfoDict["Data_KeyInfo"][keystr]["Property_Conversion"]
        text_Property_Positioning = KeyInfoDict["Data_KeyInfo"][keystr]["Property_Positioning"]
        text_Property_Bus = KeyInfoDict["Data_KeyInfo"][keystr]["Property_Bus"]
        text_Property_Bus_NPC = KeyInfoDict["Data_KeyInfo"][keystr]["Property_Bus_NPC"]
        text_Property_SwitchGroupName_PC_NPC = KeyInfoDict["Data_KeyInfo"][keystr]["Property_SwitchGroupName_PC_NPC"]
        text_Property_SwitchGroupName_Texture = KeyInfoDict["Data_KeyInfo"][keystr]["Property_SwitchGroupName_Texture"]

        invalidCount = []
        if text_Structure_Type == "type1d" or text_Structure_Type == "type1d_vo":
            result = self.get_GUIDOfPath(text_Path_InWwise_TargetActorMixer)
            if result is None:
                invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Path_InWwise_TargetActorMixer)
            result = self.get_GUIDOfPath(text_Path_InWwise_TargetEvent)
            if result is None:
                invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Path_InWwise_TargetEvent)
            result = self.get_GUIDOfPath(text_Path_InWwise_TargetBank)
            if result is None:
                invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Path_InWwise_TargetBank)

            if len(text_Property_Bus) != 0:
                result = self.get_GUIDOfPath(text_Property_Bus)
                if result is None:
                    invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Property_Bus)
            if len(text_Property_Conversion) != 0:
                result = self.get_GUIDOfPath(text_Property_Conversion)
                if result is None:
                    invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Property_Conversion)
            if len(text_Property_Positioning) != 0:
                result = self.get_GUIDOfPath(text_Property_Positioning)
                if result is None:
                    invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Property_Positioning)

        elif text_Structure_Type == "type2d" or text_Structure_Type == "type2d_vo":
            result = self.get_GUIDOfPath(text_Path_InWwise_TargetActorMixer)
            if result is None:
                invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Path_InWwise_TargetActorMixer)
            result = self.get_GUIDOfPath(text_Path_InWwise_TargetEvent)
            if result is None:
                invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Path_InWwise_TargetEvent)
            result = self.get_GUIDOfPath(text_Path_InWwise_TargetBank)
            if result is None:
                invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Path_InWwise_TargetBank)

            if len(text_Property_Bus) != 0:
                result = self.get_GUIDOfPath(text_Property_Bus)
                if result is None:
                    invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Property_Bus)
            if len(text_Property_Conversion) != 0:
                result = self.get_GUIDOfPath(text_Property_Conversion)
                if result is None:
                    invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Property_Conversion)
            if len(text_Property_Positioning) != 0:
                result = self.get_GUIDOfPath(text_Property_Positioning)
                if result is None:
                    invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Property_Positioning)

            if len(text_Property_Bus_NPC) == 0:
                invalidCount.append(lan["LOG_WwisePathIsInvalid_NPCPathMissing"][L] + keystr)
            else:
                result = self.get_GUIDOfPath(text_Property_Bus_NPC)
                if text_Property_Bus_NPC == text_Property_Bus:
                    invalidCount.append(lan["LOG_WwisePathIsInvalid_NPCPathSameAsPCBus"][L] + keystr)
                elif result is None:
                    invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Property_Bus_NPC)

            if len(text_Property_SwitchGroupName_PC_NPC) == 0:
                invalidCount.append(lan["LOG_WwisePathIsInvalid_SwitchOfNPCBusMissing"][L] + keystr)
            else:
                result = self.get_Path_From_SwitchGroupName(text_Property_SwitchGroupName_PC_NPC)
                if result is None:
                    invalidCount.append(lan["LOG_ObjectIsNotExistInWwise"][L] + text_Property_SwitchGroupName_PC_NPC)
                else:
                    switchList = self.getSwitchFromSwitchWWU(text_Property_SwitchGroupName_PC_NPC)
                    if len(switchList) != 2:
                        invalidCount.append(lan["LOG_SwitchGroupChildIsNotTwo"][L] + text_Property_SwitchGroupName_PC_NPC)

        elif text_Structure_Type == "type3d":
            result = self.get_GUIDOfPath(text_Path_InWwise_TargetActorMixer)
            if result is None:
                invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Path_InWwise_TargetActorMixer)
            result = self.get_GUIDOfPath(text_Path_InWwise_TargetEvent)
            if result is None:
                invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Path_InWwise_TargetEvent)
            result = self.get_GUIDOfPath(text_Path_InWwise_TargetBank)
            if result is None:
                invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Path_InWwise_TargetBank)

            if len(text_Property_Bus_NPC) == 0:
                invalidCount.append(lan["LOG_WwisePathIsInvalid_NPCPathMissing"][L] + keystr)
            else:
                result = self.get_GUIDOfPath(text_Property_Bus_NPC)
                if text_Property_Bus_NPC == text_Property_Bus:
                    invalidCount.append(lan["LOG_WwisePathIsInvalid_NPCPathSameAsPCBus"][L] + keystr)
                elif result is None:
                    invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Property_Bus_NPC)

            if len(text_Property_SwitchGroupName_PC_NPC) == 0:
                invalidCount.append(lan["LOG_WwisePathIsInvalid_SwitchOfNPCBusMissing"][L] + keystr)
            else:
                result = self.get_Path_From_SwitchGroupName(text_Property_SwitchGroupName_PC_NPC)
                if result is None:
                    invalidCount.append(lan["LOG_ObjectIsNotExistInWwise"][L] + text_Property_SwitchGroupName_PC_NPC)
                else:
                    switchList = self.getSwitchFromSwitchWWU(text_Property_SwitchGroupName_PC_NPC)
                    if len(switchList) != 2:
                        invalidCount.append(lan["LOG_SwitchGroupChildIsNotTwo"][L] + text_Property_SwitchGroupName_PC_NPC)

            if len(text_Property_SwitchGroupName_Texture) == 0:
                invalidCount.append(lan["LOG_WwisePathIsInvalid_SwitchOfTextureMissing"][L] + keystr)
            else:
                result = self.get_Path_From_SwitchGroupName(text_Property_SwitchGroupName_Texture)
                if text_Property_SwitchGroupName_Texture == text_Property_SwitchGroupName_PC_NPC:
                    invalidCount.append(lan["LOG_WwisePathIsInvalid_SwitchOfTextureSameAsPCNPC"][L] + keystr)
                elif result is None:
                    invalidCount.append(lan["LOG_ObjectIsNotExistInWwise"][L] + text_Property_SwitchGroupName_Texture)
                else:
                    switchList = self.getSwitchFromSwitchWWU(text_Property_SwitchGroupName_Texture)
                    if len(switchList) == 0:
                        invalidCount.append(lan["LOG_SwitchGroupIsEmpty"][L] + text_Property_SwitchGroupName_Texture)

        elif text_Structure_Type == "typet":
            result = self.get_GUIDOfPath(text_Path_InWwise_TargetActorMixer)
            if result is None:
                invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Path_InWwise_TargetActorMixer)
            result = self.get_GUIDOfPath(text_Path_InWwise_TargetEvent)
            if result is None:
                invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Path_InWwise_TargetEvent)
            result = self.get_GUIDOfPath(text_Path_InWwise_TargetBank)
            if result is None:
                invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Path_InWwise_TargetBank)
            result = self.get_GUIDOfPath(text_Path_InWwise_UserDefinedTemplate)
            if result is None:
                invalidCount.append(lan["LOG_PathIsNotExistInWwise"][L] + text_Path_InWwise_UserDefinedTemplate)

        return invalidCount

    def __del__(self):
        try:
            self.GO.disconnect()
            # LOG.debug("[*]\n")
        except:
            LOG.debug("[SimpleWaapi - Interrupted - Disconnected]")
            traceback.print_exc()

