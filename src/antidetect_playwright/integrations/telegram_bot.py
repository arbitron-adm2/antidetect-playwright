"""Telegram bot for registration management."""

import asyncio
import json
from datetime import datetime
from typing import Any, Callable, Awaitable

import aiohttp


class TelegramBot:
    """Telegram bot for managing registration tasks."""

    def __init__(
        self,
        token: str,
        allowed_users: list[int] | None = None,
    ) -> None:
        self._token = token
        self._base_url = f"https://api.telegram.org/bot{token}"
        self._allowed_users = set(allowed_users) if allowed_users else None

        self._running = False
        self._offset = 0

        # Callbacks
        self._on_start: Callable[[], Awaitable[dict]] | None = None
        self._on_stop: Callable[[], Awaitable[None]] | None = None
        self._on_status: Callable[[], Awaitable[dict]] | None = None
        self._on_results: Callable[[], Awaitable[list[dict]]] | None = None

    def set_callbacks(
        self,
        on_start: Callable[[], Awaitable[dict]] | None = None,
        on_stop: Callable[[], Awaitable[None]] | None = None,
        on_status: Callable[[], Awaitable[dict]] | None = None,
        on_results: Callable[[], Awaitable[list[dict]]] | None = None,
    ) -> None:
        """Set command callbacks."""
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_status = on_status
        self._on_results = on_results

    async def start(self) -> None:
        """Start polling for updates."""
        self._running = True

        while self._running:
            try:
                updates = await self._get_updates()
                for update in updates:
                    await self._handle_update(update)
            except Exception as e:
                print(f"Bot error: {e}")
                await asyncio.sleep(5)

    async def stop(self) -> None:
        """Stop the bot."""
        self._running = False

    async def _get_updates(self) -> list[dict]:
        """Get updates from Telegram."""
        url = f"{self._base_url}/getUpdates"
        params = {
            "offset": self._offset,
            "timeout": 30,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, params=params, timeout=aiohttp.ClientTimeout(total=35)
            ) as resp:
                data = await resp.json()

                if data.get("ok"):
                    updates = data.get("result", [])
                    if updates:
                        self._offset = updates[-1]["update_id"] + 1
                    return updates

                return []

    async def _handle_update(self, update: dict) -> None:
        """Handle incoming update."""
        message = update.get("message")
        if not message:
            return

        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        text = message.get("text", "")

        # Check permissions
        if self._allowed_users and user_id not in self._allowed_users:
            await self._send_message(chat_id, "⛔ Access denied")
            return

        # Handle commands
        if text.startswith("/"):
            await self._handle_command(chat_id, text)

    async def _handle_command(self, chat_id: int, text: str) -> None:
        """Handle bot command."""
        command = text.split()[0].lower()

        if command == "/start" or command == "/help":
            await self._send_message(chat_id, self._get_help_text())

        elif command == "/run":
            if self._on_start:
                await self._send_message(chat_id, "🚀 Starting registration batch...")
                try:
                    result = await self._on_start()
                    await self._send_message(
                        chat_id,
                        f"✅ Batch started!\n"
                        f"Tasks: {result.get('total', 0)}\n"
                        f"Concurrent: {result.get('concurrent', 0)}",
                    )
                except Exception as e:
                    await self._send_message(chat_id, f"❌ Error: {e}")
            else:
                await self._send_message(chat_id, "⚠️ Start callback not configured")

        elif command == "/stop":
            if self._on_stop:
                await self._send_message(chat_id, "⏹ Stopping...")
                await self._on_stop()
                await self._send_message(chat_id, "✅ Stopped")
            else:
                await self._send_message(chat_id, "⚠️ Stop callback not configured")

        elif command == "/status":
            if self._on_status:
                status = await self._on_status()
                await self._send_message(chat_id, self._format_status(status))
            else:
                await self._send_message(chat_id, "⚠️ Status callback not configured")

        elif command == "/results":
            if self._on_results:
                results = await self._on_results()
                await self._send_results(chat_id, results)
            else:
                await self._send_message(chat_id, "⚠️ Results callback not configured")

        else:
            await self._send_message(chat_id, f"Unknown command: {command}")

    async def _send_message(self, chat_id: int, text: str) -> None:
        """Send message to chat."""
        url = f"{self._base_url}/sendMessage"

        async with aiohttp.ClientSession() as session:
            await session.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                },
            )

    async def _send_document(
        self, chat_id: int, file_path: str, caption: str = ""
    ) -> None:
        """Send document to chat."""
        url = f"{self._base_url}/sendDocument"

        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("chat_id", str(chat_id))
                data.add_field("caption", caption)
                data.add_field("document", f)

                await session.post(url, data=data)

    async def _send_results(self, chat_id: int, results: list[dict]) -> None:
        """Send results summary and file."""
        successful = [r for r in results if r.get("status") == "success"]
        failed = len(results) - len(successful)

        text = (
            f"📊 <b>Results Summary</b>\n\n"
            f"Total: {len(results)}\n"
            f"✅ Success: {len(successful)}\n"
            f"❌ Failed: {failed}\n"
        )

        if successful:
            text += "\n<b>Last 5 successful:</b>\n"
            for r in successful[-5:]:
                text += f"• {r.get('email', 'N/A')}\n"

        await self._send_message(chat_id, text)

    def _get_help_text(self) -> str:
        """Get help message."""
        return (
            "🤖 <b>Registration Bot</b>\n\n"
            "Commands:\n"
            "/run - Start registration batch\n"
            "/stop - Stop current batch\n"
            "/status - Get current status\n"
            "/results - Get results summary\n"
            "/help - Show this message"
        )

    def _format_status(self, status: dict) -> str:
        """Format status for display."""
        return (
            f"📊 <b>Status</b>\n\n"
            f"Running: {'✅' if status.get('running') else '❌'}\n"
            f"Total: {status.get('total', 0)}\n"
            f"Completed: {status.get('completed', 0)}\n"
            f"In Progress: {status.get('in_progress', 0)}\n"
            f"Success: {status.get('successful', 0)}\n"
            f"Failed: {status.get('failed', 0)}\n"
            f"Success Rate: {status.get('success_rate', '0')}%\n"
            f"Duration: {status.get('duration', '0')}s"
        )

    async def notify(self, chat_id: int, message: str) -> None:
        """Send notification to specific chat."""
        await self._send_message(chat_id, message)

    async def notify_result(
        self,
        chat_id: int,
        result: dict,
        include_credentials: bool = True,
    ) -> None:
        """Send registration result notification."""
        if result.get("status") == "success":
            emoji = "✅"
            text = f"{emoji} <b>Registration Success!</b>\n\n"

            if include_credentials:
                text += f"📧 Email: <code>{result.get('email', 'N/A')}</code>\n"
                text += f"👤 Username: <code>{result.get('username', 'N/A')}</code>\n"
                text += f"🔑 Password: <code>{result.get('password', 'N/A')}</code>\n"

                if result.get("access_token"):
                    token = result["access_token"]
                    text += f"🎫 Token: <code>{token[:40]}...</code>\n"

            text += f"\n⏱ Duration: {result.get('duration_seconds', 0):.1f}s"
        else:
            emoji = "❌"
            text = (
                f"{emoji} <b>Registration Failed</b>\n\n"
                f"Status: {result.get('status', 'unknown')}\n"
                f"Error: {result.get('error_message', 'Unknown error')[:200]}"
            )

        await self._send_message(chat_id, text)
