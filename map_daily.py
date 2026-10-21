#!/usr/bin/env python3
"""Daily general-area situation overview: no live positions or front lines.

Reads a manually reviewed JSON file. Does not infer combat movements.
Only publishes if MAP_PUBLISH=1 and Telegram credentials exist.
"""
import datetime as dt
import json
import os
import pathlib
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "data" / "map_reviewed.json"
OUTPUT = ROOT / "data" / "map_latest.svg"
LEVEL_COLORS = {"неизвестно": "#cbd5e1", "низкая": "#bbf7d0", "средняя": "#fde68a", "высокая": "#fecaca"}


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', '&quot;'))


def validate(doc):
    required = ("date", "reviewed", "reviewed_at", "source_notes", "sectors")
    for key in required:
        if key not in doc:
            raise ValueError("Missing field: " + key)
    dt.date.fromisoformat(doc["date"])
    if doc["reviewed"] is not True:
        raise ValueError("Publication requires reviewed=true")
    if not isinstance(doc["source_notes"], list) or not doc["source_notes"]:
        raise ValueError("Source notes required")
    if not (1 <= len(doc["sectors"]) <= 12):
        raise ValueError("Expected 1–12 coarse geographic sectors")
    for s in doc["sectors"]:
        if not s.get("name") or s.get("activity") not in LEVEL_COLORS:
            raise ValueError("Invalid sector")
        if any(k in s for k in ("lat", "lng", "coordinates", "frontline", "units", "strike_location")):
            raise ValueError("Tactical or precise coordinates prohibited")
    return doc


def render(doc):
    # Schematic grid deliberately avoids GIS accuracy or operational contours.
    today=esc(doc["date"])
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800">',
           '<rect width="1200" height="800" fill="#0b1220"/>',
           '<text x="60" y="95" font-size="45" font-family="sans-serif" font-weight="bold" fill="white">NEWS RADAR</text>',
           f'<text x="60" y="151" font-size="27" font-family="sans-serif" fill="#cbd5e1">Обзор обстановки · {today}</text>',
           '<text x="60" y="194" font-size="20" font-family="sans-serif" fill="#94a3b8">Схематический обзор по крупным секторам. Не карта линии фронта.</text>']
    for i,sec in enumerate(doc["sectors"]):
        x=60+(i%3)*367; y=245+(i//3)*119
        col=LEVEL_COLORS[sec["activity"]]
        parts.extend([f'<rect x="{x}" y="{y}" width="345" height="97" rx="15" fill="#1e293b" stroke="#334155"/>',
                      f'<rect x="{x+15}" y="{y+17}" width="20" height="62" rx="8" fill="{col}"/>',
                      f'<text x="{x+50}" y="{y+42}" font-size="22" font-family="sans-serif" fill="white">{esc(sec["name"][:23])}</text>',
                      f'<text x="{x+50}" y="{y+73}" font-size="18" font-family="sans-serif" fill="#cbd5e1">Активность: {esc(sec["activity"])}</text>'])
    parts.extend(['<rect x="60" y="730" width="1080" height="1" fill="#334155"/>',
                  '<text x="60" y="766" font-size="19" font-family="sans-serif" fill="#94a3b8">Ретроспективная оценка • приблизительно • без тактических деталей</text>','</svg>'])
    return "\n".join(parts)


def caption(doc):
    headline=f"🗺 NEWS RADAR | Обзор обстановки за {doc['date']}"
    lines=[headline,"", "Схематическая ретроспективная оценка по крупным районам:"]
    lines += [f"• {s['name']}: {s['activity']}" for s in doc["sectors"]]
    lines += ["", "Источник оценки: редакционная проверка публичных обзоров.",
              "Карта не отображает текущие позиции, линии фронта или координаты боевых действий."]
    if doc.get("commentary"):
        lines += ["",str(doc["commentary"])[:600]]
    return "\n".join(lines)[:3500]


def telegram_document(path, description):
    token=os.getenv("BOT_TOKEN", ""); chat=os.getenv("MAP_CHAT_ID", "")
    if not token or not chat:
        raise RuntimeError("Missing BOT_TOKEN or MAP_CHAT_ID")
    # Telegram sendDocument via multipart (stdlib, no dependencies)
    boundary="newsradarmapboundary"
    fields={"chat_id":chat,"caption":description}
    payload=b""
    for k,v in fields.items():
        payload+=(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n").encode()
    payload+=(f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"news-radar-overview.svg\"\r\nContent-Type: image/svg+xml\r\n\r\n").encode()+path.read_bytes()+b"\r\n"
    payload+=(f"--{boundary}--\r\n").encode()
    req=urllib.request.Request(f"https://api.telegram.org/bot{token}/sendDocument",data=payload,headers={"Content-Type":f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=30) as response:
        result=json.loads(response.read())
    if not result.get("ok"):
        raise RuntimeError("Telegram rejected upload")


def main():
    path=pathlib.Path(os.getenv("MAP_INPUT",str(DEFAULT_INPUT)))
    doc=validate(json.loads(path.read_text(encoding="utf-8")))
    OUTPUT.write_text(render(doc), encoding="utf-8")
    print("Generated",OUTPUT)
    if os.getenv("MAP_PUBLISH")=="1":
        state=ROOT/"data"/"map_published.json"
        prior=json.loads(state.read_text()) if state.exists() else {}
        if prior.get("date")==doc["date"] and prior.get("reviewed_at")==doc["reviewed_at"]:
            print("Already published this revision");return
        telegram_document(OUTPUT,caption(doc))
        state.write_text(json.dumps({"date":doc["date"],"reviewed_at":doc["reviewed_at"]},ensure_ascii=False),encoding="utf-8")
        print("Published")
    else:
        print("Dry run only. Set MAP_PUBLISH=1 for publishing.")

if __name__=="__main__":
    main()
