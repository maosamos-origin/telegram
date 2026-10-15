import io, json, unittest
from unittest.mock import patch
import bot

class BotTests(unittest.TestCase):
    def setUp(self): self.c = bot.demo_data(360)
    def test_indicators_align(self):
        self.assertEqual(len(bot.indicators(self.c)[0]),len(self.c))
    def test_candidate_risk_is_directional(self):
        ind=bot.indicators(self.c)
        for i in range(55,len(self.c)):
            s=bot.candidate(self.c,i,ind)
            if s:
                self.assertLess(s.stop,s.entry) if s.side=="BUY" else self.assertGreater(s.stop,s.entry)
                return
        self.fail("demo should yield a candidate")
    def test_backtest_events_and_report(self):
        events,_=bot.alerts(self.c,int(len(self.c)*.7),len(self.c),True)
        r=bot.report(events); self.assertIn("net_price_units",r); self.assertGreaterEqual(r["closed_trades"],0)
    def test_telegram_needs_credentials(self):
        import os
        old1,old2=os.environ.pop("TELEGRAM_BOT_TOKEN",None),os.environ.pop("TELEGRAM_CHAT_ID",None)
        try:
            with self.assertRaises(RuntimeError): bot.notify("test",True)
        finally:
            if old1: os.environ["TELEGRAM_BOT_TOKEN"]=old1
            if old2: os.environ["TELEGRAM_CHAT_ID"]=old2
    def test_telegram_blocks_private_chat(self):
        import os
        old1,old2=os.environ.get("TELEGRAM_BOT_TOKEN"),os.environ.get("TELEGRAM_CHAT_ID")
        os.environ["TELEGRAM_BOT_TOKEN"]="test-token"; os.environ["TELEGRAM_CHAT_ID"]="12345"
        try:
            with self.assertRaisesRegex(RuntimeError,"private chats are blocked"): bot.notify("test",True)
        finally:
            if old1 is None: os.environ.pop("TELEGRAM_BOT_TOKEN",None)
            else: os.environ["TELEGRAM_BOT_TOKEN"]=old1
            if old2 is None: os.environ.pop("TELEGRAM_CHAT_ID",None)
            else: os.environ["TELEGRAM_CHAT_ID"]=old2
    def test_ranker_trains_only_with_two_classes(self):
        ranker=bot.LogisticRanker().fit([[0,0],[1,1],[0.1,0],[.9,1]] ,[0,1,0,1])
        self.assertFalse(ranker.ready)  # too few samples: intentional safety guard
        samples=[[0,0]]*6+[[1,1]]*6
        ranker=bot.LogisticRanker().fit(samples,[0]*6+[1]*6)
        self.assertTrue(ranker.ready)
        self.assertGreater(ranker.predict([1,1]),ranker.predict([0,0]))
    def test_web_paper_scan_never_enables_telegram(self):
        import web_service
        web_service.scan_once()
        self.assertEqual(web_service.state["telegram_delivery"], "disabled")
        self.assertIsNotNone(web_service.state["last_result"])
    def test_twelve_data_falls_back_to_second_key(self):
        class Response:
            def __init__(self, payload): self.payload=payload
            def __enter__(self): return self
            def __exit__(self,*_): return False
            def read(self,*_): return json.dumps(self.payload).encode()
        values=[{"datetime":f"2025-01-01 00:{i:02d}:00","open":"1","high":"2","low":"0.5","close":"1.5"} for i in range(80)]
        with patch("bot.urlopen", side_effect=[Response({"status":"error","message":"quota"}),Response({"values":values})]) as request:
            candles=bot.fetch_twelve_data("bad-key,good-key")
        self.assertEqual(len(candles),80)
        self.assertEqual(request.call_count,2)
if __name__ == "__main__": unittest.main()
