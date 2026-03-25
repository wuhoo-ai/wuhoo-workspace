# Skills 名称确认与更新

**更新时间**: 2026-03-10 19:50 GMT+8  
**来源**: ClawHub Registry (https://clawhub.com)

---

## ✅ 已确认的 Skills

### self-improving-agent ✅

**正确名称**: `self-improving-agent`  
**评分**: 42.2k⭐ (187 下载)  
**作者**: @ivangdavila  
**版本**: 16

**完整描述**:
> Self-reflection + Self-criticism + Self-learning + Self-organizing memory. 
> Agent evaluates its own work, catches mistakes, and improves permanently.

**功能**:
- 自我反思和自我批评
- 自我学习和组织记忆
- 评估自己的工作
- 捕获错误并永久改进
- 支持 Linux/macOS/Windows

**安装命令**:
```bash
clawhub install self-improving-agent
```

**推荐度**: ⭐⭐⭐⭐

---

### skill-vetter ✅

**正确名称**: `skill-vetter` (不是 skill-vetting)  
**评分**: 49k⭐ (204 下载)  
**作者**: @spclaudehome  
**版本**: 1

**完整描述**:
> Security-first skill vetting for AI agents. Use before installing any skill from 
> ClawdHub, GitHub, or other sources. Checks for red flags, permission scope, and 
> suspicious patterns.

**功能**:
- 安装前安全检查
- 识别危险代码模式
- 权限范围审查
- 来源可信度验证

**安全检查项目** (🚨 危险信号):
```
• curl/wget 到未知 URL
• 发送数据到外部服务器
• 请求凭证/token/API Key
• 读取~/.ssh, ~/.aws, ~/.config
• 访问 MEMORY.md, USER.md, SOUL.md, IDENTITY.md
• 使用 base64 解码
• 使用 eval() 或 exec() 执行外部输入
• 修改 workspace 外的系统文件
• 未列出的包安装
• 混淆代码 (压缩/编码/最小化)
• 请求 sudo 权限
```

**安装命令**:
```bash
clawhub install skill-vetter
```

**推荐度**: ⭐⭐⭐⭐⭐ (安全必备)

---

## 📊 更新后的推荐方案

### 方案 A：最小安装 (3 个) → 更新为 (4 个)

```bash
clawhub install skill-vetter             # ⭐ 安全审核 (新增)
clawhub install openclaw-tavily-search   # AI 搜索
clawhub install browse                   # 浏览器自动化
clawhub install openclaw-backup          # 备份工具
```

**理由**: skill-vetter 是安全必备，应该在安装任何其他 Skill 之前安装

---

### 方案 B：标准安装 (7 个) → 更新为 (8 个)

```bash
# 方案 A +
clawhub install self-improving-agent     # ⭐ 自我改进 (新增)
clawhub install debug-pro                # 调试工具
clawhub install task-status              # 任务追踪
clawhub install deepwork-tracker         # 时间管理
clawhub install technews                 # 科技新闻
```

---

### 方案 C：完整安装 (12 个) → 更新为 (13 个)

```bash
# 方案 B +
clawhub install deepwiki                 # 知识查询
clawhub install get-tldr                 # 长文摘要
clawhub install agent-news               # AI 新闻
clawhub install docker-essentials        # Docker 工具
clawhub install agentguard               # 安全监控
clawhub install skill-vetter             # Skill 审核 (已确认名称)
```

---

## 🎯 安装顺序建议

### 第一批：安全与基础 (必须)
```bash
# 1. 先安装安全审核工具
clawhub install skill-vetter

# 2. 安装备份工具
clawhub install openclaw-backup
```

### 第二批：核心能力 (推荐)
```bash
# 3. AI 搜索
clawhub install openclaw-tavily-search

# 4. 浏览器自动化
clawhub install browse

# 5. 自我改进
clawhub install self-improving-agent
```

### 第三批：实用工具 (按需)
```bash
# 6-13. 其他工具
clawhub install debug-pro
clawhub install task-status
clawhub install deepwork-tracker
clawhub install technews
clawhub install deepwiki
clawhub install get-tldr
clawhub install agent-news
clawhub install docker-essentials
```

---

## 📝 重要提示

### ⚠️ 安装任何 Skill 前

**必须先安装 skill-vetter**:
```bash
# 1. 先安装审核工具
clawhub install skill-vetter

# 2. 使用 skill-vetter 审核要安装的 Skill
# (具体使用方法查看 skill-vetter 的文档)

# 3. 审核通过后再安装
clawhub install <skill-name>
```

### 🔒 安全检查清单

安装任何 Skill 前，确保：
- [ ] 已安装 skill-vetter
- [ ] 已审核 Skill 代码
- [ ] 已确认来源可信
- [ ] 已检查权限范围
- [ ] 已查看其他用户评价

---

## 📚 参考资源

| Skill | ClawHub 链接 |
|-------|-------------|
| **self-improving-agent** | https://clawhub.ai/ivangdavila/self-improving |
| **skill-vetter** | https://clawhub.ai/spclaudehome/skill-vetter |
| **tavily-search** | https://clawhub.ai/arun-8687/tavily-search |
| **browse** | https://clawhub.ai/TheSethRose/agent-browser |
| **backup** | https://clawhub.ai/steipete/openclaw-backup |

---

**文档结束**
