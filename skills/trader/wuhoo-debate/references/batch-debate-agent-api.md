# Agent API 正确签名速查

> 2026-05-04 建立，基于实际运行中遇到的错误。

## BullAgent

### analyze(symbol, factor_data, technical_data, sentiment_data, fundamental_data)
```python
bull_view = bull.analyze(
    symbol=symbol,
    factor_data={"residual_vol": 25.0, "momentum_5d": 2.3, "momentum_10d": 1.2, ...},
    technical_data={"summary": "..."},
    sentiment_data={},
    fundamental_data={"name": "汇丰控股"}
)
# 返回: {"recommendation": "BUY|HOLD|SELL", "confidence": 0.65, "points": [...], ...}
```

### analyze_with_context(symbol, data, bear_view)
```python
# ✅ 正确（Rebuttal 阶段，不同方法！）
bull_rebuttal = bull.analyze_with_context(
    symbol=symbol,
    data={"factor_data": {...}, "technical_data": {...}, "sentiment_data": {}, "fundamental_data": {...}},
    bear_view=bear_view       # Bear 上一轮的结果
)

# ❌ 错误
bull.analyze(..., bear_arguments=...)   # 不存在此参数
```

## BearAgent

### analyze(symbol, factor_data, technical_data, sentiment_data, fundamental_data, bull_view)
```python
# ✅ 正确
bear_view = bear.analyze(
    symbol=symbol,
    factor_data={...},
    technical_data={...},
    sentiment_data={},
    fundamental_data={...},
    bull_view=bull_view        # 参数名是 bull_view
)

# ❌ 错误
bear.analyze(..., bull_arguments=...)   # 不存在此参数
```

## TraderAgent

### make_decision(symbol, bull_view, bear_view, consensus_points, disagreement_points)
```python
# ✅ 正确
trader_decision = trader.make_decision(
    symbol=symbol,
    bull_view=bull_rebuttal,      # 使用 rebuttal 后的 Bull 观点
    bear_view=bear_view,
    consensus_points=["信号混合"],
    disagreement_points=["多空分歧"]
)
# 返回: {"decision": "BUY|HOLD|SELL", "confidence": 0.65, "position_size": 0.1, ...}

# ❌ 错误
trader.decide(...)                          # 方法不存在
trader.make_decision(...)["action"]         # 字段是 'decision'，不是 'action'
trader.make_decision(...)["recommendation"] # 也可能是 'decision'
```

## RiskAgent

### review(symbol, trader_decision, ...)
（在 batch_debate.py 中未使用，run_debate.py 中有完整调用）
