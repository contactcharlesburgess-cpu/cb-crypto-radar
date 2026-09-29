"""
Vercel serverless entry point for CB Crypto Radar.

Routes (all GET, all public market data — no personal data is stored or served):
  /api/data              dashboard: markets, Fear & Greed, calendar, headlines
  /api/hyperliquid       HYPE perp stats, order book, price-history levels (?coin=SOL etc.)
  /api/quotes?symbols=   live prices for the on-device portfolio (crypto + stocks)
  /api/health
"""

import http.server
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import market


class handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        try:
            sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")
        except Exception:  # noqa: BLE001
            pass

    def send_json(self, data, status=200, max_age=0):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", f"public, s-maxage={max_age}, stale-while-revalidate={max_age * 2}"
                         if max_age else "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = urllib.parse.parse_qs(parsed.query)
        try:
            if path in ("/api/health", "/health"):
                self.send_json({"status": "ok"})
            elif path in ("/api/hyperliquid", "/api/hl"):
                coin = (qs.get("coin", ["HYPE"])[0] or "HYPE").upper()[:12]
                self.send_json(market.get_hyperliquid(coin), max_age=5)
            elif path == "/api/quotes":
                syms = [s for s in qs.get("symbols", [""])[0].split(",") if s]
                self.send_json({"quotes": market.fetch_quotes(syms)}, max_age=15)
            elif path in ("/api", "/api/data"):
                force = qs.get("refresh", ["0"])[0] == "1"
                self.send_json(market.get_dashboard(force=force), max_age=60)
            else:
                self.send_json({"error": "not found"}, status=404)
        except Exception as e:  # noqa: BLE001
            # Report the failure. Never substitute made-up numbers.
            self.send_json({"status": "error", "error": str(e)}, status=502)
