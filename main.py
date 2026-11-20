import os
import asyncio
import secrets
import string
import time
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
import uvicorn

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip()
}

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

pending = {}
devices = {}
queues = {}

class Register(BaseModel):
    device_id: str

def is_admin(user_id):
    return user_id in ADMIN_IDS

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "🟢 РАТКА запущена!\n\n"
        "Команды:\n"
        "/help — помощь\n"
        "/pair КОД — подключить компьютер\n"
        "/send Заголовок | Текст — отправить шутку\n"
        "/devices — подключённые компьютеры"
    )

@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "1. Друг запускает программу-приёмник.\n"
        "2. Он сообщает тебе код с экрана.\n"
        "3. Ты вводишь /pair КОД.\n"
        "4. Отправляешь сообщение через /send.\n\n"
        "Отключить приёмник можно в его окне."
    )

@dp.message(Command("pair"))
async def pair(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Формат: /pair 123456")
        return

    code = parts[1].strip()
    item = pending.get(code)

    if not item or item["expires"] < time.time():
        await message.answer("Код не найден или истёк.")
        return

    device_id = item["device_id"]
    token = secrets.token_urlsafe(32)

    devices[device_id] = {
        "token": token,
        "owner": message.from_user.id
    }
    queues[device_id] = []
    pending.pop(code, None)

    await message.answer("✅ Компьютер подключён!")

@dp.message(Command("send"))
async def send_message(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) != 2 or "|" not in parts[1]:
        await message.answer(
            "Формат:\n/send Заголовок | Текст"
        )
        return

    title, body = parts[1].split("|", 1)
    title = title.strip()[:70]
    body = body.strip()[:500]

    if not title or not body:
        await message.answer("Заполни заголовок и текст.")
        return

    targets = [
        device_id for device_id, data in devices.items()
        if data["owner"] == message.from_user.id
    ]

    if not targets:
        await message.answer("Сначала подключи компьютер командой /pair.")
        return

    for device_id in targets:
        queues.setdefault(device_id, []).append({
            "title": title,
            "body": body
        })

    await message.answer("📨 Сообщение отправлено!")

@dp.message(Command("devices"))
async def list_devices(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    count = sum(
        1 for data in devices.values()
        if data["owner"] == message.from_user.id
    )
    await message.answer(f"Подключённых компьютеров: {count}")

@app.post("/api/register")
def register(data: Register):
    code = "".join(secrets.choice(string.digits) for _ in range(6))
    pending[code] = {
        "device_id": data.device_id,
        "expires": time.time() + 600
    }
    return {"code": code}

@app.get("/api/status/{device_id}")
def status(device_id: str):
    for code, item in list(pending.items()):
        if item["device_id"] == device_id:
            if item["expires"] < time.time():
                pending.pop(code, None)
                break

    for data in devices.values():
        if data.get("device_id") == device_id:
            pass

    device = devices.get(device_id)
    if device:
        return {"paired": True, "token": device["token"]}

    return {"paired": False}

@app.get("/api/messages/{device_id}")
def get_messages(
    device_id: str,
    x_device_token: str = Header(default="")
):
    device = devices.get(device_id)

    if not device or not secrets.compare_digest(
        device["token"], x_device_token
    ):
        raise HTTPException(401, "Unauthorized")

    messages = queues.get(device_id, [])
    queues[device_id] = []
    return {"messages": messages}

@app.delete("/api/device/{device_id}")
def disconnect(
    device_id: str,
    x_device_token: str = Header(default="")
):
    device = devices.get(device_id)

    if not device or not secrets.compare_digest(
        device["token"], x_device_token
    ):
        raise HTTPException(401, "Unauthorized")

    devices.pop(device_id, None)
    queues.pop(device_id, None)
    return {"ok": True}

async def main():
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000"))
    )
    server = uvicorn.Server(config)
    await asyncio.gather(
        server.serve(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
