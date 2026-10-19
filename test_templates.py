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
    def test_reject_unknown(self):
        with self.assertRaises(ValueError): render(None,[],'nonexistent')
if __name__=='__main__': unittest.main()
