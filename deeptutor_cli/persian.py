"""Persian help chrome for the retained web-app launcher commands.

Keep Typer's parser and option names unchanged; localize presentation through
its public command/group extension points rather than patching the framework.
"""

from __future__ import annotations

import typer
from typer.core import TyperCommand, TyperGroup


class _PersianHelp:
    def get_usage(self, ctx):
        return (
            super().get_usage(ctx)
            .replace("Usage:", "روش استفاده:")
            .replace("[OPTIONS]", "[گزینه‌ها]")
            .replace("COMMAND [ARGS]...", "دستور [آرگومان‌ها]...")
        )

    def get_help_option(self, ctx):
        option = super().get_help_option(ctx)
        if option is not None:
            option.help = "نمایش راهنما و خروج."
        return option


class PersianCommand(_PersianHelp, TyperCommand):
    pass


class PersianGroup(_PersianHelp, TyperGroup):
    pass


class PersianTyper(typer.Typer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("cls", PersianGroup)
        super().__init__(*args, **kwargs)

    def command(self, *args, **kwargs):
        kwargs.setdefault("cls", PersianCommand)
        return super().command(*args, **kwargs)
