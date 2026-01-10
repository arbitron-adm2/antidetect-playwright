"""Registration result handler with Telegram bot integration."""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Awaitable

import aiohttp


class RegistrationStatus(Enum):
    """Registration task status."""

    SUCCESS = "success"
    FAILED = "failed"
    CAPTCHA_FAILED = "captcha_failed"
    PROXY_ERROR = "proxy_error"
    TIMEOUT = "timeout"
    BANNED = "banned"


@dataclass
class RegistrationResult:
    """Result of a registration task."""

    task_id: str
    session_id: str
    status: RegistrationStatus

    # Credentials (if successful)
    email: str | None = None
    username: str | None = None
    password: str | None = None
    phone: str | None = None

    # Auth tokens
    access_token: str | None = None
    refresh_token: str | None = None
    cookies: list[dict[str, Any]] = field(default_factory=list)

    # Session info
    user_id: str | None = None
    account_data: dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    duration_seconds: float = 0.0
    error_message: str | None = None
    screenshots: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "email": self.email,
            "username": self.username,
            "password": self.password,
            "phone": self.phone,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "cookies": self.cookies,
            "user_id": self.user_id,
            "account_data": self.account_data,
            "created_at": self.created_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "screenshots": self.screenshots,
        }

    def to_credentials_line(self) -> str:
        """Format as credentials line for export."""
        parts = []
        if self.email:
            parts.append(self.email)
        if self.username:
            parts.append(self.username)
        if self.password:
            parts.append(self.password)
        if self.access_token:
            parts.append(self.access_token)
        return ":".join(parts)


class ResultHandler:
    """Handles registration results with multiple output options."""

    def __init__(
        self,
        results_dir: str,
        telegram_bot_token: str | None = None,
        telegram_chat_id: str | None = None,
        webhook_url: str | None = None,
    ) -> None:
        self._results_dir = Path(results_dir)
        self._results_dir.mkdir(parents=True, exist_ok=True)

        self._telegram_token = telegram_bot_token
        self._telegram_chat_id = telegram_chat_id
        self._webhook_url = webhook_url

        self._results: list[RegistrationResult] = []
        self._success_count = 0
        self._failed_count = 0

        self._callbacks: list[Callable[[RegistrationResult], Awaitable[None]]] = []

    async def handle_result(self, result: RegistrationResult) -> None:
        """Process and store registration result."""
        self._results.append(result)

        if result.status == RegistrationStatus.SUCCESS:
            self._success_count += 1
        else:
            self._failed_count += 1

        await self._save_to_file(result)

        if result.status == RegistrationStatus.SUCCESS:
            await self._append_credentials(result)

        if self._telegram_token and self._telegram_chat_id:
            await self._send_telegram_notification(result)

        if self._webhook_url:
            await self._send_webhook(result)

        for callback in self._callbacks:
            try:
                await callback(result)
            except Exception:
                pass

    async def _save_to_file(self, result: RegistrationResult) -> None:
        """Save individual result to JSON file."""
        file_path = self._results_dir / f"{result.task_id}.json"
        file_path.write_text(json.dumps(result.to_dict(), indent=2))

    async def _append_credentials(self, result: RegistrationResult) -> None:
        """Append successful credentials to combined file."""
        creds_file = self._results_dir / "credentials.txt"
        line = result.to_credentials_line()
        if line:
            with open(creds_file, "a") as f:
                f.write(f"{line}\n")

        accounts_file = self._results_dir / "accounts.json"
        accounts = []
        if accounts_file.exists():
            accounts = json.loads(accounts_file.read_text())

        accounts.append(
            {
                "email": result.email,
                "username": result.username,
                "password": result.password,
                "access_token": result.access_token,
                "refresh_token": result.refresh_token,
                "user_id": result.user_id,
                "cookies": result.cookies,
                "created_at": result.created_at.isoformat(),
            }
        )

        accounts_file.write_text(json.dumps(accounts, indent=2))

    async def _send_telegram_notification(self, result: RegistrationResult) -> None:
        """Send result notification to Telegram."""
        if result.status == RegistrationStatus.SUCCESS:
            emoji = "✅"
            text = (
                f"{emoji} <b>Регистрация успешна!</b>\n\n"
                f"📧 Email: <code>{result.email or 'N/A'}</code>\n"
                f"👤 Username: <code>{result.username or 'N/A'}</code>\n"
                f"🔑 Password: <code>{result.password or 'N/A'}</code>\n"
            )
            if result.access_token:
                text += f"🎫 Token: <code>{result.access_token[:50]}...</code>\n"
            text += f"⏱ Время: {result.duration_seconds:.1f}s"
        else:
            emoji = "❌"
            text = (
                f"{emoji} <b>Регистрация не удалась</b>\n\n"
                f"📋 Task: <code>{result.task_id[:8]}</code>\n"
                f"⚠️ Статус: {result.status.value}\n"
            )
            if result.error_message:
                text += f"💬 Ошибка: {result.error_message[:200]}"

        url = f"https://api.telegram.org/bot{self._telegram_token}/sendMessage"

        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    url,
                    json={
                        "chat_id": self._telegram_chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                    },
                )
        except Exception:
            pass

    async def _send_webhook(self, result: RegistrationResult) -> None:
        """Send result to webhook URL."""
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    self._webhook_url,
                    json=result.to_dict(),
                    timeout=aiohttp.ClientTimeout(total=10),
                )
        except Exception:
            pass

    def add_callback(
        self,
        callback: Callable[[RegistrationResult], Awaitable[None]],
    ) -> None:
        """Add custom result callback."""
        self._callbacks.append(callback)

    def get_stats(self) -> dict[str, int]:
        """Get current statistics."""
        return {
            "total": len(self._results),
            "success": self._success_count,
            "failed": self._failed_count,
            "success_rate": (
                round(self._success_count / len(self._results) * 100, 1)
                if self._results
                else 0
            ),
        }

    async def generate_report(self) -> str:
        """Generate summary report."""
        stats = self.get_stats()

        status_counts: dict[str, int] = {}
        for result in self._results:
            status_counts[result.status.value] = (
                status_counts.get(result.status.value, 0) + 1
            )

        report = [
            "=" * 50,
            "REGISTRATION BATCH REPORT",
            "=" * 50,
            f"Total tasks: {stats['total']}",
            f"Successful: {stats['success']} ({stats['success_rate']}%)",
            f"Failed: {stats['failed']}",
            "",
            "Status breakdown:",
        ]

        for status, count in status_counts.items():
            report.append(f"  - {status}: {count}")

        if self._success_count > 0:
            avg_duration = (
                sum(
                    r.duration_seconds
                    for r in self._results
                    if r.status == RegistrationStatus.SUCCESS
                )
                / self._success_count
            )
            report.append(f"\nAverage success time: {avg_duration:.1f}s")

        report.append("=" * 50)

        report_text = "\n".join(report)

        report_file = self._results_dir / "report.txt"
        report_file.write_text(report_text)

        return report_text

    async def export_credentials(self, format: str = "txt") -> str:
        """Export all successful credentials."""
        successful = [
            r for r in self._results if r.status == RegistrationStatus.SUCCESS
        ]

        if format == "txt":
            output = "\n".join(r.to_credentials_line() for r in successful)
            file_path = self._results_dir / "export_credentials.txt"
        elif format == "json":
            output = json.dumps([r.to_dict() for r in successful], indent=2)
            file_path = self._results_dir / "export_credentials.json"
        elif format == "csv":
            lines = ["email,username,password,access_token,user_id"]
            for r in successful:
                lines.append(
                    f"{r.email or ''},{r.username or ''},{r.password or ''},"
                    f"{r.access_token or ''},{r.user_id or ''}"
                )
            output = "\n".join(lines)
            file_path = self._results_dir / "export_credentials.csv"
        else:
            raise ValueError(f"Unknown format: {format}")

        file_path.write_text(output)
        return str(file_path)
