from pydantic import BaseModel
from datetime import datetime, date


class PeopleModifiedAfterSchema(BaseModel):
    mdtz: datetime
    ctzoffset: int
    buid: int


class PeopleEventLogPunchInsSchema(BaseModel):
    datefor: date
    buid: int
    peopleid: int


class PgbelongingModifiedAfterSchema(BaseModel):
    mdtz: datetime
    ctzoffset: int
    buid: int
    peopleid: int


class PeopleEventLogHistorySchema(BaseModel):
    mdtz: datetime
    ctzoffset: int
    buid: int
    peopleid: int
    clientid: int
    peventtypeid: int


class AttachmentSchema(BaseModel):
    owner: str

