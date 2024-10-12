'''枚举可能用到的模型状态'''
from enum import Enum


class ModelStatus(str, Enum):
    
    INITIAL = "initial"
    BUILDING = "building"
    READY = "ready"
    FAILED = "failed"
    INVALID = "invalid"
    DELETED = "deleted"
    UNKNOWN = "unknown"


class Modelbase(object):
    def __init__(self, id=None, *args, **kwargs):
        self._model_status = ModelStatus.FAILED
        self._user_id = id 
    
    @property
    def model_status(self):
        return self._model_status
    
    @property
    def user_id(self):
        return self._user_id
    
    # 新增修改 user_id 的函数
    def set_user_id(self, new_id):
        self._user_id = new_id
