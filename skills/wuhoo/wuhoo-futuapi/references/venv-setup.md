# Python Venv 架构与合并记录

## 当前架构（2026-05-08 合并后）

所有 wuhoo skill 统一使用 **hermes-agent venv**：

```
~/.hermes/hermes-agent/venv/bin/python3        # 唯一 venv，所有 wuhoo skill 指向这里
```

### 已包含的关键依赖

| 包 | 版本 | 用途 |
|----|------|------|
| futu-api | 10.4.6408 | Futu OpenD SDK |
| yfinance | 1.3.0 | US 期货/股票日线 |
| akshare | 1.18.56 | A 股财务数据 |
| tushare | 1.4.29 | A 股行情 |
| pandas | 3.0.2 | 数据处理 |
| numpy | 2.4.4 | 数值计算 |
| ta-lib | 0.6.8 | 技术指标 |
| openpyxl | 3.1.5 | Excel 读写 |
| requests | 2.33.1 | HTTP 请求 |
| pytest | 9.0.3 | 测试框架 |
| httpx | 0.28.1 | HTTP 客户端 |

共 234 个包。

## 历史：合并前（3 个 venv）

| Venv | 位置 | 包数 | 状态 |
|------|------|:---:|------|
| hermes-agent | `~/.hermes/hermes-agent/venv` | 234 | 主 venv（超集） |
| AI-Trader | `~/.openclaw/workspace/projects/AI-Trader/venv` | 39 | 保留，解耦 wuhoo 引用 |
| akshare-stock | `~/.agents/skills/akshare-stock/venv` | 30 | 🗑️ 已删除（无引用 legacy） |

### 合并原因

- AI-Trader venv 的 futu-api 版本更旧（10.2 vs 10.4）
- AI-Trader venv 缺 yfinance、tushare、ta-lib
- akshare-stock venv 完全无引用
- hermes-agent venv 是完整超集，所有 futures 脚本已验证可运行

### 受影响文件 (已全部更新)

| 文件 | 改动 |
|------|------|
| `wuhoo-futures-pick/SKILL.md` | 双 venv → 统一 VENV 变量 |
| `wuhoo-futures-trade/SKILL.md` | VENV 路径 + 依赖说明 |
| `wuhoo-futuapi/SKILL.md` | SDK 运行环境路径 |
| `wuhoo-futuapi/references/cn-sim-trading.md` | Python 运行环境路径 |
| `wuhoo-futures-pick/futures_workflow.py` | VENV_AI/VENV_HERMES → VENV |

## 新 skill 添加依赖流程

当新 skill 需要额外 pip 包时：

```bash
~/.hermes/hermes-agent/venv/bin/pip install <package>
```

验证导入：

```bash
~/.hermes/hermes-agent/venv/bin/python3 -c "import <package>"
```

## 验证清单

```bash
# 检查 futu-api 可导入
~/.hermes/hermes-agent/venv/bin/python3 -c "from futu import *; print('OK')"

# 检查 yfinance 可导入
~/.hermes/hermes-agent/venv/bin/python3 -c "import yfinance; print(yfinance.__version__)"

# 检查 ta-lib 可导入
~/.hermes/hermes-agent/venv/bin/python3 -c "import talib; print('OK')"

# 运行期货选品验证
~/.hermes/hermes-agent/venv/bin/python3 ~/wuhoo-workspace/skills/wuhoo/wuhoo-futures-pick/futures_pick.py --top-n 3 --direction both
```
