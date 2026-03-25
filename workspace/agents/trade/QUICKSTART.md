# VnPy + 富途 快速开始指南

**创建时间**: 2026-03-25  
**更新时间**: 2026-03-25 11:05  
**状态**: 🟢 OpenD 已安装 → 等待账号配置

---

## ✅ 已完成

### 1. Python 虚拟环境

```bash
位置：~/.openclaw/workspace/agents/trade/venv-futu/
Python: 3.11.13
```

### 2. 已安装包

| 包名 | 版本 | 状态 |
|------|------|------|
| vnpy | 4.3.0 | ✅ |
| vnpy_futu | 6.3.2808.0 | ✅ |
| futu-api | 10.1.6108 | ✅ |
| numpy | 2.4.3 | ✅ |
| pandas | 3.0.1 | ✅ |
| ta-lib | 0.6.8 | ✅ |

### 3. 测试脚本

```bash
# 验证安装
cd ~/.openclaw/workspace/agents/trade
source venv-futu/bin/activate
python skills/vnpy-futu-trader/test_installation.py

# 测试连接 (需要 OpenD 运行)
python skills/vnpy-futu-trader/test_connection.py
```

### 4. 富途官方 Skills (2026-03-25 安装)

```bash
位置：~/.openclaw/skills/futu-openapi/
       ~/,openclaw/skills/futu-install-opend/

功能:
├── openapi — 行情交易助手 (25 个脚本 + 65 个 API 速查)
│   ├── 行情查询：市场快照、K 线、买卖盘、逐笔成交等
│   ├── 交易操作：下单、撤单、改单、持仓查询
│   └── 实时订阅：报价、K 线、逐笔推送
└── install-opend — OpenD 安装助手
    ├── 自动检测操作系统
    ├── 一键下载并启动 OpenD
    └── 自动升级 SDK
```

---

## 🔧 下一步：配置富途 OpenD

### 步骤 1: 下载 OpenD

访问：https://www.futumm.com/OpenAPI

选择对应版本：
- Windows: `FutuOpenD.exe`
- macOS: `FutuOpenD.dmg`
- Linux: `FutuOpenD.tar.gz`

### 步骤 2: 启动 OpenD

1. 运行 OpenD 程序
2. 登录富途账号
3. 配置：
   - **监听地址**: `127.0.0.1`
   - **监听端口**: `11111`
   - **市场**: `HK` (港股) / `US` (美股)
   - **环境**: `SIMULATE` (模拟盘)

### 步骤 3: 完成 API 合规确认

首次使用需要：
1. 打开富途牛牛 APP
2. 完成 API 使用协议确认
3. 填写量化交易问卷

### 步骤 4: 测试连接

```bash
cd ~/.openclaw/workspace/agents/trade
source venv-futu/bin/activate

# 编辑测试脚本，替换密码
vim skills/vnpy-futu-trader/test_connection.py
# 修改：gateway_setting["密码"] = "YOUR_TRADE_PASSWORD"

# 运行测试
python skills/vnpy-futu-trader/test_connection.py
```

---

## 📋 模拟盘测试清单

连接成功后，按顺序测试：

- [ ] 连接 OpenD
- [ ] 查询账户信息
- [ ] 查询持仓列表
- [ ] 订阅实时行情
- [ ] 模拟盘下单 (买入)
- [ ] 查询订单状态
- [ ] 模拟盘下单 (卖出)
- [ ] 设置止盈止损

---

## 🔐 安全配置

### 环境变量

创建 `~/.openclaw/workspace/agents/trade/.env`:

```bash
# 富途配置
FUTU_HOST=127.0.0.1
FUTU_PORT=11111
FUTU_MARKET=HK
FUTU_ENV=SIMULATE

# 交易密码 (不要明文存储，使用加密工具)
# FUTU_PASSWORD=xxx
```

### 权限控制

| 操作 | 环境 | 权限 |
|------|------|------|
| 行情查询 | 模拟/实盘 | 只读 |
| 账户查询 | 模拟/实盘 | 只读 |
| 模拟下单 | 模拟盘 | 自动 |
| 实盘下单 | 实盘 | 用户确认 |

---

## 📡 与 Pipeline 集成

### 输入格式 (来自 main-agent)

```json
{
  "action": "execute_trade",
  "params": {
    "code": "603220.SH",
    "action": "BUY",
    "position_ratio": 0.03,
    "limit_price": 12.50,
    "stop_loss": 11.50,
    "take_profit": 14.00,
    "account": "SIMULATE"
  }
}
```

### 输出格式 (返回 main-agent)

```json
{
  "success": true,
  "order_id": "VT20260325001",
  "filled_price": 12.48,
  "filled_volume": 300,
  "status": "FILLED",
  "commission": 5.00
}
```

---

## 🐛 常见问题

### Q1: 连接超时

**原因**: OpenD 未启动或端口错误

**解决**:
1. 确认 OpenD 已启动
2. 检查端口配置 (默认 11111)
3. 检查防火墙设置

### Q2: 认证失败

**原因**: 密码错误或未完成合规确认

**解决**:
1. 确认交易密码正确
2. 在富途 APP 完成 API 合规确认

### Q3: 下单失败

**原因**: 模拟盘权限未开通

**解决**:
1. 先开通实盘账户
2. 实盘账户可申请模拟账户
3. 联系富途客服

---

## 📚 相关文档

- [全链路 Pipeline](AUTOMATION_PIPELINE.md)
- [VnPy Skill](skills/vnpy-futu-trader/SKILL.md)
- [VnPy 官方文档](https://www.vnpy.com/docs/)
- [富途 OpenAPI 文档](https://openapi.futumm.com/futu-api-doc/)

---

## 📞 支持

遇到问题可以：

1. 查看 VnPy 文档：https://www.vnpy.com/docs/
2. 查看富途 API 文档：https://openapi.futumm.com/
3. 联系 trade-agent 协助排查
4. 提交 Issue 到 GitHub

---

*最后更新：2026-03-25*
