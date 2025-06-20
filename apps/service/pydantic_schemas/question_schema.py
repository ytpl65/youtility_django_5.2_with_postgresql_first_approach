from pydantic import BaseModel
from datetime import datetime

class QuestionModifiedSchema(BaseModel):
    mdtz: datetime
    ctzoffset: int
    clientid: int


class QuestionSetModifiedSchema(BaseModel):
    mdtz: datetime
    ctzoffset: int
    buid: int
    clientid: int
    peopleid: int


class QuestionSetBelongingModifiedSchema(BaseModel):
    mdtz: datetime
    ctzoffset: int
    buid: int