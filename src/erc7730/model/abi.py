from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field

from erc7730.model.base import BaseLibraryModel


class StateMutability(StrEnum):
    pure = "pure"
    view = "view"
    nonpayable = "nonpayable"
    payable = "payable"


class Component(BaseLibraryModel):
    name: str
    type: str
    internalType: str | None = None
    components: list[Self] | None = None


class InputOutput(BaseLibraryModel):
    name: str
    type: str
    internalType: str | None = None
    components: list[Component] | None = None
    indexed: bool | None = None
    unit: str | None = None


class Function(BaseLibraryModel):
    type: Literal["function"] = "function"
    name: str | None = None
    inputs: list[InputOutput] | None = None
    outputs: list[InputOutput] | None = None
    stateMutability: StateMutability | None = None
    gas: int | None = None
    signature: str | None = None


class Constructor(BaseLibraryModel):
    type: Literal["constructor"] = "constructor"
    name: str | None = None
    inputs: list[InputOutput] | None = None
    outputs: list[InputOutput] | None = None
    stateMutability: StateMutability | None = None
    gas: int | None = None
    signature: str | None = None


class Receive(BaseLibraryModel):
    type: Literal["receive"] = "receive"
    name: str | None = None
    inputs: list[InputOutput] | None = None
    outputs: list[InputOutput] | None = None
    stateMutability: StateMutability | None = None
    gas: int | None = None
    signature: str | None = None


class Fallback(BaseLibraryModel):
    type: Literal["fallback"] = "fallback"
    name: str | None = None
    inputs: list[InputOutput] | None = None
    outputs: list[InputOutput] | None = None
    stateMutability: StateMutability | None = None
    gas: int | None = None
    signature: str | None = None


class Event(BaseLibraryModel):
    type: Literal["event"] = "event"
    name: str
    inputs: list[InputOutput]
    anonymous: bool = False
    signature: str | None = None


class Error(BaseLibraryModel):
    type: Literal["error"] = "error"
    name: str
    inputs: list[InputOutput]
    signature: str | None = None


ABI = Annotated[Constructor | Event | Function | Fallback | Error | Receive, Field(discriminator="type")]
