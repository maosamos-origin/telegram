"""Windows-compatible two-process SQLite delivery claim test."""

import multiprocessing as mp
import tempfile
import time
import unittest
from pathlib import Path

from daily_sender import DailySender
from signal_history import SignalHistory


def delivery_worker(db_path, day, log_path, ready, start, results):
    sender = None
    try:
        sender = DailySender(db_path)
        ready.put(True)

        if not start.wait(timeout=10):
            raise RuntimeError("Worker start timeout")

        def mock_notify(message):
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("DELIVERED\n")
                f.flush()
            time.sleep(0.3)

        outcome = sender.send(day, mock_notify)
        results.put(("ok", outcome))

    except Exception as exc:
        results.put(("error", type(exc).__name__))

    finally:
        if sender is not None:
            sender.close()


class MultiProcessTests(unittest.TestCase):

    def test_two_processes_single_claim(self):
        ctx = mp.get_context("spawn")

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "signals.db"
            log = Path(folder) / "delivery.log"
            day = "2026-10-19"

            history = SignalHistory(path)
            history.close()

            ready = ctx.Queue()
            start = ctx.Event()
            results = ctx.Queue()

            workers = [
                ctx.Process(
                    target=delivery_worker,
                    args=(str(path), day, str(log),
                          ready, start, results)
                )
                for _ in range(2)
            ]

            try:
                for worker in workers:
                    worker.start()

                for _ in workers:
                    self.assertTrue(ready.get(timeout=10))

                start.set()

                outcomes = [
                    results.get(timeout=15)
                    for _ in workers
                ]

                for worker in workers:
                    worker.join(timeout=10)

                self.assertTrue(
                    all(not worker.is_alive() for worker in workers)
                )
                self.assertEqual(
                    sorted(outcomes),
                    [("ok", False), ("ok", True)]
                )

                lines = log.read_text(
                    encoding="utf-8"
                ).splitlines()

                self.assertEqual(lines, ["DELIVERED"])

                check = DailySender(path)
                try:
                    self.assertEqual(check.status(day), "sent")
                finally:
                    check.close()

            finally:
                start.set()
                for worker in workers:
                    if worker.is_alive():
                        worker.terminate()
                    worker.join(timeout=5)


if __name__ == "__main__":
    mp.freeze_support()
    unittest.main()
