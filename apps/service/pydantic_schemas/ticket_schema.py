from pydantic import BaseModel
from datetime import datetime


class TicketSchema(BaseModel):
    peopleid: int
    buid: int
    clientid: int
    mdtz: datetime
    ctzoffset: int
