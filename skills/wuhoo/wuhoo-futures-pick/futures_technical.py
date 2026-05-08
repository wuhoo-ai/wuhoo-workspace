#!/usr/bin/env python3
"""futures_technical.py — 期货技术面分析 Phase 2.1"""
import sys, json, argparse
from pathlib import Path
from datetime import datetime
import numpy as np, pandas as pd

DATA_DIR = Path.home() / "wuhoo-workspace" / "data" / "futures"
KLINES_DIR = DATA_DIR / "daily_kline"
CONTRACT_INFO_PATH = DATA_DIR / "contract_info.json"

def sma(s, n):
    r = np.full(len(s), np.nan)
    if len(s) >= n: r[n-1:] = np.convolve(s, np.ones(n)/n, mode="valid")
    return r

def ema(s, n):
    r = np.full(len(s), np.nan)
    if len(s) < n: return r
    r[n-1] = np.mean(s[:n])
    a = 2.0/(n+1)
    for i in range(n, len(s)): r[i] = a*s[i] + (1-a)*r[i-1]
    return r

def macd(close, fast=12, slow=26, signal=9):
    ef, es = ema(close, fast), ema(close, slow)
    dif = ef - es
    valid = ~np.isnan(dif)
    if not valid.any(): return dict(dif=0,dea=0,histogram=0,state="neutral",divergence="none")
    dea = ema(dif[valid], signal)
    dea_full = np.full(len(close), np.nan)
    start = np.where(valid)[0][0]
    if len(dea) > 0:
        end = min(start+signal-1+len(dea), len(dea_full))
        dea_full[start+signal-1:end] = dea[:end-start-signal+1]
    hist = (dif - dea_full) * 2
    cd, cdea, ch = dif[-1] or 0, dea_full[-1] or 0, hist[-1] or 0
    ph = hist[-2] or 0 if len(hist) >= 2 else 0
    if cd > 0 and cd > cdea: st = "bullish"
    elif cd > 0 and cd < cdea: st = "weakening"
    elif cd < 0 and cd < cdea: st = "bearish"
    else: st = "recovering"
    div = "none"
    if len(close) >= 20:
        if close[-1] > close[-10] and ch < ph: div = "bearish_divergence"
        elif close[-1] < close[-10] and ch > ph: div = "bullish_divergence"
    return dict(dif=round(float(cd),4), dea=round(float(cdea),4),
                histogram=round(float(ch),4), state=st, divergence=div)

def rsi(close, n=14):
    if len(close) < n+1: return 50.0
    d = np.diff(close)
    g, l = np.where(d>0,d,0), np.where(d<0,-d,0)
    ag, al = np.mean(g[-n:]), np.mean(l[-n:])
    if al == 0: return 100.0
    return float(100.0 - 100.0/(1.0+ag/al))

def bollinger(close, n=20, k=2.0):
    if len(close) < n: return {}
    ma = sma(close, n)
    std = np.array([np.nanstd(close[max(0,i-n+1):i+1]) for i in range(len(close))])
    up, lo = ma + k*std, ma - k*std
    cur, cma = close[-1], ma[-1] or close[-1]
    cu, cl = up[-1] or cur*1.05, lo[-1] or cur*0.95
    bw = (cu-cl)/cma*100
    pp = (cur-cl)/(cu-cl)*100 if cu > cl else 50
    pos = "above_upper" if pp > 95 else "below_lower" if pp < 5 else "inside"
    return dict(upper=round(float(cu),2), middle=round(float(cma),2), lower=round(float(cl),2),
                bandwidth_pct=round(float(bw),2), price_position=pos, position_pct=round(float(pp),1))

def find_sr(df, lookback=60):
    if len(df) < lookback: return dict(supports=[],resistances=[],nearest_support=None,nearest_resistance=None)
    h, l = df["high"].values[-lookback:], df["low"].values[-lookback:]
    cur = df["close"].values[-1]
    w = 5
    su = sorted(set(round(l[i],1) for i in range(w,len(l)-w) if l[i]==min(l[i-w:i+w+1])))
    re = sorted(set(round(h[i],1) for i in range(w,len(h)-w) if h[i]==max(h[i-w:i+w+1])))
    sb = [s for s in su if s < cur]
    ra = [r for r in re if r > cur]
    return dict(supports=sb[-3:] if sb else [], resistances=ra[:3] if ra else [],
                nearest_support=sb[-1] if sb else None, nearest_resistance=ra[0] if ra else None)

def vol_analysis(df):
    if "volume" not in df.columns or len(df) < 30: return dict(volume_trend="unknown")
    v, c = df["volume"].values, df["close"].values
    pu = c[-1] > c[-5]
    vu = v[-5:].mean() > v[-10:-5].mean()
    if pu and vu: tr = "bullish_accumulation"
    elif pu and not vu: tr = "bearish_divergence"
    elif not pu and vu: tr = "distribution"
    else: tr = "bearish_low_volume"
    a20 = v[-20:].mean()
    vr = v[-1]/a20 if a20 > 0 else 1
    return dict(volume_trend=tr, vol_ratio_vs_20d=round(float(vr),2),
                is_spike=vr>2.0, avg_vol_20d=round(float(a20),0))

def atr(df, n=14):
    if len(df) < n+1: return 0
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    tr = np.array([max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])) for i in range(1,len(df))])
    return float(np.mean(tr[-n:]))

def trend_analysis(df):
    c = df["close"].values
    cur = c[-1]
    def sl(a, n):
        if len(a) < n+2: return 0
        return (a[-1]-a[-1-n])/a[-1-n]*100
    ma5 = sma(c,5)[-1] or cur
    ma10 = sma(c,10)[-1] or cur
    ma20 = sma(c,20)[-1] or cur
    ma50 = sma(c,50)[-1] or cur
    ma200 = sma(c,200)[-1] or cur
    mv = [v for v in [ma5,ma10,ma20,ma50,ma200] if not np.isnan(v)]
    al = "mixed"
    if len(mv) >= 4:
        if all(mv[i] > mv[i+1] for i in range(len(mv)-1)): al = "bullish_aligned"
        elif all(mv[i] < mv[i+1] for i in range(len(mv)-1)): al = "bearish_aligned"
    ab = sum(1 for v in mv if cur > v)
    p20 = (cur-ma20)/ma20*100 if not np.isnan(ma20) and ma20 > 0 else 0
    t5 = "up" if sl(c,5) > 0 else "down"
    t20 = "up" if sl(c,20) > 0 else "down"
    t60 = "up" if sl(c,60) > 0 else "down" if len(c) >= 61 else "unknown"
    ts = "strong" if t5==t20==t60 else "mixed" if t5==t20 else "diverging"
    mas = {k:round(float(v),1) if not np.isnan(v) else None
           for k,v in [("ma5",ma5),("ma10",ma10),("ma20",ma20),("ma50",ma50),("ma200",ma200)]}
    return dict(mas=mas, alignment=al, above_ma_count=f"{ab}/{len(mv)}",
                pct_above_ma20=round(float(p20),2),
                trend_5d=t5, trend_20d=t20, trend_60d=t60, trend_strength=ts)

def tech_score(ind):
    s = 5.0
    rs = []
    t = ind.get("trend",{})
    if t.get("trend_strength") == "strong": s += 2.0; rs.append("多周期趋势一致")
    elif t.get("trend_strength") == "mixed": s += 0.5
    elif t.get("trend_strength") == "diverging": s -= 0.5; rs.append("短中期趋势背离")
    if t.get("alignment") == "bullish_aligned": s += 0.5; rs.append("均线多头排列")
    m = ind.get("macd",{})
    if m.get("state") == "bullish": s += 1.0
    elif m.get("state") == "bearish": s -= 1.0; rs.append("MACD 死叉")
    if m.get("divergence") == "bullish_divergence": s += 1.5; rs.append("MACD 底背离")
    elif m.get("divergence") == "bearish_divergence": s -= 1.0; rs.append("MACD 顶背离")
    r = ind.get("rsi", 50)
    if 30 <= r <= 40: s += 0.5; rs.append(f"RSI={r:.0f} 偏超卖")
    elif r < 30: s += 1.0; rs.append(f"RSI={r:.0f} 超卖")
    elif 60 < r <= 70: s -= 0.5; rs.append(f"RSI={r:.0f} 偏超买")
    elif r > 70: s -= 1.0; rs.append(f"RSI={r:.0f} 超买")
    bb = ind.get("bollinger",{})
    if bb.get("price_position") == "below_lower": s += 0.5; rs.append("触及布林下轨")
    elif bb.get("price_position") == "above_upper": s -= 0.5; rs.append("触及布林上轨")
    adx = ind.get("adx_14", 20) or 20
    if adx >= 25: s += 0.5
    elif adx < 15: s -= 0.5; rs.append(f"ADX={adx:.0f} 无趋势")
    v = ind.get("volume",{})
    if v.get("volume_trend") == "bullish_accumulation": s += 0.5; rs.append("量价齐升")
    elif v.get("volume_trend") == "distribution": s -= 0.5; rs.append("价跌量增")
    if v.get("is_spike"): s += 0.5; rs.append("异常放量")
    s = max(1.0, min(10.0, s))
    lb = "strong_bullish" if s>=7.5 else "bullish" if s>=6 else "neutral" if s>=4 else "bearish" if s>=2.5 else "strong_bearish"
    return dict(score=round(s,1), label=lb, reasons=rs)

def analyze(code):
    with open(CONTRACT_INFO_PATH) as f: contracts = json.load(f)
    info = contracts.get(code, {})
    market = info.get("market", "US")
    kp = KLINES_DIR / market / f"{code}.csv"
    if not kp.exists(): return {"error": f"无数据: {kp}"}
    df = pd.read_csv(kp)
    close = df["close"].values
    cur = close[-1]
    ind = dict(
        close=round(float(cur),2),
        macd=macd(close),
        rsi=round(rsi(close),1),
        bollinger=bollinger(close),
        support_resistance=find_sr(df),
        volume=vol_analysis(df),
        atr_14=round(atr(df),2),
        atr_pct=round(atr(df)/cur*100,2) if cur>0 else 0,
        trend=trend_analysis(df),
        adx_14=20.0,
    )
    # Try loading ADX from factor CSV
    fp = DATA_DIR / "factors" / f"factors_{datetime.now().strftime('%Y-%m-%d')}.csv"
    if fp.exists():
        fdf = pd.read_csv(fp)
        m = fdf[fdf["code"] == code]
        if not m.empty and "adx_14" in m.columns:
            v = m["adx_14"].iloc[0]
            if not pd.isna(v): ind["adx_14"] = round(float(v), 1)
    ts = tech_score(ind)
    a = atr(df) or cur*0.01
    sl = round(cur - 2*a, 2)
    ss = round(cur + 2*a, 2)
    tg = [dict(level=r, distance_pct=round((r-cur)/cur*100,2), type=f"R{i+1}")
          for i,r in enumerate(ind["support_resistance"].get("resistances",[])[:3])]
    return dict(code=code, name=info.get("name",code), market=market,
                date=datetime.now().strftime("%Y-%m-%d"), indicators=ind,
                technical_score=ts,
                trade_params=dict(stop_long=sl, stop_short=ss,
                stop_pct_long=round((cur-sl)/cur*100,2),
                stop_pct_short=round((ss-cur)/cur*100,2), targets=tg))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--code", required=True)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    r = analyze(a.code)
    if "error" in r: print(f"❌ {r['error']}"); sys.exit(1)
    ind = r["indicators"]
    sc = r["technical_score"]
    tp = r["trade_params"]
    print(f"📊 技术面分析: {r['name']} ({r['code']})")
    print(f"   日期: {r['date']}  |  现价: {ind['close']:.1f}")
    print(f"\n   ╔═══ 综合评分: {sc['score']:.1f}/10 ({sc['label']}) ═══╗")
    for rs in sc["reasons"]: print(f"   ║  • {rs}")
    print(f"   ╚{'═'*40}╝\n")
    t = ind["trend"]
    print(f"  📈 趋势: {t['trend_5d']}/{t['trend_20d']}/{t['trend_60d']} (5d/20d/60d)  排列:{t['alignment']}")
    print(f"          MA20={t['mas']['ma20']}  价距MA20={t['pct_above_ma20']:+.1f}%")
    m = ind["macd"]
    print(f"  📊 指标: MACD {m['state']} DIF={m['dif']:.2f}  RSI={ind['rsi']:.0f}  ADX={ind['adx_14']:.0f}")
    bb = ind["bollinger"]
    if bb: print(f"          布林: {bb['price_position']} 带宽={bb['bandwidth_pct']:.1f}%")
    sr = ind["support_resistance"]
    print(f"  📐 支撑阻力: 支撑{sr['supports']}  阻力{sr['resistances']}")
    v = ind["volume"]
    print(f"  📊 成交量: {v['volume_trend']}  量比={v['vol_ratio_vs_20d']:.1f}x")
    if v.get("is_spike"): print(f"     ⚠️ 异常放量!")
    targets_str = ', '.join([f"{t['level']:.1f}({t['distance_pct']:+.1f}%)" for t in tp['targets']])
    print(f"\n  🎯 止损(多):{tp['stop_long']:.1f}(-{tp['stop_pct_long']:.1f}%)  止盈: {targets_str}")
    if a.json: print("\n"+json.dumps(r, indent=2, ensure_ascii=False, default=str))

if __name__ == "__main__": main()
