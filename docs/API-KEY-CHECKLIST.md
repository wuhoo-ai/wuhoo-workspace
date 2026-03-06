# 🔑 OpenClaw API Key 配置清单

**生成时间**: 2026-03-01 17:01 GMT+8  
**用途**: 汇总所有需要 API Key 的工具和技能

---

## 📋 配置概览

| 优先级 | 工具/技能 | 用途 | 必需 | 状态 |
|--------|----------|------|------|------|
| 🔴 **P0** | Brave Search | 联网搜索 | 必需 (web_search) | ❌ 未配置 |
| 🟡 **P1** | AlphaVantage | 股票行情数据 | 必需 (AI-Trader) | ❌ 待确认 |
| 🟡 **P1** | Jina Search | 新闻搜索 | 必需 (AI-Trader) | ❌ 待确认 |
| 🟢 **P2** | ElevenLabs | TTS 语音合成 | 可选 (AI 直播) | ❌ 未配置 |
| 🟢 **P2** | Notion | 知识管理 | 可选 | ❌ 未配置 |
| ⚪ **P3** | GitHub | 代码仓库管理 | 可选 (dev-agent) | ❌ 待确认 |

---

## 🔴 P0 - 必需配置

### 1. Brave Search API Key

**用途**: `web_search` 技能，联网检索信息

**免费额度**: 2000 次/月

**获取方法**:
```
1. 访问：https://brave.com/search/api/
2. 注册账号
3. Dashboard → Create Key → Free 计划
4. 复制 API Key (格式：bsa_xxxxxxxxxxxxx)
```

**配置方式**:
```bash
# 添加到 ~/.openclaw/.env
BRAVE_API_KEY=bsa_你的 API_KEY

# 重启网关
systemctl --user restart openclaw-gateway
```

**验证**:
```
请搜索 "OpenClaw latest features"
```

---

## 🟡 P1 - AI-Trader 必需

### 2. AlphaVantage API Key

**用途**: 股票价格数据（AI-Trader 项目）

**免费额度**: 25 次/天（标准免费）

**获取方法**:
```
1. 访问：https://www.alphavantage.co/support/#api-key
2. 填写表单（免费）
3. 邮箱接收 API Key
4. 等待 1-5 分钟
```

**免费计划限制**:
- 25 次请求/天
- 5 次请求/分钟
- 适合低频交易（每日 1-2 次）

**配置方式**:
```bash
# 添加到 AI-Trader 的 .env 文件
cd ~/openclaw/workspace/Code/AI-Trader
echo 'ALPHA_VANTAGE_API_KEY=你的 API_KEY' >> .env
```

**AI-Trader 配置位置**:
```
~/openclaw/workspace/Code/AI-Trader/.env
```

**验证**:
```bash
cd ~/openclaw/workspace/Code/AI-Trader
python tools/price_tools.py --test
```

---

### 3. Jina API Key

**用途**: 新闻搜索、舆情分析（AI-Trader 的 search MCP 服务）

**免费额度**: 有免费额度（具体查看官网）

**获取方法**:
```
1. 访问：https://jina.ai/
2. 注册账号
3. Dashboard → API Keys → Create Key
4. 复制 API Key
```

**配置方式**:
```bash
# 添加到 AI-Trader 的 .env 文件
cd ~/openclaw/workspace/Code/AI-Trader
echo 'JINA_API_KEY=你的 API_KEY' >> .env
```

**验证**:
```bash
# 测试 Jina Search
curl https://s.jina.ai/AI%20trading -H "Authorization: Bearer 你的 API_KEY"
```

---

## 🟢 P2 - 可选但推荐

### 4. ElevenLabs API Key

**用途**: TTS 语音合成（AI 直播、语音播报）

**免费额度**: 10,000 字符/月

**获取方法**:
```
1. 访问：https://elevenlabs.io/
2. 注册账号
3. Profile → API Key
4. 复制 API Key
```

**配置方式**:
```bash
# 添加到 ~/.openclaw/.env
ELEVENLABS_API_KEY=你的 API_KEY

# 重启网关
systemctl --user restart openclaw-gateway
```

**OpenClaw 技能**: `sag` (Speech And Generate)

**用途场景**:
- AI 直播语音输出
- 故事朗读
- 交易报告语音播报

---

### 5. Notion API Key

**用途**: 知识管理、文档同步

**免费额度**: 完全免费（个人使用）

**获取方法**:
```
1. 访问：https://www.notion.so/my-integrations
2. New Integration → Create
3. 复制 Internal Integration Token
4. 分享页面到 Integration
```

**配置方式**:
```bash
# 添加到 ~/.openclaw/.env
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxx

# 重启网关
systemctl --user restart openclaw-gateway
```

**用途场景**:
- 同步交易笔记到 Notion
- 自动整理会议纪要
- 知识库管理

---

## ⚪ P3 - 按需配置

### 6. GitHub Token

**用途**: dev-agent 代码仓库管理（PR、Issue、Commit）

**免费额度**: 完全免费

**获取方法**:
```
1. 访问：https://github.com/settings/tokens
2. Generate new token (classic)
3. 选择 scopes:
   - repo (完整仓库权限)
   - workflow (CI/CD)
   - user (用户信息)
4. 复制 Token (格式：ghp_xxxxxxxxxxxxx)
```

**配置方式**:
```bash
# 添加到 ~/.openclaw/.env
GITHUB_TOKEN=ghp_你的 TOKEN

# 重启网关
systemctl --user restart openclaw-gateway
```

**用途场景**:
- 自动提交代码
- 创建 Pull Request
- 管理 Issue
- 自动备份

---

## 📝 配置文件位置汇总

### OpenClaw 全局配置
```bash
~/.openclaw/.env
```

**包含**:
- BRAVE_API_KEY
- ELEVENLABS_API_KEY
- NOTION_API_KEY
- GITHUB_TOKEN
- OPENAI_API_KEY (已有)

### AI-Trader 项目配置
```bash
~/openclaw/workspace/Code/AI-Trader/.env
```

**包含**:
- OPENAI_API_BASE (已有：https://coding.dashscope.aliyuncs.com/v1)
- OPENAI_API_KEY (已有)
- ALPHA_VANTAGE_API_KEY
- JINA_API_KEY
- MATH_HTTP_PORT=8000
- TRADE_HTTP_PORT=8002
- GETPRICE_HTTP_PORT=8003
- SEARCH_HTTP_PORT=8004

---

## 🎯 推荐配置顺序

### 第一批（立即配置）
1. ✅ **Brave Search** - web_search 技能必需
2. ✅ **AlphaVantage** - AI-Trader 行情数据
3. ✅ **Jina** - AI-Trader 新闻搜索

### 第二批（有空配置）
4. ElevenLabs - AI 直播语音
5. Notion - 知识管理

### 第三批（按需）
6. GitHub Token - 代码自动化

---

## 🔧 快速配置脚本

### 创建配置模板

```bash
#!/bin/bash
# ~/.openclaw/setup-keys.sh

echo "=== OpenClaw API Key 配置向导 ==="

# Brave Search
read -p "输入 Brave Search API Key: " BRAVE_KEY
echo "BRAVE_API_KEY=$BRAVE_KEY" >> ~/.openclaw/.env

# ElevenLabs
read -p "输入 ElevenLabs API Key (可选，直接回车跳过): " ELEVEN_KEY
if [ ! -z "$ELEVEN_KEY" ]; then
  echo "ELEVENLABS_API_KEY=$ELEVEN_KEY" >> ~/.openclaw/.env
fi

# Notion
read -p "输入 Notion API Key (可选，直接回车跳过): " NOTION_KEY
if [ ! -z "$NOTION_KEY" ]; then
  echo "NOTION_API_KEY=$NOTION_KEY" >> ~/.openclaw/.env
fi

# GitHub
read -p "输入 GitHub Token (可选，直接回车跳过): " GITHUB_TOKEN
if [ ! -z "$GITHUB_TOKEN" ]; then
  echo "GITHUB_TOKEN=$GITHUB_TOKEN" >> ~/.openclaw/.env
fi

echo ""
echo "=== AI-Trader 配置 ==="
cd ~/openclaw/workspace/Code/AI-Trader

# AlphaVantage
read -p "输入 AlphaVantage API Key: " AV_KEY
echo "ALPHA_VANTAGE_API_KEY=$AV_KEY" >> .env

# Jina
read -p "输入 Jina API Key: " JINA_KEY
echo "JINA_API_KEY=$JINA_KEY" >> .env

echo ""
echo "配置完成！重启网关..."
systemctl --user restart openclaw-gateway
echo "✅ 完成！"
```

**使用方法**:
```bash
chmod +x ~/.openclaw/setup-keys.sh
~/.openclaw/setup-keys.sh
```

---

## ✅ 配置验证

配置完成后，运行以下命令验证：

```bash
# 1. 检查 OpenClaw 配置
cat ~/.openclaw/.env | grep -E "BRAVE|ELEVEN|NOTION|GITHUB"

# 2. 检查 AI-Trader 配置
cat ~/openclaw/workspace/Code/AI-Trader/.env | grep -E "ALPHA|JINA"

# 3. 检查网关状态
systemctl --user status openclaw-gateway

# 4. 测试 web_search
# 在对话中：请搜索 "AI quant trading 2026"

# 5. 测试 AI-Trader
cd ~/openclaw/workspace/Code/AI-Trader
python tools/price_tools.py --test
```

---

## 📊 配置状态跟踪

| API Key | 获取链接 | 配置位置 | 状态 |
|---------|----------|----------|------|
| Brave Search | https://brave.com/search/api/ | ~/.openclaw/.env | ⏳ 待配置 |
| AlphaVantage | https://www.alphavantage.co/support/#api-key | AI-Trader/.env | ⏳ 待配置 |
| Jina | https://jina.ai/ | AI-Trader/.env | ⏳ 待配置 |
| ElevenLabs | https://elevenlabs.io/ | ~/.openclaw/.env | ⚪ 可选 |
| Notion | https://www.notion.so/my-integrations | ~/.openclaw/.env | ⚪ 可选 |
| GitHub | https://github.com/settings/tokens | ~/.openclaw/.env | ⚪ 可选 |

---

## 💡 提示

1. **API Key 安全**
   - 不要将 `.env` 文件提交到 Git
   - 定期检查 Key 的使用情况
   - 如泄露立即撤销并重新生成

2. **免费额度管理**
   - Brave: 2000 次/月 ≈ 66 次/天
   - AlphaVantage: 25 次/天，适合低频交易
   - 监控使用情况，避免超额

3. **配置备份**
   ```bash
   # 备份配置
   cp ~/.openclaw/.env ~/.openclaw/.env.backup
   cp ~/openclaw/workspace/Code/AI-Trader/.env ~/openclaw/workspace/Code/AI-Trader/.env.backup
   ```

---

*清单生成时间：2026-03-01 17:01 GMT+8*  
*建议优先配置 P0 和 P1 级别的 API Key*
