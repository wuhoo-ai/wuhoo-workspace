# QuantaAlpha 部署完成报告

**部署时间**: 2026-03-12 19:34  
**部署位置**: `~/.openclaw/workspace/agents/main/skills/quantaalpha-deep/`  
**Skill 位置**: `~/.openclaw/workspace/agents/main/skills/quantaalpha-skill/`

---

## ✅ 完成清单

### 1. 代码安装
- [x] 克隆 QuantaAlpha 仓库
- [x] 创建 Python 3.11 虚拟环境
- [x] 安装所有依赖（300+ 包）
- [x] 配置环境变量 (.env)

### 2. 数据下载
- [x] cn_data.zip (493 MB) - Qlib A 股数据
- [x] daily_pv.h5 (398 MB) - 全量价格 - 成交量数据
- [x] daily_pv_debug.h5 (1.41 MB) - 调试子集
- [x] 数据解压和部署

### 3. 数据验证
```
Qlib 数据目录：data/qlib/cn_data
  ✓ calendars: True
  ✓ features: True (6018 个股票特征文件)
  ✓ instruments: True

HDF5 数据目录：git_ignore_folder/factor_implementation_source_data
  ✓ daily_pv.h5: True (380 MB)
```

### 4. Skill 封装
- [x] 创建 SKILL.md 文档
- [x] 创建快速启动脚本 (quantaalpha.sh)
- [x] 配置使用说明

---

## 📁 目录结构

```
~/.openclaw/workspace/agents/main/skills/
├── quantaalpha-deep/           # QuantaAlpha 主程序
│   ├── configs/                # 配置文件
│   ├── quantaalpha/            # 核心代码
│   ├── frontend-v2/            # Web 前端
│   ├── experiment/             # 实验脚本
│   ├── docs/                   # 文档
│   ├── data/
│   │   ├── qlib/cn_data/       # Qlib 数据
│   │   └── results/            # 输出结果
│   ├── git_ignore_folder/
│   │   └── factor_implementation_source_data/  # HDF5 数据
│   ├── hf_data/                # 下载缓存
│   ├── venv/                   # Python 环境
│   ├── .env                    # 环境配置
│   └── run.sh                  # 启动脚本
│
└── quantaalpha-skill/          # Workspace Skill
    ├── SKILL.md                # Skill 文档
    └── quantaalpha.sh          # 快速启动
```

---

## 🚀 快速开始

### 方法 1: 使用 Skill 脚本
```bash
~/.openclaw/workspace/agents/main/skills/quantaalpha-skill/quantaalpha.sh "量价因子挖掘"
```

### 方法 2: 直接使用
```bash
cd ~/.openclaw/workspace/agents/main/skills/quantaalpha-deep
source venv/bin/activate
./run.sh "Price-Volume Factor Mining"
```

### 方法 3: Web Dashboard
```bash
cd ~/.openclaw/workspace/agents/main/skills/quantaalpha-deep/frontend-v2
bash start.sh
# 访问 http://localhost:3000
```

---

## 📊 研究方向示例

| 研究方向 | 命令 |
|---------|------|
| **量价因子** | `./run.sh "量价因子挖掘"` |
| **微观结构** | `./run.sh "Market Microstructure"` |
| **动量策略** | `./run.sh "Momentum Strategies"` |
| **波动率** | `./run.sh "Volatility Factors"` |
| **资金流** | `./run.sh "Order Flow Analysis"` |

---

## ⚙️ 配置说明

### 当前配置 (.env)
```bash
# 数据路径
QLIB_DATA_DIR=/home/admin/.openclaw/workspace/agents/main/skills/quantaalpha-deep/data/qlib/cn_data
DATA_RESULTS_DIR=/home/admin/.openclaw/workspace/agents/main/skills/quantaalpha-deep/data/results

# LLM API (阿里云百炼)
OPENAI_API_KEY=sk-placeholder  # 需要替换为真实 Key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
REASONING_MODEL=qwen-max
CHAT_MODEL=qwen-max
```

### 修改 API Key
```bash
nano ~/.openclaw/workspace/agents/main/skills/quantaalpha-deep/.env
# 修改 OPENAI_API_KEY=sk-your-actual-key
```

---

## 📈 预期性能

根据论文数据（沪深 300 → 中证 500 迁移）：

| 指标 | 数值 |
|------|------|
| Information Coefficient (IC) | 0.1501 |
| Rank IC | 0.1465 |
| 年化超额收益 (ARR) | 27.75% |
| 最大回撤 (MDD) | 7.98% |
| Calmar 比率 | 3.4774 |

---

## 🔧 故障处理

### 1. API Key 错误
```bash
# 检查 .env 配置
cat ~/.openclaw/workspace/agents/main/skills/quantaalpha-deep/.env | grep API_KEY
```

### 2. 数据路径错误
```bash
# 验证数据目录
ls -la ~/.openclaw/workspace/agents/main/skills/quantaalpha-deep/data/qlib/cn_data/
```

### 3. 内存不足
```bash
# 使用调试数据（较小）
cp git_ignore_folder/factor_implementation_source_data_debug/daily_pv.h5 \
   git_ignore_folder/factor_implementation_source_data/daily_pv.h5
```

---

## 📚 相关文档

- **中文文档**: `docs/README_CN.md`
- **用户指南**: `docs/user_guide.md`
- **实验指南**: `experiment/README_EXPERIMENT_CN.md`
- **Windows 兼容**: `docs/WINDOWS_COMPAT.md`

---

## 🔗 相关链接

- GitHub: https://github.com/QuantaAlpha/QuantaAlpha
- 论文：https://arxiv.org/abs/2602.07085
- 团队主页：https://quantaalpha.github.io/
- 数据源：https://huggingface.co/datasets/QuantaAlpha/qlib_csi300

---

## ✨ 下一步建议

1. **配置 API Key**: 替换 `.env` 中的 `OPENAI_API_KEY`
2. **测试运行**: 使用 `daily_pv_debug.h5` 进行快速测试
3. **查看结果**: 因子库保存在 `data/results/all_factors_library.json`
4. **回测验证**: 使用独立回测脚本验证因子表现

---

*部署完成！如有问题请查看 SKILL.md 文档。*
