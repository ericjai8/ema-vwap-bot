"""Prop-rule and loss-cutting variants + a 50K eval pass-rate simulator.

Eval model (typical 50K): pass at +$3,000; fail if the end-of-day balance falls
$2,000 below its highest end-of-day balance; stop for the day once the day is
down $1,000 (remaining trades that day are skipped). Every CME trading day in the
data is used as a start date; evals still running at the end of data are dropped.
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))
import emavwap as E
import backtest as B

TARGET, TRAIL, DLL = 3000, 2000, 1000
PROP = dict(flat_at=1650, no_entry_from=1600, news_block=((825, 840),))

VARIANTS = [
    ("A  as-is (holds overnight)", {}),
    ("B  prop rules: flat 4:55pm, no 4-6pm entries, skip 8:30 data", PROP),
    ("C  B + stop after 2 losses/day", dict(PROP, max_losses_day=2)),
    ("D  C + exit at ⚠ if under +1R", dict(PROP, max_losses_day=2, warn_exit_under=1.0)),
    ("E  C + failed-cross exit (3 bars)", dict(PROP, max_losses_day=2, inval_bars=3)),
    ("F  C + stop 2.0 ATR", dict(PROP, max_losses_day=2, hard_stop=2.0)),
    ("G  C + stop 1.5 ATR", dict(PROP, max_losses_day=2, hard_stop=1.5)),
    ("H  D + E (⚠<1R + failed cross)", dict(PROP, max_losses_day=2, warn_exit_under=1.0, inval_bars=3)),
]


def day_pnl(trades, micros_scale=1.0):
    rows = [((t["exit_ts"].tz_convert(E.ET) + pd.Timedelta(hours=6)).date(), t["exit_ts"], t["usd"] * micros_scale)
            for t in trades]
    df = pd.DataFrame(rows, columns=["day", "ts", "usd"]).sort_values("ts")
    return df


def eval_sim(trades, days, scale):
    """days: ordered list of all CME trading days in the data."""
    df = day_pnl(trades, scale)
    by_day = {d: g.usd.tolist() for d, g in df.groupby("day")}
    res = []
    for i in range(len(days)):
        bal, peak, n = 0.0, 0.0, 0
        out = None
        for d in days[i:]:
            n += 1
            dp = 0.0
            for u in by_day.get(d, []):
                if dp <= -DLL:
                    break                      # done for the day
                dp += u
            bal += dp
            if bal >= TARGET:
                out = ("pass", n); break
            peak = max(peak, bal)
            if bal <= peak - TRAIL:
                out = ("fail", n); break
        if out:
            res.append(out)
    r = pd.DataFrame(res, columns=["out", "days"])
    p = (r.out == "pass").mean()
    return p, r[r.out == "pass"].days.median(), r[r.out == "fail"].days.median()


def stats(trades, scale=1.0):
    u = np.array([t["usd"] for t in trades]) * scale
    eq = np.cumsum(u)
    dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    dp = day_pnl(trades, scale).groupby("day").usd.sum()
    s = np.sort(u)
    return dict(trades=len(u), win=f"{(u > 0).mean():.0%}", pf=round(u[u > 0].sum() / -u[u <= 0].sum(), 2),
                net=round(u.sum()), maxdd=round(dd), worst_day=round(dp.min()),
                net_ex_top1pct=round(s[:-max(1, len(u) // 100)].sum()))


if __name__ == "__main__":
    df = B.load_5m()
    et = df.index.tz_convert(E.ET)
    days = sorted(set((et + pd.Timedelta(hours=6)).date))
    rows = []
    for name, kw in VARIANTS:
        for mode, scale, label in (("single", 1, "1 micro, trend exit"), ("single", 2, "2 micros, trend exit"),
                                   ("plan", 1, "3 micros, 2R/4R/runner")):
            if mode == "single" and scale == 2:
                tr = cache
            else:
                tr, _, _ = E.run(df, exit_mode=mode, **kw)
                if mode == "single":
                    cache = tr
            st = stats(tr, scale)
            p, dpass, dfail = eval_sim(tr, days, scale)
            rows.append(dict(variant=name, size=label, **st, eval_pass=f"{p:.0%}",
                             days_to_pass=dpass, days_to_fail=dfail))
        print(name, "done", flush=True)
    out = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    print(out.to_string(index=False))
    out.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "prop_test_results.csv"), index=False)
