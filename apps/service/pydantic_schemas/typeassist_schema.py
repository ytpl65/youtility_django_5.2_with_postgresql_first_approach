from pydantic import BaseModel
from typing import List
from datetime import datetime


class TypeAssistSchema(BaseModel):
    keys : List[str]


class TypeAssistModifiedFilterSchema(BaseModel):
    mdtz : datetime
    ctzoffset : int
    clientid : int