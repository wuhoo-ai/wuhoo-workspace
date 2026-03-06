# 🔧 配置修复报告

**修复时间**: 2026-03-01 15:08 GMT+8  
**修复内容**: Agent 工具权限修复 + Brave Search API 说明

---

## ✅ 已修复问题

### 问题 1: main-agent 缺少 message 权限

**修复前**:
```json
"tools": {
  "allow": ["read", "edit", "write", "web_search", "web_fetch"]
}
```

**修复后**:
```json
"tools": {
  "allow": ["read", "edit", "write", "web_search", "web_fetch", "message"]
}
```

**效果**: main-agent 现在可以通过 DingTalk 发送消息通知

---

### 问题 2: trade-agent 工具权限不足

**修复前**:
```json
"tools": {
  "allow": ["read", "exec"]
}
```

**修复后**:
```json
"tools": {
  "allow": ["read", "edit", "write", "exec"]
}
```

**效果**: trade-agent 现在可以直接更新持仓文件和交易日志

---

## 📚 Brave Search API 说明

### Brave Search 是什么？

**Brave Search** 是 Brave 浏览器公司提供的独立搜索引擎 API，特点：

| 特性 | 说明 |
|------|------|
| **独立性** | 不依赖 Google/Bing，自有索引 |
| **隐私保护** | 不追踪用户搜索历史 |
| **无偏见** | 搜索结果不受算法操控 |
| **价格** | 有免费额度，付费计划合理 |

### OpenClaw 中的用途

`web_search` 技能使用 Brave Search API 进行联网检索：
- 搜索最新信息（新闻、数据、文档）
- 查找代码库和技术文档
- 获取实时市场信息
- 验证事实和信息

---

## 🔑 Brave Search API Key 获取方法

### 方法 1: 免费计划（推荐）

1. **访问 Brave Search API 官网**
   ```
   https://brave.com/search/api/
   ```

2. **注册账号**
   - 使用邮箱注册
   - 或使用 GitHub/Google 账号登录

3. **创建 API Key**
   - 进入 Dashboard: `https://api.search.brave.com/app/keys`
   - 点击 "Create Key"
   - 选择 "Free" 计划

4. **免费计划额度**
   ```
   - 每月 2000 次搜索请求
   - 每秒 1 次请求
   - 适合个人使用和开发测试
   ```

### 方法 2: 付费计划

如果需要更高配额：

| 计划 | 价格 | 配额 |
|------|------|------|
| Base | $3/月 | 20,000 次/月 |
| Basic | $30/月 | 200,000 次/月 |
| Standard | $90/月 | 600,000 次/月 |

---

## ⚙️ 配置 API Key

### 获取 API Key 后，添加到配置文件：

**方式 1: 添加到 ~/.openclaw/.env**
```bash
# 编辑文件
vim ~/.openclaw/.env

# 添加这行
BRAVE_API_KEY=bsa_xxxxxxxxxxxxxxxxxxxxx

# 保存后重启网关
systemctl --user restart openclaw-gateway
```

**方式 2: 使用 openclaw configure 命令**
```bash
openclaw configure --section web
# 按提示输入 API Key
```

**方式 3: 直接添加到 openclaw.json**
```json
{
  "tools": {
    "web": {
      "search": {
        "apiKey": "bsa_xxxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

---

## 🧪 测试 API Key

配置完成后，测试 web_search 是否正常工作：

```bash
# 在对话中测试
请搜索 "OpenClaw latest features"
```

或者使用 curl 测试：
```bash
curl "https://api.search.brave.com/res/v1/web/search?q=test" \
  -H "Accept: application/json" \
  -H "Accept-Encoding: gzip" \
  -H "X-Subscription-Token: YOUR_API_KEY"
```

---

## 💡 替代方案

如果不想使用 Brave Search，可以考虑：

### 1. 使用 web_fetch 代替
- `web_fetch` 不需要 API Key
- 可以直接抓取已知 URL 的内容
- 适合获取特定网页内容

### 2. 其他搜索引擎 API
- **Google Custom Search API** (免费 100 次/天)
- **Bing Search API** (付费，有免费试用)
- **DuckDuckGo API** (有限制)
- **Jina Search** (AI 优化搜索，部分免费)

### 3. OpenClaw 配置
```json
{
  "tools": {
    "web": {
      "search": {
        "provider": "brave",  // 或 "google", "bing", "jina"
        "apiKey": "xxx"
      }
    }
  }
}
```

---

## 📊 配置更新总结

| 配置项 | 修复前 | 修复后 | 状态 |
|--------|--------|--------|------|
| main-agent tools | 5 个权限 | 6 个权限 (+message) | ✅ |
| trade-agent tools | 2 个权限 | 4 个权限 (+edit, +write) | ✅ |
| Brave API Key | 未配置 | 待用户配置 | ⏳ |

---

## 🔄 下一步

1. **获取 Brave API Key** (5 分钟)
   - 访问 https://brave.com/search/api/
   - 注册并创建免费 Key

2. **配置 API Key**
   ```bash
   # 推荐方式
   echo 'BRAVE_API_KEY=bsa_xxx' >> ~/.openclaw/.env
   systemctl --user restart openclaw-gateway
   ```

3. **测试 web_search**
   ```
   请搜索 "AI quant trading 2026 trends"
   ```

---

*修复完成时间：2026-03-01 15:08 GMT+8*  
*配置已热重载，message 和文件写入权限立即生效*
