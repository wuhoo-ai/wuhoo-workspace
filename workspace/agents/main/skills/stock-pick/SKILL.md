---
name: stock-pick
description: "中证 1000 成分股选股工具，基于多因子模型筛选股票。使用 Tushare Pro API 获取数据，支持残差波动率、换手率、动量、Beta 等因子筛选。"
metadata: { "openclaw": { "emoji": "📊", "requires": { "env": ["TUSHARE_TOKEN"], "bins": ["python3"] } } }
---

# Stock Pick - 中证 1000 选股工具

基于多因子模型的中证 1000 成分股筛选工具。

## 功能特性

- ✅ 中证 1000 成分股数据管理（分批拉取、增量更新）
- ✅ 4 因子筛选模型（残差波动率、换手率、动量、Beta）
- ✅ 数据完整性检查与备份
- ✅  CLI 接口，支持指定日期选股

## 筛选条件

| 因子 | 计算方式 | 排序 | 筛选比例 |
|------|----------|------|----------|
| 252 日残差收益波动率 | 过去 252 日残差收益标准差 | 越低越好 | 前 50% |
| 5 日平均换手率 | 过去 5 日换手率均值 | 越高越好 | 前 50% |
| 5 日价格动量 | 过去 5 日累计收益率 | 越高越好 | 前 30% |
| 20 日 Beta 值 | 相对中证 1000 的 20 日 Beta | 越高越好 | 前 30% |

**最终排序**: 过去 10 日价格动量（越低越好），输出 Top 10

## 安装

```bash
cd ~/openclaw/skills/stock-pick
pip3 install -r requirements.txt
```

## 使用方式

### 指定日期选股
```bash
# 选股（指定日期）
python3 ~/openclaw/skills/stock-pick/stock_pick.py --date 2026-03-06

# 选股（默认昨天）
python3 ~/openclaw/skills/stock-pick/stock_pick.py
```

### 数据管理
```bash
# 检查并更新数据
python3 ~/openclaw/skills/stock-pick/stock_pick.py --update-data

# 强制全量更新
python3 ~/openclaw/skills/stock-pick/stock_pick.py --update-data --force
```

## 输出示例

```
=== 中证 1000 选股报告 ===
选股日期：2026-03-06

[数据准备]
- 中证 1000 成分股数量：1000
- 数据完整性检查：通过

[筛选过程]
1. 初始股票池：1000 只
2. 252 日残差波动率 (前 50%)：500 只
3. 5 日平均换手率 (前 50%)：250 只
4. 5 日价格动量 (前 30%)：75 只
5. 20 日 Beta 值 (前 30%)：23 只

[最终结果 (按 10 日动量排序，越低越好)]
排名  代码      名称    10 日动量  252 残差波  5 日换手%  5 日动量%  20 日 Beta
1    000XXX  XX 股份   0.023     0.012      8.5       12.3      1.45
2    600XXX  XX 科技   0.031     0.011      7.2       10.1      1.38
...

共选出 10 只股票
```

## 数据存储

```
~/.openclaw/workspace/agents/main/data/stock-pick/
├── index_members.csv      # 中证 1000 成分股列表
├── daily_data/            # 日线行情数据（按日期分区）
│   ├── 2026/
│   │   ├── 202603.parquet
│   │   └── ...
├── factors/               # 因子计算结果
│   └── factors_20260306.csv
└── backups/               # 数据备份
    └── index_members_20260312.csv
```

## 配置

### 环境变量
```bash
TUSHARE_TOKEN=your_token_here  # Tushare Pro API Token
```

### 可调参数（代码中）
```python
# 筛选比例
VOLATILITY_PERCENTILE = 0.50   # 残差波动率前 50%
TURNOVER_PERCENTILE = 0.50     # 换手率前 50%
MOMENTUM_5D_PERCENTILE = 0.30  # 5 日动量前 30%
BETA_PERCENTILE = 0.30         # Beta 前 30%

# 最终输出数量
TOP_N = 10
```

## 注意事项

1. **数据更新**: 首次运行会自动拉取历史数据，后续支持增量更新
2. **交易日历**: 自动跳过非交易日
3. **停牌处理**: 自动排除停牌股票
4. **ST 股票**: 默认排除 ST/*ST 股票
5. **新上市股票**: 上市不足 252 日的股票自动排除

## 故障处理

| 问题 | 解决方案 |
|------|----------|
| Token 无效 | 检查 `~/.openclaw/.env` 中的 `TUSHARE_TOKEN` |
| 无数据返回 | 检查日期是否为交易日，使用 `--update-data` 更新数据 |
| 股票数量过少 | 调整筛选比例参数，或检查数据完整性 |
| 计算超时 | 数据量大时正常，可分批处理 |

---

*创建时间：2026-03-12*
*版本：1.0*
