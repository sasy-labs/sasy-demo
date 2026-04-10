"""Convert a Python function into an OpenAI tool schema."""

import inspect
from inspect import Signature
from typing import Any, Callable, Optional

from docstring_parser import parse
import logging

logger = logging.getLogger(__name__)
from pydantic import (
    BaseModel, ConfigDict, Field, create_model,
)


class Tool(BaseModel):
    """Tool built from a Python function."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = Field(..., description="Tool name")
    short_desc: str = Field("", description="Short desc")
    long_desc: str = Field("", description="Long desc")
    params: type[BaseModel] = Field(
        ..., description="Parameter model"
    )

    def __init__(
        self, func: Callable,
        use_short_desc: bool = False,
        **predefined: Any,
    ) -> None:
        """Create a tool from *func*."""
        sig = inspect.signature(func)
        super().__init__(
            name=func.__name__,
            **_parse_data(sig, func.__doc__, predefined),
        )
        self._use_short_desc = use_short_desc
        self._predefined = predefined
        self._func = func
        self.__name__ = func.__name__
        self.__signature__ = sig  # type: ignore
        self.__doc__ = func.__doc__

    @property
    def openai_schema(self) -> dict[str, Any]:
        """Return OpenAI function-calling tool schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self._desc(),
                "parameters": (
                    self.params.model_json_schema()
                ),
            },
        }

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Call the underlying function."""
        kwargs.update(self._predefined)
        return self._func(*args, **kwargs)

    def _desc(self) -> str:
        if not self.short_desc:
            logger.warning(f"Tool {self.name}: no desc")
            return self.name
        if not self.long_desc or self._use_short_desc:
            return self.short_desc
        return self.short_desc + "\n\n" + self.long_desc


def _parse_data(
    sig: Signature,
    docstring: Optional[str],
    predefined: dict[str, Any],
) -> dict[str, Any]:
    """Parse signature + docstring into Tool fields."""
    doc = parse(docstring or "")
    data: dict[str, Any] = {
        "short_desc": doc.short_description or "",
        "long_desc": doc.long_description or "",
    }
    params: dict[str, Any] = {}
    doc_param = {p.arg_name: p for p in doc.params}
    for pname, param in sig.parameters.items():
        anno = param.annotation
        default = param.default
        if default is param.empty:
            default = ...
        if pname in doc_param:
            default = Field(
                default,
                description=doc_param[pname].description,
            )
            if (anno is param.empty
                    and doc_param[pname].type_name):
                anno = doc_param[pname].type_name
        if anno is param.empty:
            anno = Any
        if pname not in predefined:
            params[pname] = (anno, default)
    data["params"] = create_model(
        "parameters", **params
    )  # type: ignore[call-overload]
    return data


def as_tool(func: Callable, **kwargs: Any) -> Tool:
    """Wrap *func* into a Tool, hiding *kwargs* from schema."""
    return Tool(func=func, **kwargs)
