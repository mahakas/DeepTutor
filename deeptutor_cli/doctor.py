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

_LABELS_FA = {
    "llm_config": "پیکربندی مدل زبانی",
    "llm_credentials": "اطلاعات احراز هویت مدل",
    "llm_endpoint": "نقطهٔ پایانی مدل",
    "storage": "ذخیره‌سازی اجرا",
    "rag": "پیش‌نیازهای بازیابی",
    "online": "پاسخ ارائه‌دهنده",
    "turn_coordination": "هماهنگی نوبت‌ها",
    "turn_repository": "مخزن نوبت‌ها",
    "legacy_chat_migration": "انتقال گفتگوهای قدیمی",
}


def _detail_fa(detail: str) -> str:
    """Localize our diagnostic prose without changing JSON or third-party errors."""
    exact = {
        "No provider endpoint is configured.": "نقطهٔ پایانی ارائه‌دهنده تنظیم نشده است.",
        "The configured provider endpoint is not a valid HTTP(S) URL.": "نقطهٔ پایانی ارائه‌دهنده نشانی معتبر HTTP(S) نیست.",
        "The selected local provider does not require an API key.": "ارائه‌دهندهٔ محلی انتخاب‌شده به کلید API نیاز ندارد.",
        "No active LLM model is configured.": "مدل زبانی فعالی تنظیم نشده است.",
        "The OAuth provider manages its endpoint.": "ارائه‌دهندهٔ OAuth نقطهٔ پایانی را مدیریت می‌کند.",
        "Knowledge module is unavailable.": "ماژول دانش در دسترس نیست.",
        "No knowledge bases are configured.": "پایگاه دانشی تنظیم نشده است.",
        "Not requested. Use --online to send a small model request.": "درخواست نشده. برای ارسال درخواست کوچک مدل، --online را به کار ببرید.",
        "Skipped because local LLM checks failed.": "به‌علت شکست بررسی‌های محلی مدل زبانی رد شد.",
        "The model returned a response.": "مدل پاسخ برگرداند.",
        "The configured coordination backend is unavailable.": "سامانهٔ هماهنگی تنظیم‌شده در دسترس نیست.",
        "No recognized credential is configured for this custom endpoint. "
        "Use --online to verify whether it accepts unauthenticated requests.": "اطلاعات احراز هویت شناخته‌شده‌ای برای این نقطهٔ پایانی سفارشی تنظیم نشده. "
        "با --online پذیرش درخواست بدون احراز هویت را بررسی کنید.",
    }
    if detail in exact:
        return exact[detail]
    replacements = {
        "Active model: ": "مدل فعال: ",
        "unknown provider": "ارائه‌دهندهٔ نامشخص",
        "Credentials are configured for ": "اطلاعات احراز هویت تنظیم شده برای ",
        "No credentials are configured for ": "اطلاعات احراز هویت تنظیم نشده برای ",
        "the selected provider": "ارائه‌دهندهٔ انتخاب‌شده",
        "Selected provider": "ارائه‌دهندهٔ انتخاب‌شده",
        " uses provider-managed OAuth.": " از OAuth مدیریت‌شدهٔ ارائه‌دهنده استفاده می‌کند.",
        "Writable: ": "قابل‌نوشتن: ",
        "Cannot write to ": "نوشتن ممکن نیست در ",
        "Ready for configured provider(s): ": "آماده برای ارائه‌دهندگان تنظیم‌شده: ",
        "Could not resolve active LLM settings: ": "خواندن تنظیمات مدل زبانی فعال ممکن نشد: ",
        "Could not inspect RAG settings: ": "بررسی تنظیمات بازیابی ممکن نشد: ",
        " coordination is ready for ": " برای هماهنگی آماده است؛ تعداد پردازشگر: ",
        " worker(s).": ".",
        " schema and active-turn query are ready.": " برای ساختار و پرس‌وجوی نوبت فعال آماده است.",
        "Preflight succeeded; ": "بررسی مقدماتی موفق بود؛ ",
        " session(s) pending migration.": " نشست در انتظار انتقال.",
        "invalid WeKnora server URL": "نشانی سرور وی‌کنورا نامعتبر است",
        "invalid LightRAG server URL": "نشانی سرور لایت‌رگ نامعتبر است",
        "preflight could not run": "اجرای بررسی مقدماتی ممکن نشد",
        "requirement failed": "پیش‌نیاز برقرار نیست",
    }
    for source, target in replacements.items():
        detail = detail.replace(source, target)
    return detail


def _render_rich(report: DoctorReport) -> None:
    table = Table(title="عیب‌یابی راه‌اندازی درسیار")
    table.add_column("وضعیت", no_wrap=True)
    table.add_column("بررسی")
    table.add_column("جزئیات")
    for check in report.checks:
        if check.status == "pass":
            status = "[green]موفق[/green]"
        elif check.status == "fail" and not check.required:
            status = "[yellow]هشدار[/yellow]"
        elif check.status == "fail":
            status = "[red]ناموفق[/red]"
        else:
            status = "[dim]ردشده[/dim]"
        table.add_row(status, _LABELS_FA.get(check.key, check.label), _detail_fa(check.detail))
    console.print(table)
    if report.ok:
        console.print("[green]بررسی‌های الزامی موفق بودند.[/green]")
    else:
        console.print("[red]یک یا چند بررسی الزامی ناموفق بودند.[/red]")


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
            raise typer.BadParameter("باید rich یا json باشد", param_hint="--format")

        if target not in {None, "runtime"}:
            raise typer.BadParameter("باید runtime باشد", param_hint="target")
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
