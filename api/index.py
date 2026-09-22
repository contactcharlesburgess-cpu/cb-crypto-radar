"""
Vercel Serverless Function entry point for CB Crypto AI Radar.
"""

import http.server
import json
import os
import sys
import urllib.parse
from pathlib import Path

# Add current directory to path
CURR_DIR = os.path.dirname(os.path.abspath(__file__))
if CURR_DIR not in sys.path:
    sys.path.insert(0, CURR_DIR)

import config
import data_fetcher
import sentiment_analyzer
import signal_generator


def get_fresh_report(force: bool = False):
    """Retrieve all data, analyze sentiment, and generate report."""
    raw_data = data_fetcher.get_all_data(force_refresh=force)
    
    crypto_news = sentiment_analyzer.process_all_news(raw_data.get("crypto_news", []))
    fj_squawk = sentiment_analyzer.process_all_news(raw_data.get("financial_juice", []))
    all_news = crypto_news + fj_squawk
    all_news.sort(key=lambda x: abs(x.get("score", 0)), reverse=True)

    report = signal_generator.build_full_intelligence_report(raw_data, all_news)
    report["forex_factory"] = raw_data.get("forex_factory", [])
    report["financial_juice"] = fj_squawk
    report["crypto_news"] = crypto_news
    report["fear_and_greed"] = raw_data.get("fear_and_greed", {})
    return report


class handler(http.server.BaseHTTPRequestHandler):
    """Vercel Serverless Function Handler."""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ["/api/health", "/health"]:
            self.send_json({"status": "ok", "platform": "vercel"})
        else:
            # Default GET /api/data
            try:
                report = get_fresh_report(force=False)
                self.send_json(report)
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        try:
            report = get_fresh_report(force=True)
            self.send_json({"status": "success", "report": report})
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
