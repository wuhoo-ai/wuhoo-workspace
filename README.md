# wuhoo-workspace

Hermes Agent 工作空间 - 单一仓库管理所有技能、配置和学习成果。

## 目录结构

```
skills/        # 所有自定义技能 (SKILL.md + 执行代码)
data/          # 运行时数据 (有价值的结果被git托管)
learning/      # 学习循环产出 (自动审查报告)
config/        # Hermes配置 (非敏感)
scripts/       # 自动化脚本
docs/          # 项目文档
```

## 技能列表

| 技能 | 描述 | 入口 |
|------|------|------|
| stock-pick | 多市场多因子选股 | `python3.11 stock_pick.py` |
| deep-analysis | 单股深度分析 | `python3.11 deep_analysis.py` |
| trade | 多市场交易执行 | `python3.11 workflow_c_multi_market.py` |
| debate | 多空辩论分析 | `python3.11 run_debate.py` |
| diagnose | 持仓诊断 | `python3.11 diagnose.py` |
| news-rss | RSS新闻采集 | `python3.11 src/fetcher.py` |
| futu-api | 富途API行情/交易 | `python3.11 scripts/quote/*.py` |

## 学习循环

每日凌晨3点自动执行:
1. 分析过去24小时session执行情况
2. 生成技能性能报告
3. 检查memory使用率
4. 自动commit + push

## 配置

敏感信息 (API keys) 存储在 `~/.hermes/.env`，不提交到仓库。
配置模板在 `config/.env.example`。

## 分支

- `openclaw`: 旧版OpenClaw配置 (归档)
- `hermes-agent`: 当前活跃分支
