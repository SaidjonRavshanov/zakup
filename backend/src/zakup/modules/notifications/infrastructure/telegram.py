"""Telegram Bot API: sendMessage (HTML) + Mini App tugmasi (inline web_app)."""

from typing import Any

import httpx

from zakup.modules.notifications.application.ports import DeliveryRefusedError


class TelegramSender:
    def __init__(self, token: str, client: httpx.AsyncClient | None = None) -> None:
        self._url = f"https://api.telegram.org/bot{token}/sendMessage"
        self._client = client or httpx.AsyncClient(timeout=15)

    async def send(self, chat_id: int, text: str, button: tuple[str, str] | None) -> None:
        body: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
        }
        if button is not None:
            label, url = button
            body["reply_markup"] = {"inline_keyboard": [[{"text": label, "web_app": {"url": url}}]]}
        response = await self._client.post(self._url, json=body)
        if response.status_code == httpx.codes.OK:
            return
        description = _description(response)
        # 400 chat not found / 403 bot blocked — qayta urinish foydasiz
        if response.status_code in (httpx.codes.BAD_REQUEST, httpx.codes.FORBIDDEN):
            raise DeliveryRefusedError(f"{response.status_code}: {description}")
        raise RuntimeError(f"telegram {response.status_code}: {description}")


def _description(response: httpx.Response) -> str:
    try:
        return str(response.json().get("description", ""))
    except ValueError:
        return response.text[:200]
