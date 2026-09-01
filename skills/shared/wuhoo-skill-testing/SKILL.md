---
name: wuhoo-skill-testing
description: Writing and running unit tests for wuhoo skills -- test directory structure, conftest patterns, mock strategies for LLM/Futu/external deps, and resolving pytest conftest conflicts.
tags: ["wuhoo"]
version: 1.0.0
---

# Wuhoo Skill 单元测试指南

## 测试目录结构

每个 skill 的测试放在 `skills/{skill-name}/tests/` 下：

```
skills/
├── wuhoo-trade/tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_*.py
├── wuhoo-debate/tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_debate.py
├── wuhoo-stock-deep-analysis/tests/
│   ├── conftest.py
│   └── test_deep_analysis.py
├── wuhoo-trade-diagnose/tests/
│   ├── conftest.py
│   └── test_diagnose.py
└── wuhoo-futuapi/tests/
    ├── conftest.py
    └── test_futu_api.py
```

## conftest.py 模板

每个 skill 的 `tests/conftest.py` 只需注入路径：

```python
"""{SkillName} 测试套件"""
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_DIR))
```

**注意**：`__init__.py` 在 trade/debate tests 中存在，其他 skill 可不加。

## 运行测试

### 关键：分 skill 运行

pytest 全量运行 `skills/` 时会因多个 `conftest.py` 同名（都叫 `tests.conftest`）而报 `ImportPathMismatchError` 或 `Plugin already registered` 错误。

**正确做法 -- 逐个 skill 运行：**

```bash
for skill in trade debate stock-pick deep-analysis diagnose futu-api; do
  echo "=== Testing $skill ==="
  python3.11 -m pytest skills/$skill/tests/ -v -W ignore::DeprecationWarning
done
```

或在 `pyproject.toml` 中配置 testpaths 后，仍然分目录运行：

```bash
python3.11 -m pytest skills/wuhoo-stock-deep-analysis/tests/ -v
python3.11 -m pytest skills/wuhoo-trade-diagnose/tests/ -v
```

## Mock 策略

### LLM/AI Agent 依赖

对于需要调用 LLM 的模块（debate, deep-analysis），全面使用 `unittest.mock.patch` 隔离：

```python
from unittest.mock import patch, MagicMock

# 不要直接初始化 Agent -- 会触发真实 LLM 调用导致超时
# 而是测试纯逻辑函数
def test_determine_signal_hold():
    handler = WorkflowDHandler(market='CN', account_id=18767295)
    signal, reason = handler._determine_signal(
        code="600519",
        pl_ratio=5.0,
        weight=0.08,
        diag_status="success",
        wb_signal="持有",
        has_violation=False,
        data_quality="good"
    )
    assert signal == "HOLD"
```

### Futu/OpenD 依赖

futu-api 测试不连接真实 OpenD：

```python
def test_import_common(self):
    """验证模块可导入 + 核心类存在"""
    import common
    assert hasattr(common, 'FutuConfig')

def test_futu_config(self):
    """测试数据类字段"""
    from common import FutuConfig
    config = FutuConfig()
    assert config.opend_host == "127.0.0.1"
    assert config.trd_env == "SIMULATE"
```

### Akshare/网络数据依赖

```python
def test_not_available_returns_error(self):
    from deep_analysis import AkshareFetcher
    f = AkshareFetcher()
    if not f.is_available():
        result = f.fetch_all("600519", "贵州茅台")
        assert "error" in result or "available" in result
```

## 编写测试的关键步骤

### 1. 先读实际方法签名

**不要猜参数名！** 打开源文件确认实际签名：

```bash
grep -n 'def _determine_signal' skills/diagnose/diagnose.py
# 输出: def _determine_signal(self, code, pl_ratio, weight, diag_status, wb_signal, has_violation, data_quality)
```

常见错误：
- `diagnosis` vs `diag_status`
- `current_weight` vs `weight`
- `host/port` vs `opend_host/opend_port`

### 2. 测试覆盖层级

| 层级 | 示例 | 是否需要 Mock |
|------|------|--------------|
| 工具函数 | `safe_float`, 代码格式化 | 不需要 |
| 数据类 | `FutuConfig` 字段验证 | 不需要 |
| 业务逻辑 | `_determine_signal`, 权重计算 | 不需要（纯函数） |
| 外部调用 | Akshare 拉取、LLM 推理 | 必须 Mock 或跳过 |
| 模块导入 | import 成功、类存在 | 不需要 |

### 3. 测试类组织

```python
class TestSafeConverters:    # 工具函数
class TestAkshareFetcher:    # 外部数据源
class TestFactorDataLoader:  # 因子加载器
class TestDebateRunner:      # 辩论逻辑
class TestFinancialAnalyzer: # 财务分析
class TestNormalizeCode:     # 代码转换
class TestSignalConstants:   # 常量验证
class TestWorkflowDHandler:  # 工作流核心
```

### 4. 验证测试失败原因

测试失败时先确认：
- **AssertionError** = 逻辑错误，检查代码或测试预期
- **TypeError** = 方法签名不匹配，回源文件确认实际参数
- **AttributeError** = 方法不存在，检查方法名是否正确
- **ImportError** = 路径问题，检查 conftest.py

## 已知问题

### conftest 模块名冲突

多个 skill 的 `tests/conftest.py` 在 pytest 全量扫描时冲突：

```
ImportPathMismatchError: ('tests.conftest', '.../wuhoo-debate/tests/conftest.py', '.../wuhoo-trade/tests/conftest.py')
```

**解决方案**：始终分 skill 运行，不要用 `pytest skills/` 一次跑全部。

### futu SDK DeprecationWarning

futu SDK 内部产生大量 `DeprecationWarning`（protobuf descriptor），运行测试时加 `-W ignore::DeprecationWarning` 屏蔽。

### Debate 测试超时

直接初始化 DebateAgent 会调用 LLM，导致超时。**必须 mock 或使用纯逻辑测试**。