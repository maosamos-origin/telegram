# XAUUSD Hybrid Signal Bot — Prototype (Paper only)

នេះជា prototype សម្រាប់ **simulation / paper mode ប៉ុណ្ណោះ**។ វាមិនអាចបើក order, កែប្រែ account broker, ឬដាក់លុយពិតបានទេ។ សញ្ញាគឺជាលទ្ធផលពី rule-based rules ហើយ ML ranking ជាជម្រើស។ វាមិនមែនជាការណែនាំវិនិយោគទេ។

## តម្រូវការ

- Python 3.10+ (មិនត្រូវការ package ខាងក្រៅ)
- ទិន្នន័យ CSV មាន header: `time,open,high,low,close,volume`

## រត់ភ្លាម (demo data, Telegram dry-run)

```bash
python3 bot.py backtest --demo --ml
python3 bot.py simulate --demo --ml
python3 -m unittest -v
```

`--demo` បង្កើត OHLC សិប្បនិម្មិត deterministic សម្រាប់សាកល្បង code តែប៉ុណ្ណោះ។ លទ្ធផលពីវា **មិនមែន** win rate សម្រាប់ទីផ្សារពិតទេ។

## ប្រើ historical CSV

```bash
python3 bot.py backtest --csv /path/to/XAUUSD_M5.csv --ml
python3 bot.py simulate --csv /path/to/XAUUSD_M5.csv --dry-run
```

Backtest បែងចែកតាមពេលវេលា: 70% ដំបូងសម្រាប់ train ML និង 30% ចុងក្រោយសម្រាប់ test។ មិនមានការច្របល់ row ពេល train/test ទេ។ ប្រសិនបើមិនបញ្ចូល `--ml` វាប្រើ rules តែប៉ុណ្ណោះ។

ML ត្រូវការយ៉ាងហោចណាស់ 10 historical candidate setups ដែលមានទាំងលទ្ធផលឈ្នះ និងចាញ់នៅក្នុងផ្នែក train។ បើ data មិនគ្រប់ Bot នឹងបន្តជាមួយ rules តែប៉ុណ្ណោះ ហើយបង្ហាញ `"ml_trained": false`—វាមិនបង្កើត score ក្លែងក្លាយទេ។

## Telegram (ជាជម្រើស)

លំនាំដើមគឺ dry-run: alert នឹងបោះពុម្ពក្នុង terminal ហើយមិនផ្ញើអ្វីទៅ Telegram ទេ។ ដើម្បីផ្ញើ alert ពិត សូមកំណត់ environment variables នៅក្នុង shell របស់អ្នក (កុំ commit token):

```bash
export TELEGRAM_BOT_TOKEN='your-token'
export TELEGRAM_CHAT_ID='your-chat-id'
python3 bot.py simulate --csv /path/to/XAUUSD_M5.csv --telegram
```

Bot នឹងបដិសេធ `--telegram` ប្រសិនបើ variables ទាំងពីរមិនមាន ហើយមិនបង្ហាញ token ក្នុង output។ អ្នកមិនចាំបាច់ផ្តល់ credentials ដល់ខ្ញុំទេ។

## Render Web Service (Paper mode)

`render.yaml` និង `web_service.py` ត្រូវបានរៀបចំសម្រាប់ Render។ Web Service បើក `/health` (សម្រាប់ Render) និង `/status` (សម្រាប់មើលស្ថានភាព)។ នៅ configuration ដំបូង វាប្រើ `PAPER_DATA_MODE=demo` និង **បិទ Telegram delivery ជាអចិន្ត្រៃយ៍** ដើម្បីកុំឱ្យ demo candles បង្កើត alert ក្លែងក្លាយ។

មុន deploy សូម push project ទៅ GitHub/GitLab/Bitbucket រួចទៅ Render Dashboard → **New** → **Blueprint** → ជ្រើស repository → Apply។ `render.yaml` កំណត់ `plan: free` និង `autoDeployTrigger: off`; អ្នកអាចប្តូរទៅ paid plan ពេលត្រូវឱ្យ service រត់បន្ត។ Free Web Service អាច sleep នៅពេលគ្មាន traffic ដូច្នេះវាមិនសមសម្រាប់ alert 24/7។

ពេលក្រោយ មុនបើក Telegram delivery យើងត្រូវបន្ថែម live market-data adapter មុន។ កុំប្ដូរ `PAPER_DATA_MODE` ទៅ `csv` លុះត្រាតែមាន `XAUUSD_CSV_PATH` អាចអានបាននៅ runtime។

## Logic សង្ខេប

- **Trend:** EMA(20) ទល់ EMA(50)
- **Liquidity sweep:** low/high បំបែក rolling range រួច close ត្រឡប់ចូល range
- **Momentum:** RSI(14)
- **Risk:** ATR(14), SL = 1.2×ATR, TP = 2.0×risk
- **Exit:** CLOSE នៅពេល TP/SL ប៉ះ ឬ trend ប្រែទិស (deterministic)
- **WAIT:** alert នៅពេលគ្មាន entry ឬ risk data មិនគ្រប់

## កំណត់ចំណាំសំខាន់

CSV គួរតែមាន candles តាម timeframe តែមួយ (ឧ. M5) និងតម្រៀបពេលពីចាស់ទៅថ្មី។ Backtest គិត fill នៅ close របស់ candle signal ហើយពិនិត្យ SL មុន TP នៅ candle បន្ទាប់ ប្រសិនបើទាំងពីរប៉ះក្នុង candle ដូចគ្នា—នេះជាសន្មត់ conservative។
