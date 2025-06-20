from pydantic import BaseModel
from typing import List
from datetime import datetime


class LocationSchema(BaseModel):
    mdtz:datetime
    ctzoffset:int
    buid:int 


class GeofenceSchema(BaseModel):
    siteids:List[int]


class ShiftSchema(BaseModel):
    mdtz:datetime
    buid:int
    clientid:int


class GroupsModifiedAfterSchema(BaseModel):
    mdtz:datetime
    ctzoffset:int
    buid:int

class SiteListSchema(BaseModel):
    clientid:int
    peopleid:int

class SendEmailVerificationLinkSchema(BaseModel):
    clientcode:str
    loginid:str

class SuperAdminMessageSchema(BaseModel):
    client_id:int

class SiteVisitedLogSchema(BaseModel):
    ctzoffset:int
    clientid:int
    peopleid:int

class VerifyClientSchema(BaseModel):
    clientcode:str