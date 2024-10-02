from typing import Callable
from rich.console import RenderableType
from .._base import BarBase

DEFFAULT_MSG = r"Are you sure? \[y/N]"


class ConfirmBar(BarBase):
    DEFAULT_CSS = """
    ConfirmBar {
        padding-left: 1;
        padding-right: 1;
    }
    """

    def __init__(
        self,
        callback: Callable,
        message: str = DEFFAULT_MSG,
        *args,
        **kwargs,
    ):
        super().__init__(callback, *args, **kwargs)
        self.message = message

    def perform_action(self, cancel: bool):
        if not cancel:
            self.callback()

    def flash_confirm(self, cancelled: bool):
        self.focused = False
        if not cancelled:
            self.message = "The items were deleted!"
            self.add_class("not-cancelled")
        else:
            self.message = "The items were retained!"
            self.add_class("cancelled")

        self.refresh()
        self.set_interval(1.2, self.close)

    async def handle_keypress(self, key: str) -> None:
        cancel = key.lower() != "y"
        self.flash_confirm(cancel)
        self.dismiss(cancel, close=False)

    def render(self) -> RenderableType:
        return self.message