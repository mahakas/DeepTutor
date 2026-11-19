"""Setup diagnostics for the DeepTutor CLI."""

from __future__ import annotations

import asyncio
import json

from rich.table import Table
import typer

from deeptutor.services.doctor import (
    DoctorReport,
    run_diagnostics,
    run_runtime_diagnostics,
)

from .common import console


def _render_rich(report: DoctorReport) -> None:
    table = Table(title="عیب‌یابی راه‌اندازی درسیار")
    table.add_column("Status", no_wrap=True)
    table.add_column("Check")
    table.add_column("Details")
    for check in report.checks:
        if check.status == "pass":
            status = "[green]PASS[/green]"
        elif check.status == "fail" and not check.required:
            status = "[yellow]WARN[/yellow]"
        elif check.status == "fail":
            status = "[red]FAIL[/red]"
        else:
            status = "[dim]SKIP[/dim]"
        table.add_row(status, check.label, check.detail)
    console.print(table)
    if report.ok:
        console.print("[green]Required checks passed.[/green]")
    else:
        console.print("[red]One or more required checks failed.[/red]")


def register(app: typer.Typer) -> None:
    @app.command("doctor")
    def doctor(
        target: str | None = typer.Argument(
            None,
            help="هدف اختیاری عیب‌یابی؛ برای هماهنگی/ذخیره‌سازی نسخهٔ ۲ از 'runtime' استفاده کنید.",
        ),
        online: bool = typer.Option(
            False,
            "--online",
            help="ارسال یک درخواست کوچک به ارائه‌دهندهٔ مدل تنظیم‌شده.",
        ),
        fmt: str = typer.Option(
            "rich",
            "--format",
            "-f",
            help="قالب خروجی: rich | json.",
        ),
    ) -> None:
        """بررسی آماده بودن درسیار برای آغاز یک نشست."""
        if fmt not in {"rich", "json"}:
            raise typer.BadParameter("must be 'rich' or 'json'", param_hint="--format")

        if target not in {None, "runtime"}:
            raise typer.BadParameter("must be 'runtime'", param_hint="target")
        report = asyncio.run(
            run_runtime_diagnostics() if target == "runtime" else run_diagnostics(online=online)
        )
        if fmt == "json":
            console.print_json(json.dumps(report.to_dict()))
        else:
            _render_rich(report)
        if not report.ok:
            raise typer.Exit(code=1)


__all__ = ["register"]
