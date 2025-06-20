from pydantic import BaseModel


class JobneedModifiedAfterSchema(BaseModel):
    peopleid: int
    buid: int
    clientid: int


class JobneedDetailsModifiedAfterSchema(BaseModel):
    jobneedids: str # comma separated jobneedids
    ctzoffset: int


class ExternalTourModifiedAfterSchema(BaseModel):
    peopleid: int
    buid: int
    clientid: int


