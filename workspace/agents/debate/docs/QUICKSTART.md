# 快速开始指南

## 5 分钟快速体验

### 1. 安装依赖

```bash
cd /home/admin/.openclaw/workspace/agents/debate
pip install requests pyyaml
```

### 2. 配置 API Key

```bash
export BAILIAN_API_KEY="your-api-key"
```

### 3. 运行第一次辩论

```bash
python run_debate.py --symbol 600519.SH --name "贵州茅台"
```

### 4. 查看结果

辩论记录保存在 `data/` 目录：

```bash
cat data/debate_*.json | jq
```

---

## 15 分钟深度体验

### 1. 运行测试套件

```bash
python tests/test_debate_system.py
python tests/test_agents.py
```

### 2. 查看辩论历史

```bash
ls -lh data/
cat data/debate_*.json | jq '.bull_view, .bear_view, .trader_decision'
```

### 3. 自定义运行

```bash
# 使用真实数据 (如果数据源可用)
python run_debate.py --symbol 000858.SZ --name "五粮液" --mode full

# 指定输出目录
python run_debate.py --symbol 601318.SH --name "中国平安" --output my_debates
```

---

## 30 分钟完整配置

### 1. 安装 akshare (可选，提升数据质量)

```bash
pip install akshare
```

### 2. 配置数据源

编辑 `adapters/data_aggregator.py` 配置数据源路径：

```python
def __init__(self):
    self.quantaalpha_data_dir = "/path/to/quantaalpha/data"
    self.trendradar_data_dir = "/path/to/trendradar/output"
```

### 3. 与 AI-Trader 集成

确保 AI-Trader 路径正确：

```python
# integrations/ai_trader_integration.py
self.ai_trader_path = Path("/home/admin/.openclaw/workspace/projects/AI-Trader")
```

### 4. 运行回测

```bash
python scripts/backtest_debate.py --symbol 600519.SH --start 2026-01-01 --end 2026-03-17
```

---

## 常见问题

### Q: akshare not installed 警告

**A**: akshare 是可选依赖。如果不安装，系统会使用模拟数据。如需真实技术面数据：

```bash
pip install akshare
```

### Q: API Key 错误

**A**: 确保设置了正确的环境变量：

```bash
export BAILIAN_API_KEY="sk-..."
echo $BAILIAN_API_KEY  # 验证
```

### Q: 辩论记录在哪里

**A**: 默认在 `data/` 目录：

```bash
ls data/
# debate_20260317_120000_600519SH.json
```

### Q: 如何修改风控规则

**A**: 编辑 `rules/risk_rules.yaml`：

```yaml
position_limits:
  single_stock_max: 0.20  # 修改单票最大仓位
```

### Q: 如何添加新的分析维度

**A**: 
1. 在 `prompts/bull_analyst.md` 和 `prompts/bear_analyst.md` 添加新维度
2. 在 `adapters/` 添加对应的数据适配器
3. 在 `agents/` 更新 Agent 逻辑

---

## 下一步

- 📖 阅读 [README.md](../README.md) 了解完整架构
- 🔧 查看 [PERFORMANCE_GUIDE.md](./PERFORMANCE_GUIDE.md) 优化性能
- 📊 运行回测验证策略有效性
- 🔌 集成到你的交易系统

---

**祝你使用愉快！** 🎉
