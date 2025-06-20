from pydantic import BaseModel


class WomPdfUrlSchema(BaseModel):
    wom_uuid: str
    peopleid: int

class WomRecordSchema(BaseModel):
    workpermit: str
    peopleid: int
    buid: int
    parentid: int
    clientid: int
    fromdate: str
    todate: str

class ApproveWorkpermitSchema(BaseModel):
    peopleid: int
    identifier: str
    wom_uuid: str


class RejectWorkpermitSchema(BaseModel):
    peopleid: int
    identifier: str
    wom_uuid: str


class ApproverSchema(BaseModel):
    buid: int
    clientid: int


class VendorSchema(BaseModel):
    clientid: int
    mdtz: str
    buid: int
    ctzoffset: int