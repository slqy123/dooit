from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional
from uuid import uuid4
from dataclasses import dataclass
from dooit.api.workspace import ModelType

if TYPE_CHECKING: # pragma: no cover
    from dooit.ui.api.dooit_api import DooitAPI


@dataclass
class FormatterFunc:
    name: str
    func: Callable
    disabled: bool = False


def trigger_refresh(func: Callable) -> Callable:
    def wrapper(self: "FormatterStore", *args, **kwargs):
        res = func(self, *args, **kwargs)
        self.trigger()
        return res

    return wrapper


class FormatterStore:
    def __init__(self, trigger: Callable, api: "DooitAPI") -> None:
        self.formatters = dict(
            default=FormatterFunc(
                "dooit_default",
                lambda x, *_: str(x),
            )
        )
        self.trigger = trigger
        self.api = api

    @trigger_refresh
    def add(self, func: Callable, id: Optional[str] = None) -> str:
        id = id or uuid4().hex
        self.formatters[id] = FormatterFunc(
            id,
            func,
        )
        return id

    @trigger_refresh
    def remove(self, id: str) -> None:
        self.formatters.pop(id, None)

    @trigger_refresh
    def disable(self, id: str) -> bool:
        formatter = self.formatters.get(id)
        if not formatter:
            return False

        formatter.disabled = True
        return True

    @trigger_refresh
    def enable(self, id: str, set_current: bool = False) -> bool:
        formatter = self.formatters.get(id)
        if not formatter:
            return False

        formatter.disabled = False

        if set_current:
            formatter = self.formatters.pop(id)
            self.formatters.update({id: formatter})

        return True

    @property
    def formatter_functions(self) -> List[Callable]:
        return [
            formatter.func
            for formatter in self.formatters.values()
            if not formatter.disabled
        ]

    def _get_function_params(self, func: Callable) -> List[str]:
        return list(func.__code__.co_varnames)

    def format_value(self, value: Any, model: ModelType) -> str:
        params = dict(api=self.api)

        def get_extra_args(func: Callable) -> Dict[str, Any]:
            func_params = self._get_function_params(func)
            extra_args = {}

            for param in func_params:
                if param in params:
                    extra_args[param] = params[param]

            return extra_args

        res = None

        for func in reversed(self.formatter_functions):
            res = func(value, model, **get_extra_args(func))
            if res is not None:
                return res

        return "???"
