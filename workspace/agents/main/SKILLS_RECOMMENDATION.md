# Skills 推荐与安装建议

**更新时间**: 2026-03-10  
**来源**: 现有 Skills + ClawHub Registry

---

## 📊 状态总览

| 状态 | 数量 | 说明 |
|------|------|------|
| ✅ 已安装 | 3 | github, coding-agent, summarize |
| 🔍 可安装 | 17 | ClawHub 可搜索到 |
| ❓ 需确认 | 1 | 名称可能不准确 |

---

## ✅ 已安装 Skills (3)

### 1. github 🐙
**状态**: ✅ 已安装  
**评分**: 3.63 (ClawHub 类似 Skills)  
**用途**: GitHub 操作集成

**功能**:
- 检查 PR 状态、CI 运行
- 创建/评论 Issues
- 列出/筛选 PRs 和 Issues
- 查看运行日志
- 通过 `gh` CLI 执行操作

**依赖**: `gh` (GitHub CLI)

**推荐度**: 🔴 已安装，无需操作

---

### 2. coding-agent 🧩
**状态**: ✅ 已安装  
**用途**: 委派编码任务给 AI Agent

**功能**:
- 构建新功能或应用
- 审查 PR（在临时目录中）
- 重构大型代码库
- 迭代式编码（需要文件探索）

**依赖**: `claude` / `codex` / `opencode` / `pi` (至少一个)

**推荐度**: 🔴 已安装，无需操作

---

### 3. summarize 🧾
**状态**: ✅ 已安装  
**评分**: 3.5+ (类似 Skills)  
**用途**: 总结 URL、播客、本地文件内容

**功能**:
- 总结网页内容
- 提取播客转录
- 总结 YouTube 视频（作为转录备选）
- 提取本地文件内容

**依赖**: `summarize` CLI (通过 brew 安装)

**推荐度**: 🔴 已安装，无需操作

---

## 🔍 可安装 Skills 推荐

### 🔴 强烈推荐 (优先级高)

#### 4. tavily-search 🔍
**状态**: ❌ 可安装  
**评分**: 3.61 (openclaw-tavily-search)  
**用途**: Tavily AI 搜索引擎

**功能**:
- AI 优化的网页搜索
- 提取结构化数据
- 支持深度研究
- 比传统搜索更准确

**依赖**: Tavily API Key

**安装命令**:
```bash
clawhub install openclaw-tavily-search
```

**推荐理由**: 
- 比 jina_search 更智能
- 支持深度研究模式
- 适合复杂查询

**推荐度**: ⭐⭐⭐⭐⭐

---

#### 5. browse 🌐
**状态**: ❌ 可安装  
**评分**: 3.14 (browse - Browserbase)  
**用途**: 浏览器自动化

**功能**:
- 自动化网页交互
- 截图和录制
- 填写表单
- 抓取动态内容

**依赖**: Browserbase API 或本地浏览器

**安装命令**:
```bash
clawhub install browse
```

**推荐理由**:
- 补充 web_fetch 的不足
- 支持 JavaScript 渲染页面
- 适合复杂网页交互

**推荐度**: ⭐⭐⭐⭐⭐

---

#### 6. backup 💾
**状态**: ❌ 可安装  
**评分**: 3.65 (openclaw-backup)  
**用途**: OpenClaw 配置和数据备份

**功能**:
- 自动备份配置文件
- 备份 Skills 和 Agents
- 定时备份任务
- 快速恢复

**依赖**: 无

**安装命令**:
```bash
clawhub install openclaw-backup
```

**推荐理由**:
- 保护配置和数据
- 防止意外丢失
- 必备工具

**推荐度**: ⭐⭐⭐⭐⭐

---

### 🟡 推荐安装 (实用工具)

#### 7. debug-pro 🐛
**状态**: ❌ 可安装  
**用途**: 高级调试工具

**功能**:
- 日志分析
- 性能分析
- 错误追踪
- 代码调试

**依赖**: 可能需安装额外工具

**推荐理由**:
- 开发必备
- 提高调试效率

**推荐度**: ⭐⭐⭐⭐

---

#### 8. task-status ✅
**状态**: ❌ 可安装  
**用途**: 任务状态追踪

**功能**:
- 任务进度追踪
- 状态更新通知
- 任务历史记录

**推荐理由**:
- 适合多任务管理
- 提高透明度

**推荐度**: ⭐⭐⭐⭐

---

#### 9. deepwork-tracker 🎯
**状态**: ❌ 可安装  
**用途**: 深度工作时间追踪

**功能**:
- 记录专注时间
- 阻止干扰
- 生产力统计

**推荐理由**:
- 提高生产力
- 时间管理工具

**推荐度**: ⭐⭐⭐⭐

---

### 🟢 可选安装 (按需)

#### 10. technews 📰
**状态**: ❌ 可安装  
**用途**: 科技新闻聚合

**功能**:
- 聚合科技新闻
- 自定义新闻源
- 定时推送

**推荐理由**:
- 保持技术敏感度
- 适合开发者

**推荐度**: ⭐⭐⭐

---

#### 11. deepwiki 📚
**状态**: ❌ 可安装  
**用途**: Wikipedia 深度搜索

**功能**:
- Wikipedia 高级搜索
- 关联条目推荐
- 知识图谱浏览

**推荐理由**:
- 研究工具
- 知识查询

**推荐度**: ⭐⭐⭐

---

#### 12. get-tldr 📝
**状态**: ❌ 可安装  
**用途**: 长文摘要

**功能**:
- 自动摘要长文
- 提取关键点
- TL;DR 生成

**推荐理由**:
- 快速阅读
- 信息筛选

**推荐度**: ⭐⭐⭐

---

#### 13. agent-news 🤖
**状态**: ❌ 可安装  
**用途**: AI Agent 相关新闻

**功能**:
- AI Agent 新闻聚合
- 行业动态
- 技术更新

**推荐理由**:
- 跟踪 AI 发展
- 行业动态

**推荐度**: ⭐⭐⭐

---

#### 14. docker-essentials 🐳
**状态**: ❌ 可安装  
**用途**: Docker 基础工具

**功能**:
- Docker 命令辅助
- 容器管理
- 镜像构建辅助

**依赖**: Docker

**推荐理由**:
- Docker 用户必备
- 简化容器操作

**推荐度**: ⭐⭐⭐

---

#### 15. agentguard 🛡️
**状态**: ❌ 可安装  
**用途**: Agent 安全监控

**功能**:
- 监控 Agent 行为
- 安全策略执行
- 异常检测

**推荐理由**:
- 安全防护
- 企业级需求

**推荐度**: ⭐⭐⭐

---

#### 16. self-improving-agent 🔄
**状态**: ✅ 可安装  
**评分**: 42.2k⭐ (187 下载)  
**用途**: 自我反思 + 自我改进的 Agent

**功能**:
- 自我反思和自我批评
- 自我学习和记忆
- 评估自己的工作
- 捕获错误并永久改进
- 支持 Linux/macOS/Windows

**依赖**: 无

**安装命令**:
```bash
clawhub install self-improving-agent
```

**推荐理由**:
- 持续改进 Agent 性能
- 从错误中学习
- 建立长期记忆

**推荐度**: ⭐⭐⭐⭐

---

#### 17. using-superpowers ⚡
**状态**: ❌ 可安装  
**用途**: 高级功能教程

**功能**:
- 高级用法指南
- 最佳实践
- 技巧分享

**推荐理由**:
- 学习资源
- 提高技能

**推荐度**: ⭐⭐

---

#### 18. agent-browser 🌐
**状态**: ❌ 可安装  
**评分**: 2.40 (多个版本)  
**用途**: Agent 浏览器集成

**功能**:
- 浏览器控制
- 网页自动化
- Agent 交互

**推荐理由**:
- 类似 browse
- 评分较低，可选

**推荐度**: ⭐⭐

---

### ❓ 需确认

#### 19. skill-vetter ✅
**状态**: ✅ 可安装  
**评分**: 49k⭐ (204 下载)  
**用途**: AI Agent Skills 安全审核

**功能**:
- 安装前安全检查
- 识别危险代码模式
- 权限范围审查
- 来源可信度验证

**安全检查项目**:
```
🚨 立即拒绝的危险信号:
• curl/wget 到未知 URL
• 发送数据到外部服务器
• 请求凭证/token/API Key
• 读取~/.ssh, ~/.aws, ~/.config
• 访问 MEMORY.md, USER.md, SOUL.md
• 使用 base64 解码
• 使用 eval() 或 exec() 执行外部输入
• 修改 workspace 外的系统文件
• 未列出的包安装
• 混淆代码
```

**安装命令**:
```bash
clawhub install skill-vetter
```

**推荐理由**:
- **安全必备** - 安装任何 Skill 前先审核
- 避免恶意代码
- 保护敏感数据

**推荐度**: ⭐⭐⭐⭐⭐ (安全必备)

---

## 📦 安装建议方案

### 方案 A：最小安装 (3 个)

**优先级最高，必备工具**:

```bash
clawhub install openclaw-tavily-search   # AI 搜索
clawhub install browse                   # 浏览器自动化
clawhub install openclaw-backup          # 备份工具
```

**总评分**: ⭐⭐⭐⭐⭐ (10.4/5)

**理由**: 补充核心能力，保护数据安全

---

### 方案 B：标准安装 (7 个)

**实用工具组合**:

```bash
# 方案 A +
clawhub install debug-pro                # 调试工具
clawhub install task-status              # 任务追踪
clawhub install deepwork-tracker         # 时间管理
clawhub install technews                 # 科技新闻
```

**总评分**: ⭐⭐⭐⭐⭐

**理由**: 覆盖开发、管理、学习场景

---

### 方案 C：完整安装 (12 个)

**全面功能组合**:

```bash
# 方案 B +
clawhub install deepwiki                 # 知识查询
clawhub install get-tldr                 # 长文摘要
clawhub install agent-news               # AI 新闻
clawhub install docker-essentials        # Docker 工具
clawhub install agentguard               # 安全监控
clawhub install skill-vetter             # Skill 审核 (需确认名称)
```

**总评分**: ⭐⭐⭐⭐⭐

**理由**: 全面覆盖各种使用场景

---

## 🎯 分类推荐

### 搜索与信息获取
| Skill | 推荐度 | 说明 |
|-------|--------|------|
| tavily-search | 🔴 | AI 搜索，强烈推荐 |
| browse | 🔴 | 浏览器自动化 |
| deepwiki | 🟡 | Wikipedia 搜索 |
| get-tldr | 🟡 | 长文摘要 |

### 开发与调试
| Skill | 推荐度 | 说明 |
|-------|--------|------|
| coding-agent | 🔴 | 已安装 |
| github | 🔴 | 已安装 |
| debug-pro | 🟡 | 高级调试 |
| docker-essentials | 🟢 | Docker 工具 |

### 生产力与管理
| Skill | 推荐度 | 说明 |
|-------|--------|------|
| task-status | 🟡 | 任务追踪 |
| deepwork-tracker | 🟡 | 时间管理 |
| backup | 🔴 | 数据备份 |

### 学习与资讯
| Skill | 推荐度 | 说明 |
|-------|--------|------|
| technews | 🟢 | 科技新闻 |
| agent-news | 🟢 | AI 新闻 |
| using-superpowers | 🟢 | 高级教程 |

### 安全与监控
| Skill | 推荐度 | 说明 |
|-------|--------|------|
| agentguard | 🟢 | 安全监控 |
| skill-vetter | 🟡 | Skill 审核 |

---

## ⚠️ 注意事项

1. **API Key 需求**: 部分 Skills 需要 API Key（如 Tavily）
2. **依赖安装**: 某些 Skills 需要安装 CLI 工具
3. **功能重叠**: 部分 Skills 功能可能重叠（如 browse 和 agent-browser）
4. **评分参考**: ClawHub 评分仅供参考，实际体验可能不同
5. **名称确认**: skill-vetting/skill-vetter 需确认正确名称

---

## 📚 参考资源

| 资源 | 链接 |
|------|------|
| **ClawHub** | https://clawhub.com |
| **Skills 文档** | https://docs.openclaw.ai/skills |
| **安装指南** | ~/workspace/agents/main/CLAWHUB_SKILLS_GUIDE.md |

---

**文档结束**
