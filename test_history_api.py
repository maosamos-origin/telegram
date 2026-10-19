import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import web_service as ws
from signal_history import SignalHistory


class HistoryAPITests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "history.db"

        db = SignalHistory(self.path)
        db.save_signal(
            "test-001", "XAU/USD", "5min",
            "BUY", 2500, 2495, 2510,
            "2026-10-19T12:00:00Z"
        )
        db.close()

        self.patches = [
            patch.object(ws, "HISTORY_DB", self.path),
            patch.dict(os.environ, {"HISTORY_API_TOKEN": "test-secret"})
        ]

        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ws.Handler)
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

        self.base = "http://127.0.0.1:" + str(self.server.server_port)

    def request(self, path, token=None):
        headers = {}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = Request(self.base + path, headers=headers)
        return urlopen(req, timeout=5)

    def test_history_requires_auth(self):
        with self.assertRaises(HTTPError) as result:
            self.request("/api/history")
        self.assertEqual(result.exception.code, 401)
        result.exception.close()

    def test_invalid_token_rejected(self):
        with self.assertRaises(HTTPError) as result:
            self.request("/api/stats", "wrong")
        self.assertEqual(result.exception.code, 401)
        result.exception.close()

    def test_history_authorized(self):
        with self.request("/api/history", "test-secret") as response:
            import json
            data = json.load(response)
        self.assertEqual(len(data["history"]), 1)
        self.assertEqual(data["history"][0]["side"], "BUY")

    def test_stats_authorized(self):
        with self.request("/api/stats", "test-secret") as response:
            import json
            data = json.load(response)
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["buy"], 1)


if __name__ == "__main__":
    unittest.main()
