# EMA × VWAP Bot

A 9 EMA × VWAP crossover strategy for MNQ, with a trend-change exit. This repo holds:

- the TradingView scripts
- a Python copy of the same logic
- a 2.5-year backtest
- a paper-trading bot that posts every trade to Discord around the clock

**Paper only. Nothing in this repo places real orders.**

## The strategy (v3.3.1)

| | Rule |
|---|---|
| **Signal** | The 9 EMA crosses session VWAP on a closed bar. The close is beyond both the 9 EMA and VWAP. The 9 EMA is beyond the 21 EMA. VWAP slope over the last 5 bars is beyond 0.05 pts. VWAP resets at 6pm ET. |
| **Entry** | At the signal bar's close, only when flat. 3 MNQ micros. |
| **R** | 1.2 × ATR(14) at entry. This matches the indicator's R labels. |
| **Stop** | A hard stop at 2.5 × ATR(14) on every contract. |
| **TP1** | 1 micro at 2R. After it fills, the stop on the remaining contracts moves to breakeven. |
| **TP2** | 1 micro at 4R, or closed at the ⚠ warning if the trade is in profit. |
| **Runner** | Held until the trend-change exit. That exit fires when the score is 3/4 for 2 closes. |

**How the trend-change score works.** The score counts four checks against the trade. For a long:

1. Close below VWAP.
2. 9 EMA below the 21 EMA.
3. VWAP sloping down.
4. Swing structure broken.

Shorts use the mirror image. The ⚠ warning prints at a score of 2/4.

## Layout

```
tradingview/   Pine v6: indicator, auto-sim strategy, backtest strategy
engine/        emavwap.py: the strategy in Python (fills follow TradingView's broker emulator)
backtest/      backtest.py: results by year, session and side
bot/           bot.py: 24/5 Discord paper bot; state.json and trades.csv are written by the bot
data/          NQ 5m bars, Jan 2024 to Oct 2026
.github/       workflows/bot.yml: runs the bot on GitHub Actions
```

## Backtest (5m, all sessions, Jan 2024 to Oct 2026)

Run it with:

```
pip install -r requirements.txt
python backtest/backtest.py
```

| | Trades | Win | PF | Net | Max DD |
|---|---|---|---|---|---|
| Plan, 3 micros | 2,499 | 48% | 1.09 | +$32.1K | −$10.2K |
| 1 micro, stop + trend exit | 2,410 | 26% | 1.18 | +$25.6K | −$4.4K |
| 1 micro, classic 9 EMA exit | 2,989 | 32% | 0.97 | −$2.2K | −$5.8K |

**Breakdown.** Longs had a PF of 1.25 and shorts 0.97. The best sessions were Asia (PF 1.15) and NY AM (PF 1.12). NY PM was flat.

**Engine check.** I ran the Python engine and TradingView's 5m strategy over the same window, Sep 6 to Oct 31, 2026. They came out close:

| | Trades | Win | PF | Net |
|---|---|---|---|---|
| Python engine | 132 | 29.5% | 1.11 | +$1,075 |
| TradingView | 142 | 27.5% | 1.07 | +$1,068 |

## Discord bot setup

1. In the Discord channel, go to **Edit Channel → Integrations → Webhooks → New Webhook**, then copy the URL.
2. In this repo, go to **Settings → Secrets and variables → Actions → New repository secret**. Name it `EMAVWAP` and paste the URL as the value.
3. Go to **Actions → EMA x VWAP paper bot → Run workflow**. This runs one test pass. After that, the bot runs on its own Sun 6pm to Fri 5pm ET.

**What it posts:**

- entries, with the stop, targets and $ at risk
- TP1 and TP2 fills
- R milestones
- the ⚠ warning, once per trade
- exits, with total R, $ and the max R reached
- a daily summary after the 5pm ET close

**Data delay.** The bot gets its bars from Yahoo, which is about 10 minutes behind. GitHub's scheduler can add a few minutes on top of that. Because the data source differs, prices and volume can differ slightly from TradingView, so the occasional signal may not match the chart exactly.
