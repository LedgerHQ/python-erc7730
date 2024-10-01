"""
Base model for library, using pydantic.

See https://docs.pydantic.dev
"""

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    """
    Base model for library, using pydantic.

    See https://docs.pydantic.dev
    """

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        validate_default=True,
        validate_return=True,
        use_enum_values=True,
        validate_assignment=True,
        arbitrary_types_allowed=False,
        allow_inf_nan=False,
    )
