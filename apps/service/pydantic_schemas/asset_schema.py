from pydantic import BaseModel
from datetime import datetime


class AssetFilterSchema(BaseModel):
    mdtz:datetime
    ctzoffset:int
    buid:int

    