from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import httpx
import traceback

from app.core import logging

class TelegramErrorMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, telegram_bot_token: str, telegram_chat_id: str):
        super().__init__(app)
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Collect error details
            error_details = {
                "path": request.url.path,
                "method": request.method,
                "query_params": dict(request.query_params),
                "body": await self._get_request_body(request),
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            }
            # Send error details to the Telegram bot
            await self._send_to_telegram(error_details)

            # Return an internal server error response
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error"},
            )

    async def _get_request_body(self, request: Request):
        """Utility to safely get the request body."""
        try:
            body = await request.body()
            return body.decode("utf-8") if body else None
        except Exception:
            return None

    async def _send_to_telegram(self, error_details: dict):
        """Send error details to a Telegram bot."""
        try:
            message = (
                f"🚨 *Error Occurred*\n\n"
                f"*Path:* {error_details['path']}\n"
                f"*Method:* {error_details['method']}\n"
                f"*Query Params:* {error_details['query_params']}\n"
                f"*Body:* {error_details['body']}\n"
                f"*Error:* {error_details['error']}\n"
                f"*Traceback:* ```{error_details['traceback']}```"
            )
            telegram_url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            async with httpx.AsyncClient() as client:
                await client.post(telegram_url, json={
                    "chat_id": self.telegram_chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                })
        except Exception as telexc:
            print(f"Failed to send message to Telegram: {telexc}")