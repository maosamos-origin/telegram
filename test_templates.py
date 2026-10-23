import unittest
from types import SimpleNamespace
from alert_templates import render, STYLES

class TemplateTests(unittest.TestCase):
    def test_all_styles_and_close(self):
        signal=SimpleNamespace(side='BUY',entry=4250,stop=4245,target=4260,score=.74,reason='EMA + RSI')
        candles=[SimpleNamespace(time='2026-10-19T12:00:00+00:00')]
        for style in STYLES:
            self.assertIn('BUY',render(('BUY',0,signal,None,'entry',None),candles,style))
            self.assertIn('CLOSE',render(('CLOSE',0,signal,4260,'take profit',10),candles,style))
    def test_khmer_content(self):
        signal=SimpleNamespace(side='SELL',entry=4250,stop=4256,target=4238,score=1.0,reason='EMA trend pullback + rejection candle + RSI 41.0; ATR 4.10')
        candles=[SimpleNamespace(time='2026-10-23T07:05:00+00:00')]
        text=render(('SELL',0,signal,None,'entry',None),candles,'khmer')
        self.assertIn('លក់',text); self.assertIn('23/10/2026 14:05',text); self.assertIn('RSI 41.0',text)
        close=render(('CLOSE',0,signal,4256,'stop loss',-6),candles,'khmer')
        self.assertIn('ខាត',close); self.assertIn('Stop Loss',close)
    def test_reject_unknown(self):
        with self.assertRaises(ValueError): render(None,[],'nonexistent')
if __name__=='__main__': unittest.main()
