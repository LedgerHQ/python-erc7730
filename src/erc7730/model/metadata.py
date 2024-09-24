from datetime import datetime
from erc7730.model.base import BaseLibraryModel
from typing import Union, Optional, Dict


class OwnerInfo(BaseLibraryModel):
    legalName: str
    lastUpdate: Optional[datetime]
    url: str


class TokenInfo(BaseLibraryModel):
    name: str
    ticker: str
    decimals: int


class Metadata(BaseLibraryModel):
    owner: Optional[str] = None
    info: Optional[OwnerInfo] = None
    token: Optional[TokenInfo] = None
    constants: Optional[Dict[str, str]] = None
    enums: Optional[Dict[str, Union[str, Dict[str, str]]]] = None
