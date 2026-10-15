#!/usr/bin/env python3
"""Render-facing, paper-only status service for the XAUUSD signal prototype."""
from __future__ import annotations

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import bot

INTERVAL_SECONDS = max(60, int(os.getenv("PAPER_SCAN_INTERVAL_SECONDS", "300")))
DATA_MODE = os.getenv("PAPER_DATA_MODE", "demo").lower()
CSV_PATH = os.getenv("XAUUSD_CSV_PATH", "")
TWELVE_SYMBOL = os.getenv("TWELVE_DATA_SYMBOL", "XAU/USD")
TWELVE_INTERVAL = os.getenv("TWELVE_DATA_INTERVAL", "5min")
TWELVE_OUTPUTSIZE = max(80, int(os.getenv("TWELVE_DATA_OUTPUTSIZE", "200")))
state = {"mode": "paper", "data_mode": DATA_MODE, "telegram_delivery": "disabled", "last_scan": None, "last_result": None, "error": None}

def scan_once():
    # Demo data is intentionally non-deliverable: it must never create fake Telegram signals.
    if DATA_MODE == "demo": candles = bot.demo_data()
    elif DATA_MODE == "csv": candles = bot.load_csv(CSV_PATH)
    elif DATA_MODE == "twelve_data":
        candles = bot.fetch_twelve_data(os.getenv("TWELVE_DATA_API_KEYS", ""), TWELVE_SYMBOL, TWELVE_INTERVAL, TWELVE_OUTPUTSIZE)
    else: raise ValueError("PAPER_DATA_MODE must be demo, csv, or twelve_data")
    start = int(len(candles) * .70)
    events, ml_trained = bot.alerts(candles, start, len(candles), os.getenv("ML_ENABLED", "true").lower() == "true")
    state.update({"last_scan": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "last_result": bot.report(events), "ml_trained": ml_trained, "symbol": TWELVE_SYMBOL if DATA_MODE == "twelve_data" else "XAUUSD", "interval": TWELVE_INTERVAL if DATA_MODE == "twelve_data" else None, "error": None})

def monitor():
    while True:
        try: scan_once()
        except Exception as exc: state["error"] = type(exc).__name__ + ": " + str(exc)
        time.sleep(INTERVAL_SECONDS)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def do_GET(self):
        if self.path == "/health": body, code = {"ok": True, "mode": "paper"}, 200
        elif self.path in ("/", "/status"): body, code = state, 200
        else: body, code = {"error": "not found"}, 404
        data = json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", int(os.getenv("PORT", "10000"))), Handler).serve_forever()
