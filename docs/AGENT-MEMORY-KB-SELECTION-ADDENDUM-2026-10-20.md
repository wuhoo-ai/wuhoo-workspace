# 多 Agent 记忆与知识库选型增补（第二轮）

**日期**：2026-10-20  
**范围**：在你指定的四个项目（Engram、MCP Reference Memory、千问记忆库、千问 RAG）基础上，扩大检索到 20+ 个候选，重新评估“记忆层 + 知识库层”的选型。  
**与原文档的关系**：本文是对 `AGENT-MEMORY-KB-PLAN-2026-10-20.md` §4「组件选型」的修订；原文档的架构原则、三端接线、验收流程仍然有效。  
**一句话结论**：方向不变（MCP + 双层），但记忆层默认从 Memorix 改为 **MemPalace**。推荐 **MemPalace（本地多语言记忆/KG 中枢）+ 千问 RAG（托管中文知识库）**；需要文件级锁/验证门时用 **Memorix + 千问 RAG**；数据不能出本机时用 **MemPalace + Basic Memory**；自动捕获优先用 **agentmemory + 千问 RAG**；生产级学习记忆用 **Hindsight + 千问 RAG**。

---

## 0. 第二轮结论

1. **记忆层不能只看 star 数，也不能只看 benchmark。** 关键分水岭是：
   - 是否有**原生 HTTP MCP**（三端共用一个服务，避免多进程争 SQLite/ChromaDB）；
   - 是否支持**中文语义检索**；
   - 是否提供**跨 Agent 协调**（任务、锁、交接、消息、共享产物）；
   - 是否能在 4 vCPU / 7.4 GB 内存上长期稳定运行。

2. **MemPalace 是本轮最大的修正：它不再是“等 HTTP”，而是默认记忆层候选。** 约 59.6k stars、MIT、Python + ChromaDB、47 个 MCP 工具、时序知识图谱、Agent diary/协调、仓库含 `.dsh-plugin`、Codex hooks，默认 `minilm`（英文，~80MB；中文需切 `embeddinggemma`，多语言，~300MB），LongMemEval 96.6% R@5 无需 LLM。据 v3.5.0 release notes，**HTTP transport 已在 v3.5.0 合入（PR #1806）**，v3.9.0 起提供 `mempalace serve` 单 hub，并在同版本加入 task coordination/task handoff（immutable base commit + definition of done）：`mempalace-mcp --transport http --host 127.0.0.1 --port 8765`，MCP 在 `/mcp`，健康检查 `/healthz`；hub 持有单写者 lease，读并发、写独占；据 issue #1646 说明，stdio 客户端也可转发到 hub。这正好解决“多个 Hermes profile / Codex / dsh 同时读写同一个 palace 导致 ChromaDB HNSW 漂移”的问题。官方 shared-brain 指南明确把 **Hermes bot、Codex、OpenCode、Claude Code** 列为同一个 hub 的客户端示例；协调层用 logstream 事件/产物（`task.request`/`task.reply`、`claimed`、`ack`、`patch.ready`），本地 stdio 会自动代理到 hub。**注意：必须只跑一个 hub，不要让多个进程直接写 palace（#1963 仍在跟踪直写场景）。**

3. **Memorix 仍然是“编排优先”场景的首选。** 原生 HTTP MCP（3211）、SQLite、Apache-2.0，明确支持 Hermes/Codex/DeepSeek Harness；文件级锁/验证门/消息/交接是它相对其它项目的差异化能力（MemPalace v3.9+ 也有 task coordination/handoff，但没有文件级锁）。弱点是项目较年轻（约 850 stars）、中文检索需要向量补足。它的“锁”是**任务/文件级协调锁**，MemPalace 的锁是**存储层单写者 lease**，两者不是一回事。

4. **agentmemory 是最强的“自动捕获/成熟度”挑战者。** 约 29.7k stars、Apache-2.0、3,700+ 测试；一个本地服务（HTTP MCP 3111）供所有 Agent 共享，54 个 MCP 工具、12 个 hooks，原生支持 Codex/Hermes，DeepSeek Harness 走 MCP；混合 BM25+向量+图检索，LongMemEval-S R@5 95.2%（厂商自测）。弱点：默认本地 embedding 是英文向 `all-MiniLM-L6-v2`，中文必须换 embedding 或接受 BM25；依赖 pinned iii-engine，端口多（3111/3112/3113/49134）。

5. **Hindsight 是“生产级学习记忆”的重型选项。** 约 51.8k stars、MIT；retain/recall/reflect、memory banks、mental models/knowledge pages；原生 HTTP MCP（8888），支持 DeepSeek 等 25+ LLM provider。弱点：需要 Docker/Postgres（或 embedded pg0）+ LLM，资源与运维明显重于 MemPalace/Memorix/agentmemory。

6. **Engram 不适合做中文跨 Agent 主记忆。** MIT、单 Go 二进制、SQLite FTS5、26 个 MCP 工具、HTTP API 7437、项目感知、冲突提示；但 README 明确选择“FTS5 over vector DB”，没有向量检索路径，中文连续文本又不分词——中文召回会明显不足。适合英文/代码标识符为主的轻量项目记忆，或作为 fallback。

7. **MCP Reference Memory 仍然只适合 PoC。** 官方 `@modelcontextprotocol/server-memory` 2.0.0，JSONL 知识图谱、子串搜索；新版增加了文件锁（独占锁、60 秒超时、陈旧锁处理），多客户端写入比以前安全，但仍没有向量、摘要、冲突处理和规模能力。

8. **千问记忆库（Qianwen Memory）不是项目记忆。** 它是托管 API，按 `user_id` 隔离，做“事实记忆 + 用户画像”，有 Pro/Lite、语义检索、rerank、异步写入；但没有官方 MCP（需自建适配器），Search 接口没有 metadata 过滤，`project_id` 是“记忆规则 ID”而不是项目命名空间，也没有任务/锁/交接。适合用户偏好/画像，不适合代码项目记忆。

9. **千问 RAG 是中文知识库的最优托管选项。** 原生 MCP Server（Streamable HTTP，`Retrieve` / `ListIndices`），中文 hybrid 检索 + `qwen3-rerank`，标准版 ¥0.03/小时（约 ¥21.6/月）+ 模型 token，100 GB / 100k 文档，Codex 0.120+ 直接支持。弱点是数据出本机、MCP 只读（写入要靠控制台/API/同步流水线）、需要单独的 `DASHSCOPE_API_KEY`。

10. **推荐组合（按数据边界与协调需求分）**：
    - **默认（数据可上云，记忆优先）**：**MemPalace + 千问 RAG**。本地多语言记忆/KG/共享产物，托管中文知识库。
    - **编排优先（需要文件级锁/验证门）**：**Memorix + 千问 RAG**。
    - **本地-only（数据不出机）**：**MemPalace + Basic Memory**。
    - **自动捕获优先**：**agentmemory + 千问 RAG**（先解决中文 embedding）。
    - **生产级学习记忆**：**Hindsight + 千问 RAG**（接受 Docker/Postgres + LLM）。

---

## 1. 四个指定项目深评

### 1.1 Engram

| 维度 | 事实 |
|---|---|
| 定位 | 面向 AI coding agent 的持久记忆；Go 单二进制 |
| 版本/许可 | v3.4.0（2026-10-12），MIT；约 5.9k stars（第三方统计） |
| 存储 | SQLite + FTS5；observations/sessions/prompts；`embedding` 列存在，但检索路径没有向量 |
| 传输 | MCP stdio；本地 HTTP API `127.0.0.1:7437`；CLI/TUI |
| 工具 | 26 个 MCP 工具：save/search/timeline/session/review/compare/conflicts 等 |
| 跨 Agent | Codex 有 setup/plugin；任何 MCP 客户端可接；Hermes/dsh 需手工配置 |
| 协调 | 项目感知、冲突提示（`mem_judge`/`mem_compare`）、session、prompt 存储；没有任务/文件锁/交接 |
| 中文 | FTS5 `unicode61` 不分词；没有向量路径 → 中文召回弱 |
| 资源 | 极低；单二进制 + SQLite，部署最简单 |

**判断**：Engram 是“最小可用的英文/代码项目记忆”。如果你的记忆内容以英文标识符、commit、文件路径为主，它很合适；但本次场景有大量中文设计/决策/坑点，且要求跨 Agent 语义召回，Engram 不适合做第一层。保留为“MemPalace/Memorix 都太重时的 fallback”。

### 1.2 MCP Reference Memory

| 维度 | 事实 |
|---|---|
| 定位 | 官方参考实现，不是生产记忆系统 |
| 版本/许可 | `@modelcontextprotocol/server-memory` 2.0.0；MIT（新贡献 Apache-2.0 过渡） |
| 存储 | 单个 JSONL 知识图谱：实体、关系、observation |
| 检索 | 实体名/类型/observation 的大小写不敏感子串匹配；无向量 |
| 并发 | 新版每个写工具取独占锁 `<memory file>.lock`；60 秒拿不到锁则失败；崩溃残留锁可自动清理 |
| 工具 | create_entities / create_relations / add_observations / delete_* / read_graph / search_nodes / open_nodes；资源 `memory://knowledge-graph` |
| 规模 | 全图读/写 JSONL；没有摘要、冲突、遗忘、分页语义 |

**判断**：适合验证 MCP 链路和极小规模个人图谱；不适合三端共享的项目记忆。新版文件锁解决了“多客户端互相覆盖”的一半问题，但没有解决检索质量与规模问题。

### 1.3 千问记忆库（Qianwen Memory）

| 维度 | 事实 |
|---|---|
| 定位 | 托管“跨会话长期记忆”：事实记忆 + 用户画像 |
| API | `https://maas.qianwenaiapi.com/api/v2/apps/memory/`；DashScope Key；HTTPS/JSON |
| 写入 | `POST /add`：对话最多 50 条，或 `custom_content` ≤512 字符；可带 `profile_schema`、`memory_library_id`、`meta_data` |
| 检索 | `POST /memory_nodes/search`：`user_id`、`query`、`max_results` 1–100、`rewrite`、`rerank`、`similarity_threshold`、`plan_version` |
| 隔离 | `user_id`（记忆实体，≤64 字符）；`project_id` 是“事实记忆规则 ID”，不是项目命名空间 |
| 策略 | Pro（开 Rerank）/ Lite（关 Rerank）；Add 版本由规则决定，Search 版本由请求参数决定 |
| 计费 | Add Pro ¥0.03/次、Lite ¥0.018；Search Pro ¥0.001/次、Lite ¥0.00002；存储约 ¥1.44/万条/月；免费 1,500 Add + 5,000 Search + 1 万条存储（3 个月） |
| 限流 | 总 3,000 QPM；事实 Add 120 QPM；Search 300 QPM |
| MCP | 截至 2026-10-20 未见官方 MCP 入口；要接三端需自建 MCP 适配器 |
| 中文 | 中文原生，语义检索/改写/rerank 质量预期好 |
| 数据 | 托管在阿里云；文档/记忆出本机 |

**判断**：它解决的是“用户偏好/画像/事实记忆”，不是“项目代码记忆”。如果用 `user_id` 编码项目（如 `guimei__codex`），会把同一项目的记忆按 Agent 切碎；如果所有 Agent 共用一个 `user_id`，又会把不同项目混在一起，且 Search 没有 metadata 过滤。**不建议作为核心共享记忆层**；可作为“用户画像”补充，但会增加第三套系统，首期不做。

### 1.4 千问 RAG（Qianwen RAG）

| 维度 | 事实 |
|---|---|
| 定位 | 托管企业级 RAG 知识库：解析、切片、向量化、索引、检索、问答 |
| 数据接入 | 文件、表格、MySQL、OSS；文档 150 MB/1000 页；文本 10 MB；图片 20 MB；音视频 512 MB |
| 检索 | 单库/多库联合；向量 + 关键词 + `qwen3-rerank`；Query 改写、路由、标签过滤、阈值、TopK 1–100、最终召回 1–20 |
| MCP | `https://maas.qianwenaiapi.com/api/v1/indices/rag/mcp`；Streamable HTTP；MCP 2024-11-05；工具 `Retrieve`、`ListIndices`；Codex 0.120+ 有官方配置示例 |
| 鉴权 | `Authorization: Bearer <DASHSCOPE_API_KEY>` |
| 计费 | 标准版 ¥0.03/知识库/小时（约 ¥21.6/月），1 QPS，100 GB；旗舰版 ¥0.2/RCU/小时，50–10,000 QPS；免费 720 小时（开通后 30 天内一次性） |
| 模型费 | Embedding/Rerank 按 token；文档示例 ¥0.03755/次（100 token 查询 + 150 个 500-token 切片 rerank）；关闭 rerank 显著降低 |
| 限制 | 单空间 50 库；单库 100k 文档；检索 QPS 2,000；文档/切片管理 QPS 10 |
| 写入 | MCP 只读；文档写入走控制台、REST API、连接器或同步任务 |
| 中文 | 强：`text-embedding-v4` + `qwen3-rerank` + hybrid |
| 数据 | 托管在阿里云；知识库内容出本机 |

**判断**：如果你能接受“知识库文档上阿里云”，千问 RAG 是当前中文检索质量/运维成本最优的知识库层。它原生 MCP，三端都能接；但 MCP 只读，Agent 不能直接写知识页，需要“本地 Markdown/git → 同步上传 RAG”的流水线。

### 1.5 追加：MemPalace（本轮最大修正）

| 维度 | 事实 |
|---|---|
| 定位 | 本地优先的 Agent 记忆“宫殿”：wings/rooms/drawers + 时序知识图谱 + Agent diary/协调 |
| 版本/许可 | v3.11.0（2026-10-14 最新稳定版），MIT；约 59.6k stars |
| 存储 | ChromaDB 默认；可选 `sqlite_exact`、`rust_exact`、Milvus、Qdrant、pgvector |
| 传输 | **HTTP MCP**：`mempalace-mcp --transport http --host 127.0.0.1 --port 8765`，MCP `/mcp` + `/healthz`；也支持 stdio |
| 多 Agent | v3.5.0 起 HTTP transport；v3.9.0 起 `mempalace serve` 单 hub，单写者 lease + 读并发/写独占；stdio 客户端可转发到 hub；v3.9+ task coordination/handoff；远程/团队模式需 HTTPS + bearer token；agent 身份用 `host:harness:project`；`--read-only` 可隐藏写工具 |
| 工具 | 47 个 MCP 工具：palace 读写、知识图谱、跨 wing 导航、drawer 管理、agent diary、logstream/artifact handoff |
| 中文 | 默认 `minilm`（英文，约 80 MB）；中文需 `mempalace init ~/mempalace --embedding-model embeddinggemma`（多语言，100+ 语言，约 300 MB），或 OpenAI-compatible embedding 服务；已建 palace 切模型需 `mempalace repair rebuild-index` |
| 检索 | 原生向量 + 关键词 + 时序/偏好 hybrid；LongMemEval 96.6% R@5（无 LLM），hybrid v4 held-out 98.4% |
| 跨 Agent | MCP 通用；仓库含 `.dsh-plugin`；Claude Code / Codex CLI / Cursor 有 auto-save hooks |
| 协调 | agent diary、logstream 事件/产物（`task.request`/`task.reply`、`claimed`、`ack`、`patch.ready`）、artifact handoff；v3.9+ task coordination/task handoff（immutable base commit + definition of done）；**没有** Memorix 那种文件级锁/验证门 |
| 资源 | Python 3.10+ + ChromaDB；默认 minilm ~80 MB，中文 embeddinggemma ~300 MB；预计 500 MB–1 GB RSS，需实测 |
| 注意 | 必须只跑一个 hub；不要让两个 server 进程指向同一个 palace（#1963 仍在跟踪直写场景）；远程/团队模式必须 bearer token；peer sync 只同步 logstream，不同步 memory；47 个工具可能带来上下文/选择开销 |

**判断**：这是当前“本地 + 中文 + 多 Agent + 知识图谱”最均衡的候选。它比 Memorix 成熟、比 agentmemory 中文友好、比 Hindsight 轻。**默认记忆层改为 MemPalace**；如果你需要文件级锁/验证门，仍选 Memorix；如果只是任务协调/交接，MemPalace v3.9+ 已覆盖。

---

## 2. 扩大检索：候选全景

下表按“本地记忆 / 托管记忆 / 知识图谱 / 知识库平台”分组；只列对本次场景有意义的候选。

| 候选 | 类型 | 跨 Agent/传输 | 中文 | 记忆/知识 | 协调 | 数据位置 | 许可 | 结论 |
|---|---|---|---|---|---|---|---|---|
| **MemPalace** | 本地记忆+KG | **MCP HTTP 8765（v3.5+）**，仓库含 `.dsh-plugin`/Codex hooks | **embeddinggemma 多语言（需切换）** | 记忆+KG+diary | diary/logstream/artifact handoff；hub 单写者 | 本地 | MIT | **默认记忆层候选** |
| **Memorix** | 本地记忆+协作 | MCP HTTP 3211，官方 Hermes/Codex/DSH | 需向量补足 | 记忆强、知识页中 | **文件级锁/验证门/消息/交接** | 本地 | Apache-2.0 | **编排优先候选** |
| **agentmemory** | 本地记忆 | MCP HTTP 3111 + REST，Codex/Hermes 官方；DSH 走 MCP | 默认英文 embedding | 记忆强、无文档 KB | leases/signals/handoff | 本地 | Apache-2.0 | **自动捕获挑战者** |
| **Hindsight** | 本地/自托管记忆 | HTTP MCP 8888 + REST | 依赖 LLM/embedding | 记忆+knowledge pages | memory banks | 本地/Docker | MIT | **生产级备选** |
| **claude-mem** | 本地会话捕获 | hooks + MCP search | 依赖摘要 LLM | 会话摘要强 | 无正式协调 | 本地/可选云 | Apache-2.0 | Claude 向；LLM 成本 |
| **Engram** | 本地记忆 | MCP stdio + HTTP API 7437 | FTS5 中文弱 | 记忆、无 KB | 冲突提示 | 本地 | MIT | 轻量 fallback |
| **Basic Memory** | 本地知识库 | MCP HTTP 3212/stdio | 可配 bge-small-zh | KB 强、记忆弱 | 无 | 本地 Markdown | AGPL-3.0 | **本地 KB 首选** |
| **Cognee** | 本地 KG 记忆 | MCP；Python | 依赖 embedding/LLM | KG+文档 | 无正式协调 | 本地 | Apache-2.0 | 本地 KG 备选 |
| **MCP Reference** | 本地 KG | stdio | 子串匹配 | 仅 PoC | 无 | 本地 JSONL | MIT/Apache | PoC |
| **MemOS** | 本地记忆 OS | MCP + Hermes/DSH 插件 | 依赖模型 | 记忆强 | 有 | 本地/Docker | Apache-2.0 | 重型，暂不 |
| **MemoryOS** | 研究型记忆 | MCP | 中文研究 | 记忆 | 无 | 本地 | Apache-2.0 | 研究/停更风险 |
| **Redis Agent Memory** | 研究/托管 | REST；MCP 仅旧后端 | 依赖 embedding | 记忆 | 无 | Redis/托管 | Apache-2.0 | 不合适 |
| **Letta** | Agent runtime | MCP 管理 | 依赖模型 | Agent 内部记忆 | Agent 内 | 自托管/云 | Apache-2.0 | 不是共享库 |
| **Zep/Graphiti** | 时序 KG | MCP | 依赖 LLM/embedding | 记忆强 | 无 | Docker/图库 | Apache-2.0 | 重型，暂缓 |
| **mem0** | 记忆 API | MCP/托管 | 依赖 OpenAI | 记忆强 | 无 | Qdrant/pgvector/云 | Apache-2.0 | 重型/出境 |
| **Supermemory** | 托管记忆 | MCP | 依赖模型 | 记忆强 | 无 | 托管为主 | 专有/部分开源 | 出境/闭源 |
| **千问记忆库** | 托管记忆 | API only（无官方 MCP） | 强 | 用户画像/事实 | 无 | 阿里云 | 商业 API | 不做核心 |
| **千问 RAG** | 托管知识库 | **MCP HTTP 原生** | **强** | KB 强 | 无 | 阿里云 | 商业 API | **默认 KB 候选** |
| **RAGFlow/Dify/LightRAG** | 自托管 RAG | 部分 MCP | 强（可配） | KB 强 | 无 | 本地/Docker | 开源 | 重型，暂不 |
| **Khoj/Onyx/AnythingLLM** | 知识/搜索平台 | 部分 MCP | 中 | KB | 无 | 自托管 | 开源 | 重型，暂不 |

**短名单**：
- 记忆层：**MemPalace（默认）、Memorix（编排）、agentmemory（自动捕获）、Hindsight（生产级）**。
- 知识库：**千问 RAG（托管）、Basic Memory（本地-only）**；Cognee 作为本地 KG 备选。
- 明确不作为主选：MCP Reference、千问记忆库、claude-mem、MemOS、MemoryOS、Redis、Supermemory、Letta、Graphiti、mem0、重型 RAG 平台。

---

## 3. 修订后的对比矩阵（短名单）

| 维度 | MemPalace | Memorix | agentmemory | Hindsight | Basic Memory | 千问 RAG |
|---|---|---|---|---|---|---|
| 原生 HTTP MCP | ✅ 8765（v3.5+） | ✅ 3211 | ✅ 3111 | ✅ 8888 | ✅ 3212 | ✅ 托管 |
| 跨 Agent 接入 | MCP 通用；仓库含 `.dsh-plugin`；Codex hooks | Hermes/Codex/DSH 官方 | Codex/Hermes 官方；DSH 走 MCP | MCP 通用 | MCP 通用 | MCP 通用/Codex 官方示例 |
| 中文检索 | **embeddinggemma 多语言（需切换）** | 需开 embedding | 默认英文，需换 embedding | 依赖 LLM/embedding | bge-small-zh | **text-embedding-v4 + qwen3-rerank** |
| 记忆能力 | 强（palace/KG/diary） | 强（事实/决策/坑点/摘要） | 强（会话捕获/压缩/图） | 强（retain/recall/reflect） | 弱（笔记为主） | 弱（文档 KB） |
| 知识库能力 | 中（KG/diary） | 中（Knowledge Workspace） | 弱 | 中（knowledge pages） | **强** | **强** |
| 协调能力 | diary/logstream/artifact handoff；v3.9+ task coordination/handoff；**存储层单写者 lease**；无文件级锁 | **文件级锁/验证门/消息/交接** | leases/signals/handoff | memory banks | 无 | 无 |
| 多 Agent 并发 | hub 单写者 + 读并发/写独占（v3.9+）；禁止多进程直写 | HTTP 服务 + SQLite | HTTP 服务 + leases | Postgres | SQLite | 托管 |
| 资源 | 中（Python+Chroma+~80/300MB 模型） | 低（SQLite） | 中（Node+iii） | 高（Postgres/Docker） | 中（Python+FastEmbed） | 托管，本地零 |
| 运维 | 中（单 hub + systemd 守护） | 低 | 中（4 端口/engine pinned） | 高 | 低 | 最低 |
| 数据位置 | 本地 | 本地 | 本地 | 本地 | 本地 | 阿里云 |
| 许可 | MIT | Apache-2.0 | Apache-2.0 | MIT | AGPL-3.0 | 商业 API |
| 成熟度 | **高（~59.6k★，v3.11）** | 年轻（~850★） | 高（~29.7k★，3,700+ 测试） | 高（~51.8k★） | 中（~3.6k★） | 平台服务 |
| 结论 | **默认记忆层** | **编排优先** | **自动捕获挑战者** | **生产级备选** | **本地 KB 首选** | **托管 KB 首选** |

---

## 4. 修订建议

### 4.1 决策树

1. **知识库数据能否离开本机/上阿里云？**
   - 能 → **千问 RAG**（中文检索最好、原生 MCP、运维最低）。
   - 不能 → **Basic Memory**（Markdown+git，本地 bge-small-zh；接受 AGPL 与中文 FTS 限制）。
2. **是否需要文件级锁/验证门/消息队列？**
   - 需要 → **Memorix**（这是它的差异化能力；锁是任务/文件级）。
   - 不需要 → **MemPalace**（默认；记忆/KG/共享产物更强，存储层有单写者 lease）。
3. **是否希望“Agent 不用自觉写记忆，自动捕获”？**
   - 是 → **agentmemory**（12 hooks、54 工具、会话压缩）；但先解决中文 embedding。
   - 否 → **MemPalace**（显式 MCP 工具 + diary/handoff）。
4. **是否接受 Docker/Postgres 与 LLM 成本，追求“会学习”的记忆？**
   - 是 → **Hindsight**（memory banks、reflect、knowledge pages）。
   - 否 → MemPalace/Memorix。

### 4.2 推荐组合

**方案 A（默认，推荐）**：**MemPalace + 千问 RAG**
- MemPalace 作为本地记忆/KG/共享产物中枢：一个 `mempalace serve` hub，三端通过 HTTP MCP 接入；初始化时切 embeddinggemma，中文语义检索有保障。
- 千问 RAG 作为中文文档知识库：Markdown/git 为真源，增量同步到 RAG，三端通过 `Retrieve` 检索。
- 成本：MemPalace 0 许可 + 本地资源；千问 RAG 标准版约 ¥21.6/月 + 检索 token。
- 风险：47 个工具/ChromaDB 资源需 pilot；必须单 hub，不能多进程直写。

**方案 B（编排优先）**：**Memorix + 千问 RAG**
- 需要文件级锁/验证门时选它；MemPalace v3.9+ 有任务协调/交接，但没有文件级锁。
- 代价：项目年轻（~850★）、中文检索需向量补足、无多语言默认 embedding。
- 适合“多个 Agent 会改同一批文件/需要明确交接单”的场景。

**方案 C（本地-only）**：**MemPalace + Basic Memory**
- 数据不出机；Basic Memory 用 Markdown + git，中文向量用 `BAAI/bge-small-zh-v1.5`。
- 代价：AGPL-3.0、中文 FTS 不分词、需要自己维护索引与备份。

**方案 D（自动捕获优先）**：**agentmemory + 千问 RAG**
- agentmemory 负责会话自动捕获、压缩、跨 Agent 召回；需要先验证中文 embedding（默认 all-MiniLM-L6-v2 是英文向），并接受 iii-engine 与 4 端口。
- 适合“不想靠纪律写记忆”的团队。

**方案 E（生产级学习记忆）**：**Hindsight + 千问 RAG**
- Hindsight 提供 memory banks、reflect、mental models/knowledge pages；需要 Docker/Postgres + LLM（支持 DeepSeek）。
- 适合把记忆当核心资产、愿意投入运维的场景。

### 4.3 明确不推荐作为主选

- **Engram**：FTS5-only，中文弱；做 fallback。
- **MCP Reference Memory**：PoC；不要承载生产记忆。
- **千问记忆库**：API-only、user_id 隔离、无项目 metadata 过滤、无协调；不要当项目记忆。
- **claude-mem**：Claude 向、依赖摘要 LLM；适合补充，不适合作为唯一共享层。
- **MemOS/MemoryOS/Redis/Supermemory/Letta/Graphiti/mem0/重型 RAG**：资源、依赖或许可不匹配当前 4C/7.4G。
- **MemPalace 的唯一注意事项**：只跑一个 hub，不要让多个进程直接写 palace；47 工具/资源需 pilot。它不是“不能用”，而是“必须按官方 hub 模式用”。

---

## 5. 记忆层 Bake-off（1 周）

不要直接全量迁移。用同一份测试集跑候选，按数据选，不按 star 选。

**候选**：
1. **MemPalace**（`mempalace serve` hub，v3.11+；三端都连 8765）。
2. **Memorix**（HTTP 3211；文件锁/验证门场景）。
3. **agentmemory**（HTTP 3111；自动捕获场景）。
4. Hindsight（可选；Docker/Postgres，成本最高）。

**测试集**：
- 30 条记忆：10 条中文决策/坑点、10 条英文代码事实、10 条混合（中文描述 + 文件路径/commit）。
- 20 条查询：8 条中文语义、4 条中文短词（2 字）、4 条代码标识符、4 条跨会话时间/决策查询。
- 三端：Hermes 写入 → Codex 新会话读取 → dsh headless 读取；反向再跑一次。
- 并发：三端同时写 5 条，再同时读 20 条；检查 palace 是否出现 HNSW drift/SIGSEGV/锁超时。

**指标**：
| 指标 | 目标 |
|---|---|
| 跨 Agent Recall@5 | ≥ 95% |
| 中文语义 Recall@5 | ≥ 80%（低于则记录基线） |
| 中文 2 字短词 Recall@5 | 记录，不设硬门槛 |
| 搜索 p95 | < 800 ms |
| 服务 RSS | < 1 GB（MemPalace 放宽到 1 GB） |
| 安装/接入时间 | < 30 分钟/Agent |
| 工具数量/上下文开销 | 记录（MemPalace 47 / agentmemory 54 是否导致选择困难） |
| 72h 稳定性 | 无 HNSW drift、无 SIGSEGV、无锁错误、无工具丢失 |
| 多 Agent 并发写 | 100 次并发写无损坏 |
| 许可/数据位置 | 符合要求 |

**交付物**：一页 scorecard（每项实际值 + 失败模式 + 结论），据此定记忆层。KB 层用 20 篇中文文档 + 10 条查询，对比千问 RAG 与 Basic Memory 的 Recall@5、延迟、成本、运维。

**预判**：MemPalace 在中文/多语言与成熟度上领先；Memorix 在文件级锁/验证门上领先（MemPalace v3.9+ 已覆盖任务协调/交接）；agentmemory 在自动捕获上领先。若 MemPalace hub 72h 稳定，默认选它；若出现工具过多/资源超限，回退 Memorix。

---

## 6. 接入配置

### 6.1 MemPalace hub（默认记忆层）

```bash
# 安装（推荐 uv tool）
uv tool install mempalace

# 初始化；中文/多语言选 embeddinggemma（约 300 MB）
mempalace init ~/mempalace --embedding-model embeddinggemma

# 单 hub 常驻；三端都连这个端口
mempalace serve --host 127.0.0.1 --port 8765

# 协调协议：把输出放入各 Agent 的 AGENTS.md/指令文件
# （有 start/end marker，更新时替换整块，不要重复追加）
mempalace rules --host <host> --harness <codex|dsh|hermes> --project <project>
```

健康检查：`curl http://127.0.0.1:8765/healthz`。  
建议 systemd user service 守护，并设置 `MEMPALACE_MCP_IDLE_HOURS=0`（默认 8 小时空闲退出）或 `Restart=always`。  
**只跑一个 hub**；不要让 Hermes/Codex/dsh 各自起 stdio 直写 palace（#1963）。

Hermes：

```yaml
mcp_servers:
  mempalace:
    url: http://127.0.0.1:8765/mcp
    timeout: 60
    connect_timeout: 30
```

Codex：

```toml
[mcp_servers.mempalace]
url = "http://127.0.0.1:8765/mcp"
startup_timeout_sec = 30
tool_timeout_sec = 60
```

dsh：

```yaml
- insert:
    - id: mcp-mempalace
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: mempalace
        transport: streamable-http
        url: http://127.0.0.1:8765/mcp
        toolCallTimeoutMs: 60000
        reconnect:
          enabled: true
```

### 6.2 千问 RAG

前置：

```bash
export DASHSCOPE_API_KEY="sk-..."   # 千问AI平台 API Key，不是 token-plan key
```

当前 `~/.hermes/.env` 只有 `DEEPSEEK_API_KEY` 和 `TOKEN_PLAN_API_KEY`，**没有 DASHSCOPE_API_KEY**；需要先在千问AI平台创建。

Hermes：

```yaml
mcp_servers:
  qianwen_rag:
    url: https://maas.qianwenaiapi.com/api/v1/indices/rag/mcp
    headers:
      Authorization: "Bearer <DASHSCOPE_API_KEY>"
    timeout: 60
    connect_timeout: 30
```

Codex：

```toml
[mcp_servers.qianwen_rag]
url = "https://maas.qianwenaiapi.com/api/v1/indices/rag/mcp"
bearer_token_env_var = "DASHSCOPE_API_KEY"
startup_timeout_sec = 30
tool_timeout_sec = 60
```

Codex 0.120.0+ 支持；`bearer_token_env_var` 会发送 `Authorization: Bearer <值>`，避免 `${...}` 在 TOML 里不展开的问题。

dsh：

```yaml
- insert:
    - id: mcp-qianwen-rag
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: qianwen_rag
        transport: streamable-http
        url: https://maas.qianwenaiapi.com/api/v1/indices/rag/mcp
        headers:
          Authorization: !!js '`Bearer ${process.env.DASHSCOPE_API_KEY}`'
        toolCallTimeoutMs: 60000
        reconnect:
          enabled: true
```

### 6.3 知识写入流水线

千问 RAG 的 MCP 只有 `Retrieve` / `ListIndices`，**不能通过 MCP 写知识**。推荐：

```text
Agent 写 Markdown（~/wuhoo-brain/...）
  → git commit（本地审计）
  → 同步脚本（只上传变更文件到千问 RAG：API/连接器）
  → 千问 RAG 解析/切片/向量化
  → 三端通过 MCP Retrieve 检索
```

同步脚本可以按文件 mtime/hash 做增量；失败重试；上传后在 RAG 控制台确认文档状态。这样既保留本地 Markdown/git 的审计，又获得托管中文检索。

---

## 7. 成本估算

| 项目 | 估算 |
|---|---|
| MemPalace | 0 许可；Python+ChromaDB；默认 minilm ~80 MB，中文 embeddinggemma ~300 MB；预计 500 MB–1 GB RSS；磁盘按 palace 规模 |
| Memorix | 0 许可；本地 ~20–100 MB RSS；SQLite 磁盘 |
| agentmemory | 0 许可；本地 Node+iii，~数百 MB RSS；4 端口 |
| Hindsight | 0 许可；Docker/Postgres + LLM，资源最高 |
| Basic Memory | 0 许可；Python + FastEmbed，~150–500 MB RSS |
| 千问 RAG 标准版 | ¥0.03/小时 ≈ **¥21.6/月/库**；免费 720 小时（开通后 30 天内一次性） |
| 千问 RAG 检索 | 文档示例 ¥0.03755/次（Query 向量化 0.00005 + 排序 0.0375，150×500 token rerank）；50 次/天 ≈ ¥1.9/天 ≈ **¥56/月**；关 rerank 显著降低 |
| 千问记忆库 | Add Pro ¥0.03/次、Search Pro ¥0.001/次；100 Add + 1,000 Search/天 ≈ **¥3.1/天 ≈ ¥93/月** + 存储；Lite 更便宜 |
| Codex | 按 DeepSeek token 计费 |

结论：本地记忆层 0 许可；千问 RAG 的固定成本很低（约 ¥22/月/库），主要成本在检索 rerank 的 token；对“每天几十次检索”的个人/小团队足够。

---

## 8. 风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| 千问 RAG 数据出本机 | 文档/知识上阿里云 | 先做数据分级：敏感项目文档留 Basic Memory；公开/半公开文档上 RAG |
| 千问 RAG MCP 只读 | Agent 不能直接写知识 | Markdown/git 为真源 + 增量同步；不要试图用 MCP 写 |
| 千问 RAG API Key 缺失 | 无法接入 | 先申请 DASHSCOPE_API_KEY；不要拿 token-plan key 代替 |
| 千问 RAG 供应商锁定 | 迁移成本 | 保留 Markdown 真源；RAG 只做索引；随时可切 Basic Memory |
| 千问记忆库无 MCP/无 metadata 过滤 | 不能做项目隔离 | 不作为核心；如用，仅做用户画像 |
| MemPalace 多进程直写 | ChromaDB HNSW drift/SIGSEGV | **只跑一个 `mempalace serve` hub**；三端连 HTTP；不要各自起 stdio 直写；按 #1963 持续观察 |
| MemPalace 47 工具/资源 | 上下文开销；RSS 可能接近 1 GB | 先 pilot；必要时用 `--read-only` hub 给只读 Agent；记录工具选择准确率 |
| MemPalace 版本 | v3.5.0 以下没有 HTTP | 钉 v3.11+；升级前看 release notes |
| MemPalace 默认 embedding 英文 | 中文召回差 | 初始化时 `--embedding-model embeddinggemma`；已建 palace 切模型需 `mempalace repair rebuild-index` |
| agentmemory 默认英文 embedding | 中文召回差 | 配置中文/多语 embedding（需验证 provider），或只用于英文/代码记忆 |
| agentmemory 依赖 iii-engine | 升级/端口/资源 | 钉版本；先 pilot；保留 MemPalace/Memorix fallback |
| Hindsight 需要 Docker/Postgres+LLM | 资源/运维重 | 只在接受运维投入时选 |
| Memorix 年轻/中文检索 | 稳定性/召回 | 钉版本；开 bge-small-zh 向量；1 周 pilot |
| Engram 仅 FTS5 | 中文召回弱 | 只做英文/代码 fallback |
| MCP Reference 仅 PoC | 无规模/语义 | 只用于链路验证 |
| 许可 | AGPL/商业 API | Basic Memory AGPL 内部可；千问 RAG 商业条款需确认 |

---

## 9. 待拍板

1. **知识库数据能否上阿里云？**
   - A 可以 → 千问 RAG（推荐）；
   - B 不可以 → Basic Memory；
   - C 分级：敏感留本地、公开/半公开上 RAG。

2. **默认记忆层是否改为 MemPalace？**
   - A 是（推荐；按官方 hub 模式，先 1 周 pilot）；
   - B 仍选 Memorix（编排/任务锁优先）；
   - C 选 agentmemory（自动捕获优先）；
   - D 选 Hindsight（生产级学习记忆）。

3. **默认组合是否采用方案 A（MemPalace + 千问 RAG）？**
   - A 是；
   - B 编排优先（Memorix + 千问 RAG）；
   - C 本地-only（MemPalace + Basic Memory）；
   - D 自动捕获（agentmemory + 千问 RAG）；
   - E 生产级（Hindsight + 千问 RAG）。

4. **是否现在申请 DASHSCOPE_API_KEY 并做千问 RAG 小样本测试？**
   - 需要你提供/创建 Key；我可以用 10 篇中文文档 + 10 条查询做召回与成本实测。

5. **执行窗口**：先 Bake-off/小样本，还是直接进入 Phase 0–1 安装？建议先测试，避免把未验证的组件写进长期记忆。

---

## 10. 参考链接

- Engram：https://github.com/Gentleman-Programming/engram
- Engram DOCS：https://github.com/Gentleman-Programming/engram/blob/main/DOCS.md
- MCP Reference Memory：https://github.com/modelcontextprotocol/servers/tree/main/src/memory
- 千问记忆库：https://platform.qianwenai.com/docs/agent-infra/memory
- 千问记忆库 API：https://platform.qianwenai.com/docs/api-reference/agent-infra/memory/overview
- 千问记忆库计费：https://platform.qianwenai.com/docs/agent-infra/memory/reference/billing
- 千问 RAG：https://platform.qianwenai.com/docs/agent-infra/rag/introduction
- 千问 RAG 服务渠道（MCP）：https://platform.qianwenai.com/docs/agent-infra/rag/integration/channels
- 千问 RAG 检索：https://platform.qianwenai.com/docs/agent-infra/rag/service/retrieval
- 千问 RAG 计费：https://platform.qianwenai.com/docs/agent-infra/rag/settings/billing
- 千问 RAG 限制：https://platform.qianwenai.com/docs/agent-infra/rag/settings/limits
- MemPalace：https://github.com/MemPalace/mempalace
- MemPalace shared brain（单 hub）：https://mempalaceofficial.com/guide/shared-brain.html
- MemPalace remote/team server：https://mempalaceofficial.com/guide/remote-server.html
- MemPalace HTTP transport issue：https://github.com/MemPalace/mempalace/issues/1646
- MemPalace HTTP transport PR：https://github.com/MemPalace/mempalace/pull/1806
- MemPalace 多进程直写跟踪：https://github.com/MemPalace/mempalace/issues/1963
- Memorix：https://github.com/AVIDS2/memorix
- agentmemory：https://github.com/rohitg00/agentmemory
- Hindsight：https://github.com/vectorize-io/hindsight
- Basic Memory：https://github.com/basicmachines-co/basic-memory
- Cognee：https://github.com/topoteretes/cognee
- claude-mem：https://github.com/thedotmack/claude-mem
- Memory MCP 对比（13 个）：https://mnemoverse.com/docs/library/memory-mcp-servers-compared

---

*本文为第二轮选型修订，未执行安装/配置变更。所有托管服务与 API Key 使用需用户确认数据边界后执行。*