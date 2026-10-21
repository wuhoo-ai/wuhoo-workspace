# 多 Agent 共享记忆与知识库方案评估

**文档日期**：2026-10-20  
**评估环境**：阿里云新加坡（Hermes 云端主机）  
**评估对象**：Hermes（基础事务/编排）、Codex（代码开发）、dsh / DeepSeek Harness（插件开发与调试）  
**文档状态**：调研与方案评估完成，未实施安装与配置变更  
**结论一句话**：可行，且不需要自研。推荐用 MCP 作为三端唯一公共协议，采用“Memorix（记忆与协作层）+ Basic Memory（知识库层）”的双层本地服务；首期先上 Memorix 单层验证跨 Agent 协议，再按门槛加知识库。

> **第二轮修订（2026-10-20）**：用户补充 Engram、MCP Reference Memory、千问记忆库、千问 RAG，并要求扩大检索范围。修订后的选型结论见
> [`AGENT-MEMORY-KB-SELECTION-ADDENDUM-2026-10-20.md`](./AGENT-MEMORY-KB-SELECTION-ADDENDUM-2026-10-20.md)。
> 要点：记忆层默认改为 **MemPalace**（原生 HTTP MCP 已在 v3.5+ 落地，单 hub 解决多 Agent 并发），**Memorix** 作为编排优先备选，**agentmemory / Hindsight** 作为自动捕获/生产级备选；知识库默认改为 **千问 RAG**（数据可上云时），本地-only 仍用 **Basic Memory**。
> **本文 §0 第 5 条与 §4 的组件结论均以增补文档为准；架构原则、三端接线、验收流程继续有效。**

---

## 0. 结论先行

1. **三端都支持 MCP，这是本方案成立的关键前提。** Hermes v0.22.2 自带 MCP 客户端（stdio + Streamable HTTP）；Codex CLI 在 `~/.codex/config.toml` 的 `[mcp_servers.<name>]` 中支持 stdio/HTTP；dsh 0.1.7-alpha.1 内置 `@deepseek-ai/dsh-mcp-client`，支持 `stdio` 与 `streamable-http`，工具名形如 `mcp__memorix__*`。因此“外挂记忆库/知识库”不需要改三端源码，只需要一个共享 MCP 服务。

2. **Hermes 自带的 memory provider 不能承担跨 Agent 共享。** 它是进程内插件，按 profile 隔离，只服务 Hermes 自己；Codex 和 dsh 读不到它的 `MEMORY.md` / `USER.md` / provider 数据库。Hermes 原生记忆应继续用于“用户身份与偏好”，跨 Agent 共享必须走 MCP。

3. **Codex 可以用，但要走 Responses API。** 2026 年起 Codex 只支持 `wire_api = "responses"`，旧的 `wire_api = "chat"` 已移除。DeepSeek 官方已提供 Codex 集成脚本，DeepSeek API 与 token-plan 端点的 `/responses` 均已实测返回 200。推荐 Codex 走 `api.deepseek.com`（官方集成、模型元数据齐全），token-plan 留作备选实验。

4. **dsh 的 MCP 能力已在本机安装包中确认。** `dsh-mcp-client` 与 `dsh-mcp-resources` 随 0.1.7-alpha.1 一起安装，支持 HTTP 与 stdio；官方文档还给了 Memorix、Engram、MCP Reference Memory 三个记忆服务器示例。dsh 没有 hooks 面，跨 Agent 记忆要靠 MCP 工具 + `AGENTS.md` 纪律。

5. **推荐目标架构是双层，不是单库。**
   - **记忆层 Memorix**：项目事实、决策、坑点、推理、会话摘要、任务/锁/交接/消息，本地 SQLite + FTS5，HTTP MCP 端口 3211。
   - **知识库层 Basic Memory**：长期成文知识、设计文档、调研、runbook，Markdown 文件为真源 + SQLite 索引 + 本地 FastEmbed 向量检索，HTTP MCP 端口 3212。
   - 两者职责不同：**过程记忆进 Memorix，成文知识进 Basic Memory**；同一内容不双写，Memorix 存摘要与链接。

6. **不建议现在上 Graphiti / mem0 自托管 / RAGFlow。** 它们分别需要 FalkorDB/Neo4j、Postgres+pgvector+Docker、或重型 RAG 栈；当前主机是 4 vCPU / 7.4 GB 内存 / 22 GB 可用磁盘、无 OpenAI key、无 GPU。资源与依赖不匹配，收益不足以抵消运维复杂度。等出现“时间维度事实推理”或“多用户大规模知识库”的硬需求再评估。

7. **中文检索是本次评估发现的最大技术风险。** Basic Memory 的 FTS 使用 SQLite `unicode61`，对中文连续文本不分词；Memorix 的 FTS5 也有同类问题。两者都必须靠**多语言/中文向量检索**兜底。Basic Memory 可配置本地 `BAAI/bge-small-zh-v1.5`（512 维、约 90 MB、MIT），这是当前最务实的中文方案；上线前必须用中文查询集实测召回率。

8. **建议首期范围只覆盖云端 default profile + Codex + dsh，不把 trader/gamedev/GPU 一起拉进来。** 先在 1 周内跑通“写入 → 另一 Agent 新会话读取 → 实际使用”的闭环，再按门槛扩展。GPU 当前离线（frp 2222/28642 无监听），不纳入首期。

---

## 1. 需求拆解与验收标准

### 1.1 三个 Agent 的分工

| Agent | 角色 | 主要工作 | 对共享层的诉求 |
|---|---|---|---|
| Hermes | 总控/编排/运维 | 日常事务、cron、监控、跨域调度、任务拆解 | 读取项目上下文、创建任务/交接、汇总结果、把稳定知识沉淀为文档 |
| Codex | 代码开发 | 仓库内编码、重构、测试、PR、代码审查 | 开工前拿到项目记忆与设计决策、写回实现决策与坑点、声明文件锁 |
| dsh | 插件开发/调试 | dsh 插件 bundle、headless 验证、Web UI 调试 | 读取插件规范与历史坑点、写回验证结果、与 Codex 交接 |

### 1.2 共享层要解决的六个问题

1. **跨会话记忆**：新会话不需要重新解释项目背景、已做决策、已知坑点。
2. **跨 Agent 记忆**：Codex 学到的实现细节，dsh 和 Hermes 能读到；反之亦然。
3. **知识沉淀**：调研、设计、runbook 形成可检索、可引用、可版本化的文档，而不是散落在聊天记录里。
4. **交叉工作协调**：任务认领、文件锁、交接、消息、验证门，避免两个 Agent 同时改同一块代码。
5. **可审计**：谁在什么时候写了什么、依据是什么、是否被后续事实推翻。
6. **本地优先与安全**：数据不出本机；密钥不进入记忆库；服务只监听回环地址。

### 1.3 判定标准

| 维度 | 要求 | 验收方式 |
|---|---|---|
| 跨 Agent 召回 | A 写入，B 在新会话能读到并正确使用 | 三端交叉写入/读取测试，成功率 ≥ 95% |
| 检索质量 | 中文语义查询可召回；英文/代码标识符可精确匹配 | 20 条中文查询 + 20 条代码查询，Recall@5 记录基线 |
| 延迟 | 本地检索 p95 < 800 ms | 压测 100 次查询统计 |
| 资源 | 两个服务合计 RSS < 800 MB，磁盘 < 2 GB | `ps`/`/health`/`du` 实测 |
| 稳定性 | 连续 72 小时无 SQLite lock 错误、无工具丢失 | 日志与 health 检查 |
| 可审计 | 每次写入有 agent、session、时间、来源 | 查询 Memorix 记录与审计日志 |
| 可回滚 | 5 分钟内可禁用共享层，三端恢复独立工作 | 删除/注释 MCP 配置并重启验证 |
| 许可 | 内部使用无法律障碍；未来分发有明确边界 | 许可证复核 |

---

## 2. 环境实测基线

### 2.1 主机与运行时

| 项目 | 实测值 | 判读 |
|---|---|---|
| 主机 | Alibaba Cloud Linux 5.10.134-19.2.al8.x86_64 | 稳定 |
| CPU/内存 | 4 vCPU / 7,462 MB（可用约 4,970 MB） | 足够跑两个轻量 MCP 服务；不适合重型图数据库 |
| 磁盘 | / 69 GB，已用 44 GB，可用 22 GB | 足够；需给索引/模型留 2 GB |
| Hermes | v0.22.2 (2026.9.24) stable，git 安装 d923a5eb | 支持原生 MCP 客户端 |
| dsh | 0.1.7-alpha.1，`@deepseek-ai/dsh` 全局安装 | 已含 `dsh-mcp-client` / `dsh-mcp-resources` |
| Codex | **未安装**；npm 最新 `@openai/codex` 0.163.0 | 可安装，需实测 |
| Node/npm | v24.9.0 / 11.6.0 | 满足 Memorix 要求（Node ≥ 22.18） |
| Python/uv | 系统 python3 3.6.8；uv 0.11.7 可管理 3.12/3.13/3.14 | Basic Memory 建议用 `uv tool install` 隔离 |
| bubblewrap | `/usr/bin/bwrap` 0.4.0 | Codex Linux 沙箱前置满足 |
| user namespace | `unshare -Ur true` 成功 | Codex 沙箱可创建命名空间 |
| SELinux | Disabled | 不额外阻碍 bwrap |
| 容器 | podman 4.9.4（docker 命令为 podman 模拟） | 可用，但首期不需要容器 |
| 端口 | 3210/3211/3212 均空闲 | Memorix/Basic Memory 端口可用 |
| systemd user | `Linger=yes`，已有 hermes-gateway/serve 用户服务 | 可加用户级常驻服务 |

### 2.2 模型端点实测（2026-10-20 14:5x CST）

| 端点 | 模型 | 协议 | 结果 |
|---|---|---|---|
| token-plan.cn-beijing.maas.aliyuncs.com | qwen3.8-flash | Chat Completions | HTTP 200，2.65 s |
| token-plan.cn-beijing.maas.aliyuncs.com | qwen3.8-max | Chat Completions | HTTP 200 |
| token-plan.cn-beijing.maas.aliyuncs.com | deepseek-v4.1-flash-1017 | Chat Completions | HTTP 200，4.55 s |
| token-plan.cn-beijing.maas.aliyuncs.com | qwen3.8-flash | Responses | HTTP 200 |
| api.deepseek.com | deepseek-v4-pro | Chat Completions | HTTP 200，1.18 s |
| api.deepseek.com | deepseek-flash | Chat Completions | HTTP 200，0.59 s |
| api.deepseek.com | deepseek-v4-pro | Responses | HTTP 200，2.20 s |
| api.deepseek.com | deepseek-v4-flash-vision-exp | 图像输入 | HTTP 200，能识别 64×64 红图 |

**判读**：
- Codex 需要的 `/responses` 在 DeepSeek 官方与 token-plan 两端都可用，因此 Codex 不必绑定 OpenAI 账号。
- 推荐 Codex 先走 DeepSeek 官方：DeepSeek 官方提供了 Codex 专用 `models.json` 与 `config.toml` 字段（上下文 1,048,576、reasoning levels、工具调用格式），兼容性最稳。
- token-plan 的 qwen3.8 系列可作为“低成本/备用 provider”后续实验；需要为 Codex 手工补模型元数据，不作为首期主线。

### 2.3 三端 MCP 能力对照

| 能力 | Hermes v0.22.2 | Codex CLI 0.163.0 | dsh 0.1.7-alpha.1 |
|---|---|---|---|
| MCP stdio | 支持 | 支持 | 支持 |
| MCP Streamable HTTP | 支持 | 支持 | 支持 |
| HTTP 自定义 Header | `headers` 静态值 | `http_headers` / `env_http_headers` | `headers` |
| 工具命名 | `mcp_<server>_<tool>` | MCP 原始工具名 | `mcp__<serverName>__<rawName>` |
| 配置位置 | `~/.hermes/config.yaml` 的 `mcp_servers` | `~/.codex/config.toml` 的 `[mcp_servers.*]` | `~/.dsh/cordis.patch.yml` 或 profile patch |
| 会话级自动注入 | 是（启动时发现，重启生效） | 是（启动时发现） | 是（启动前发现，工具列表热更新） |
| 失败行为 | 连接失败重试 | 可配 `required` / timeout | 默认 `failOnStartupError=false`，自动重连 |

**结论**：MCP 是唯一不需要改三端代码的公共层。不要分别给三端写私有集成，否则维护成本会随版本升级爆炸。

---

## 3. 可行性分析

### 3.1 Hermes：原生 MCP 客户端可用，但 memory provider 不能共享

- Hermes 的 `mcp_servers` 支持 stdio 与 HTTP，HTTP 方式可配 `url`、`headers`、`timeout`、`connect_timeout`。MCP 工具会自动注入 `hermes-*` 工具集，所有会话可见。
- **重要边界**：Hermes 的 external memory provider（Holographic、EntropicMem、Mem0、Honcho 等）运行在 Hermes 进程内，按 profile 隔离，只服务 Hermes。它适合做“Hermes 自己的长期记忆”，但不能作为三端共享库。
- 多 profile 注意：云端有 default / trader / gamedev 三份 `config.yaml`，`mcp_servers` 各自独立。首期只改 default；确认稳定后再复制到 trader/gamedev。
- 变更后必须重启 gateway。网关内不能自重启（硬守卫），需要用户在聊天里发 `/restart`，或在网关外执行 `systemctl --user restart hermes-gateway`。
- **建议**：MCP-first，不先装 Memorix 的 Hermes 插件。插件会注册 hooks、slash command、skills，功能更强但耦合更深；先验证纯 MCP 协议，稳定后再评估插件。

### 3.2 Codex：可安装、可接 DeepSeek、可接 MCP，但有三条硬约束

1. **协议约束**：Codex 2026 只支持 `wire_api = "responses"`。`chat` 已从代码中移除，旧教程里的 `wire_api = "chat"` 会启动失败。DeepSeek 官方已原生支持 Responses API，这是可行性的基础。
2. **配置位置约束**：`model_provider` / `model_providers` 只在用户级 `~/.codex/config.toml` 生效，项目级 `.codex/config.toml` 不接管模型 provider。MCP 配置可以放用户级，也可以放受信任项目的 `.codex/config.toml`。
3. **认证约束**：第三方 provider 用 `env_key` 指向环境变量。需要把 `DEEPSEEK_API_KEY` 放进 Codex 进程环境（shell profile 或启动 wrapper），不要把 key 写进 `config.toml`。

**安装方式**：
- 官方脚本：`curl -fsSL https://chatgpt.com/codex/install.sh | sh`（下载独立二进制）。
- npm：`npm install -g @openai/codex`（当前 0.163.0）。
- 本机是 x86_64 Linux、glibc 2.32、musl 二进制可用；npm 包只是 wrapper，会拉取对应原生二进制。

**DeepSeek 官方集成**：
- 官方提供一键脚本，自动备份 `~/.codex/config.toml`、写 `~/.codex/models.json`、写 `[model_providers.deepseek]`，并保留已有 MCP 配置。
- 菜单可选 `deepseek-flash`（支持图像输入）或 `deepseek-v4-pro`；本文建议默认 `deepseek-v4-pro` 做复杂编码，日常小改用 `deepseek-flash`。
- 官方脚本会禁用内置 web search；需要时切到 `deepseek-v4-pro` 并设置 `web_search = "live"`。

**沙箱**：
- Codex Linux 沙箱依赖 `bubblewrap`；本机已装 bwrap 0.4.0，`unshare -Ur` 成功，SELinux 关闭。前置条件满足。
- 推荐 `sandbox_mode = "workspace-write"` + `approval_policy = "on-request"`，不要用 `danger-full-access`。Codex 进程与 Hermes gateway 同机，后者持有微信、模型、peer 等密钥，必须收紧。
- 若 bwrap 在某些内核/发行版上失败，Codex 会回退到自带 helper，但要求 unprivileged userns；本机已满足。上线前仍要实跑一次 `codex` 并确认没有 sandbox 启动警告。
- 本机 bwrap 是 0.4.0（较旧）。Codex 官方建议安装发行版最新 bubblewrap；若启动时报 userns/sandbox 错误，优先升级 bwrap 或使用 Codex 自带 helper，不要直接关沙箱。
- **协议 200 不等于工具链可用**：`/responses` 返回 200 只证明端点存在；Codex 的实际工具调用、apply_patch、多轮 reasoning 回传必须在 Phase 3 实跑验证。先跑只读任务（读文件/搜索），再跑写任务（改文件/跑测试）。

**MCP 接入**：
- `~/.codex/config.toml` 增加 `[mcp_servers.memorix]` 与 `[mcp_servers.basic_memory]`，HTTP 方式，配 `startup_timeout_sec` / `tool_timeout_sec`。
- 用 `codex mcp list` 验证已注册；用 `codex mcp get <name>` 查看 transport/url。
- `AGENTS.md`：Codex 支持全局 `~/.codex/AGENTS.md` 与项目内 `AGENTS.md`，启动时按“全局 → 仓库根 → 子目录”顺序拼装。把“开工先查记忆、收工写回决策”的协议写进全局 `AGENTS.md`，项目内只写项目特有约束。

### 3.3 dsh：MCP 客户端已内置，但没有 hooks 面

- 本机 `@deepseek-ai/dsh` 0.1.7-alpha.1 的依赖树中已存在 `@deepseek-ai/dsh-mcp-client` 与 `@deepseek-ai/dsh-mcp-resources`。README 明确支持 `stdio` 与 `streamable-http`，工具名 `mcp__<serverName>__<rawName>`，并有自动重连、工具列表热更新、超时与取消。
- 配置方式：在 `~/.dsh/cordis.patch.yml`（全局）或 `~/.dsh/profiles/<name>/cordis.patch.yml`（单 profile）追加一条 `@deepseek-ai/dsh-mcp-client` 记录。每台服务器一条记录，`serverName` 唯一。
- 官方文档给了三个记忆服务器示例：Memorix、MCP Reference Memory、Engram。三者都是 stdio 示例；跨三端共享时应改 `streamable-http`，让 dsh、Codex、Hermes 连同一个服务，避免三个 stdio 进程争同一份 SQLite。
- **dsh 没有 hooks 面**，不能像 Hermes/Codex 那样自动捕获会话事件。跨 Agent 记忆要靠 `AGENTS.md` 纪律 + 模型显式调用 `mcp__memorix__*` 工具。dsh 的 `AGENTS.md` 默认在 `~/.dsh/AGENTS.md`。
- dsh 仍是 alpha 线，升级可能 breaking。首期钉 0.1.7-alpha.1；每次升级后重跑 MCP 工具发现与会话召回测试。

### 3.4 共享服务的并发模型

- SQLite 的 WAL 允许多读单写。**多个 stdio 进程各开一个服务、写同一个库**会出现写锁竞争、索引重复构建、内存翻倍。Memorix 的性能文档明确建议：多个 agent harness 场景优先用一个本地 `serve-http` 控制面，让写入由一个 owner 串行化。
- 因此目标架构统一用 **HTTP MCP 单服务**：
  - Memorix `serve-http` 监听 127.0.0.1:3211，三端都连它。
  - Basic Memory `bm mcp --transport streamable-http --host 127.0.0.1 --port 3212`，三端都连它。
- 不要把 stdio 和 HTTP 混用在同一份数据目录上；也不要在 systemd 服务之外再手起一个 stdio 实例。

### 3.5 中文检索可行性（关键风险）

- **Basic Memory 的 FTS 是 `unicode61`**，中文连续文本会被当成一个 token，只有前缀匹配；官方 issue #1294 已确认这个问题，当前工作路径是“用多语言向量检索”，`search_fts_tokenizer` 设置仍在计划中。
- **Memorix 的 FTS5 同样是英文分词逻辑**；中文关键词检索不能假设可用。它的 `[embedding]` 支持 `off / api / auto / fastembed / transformers`，可用本地向量或 API 向量补足。
- **可行方案**：
  - Basic Memory：`semantic_embedding_provider=fastembed`，`semantic_embedding_model=BAAI/bge-small-zh-v1.5`，`dimensions=512`。FastEmbed 官方支持列表确认该模型存在（Chinese，512 维，约 90 MB，MIT），比 `multilingual-e5-large`（2.24 GB、1024 维）轻得多，适合当前 7.4 GB 内存。
  - Memorix：首期可先 `provider = "off"` 用 BM25/FTS 处理英文/代码标识符；中文项目记忆再按需开 `fastembed`（同一 bge-small-zh）或 `api`（如 DashScope `text-embedding-v4`）。
  - 精确中文短词（2 字，如“止损”“健康”）在 FTS 上仍可能失败；这类查询走向量模式，或在二期加“写入前 bigram 预处理”的自定义层。
- **验收必须包含中文查询集**：20 条中文语义查询 + 10 条中文精确短词查询，记录 Recall@5；不达标就不把知识库设为默认入口。

---

## 4. 组件选型

### 4.1 候选组件评分

权重：跨 Agent 兼容 25%、记忆能力 20%、知识库能力 20%、资源占用 10%、成熟度/维护 10%、许可/可控 10%、部署复杂度 5%。评分 1–5，分数越高越好。

| 组件 | 跨 Agent | 记忆 | 知识库 | 资源 | 成熟度 | 许可 | 部署 | 加权分 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Memorix** | 5 | 5 | 3 | 4 | 3 | 5 | 4 | **4.25** |
| **Basic Memory** | 4 | 2 | 5 | 3 | 4 | 3 | 3 | **3.55** |
| Engram | 4 | 4 | 2 | 5 | 4 | 5 | 5 | **3.85** |
| Graphiti + FalkorDB | 4 | 4 | 3 | 2 | 4 | 4 | 2 | **3.50** |
| mem0 自托管 | 4 | 5 | 2 | 2 | 4 | 4 | 2 | **3.50** |
| 自研 brain MCP | 5 | 4 | 4 | 4 | 2 | 5 | 3 | **4.10** |

**注意**：这张表是“单组件适配度”，不是最终方案分。Memorix 与 Basic Memory 是互补关系：前者强在记忆与协作，后者强在成文知识库；组合后覆盖的是两个不同维度，不能用简单平均分判断。

### 4.2 候选逐一分析

#### 4.2.1 Memorix（推荐：记忆与协作层）

- **定位**：面向 AI Coding Agent 的本地优先共享记忆层；官方支持 Hermes Agent、Codex CLI、DeepSeek Harness（dsh），也支持 Claude Code、Cursor、Windsurf、Copilot、Gemini CLI、OpenCode 等。
- **核心能力**：Observation Memory（事实/修复/坑点/会话摘要）、Reasoning Memory（设计原因/备选/权衡）、Git Memory（commit 转工程事实）、Knowledge Workspace（有审核门槛的 Markdown 知识页/claim）、Orchestration（任务、认领、文件锁、消息、交接、验证门）、CodeGraph（TS/JS 符号索引，其它语言 Lite 兜底）。
- **传输**：`memorix serve`（stdio）或 `memorix serve-http` / `memorix background start`（HTTP，默认 3211/mcp，dashboard 3210）。
- **存储**：SQLite 为权威存储；FTS5 关键词索引；可选 LanceDB 语义影子索引；LLM formation/embedding 可选，默认无 LLM 也能用本地启发式。
- **资源**：官方性能文档称 HTTP 服务空闲约 16 MB 工作集；10 万条记忆压测峰值约 419 MB、冷启动 HTTP MCP 搜索约 296 ms。以实测为准，但量级适合本机。
- **许可**：Apache-2.0，内部使用与二次分发都宽松。
- **集成**：`memorix setup --agent hermes --global` 写 Hermes 插件 + `mcp_servers`；`--agent codex --global` 写 Codex 插件 + MCP + hooks；`--agent dsh --global` 写 `~/.dsh/cordis.patch.yml` + `AGENTS.md` + skills。首期建议手写 MCP 配置以便审计，自动 setup 作为对照与后续加速手段。
- **风险**：项目较年轻（约 850 stars、v1.9.12，2026-10 仍高频提交）；功能面很宽，需要钉版本、先跑通核心闭环；插件/hook 与宿主版本耦合，首期建议 MCP-only。

#### 4.2.2 Basic Memory（推荐：知识库层）

- **定位**：Markdown 文件为真源的知识库/语义图谱；实体 = 文档，observation = 分类事实，relation = 文档间链接；SQLite 只做索引。
- **核心能力**：`write_note` / `edit_note` / `read_note` / `search_notes` / `build_context` / `recent_activity` / schema（类型与字段校验）/ 元数据过滤 / 语义搜索 / 图谱链接。
- **传输**：`bm mcp` 默认 stdio；`bm mcp --transport streamable-http --host 127.0.0.1 --port 3212` 可做共享 HTTP 服务；也支持 SSE。**默认 host 是 0.0.0.0，必须显式改 127.0.0.1**。
- **检索**：默认 `fastembed` + `bge-small-en-v1.5`（英文）；可切 `BAAI/bge-small-zh-v1.5`（512 维，中文，约 90 MB）；支持 reranker（本地 jina tiny 或 LiteLLM）。
- **存储**：Markdown vault + SQLite 索引；文件可直接 git 版本化，人类可读。
- **许可**：AGPL-3.0。内部使用没问题；如果未来把服务暴露给第三方或嵌入商业产品，需要法务复核 AGPL 的网络分发义务。
- **活跃度**：4.3k stars，v0.23.2，2026-10 仍在提交；已有 Hermes、Codex 集成文档与 skills。
- **风险**：中文 FTS 分词问题（见 3.5）；默认英文 embedding，必须改中文模型；AGPL 许可；本地 HTTP 模式没有 Cloud 那套 JWT 鉴权，必须 loopback。

#### 4.2.3 Engram（备选：更轻的记忆层）

- **定位**：Go 单二进制、SQLite + FTS5、MCP + HTTP API + CLI + TUI；14 个 agent 接入目标，含 Codex；MIT。
- **优势**：零依赖、部署最简单、资源最省；26 个 MCP 工具；项目感知；冲突提示；团队使用约定；Obsidian 图谱导出（beta）。
- **不足**：没有 Memorix 那样的 Knowledge Workspace 和 orchestration（任务/锁/交接/消息）；对 Hermes/DSH 没有官方一键集成，需要手工 MCP 配置；中文检索同样依赖 FTS/向量策略。
- **适用**：如果首期只想“给三个 agent 一个共享记忆”，不想引入太多功能，Engram 是最稳的最小方案。

#### 4.2.4 MCP Reference Memory（仅 PoC）

- 官方 `@modelcontextprotocol/server-memory`：JSONL 知识图谱，实体/关系/观察，搜索是大小写不敏感子串匹配。
- 没有向量、没有摘要、没有冲突处理、没有遗忘策略；多客户端同文件还会互相覆盖。
- **结论**：只适合验证 MCP 链路，不适合生产。

#### 4.2.5 Graphiti + FalkorDB（暂不推荐）

- 时序知识图谱，支持 bi-temporal、增量更新、事实有效期、冲突处理；MCP server 提供 `add_memory` / `search` / `get` 等工具。
- 需要 Docker + FalkorDB（默认）或 Neo4j；需要 LLM 做实体/关系抽取，默认 OpenAI。当前无 OpenAI key，且 4C/7.4G 跑图数据库 + LLM 抽取偏重。
- **结论**：等出现“事实随时间变化、需要历史查询/矛盾推理”的硬需求再评估；可先用 Memorix 的 Reasoning Memory 过渡。

#### 4.2.6 mem0 自托管（暂不推荐）

- 记忆抽取能力强，支持多用户/多 Agent；但自托管是 Docker + Postgres + pgvector + dashboard，默认 LLM/embedding 都是 OpenAI；托管版有配额与数据出境问题。
- 当前环境没有 OpenAI key，Docker 是 podman 模拟，资源也偏紧。
- **结论**：不在首期。

#### 4.2.7 Hermes 自带 memory provider（只做 Hermes 内部记忆）

- Holographic / EntropicMem / Mem0 / Honcho / Supermemory 等：安装简单、与 Hermes 深度集成、可按 profile 隔离。
- 但它们是**进程内插件**，Codex/dsh 无法读取；把它们当跨 Agent 共享库是方向性错误。
- **结论**：保留 Hermes 原生 `MEMORY.md` / `USER.md` 作为“用户身份与偏好”层；不启用额外 provider，避免与 Memorix 双写。

#### 4.2.8 自研 brain MCP（兜底方案）

- 自研可以做最贴合业务的数据模型（项目/任务/决策/知识/审计/权限），但至少 1–3 周开发 + 长期维护；当前没有必须自研的证据。
- **触发条件**：Memorix + Basic Memory 的组合在中文检索、权限模型、审计或性能上被证伪，且无法通过配置/插件解决。

---

## 5. 最优方案

### 5.1 目标架构

```text
                    ┌──────────────────────────────┐
                    │           用户 / 微信          │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │   Hermes（编排/运维/汇总）     │
                    │   - cron / kanban / 监控      │
                    │   - 原生 MEMORY.md（个人偏好） │
                    └──────┬───────────────┬───────┘
                           │ MCP HTTP      │ MCP HTTP
                    ┌──────▼──────┐  ┌─────▼────────┐
                    │  Memorix    │  │ Basic Memory │
                    │ 127.0.0.1   │  │ 127.0.0.1    │
                    │ :3211/mcp   │  │ :3212/mcp    │
                    │ 记忆+协作    │  │ 知识库        │
                    │ SQLite+FTS5 │  │ Markdown+    │
                    │ +可选向量    │  │ SQLite+向量   │
                    └──────▲──────┘  └─────▲────────┘
                           │ MCP HTTP      │ MCP HTTP
                    ┌──────┴───────────────┴───────┐
                    │   Codex（代码）   dsh（插件）  │
                    │   ~/.codex       ~/.dsh       │
                    │   config.toml    cordis.patch │
                    └───────────────────────────────┘
```

### 5.2 职责边界（防止双写与检索噪声）

| 内容类型 | 归属 | 例子 | 写入方式 |
|---|---|---|---|
| 用户身份、偏好、沟通风格 | Hermes 原生 `MEMORY.md` / `USER.md` | “用户要求中文输出”“决策需拍板” | Hermes memory 工具 |
| 项目事实、决策、坑点、修复、推理 | Memorix | “dsh 插件 check 子命令复用 render manifest”“某 shader 参数导致脖子断开” | `memorix_store` / `memorix_store_reasoning` |
| 会话摘要、跨 Agent 交接 | Memorix | “Codex 已完成 A 模块，dsh 接手验证” | `memorix_session_end` / `memorix_handoff` |
| 任务、文件锁、消息、验证门 | Memorix（跨 Agent 协调） | “锁定 plugin/ 目录”“等待 dsh 验证” | `memorix_task_*` / `memorix_lock` |
| 成文知识、设计文档、调研、runbook | Basic Memory | “motion-verdict 设计稿”“RSSHub 恢复手册” | `write_note` / `edit_note` |
| 稳定知识从记忆晋升为文档 | Basic Memory | 把一条 `decision` 整理成设计页 | 人工/Agent 审核后写 note |

**铁律**：
1. 同一内容不要同时写 Memorix 和 Basic Memory。Memorix 存“发生了什么、为什么”，Basic Memory 存“整理后的可复用知识”。
2. Memorix 记录可以引用 Basic Memory 的 `memory://` permalink；Basic Memory 文档可以在 frontmatter 里写 `memorix_ids`。
3. 任何 Agent 不得把密钥、token、密码写入任一库；写入前做模式扫描。

### 5.3 身份与命名空间

| 维度 | 规则 |
|---|---|
| Agent 身份 | `hermes-main` / `codex-main` / `dsh-main`；在 Memorix `identity join` 或 `session_start` 时显式声明 |
| 项目身份 | 以 Git 仓库真实根目录为准；Memorix 从 Git root 推导 project identity，避免同名目录串库 |
| 可见性 | `personal`（仅自己）/ `project`（当前项目所有 Agent）/ `team`（显式加入团队后共享） |
| 知识库项目 | Basic Memory 的 project 按业务域划分（如 `infra`、`guimei`、`invest`）；跨域知识放 `shared` |
| 会话 | 每次 Agent 会话一个 session；开工 `session_start`，收工 `session_end` |

### 5.4 读写协议（写进三端 `AGENTS.md` / skill）

建议把下面这段作为三端共享的“记忆协议”，按宿主能力裁剪：

```markdown
## 共享记忆协议（Memorix + Basic Memory）

### 开工
1. 调用 Memorix 的 project context / session start，拿到当前项目的：
   - 最近决策、已知坑点、未完成任务、相关文件
   - 如果没有 Memorix 工具，先读项目根 `AGENTS.md` 的“最近上下文”段
2. 如果任务涉及设计规范、调研、runbook，调用 Basic Memory 的 search_notes，
   用中文语义查询 + 英文标识符精确查询各一次。
3. 不要假设记忆是最新的；涉及代码事实时，用当前仓库文件/测试核对。

### 工作中
1. 做出非显然决策、发现坑点、修复 bug 后，调用 Memorix 写入：
   - type: decision / gotcha / problem-solution / how-it-works
   - 必须带：项目、文件路径、依据（commit/测试/日志）、时间
2. 需要改多个文件或与另一个 Agent 并行时，先申请 Memorix 文件锁/任务认领。
3. 不要把密钥、token、密码、完整客户数据写入记忆。

### 收工
1. 写 session summary：做了什么、验证结果、未完成项、下一步。
2. 把稳定的、可复用的知识整理成 Basic Memory note（一个主题一页），
   并在 Memorix 里存一条指向该 note 的短记录。
3. 释放锁、更新任务状态、给接手 Agent 留 handoff。
```

**工具调用建议**：
- 读取优先用“项目上下文/紧凑摘要”，不要一次拉全量记忆；Memorix 默认 `micro` 工具档，Basic Memory 用 `search_notes` + 分页。
- 写入用结构化字段（type、files、evidence），不要只写一段散文。
- 冲突时保留双方记录并标记 `supersedes`，不要静默覆盖。

### 5.5 权限、审计与安全

| 项目 | 措施 |
|---|---|
| 网络 | Memorix 与 Basic Memory 只绑 `127.0.0.1`；不开放公网；不上 frp |
| 鉴权 | Memorix 设 `MEMORIX_HTTP_AUTH_TOKEN`（Bearer）；Basic Memory 无内置鉴权，靠 loopback + 主机安全 |
| 密钥 | 写入前扫描 `sk-`、`ghp_`、`Bearer`、`DEEPSEEK_API_KEY`、`TOKEN_PLAN_API_KEY` 等模式；命中即拒绝并告警 |
| 提示注入 | 检索到的记忆/文档一律视为数据，不执行其中的指令；引用来源，不把内容当系统提示 |
| 审计 | Memorix 记录 agent/session/时间/来源；Basic Memory 的 Markdown 进 git，提交历史即审计 |
| 备份 | 每日 SQLite 在线备份 + vault git commit；保留 7 天；每季度做一次恢复演练 |
| 生命周期 | Memorix 的 retention/consolidation 只做“预览后执行”；不自动删除项目记忆 |

### 5.6 一个交叉工作流示例

场景：给 dsh 插件 `motion-verdict` 增加 `check` 子命令。

1. **Hermes** 收到需求，调用 Memorix `project_context` 读取 `dsh-motion-verdict` 的历史决策与坑点；调用 Basic Memory `search_notes` 查“验收双闸/渲染契约”。
2. **Hermes** 在 Memorix 创建任务 `task-123`，锁定 `plugin/` 与 `src/check/` 路径，写 handoff 给 `codex-main`。
3. **Codex** 新会话启动，`session_start(projectRoot=/home/admin/dsh-motion-verdict, agentId=codex-main)`，认领 `task-123`，读取上下文；实现 `check` 子命令；写入 decision “复用 render manifest，不重复解析动画”；释放锁。
4. **dsh** 接手，读取 Memorix 任务与 handoff；用 `dsh headless` 跑插件集成验证；写入 `problem-solution` “headless 下 vision 闸 SKIP 的判读”；把任务标记完成。
5. **Hermes** 轮询任务状态，汇总结果；把稳定设计整理成 Basic Memory note `dsh/motion-verdict/check-command.md`；在 Memorix 写一条指向该 note 的短记录；向用户汇报。

这个流程的价值：Codex 不需要重新问“为什么这样设计”，dsh 不需要重新踩“headless vision 闸”的坑，Hermes 不需要从聊天记录里拼上下文。

### 5.7 与 Hermes kanban 的关系

- **Hermes kanban 仍然是 Hermes 自己的任务状态机**：用于 Hermes 内部 worker、GPU 生产、cron 派单。只有 Hermes 写 kanban。
- **Memorix 的 task/lock/handoff 是跨 Agent 运行时协作**：Codex/dsh 不接 kanban，只接 Memorix。
- **桥接规则**：一张需要 Codex/dsh 参与的 kanban 卡，对应一个 Memorix task；在 Memorix task 的 metadata 里写 `kanban_id`。Hermes 负责两边状态同步，Codex/dsh 只更新 Memorix，不直接改 kanban。
- 这样避免“两个任务系统各自为政”，也避免 Codex/dsh 越权改 Hermes 的看板。

---

## 6. 实施计划

> 以下命令是实施草案，**本次评估未执行**。执行前需要用户拍板（见第 10 节）。所有配置改动前先备份。

### Phase 0：准备（约 0.5 天）

```bash
# 备份三端配置
cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak.$(date +%Y%m%d_%H%M%S)
cp ~/.hermes/profiles/trader/config.yaml ~/.hermes/profiles/trader/config.yaml.bak.$(date +%Y%m%d_%H%M%S)
cp ~/.hermes/profiles/gamedev/config.yaml ~/.hermes/profiles/gamedev/config.yaml.bak.$(date +%Y%m%d_%H%M%S)
[ -f ~/.codex/config.toml ] && cp ~/.codex/config.toml ~/.codex/config.toml.bak.$(date +%Y%m%d_%H%M%S)
[ -f ~/.dsh/cordis.patch.yml ] && cp ~/.dsh/cordis.patch.yml ~/.dsh/cordis.patch.yml.bak.$(date +%Y%m%d_%H%M%S)

# 安装 Codex（二选一）
npm install -g @openai/codex@0.163.0
codex --version

# 安装 Memorix
npm install -g memorix@1.9.12
memorix --version

# 安装 Basic Memory（uv 隔离 Python）
uv tool install basic-memory
bm --version
```

验收：三个命令都能输出版本；`bwrap --version`、`unshare -Ur true` 成功；3211/3212 仍空闲。

> Codex 安装器默认从 releases.openai.com 下载原生二进制；若网络慢/被拦，设置 `CODEX_INSTALLER_USE_RELEASES_OPENAI_COM=false` 回退 GitHub Releases，或直接用 npm 包。安装后必须 `codex --version` 与一次空仓库启动验证。

### Phase 1：记忆中枢（约 0.5 天）

```bash
# 初始化 Memorix 全局配置
memorix init --global

# 编辑 ~/.memorix/config.toml：
#   [server] dashboard=true, dashboard_port=3210
#   [embedding] provider="off"     # 首期先关闭向量，验证 FTS/BM25 与协议
```

`~/.memorix/config.toml` 关键片段：

```toml
[server]
transport = "stdio"
dashboard = true
dashboard_port = 3210

[embedding]
provider = "off"
# 二期中文向量：
# provider = "fastembed"
# model = "BAAI/bge-small-zh-v1.5"
# dimensions = 512
```

systemd 用户服务（`~/.config/systemd/user/memorix.service`）：

```ini
[Unit]
Description=Memorix shared memory MCP service
After=network.target

[Service]
Type=simple
ExecStart=/home/admin/local/node-v24.9.0-linux-x64/bin/memorix serve-http --port 3211
Environment=MEMORIX_HTTP_AUTH_TOKEN=<随机令牌>
Restart=always
RestartSec=3
WorkingDirectory=/home/admin

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now memorix.service
curl -s http://127.0.0.1:3211/health | head
```

验收：`/health` 返回 200；`memorix status` 能看到当前项目；CLI 写入一条测试记忆，再搜索命中；重启服务后数据仍在。

### Phase 2：知识库（约 0.5 天，Gate 2 通过后）

```bash
# 建立 vault
mkdir -p ~/wuhoo-brain/{shared,infra,guimei,invest,runbooks}
cd ~/wuhoo-brain && git init

# Basic Memory 中文向量配置
bm config set semantic_embedding_provider fastembed
bm config set semantic_embedding_model BAAI/bge-small-zh-v1.5
bm config set semantic_embedding_dimensions 512
bm reindex --embeddings
```

systemd 用户服务（`~/.config/systemd/user/basic-memory.service`）：

```ini
[Unit]
Description=Basic Memory knowledge base MCP service
After=network.target

[Service]
Type=simple
ExecStart=/home/admin/.local/bin/bm mcp --transport streamable-http --host 127.0.0.1 --port 3212
Restart=always
RestartSec=3
WorkingDirectory=/home/admin

[Install]
WantedBy=default.target
```

验收：
- `bm mcp` 启动后 3212 可连；
- 写入一篇中文测试笔记，`search_notes` 用中文语义查询能命中；
- 10 条中文精确短词查询记录命中率（预期部分失败，作为基线）；
- 重启后 Markdown 文件与索引一致（`bm doctor`）。

### Phase 3：三端接入（约 1 天）

**Hermes**（先只改 default）：

```yaml
mcp_servers:
  memorix:
    url: http://127.0.0.1:3211/mcp
    headers:
      Authorization: "Bearer <随机令牌>"
    timeout: 60
    connect_timeout: 30
  basic_memory:
    url: http://127.0.0.1:3212/mcp
    timeout: 60
    connect_timeout: 30
```

重启 gateway（用户 `/restart` 或网关外 `systemctl --user restart hermes-gateway`）。验收：新会话里 Hermes 能调用 `mcp_memorix_*` 与 `mcp_basic_memory_*` 工具。

**Codex**：

1. 先跑 DeepSeek 官方 Codex 配置脚本（自动备份 + 写 `models.json` + 写 `[model_providers.deepseek]`）。
2. 在 `~/.codex/config.toml` 追加：

```toml
model = "deepseek-v4-pro"
model_provider = "deepseek"
model_reasoning_effort = "high"

[model_providers.deepseek]
name = "DeepSeek"
base_url = "https://api.deepseek.com/v1"
env_key = "DEEPSEEK_API_KEY"
wire_api = "responses"

[mcp_servers.memorix]
url = "http://127.0.0.1:3211/mcp"
startup_timeout_sec = 30
tool_timeout_sec = 60

[mcp_servers.basic_memory]
url = "http://127.0.0.1:3212/mcp"
startup_timeout_sec = 30
tool_timeout_sec = 60
```

3. `~/.codex/AGENTS.md` 写入 5.4 的记忆协议（按 Codex 的全局指令链）。
4. 启动 Codex 前导出 `DEEPSEEK_API_KEY`：

```bash
export DEEPSEEK_API_KEY="$(grep -m1 '^DEEPSEEK_API_KEY=' ~/.hermes/.env | cut -d= -f2-)"
codex
```

验收：`codex mcp list` 看到两个 server；新 Codex 会话能读 Memorix 测试记忆；Codex 能写一条 decision 并被 dsh 读到；启动无 sandbox 警告。

**dsh**：

在 `~/.dsh/cordis.patch.yml` 追加（或放到 `~/.dsh/profiles/headless/cordis.patch.yml`）：

```yaml
- insert:
    - id: mcp-memorix
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: memorix
        transport: streamable-http
        url: http://127.0.0.1:3211/mcp
        toolCallTimeoutMs: 60000
        reconnect:
          enabled: true
    - id: mcp-basic-memory
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: basic_memory
        transport: streamable-http
        url: http://127.0.0.1:3212/mcp
        toolCallTimeoutMs: 60000
        reconnect:
          enabled: true
```

`~/.dsh/AGENTS.md` 追加 5.4 的记忆协议。

> **dsh 启动铁律**：dsh 读 CWD 的 `.env`，且 `NODE_PATH` 非空会拒启。任何 dsh 命令都要在空目录（如 `/home/admin/dsh-trial/run`）执行并先 `unset NODE_PATH`；否则会读 `~/.hermes/.env` 里的 `NODE_PATH` 直接失败。这个坑与 MCP 配置无关，但会让“接入后启动不了”被误判为 MCP 故障。

验收：

```bash
cd /home/admin/dsh-trial/run && unset NODE_PATH
dsh --profile headless --dump-config | grep -A4 mcp-
dsh headless "查询 Memorix 里的验证口令 X，并说明你是从哪个项目读到的"
```

验收：`mcp__memorix__*` 工具出现；headless 能调用并返回正确口令；dsh 写入的记忆能被 Hermes 读到。

### Phase 4：验收（约 0.5 天）

| # | 测试 | 操作 | 通过标准 |
|---|---|---|---|
| 1 | Hermes → Codex | Hermes 写唯一口令；Codex 新会话查 Memorix | 正确返回，< 3 次工具调用 |
| 2 | Codex → dsh | Codex 写一条 decision；dsh headless 查 | 正确返回，含文件路径 |
| 3 | dsh → Hermes | dsh 写验证结果；Hermes 查 | 正确返回，含 task id |
| 4 | 项目隔离 | 两个 Git 仓库写同名 key | 不串库 |
| 5 | 冲突/去重 | 同一事实写两次不同值 | 冲突可见，不静默覆盖 |
| 6 | 重启恢复 | 重启两个 MCP 服务 | 三端重连，工具仍可用 |
| 7 | 中文检索 | 20 条语义 + 10 条短词 | 记录 Recall@5 基线，语义 ≥ 80% |
| 8 | 资源 | 查看 RSS/磁盘 | 合计 < 800 MB / < 2 GB |
| 9 | 安全 | 尝试写入假密钥 | 被拒绝或告警；扫描无泄漏 |
| 10 | 回滚 | 注释 MCP 配置并重启 | 5 分钟内三端恢复独立工作 |

### Phase 5：扩展（可选）

- 把 MCP 配置复制到 trader/gamedev profile，验证多 profile 不冲突。
- 给 Codex/Hermes 启用 Memorix 插件/hooks（自动捕获），观察 1 周再决定是否长期保留。
- GPU 恢复后，评估 GPU 侧 Codex 是否通过 frp 连云端 MCP；如需要，单独做 TLS/鉴权，不直接暴露 3211/3212。
- 知识库接入现有 `~/wuhoo-workspace/docs`、GDD、runbook，写批量导入脚本。
- Basic Memory schema：为 `decision`、`runbook`、`design` 定义字段，减少自由格式漂移。

---

## 7. 资源与成本估算

| 项目 | 估算 | 说明 |
|---|---|---|
| Memorix 常驻 RSS | 20–100 MB（空闲/日常）；10 万条峰值约 419 MB | 官方性能文档 + 实测修正 |
| Basic Memory 常驻 RSS | 150–500 MB（含 bge-small-zh ONNX） | 取决于模型与索引大小 |
| Codex 进程 | 100–400 MB | 取决于会话与仓库 |
| 磁盘 | Memorix 数据 + Basic Memory 索引/模型 < 2 GB | 不含代码仓库 |
| 许可费 | 0 | Memorix Apache-2.0；Basic Memory AGPL-3.0 |
| 模型费 | Codex 走 DeepSeek 按 token 计费 | 可用 flash 降本；无 GPU 费用 |
| 运维 | systemd 两个用户服务 + 备份 cron | 首期每周 < 1 小时 |

---

## 8. 风险与对策

| # | 风险 | 影响 | 对策 |
|---|---|---|---|
| 1 | Memorix 较年轻，版本漂移 | 升级后工具/配置变化 | 钉 1.9.12；升级前读 CHANGELOG；保留回滚版本 |
| 2 | Basic Memory AGPL | 未来分发/托管有义务 | 内部使用先做；若要产品化，法务复核或换 Engram/自研 |
| 3 | 中文 FTS 不分词 | 中文关键词搜不到 | 用 bge-small-zh 向量；短词走向量；二期评估 bigram/trigram |
| 4 | SQLite 单写者 | 多进程写锁/索引竞争 | 只用 HTTP 单服务；禁止 stdio 与 HTTP 混用 |
| 5 | 双库职责混淆 | 重复、检索噪声 | 5.2 职责表 + 写入协议；同一内容不双写 |
| 6 | 上下文膨胀 | token 成本上升、模型注意力下降 | 紧凑摘要、micro 工具档、限制返回条数、按需 detail |
| 7 | Hermes multiplex | 次级 profile 没工具 | 首期只改 default；稳定后逐 profile 加并验证 |
| 8 | dsh alpha breaking | MCP 配置失效 | 钉 0.1.7-alpha.1；升级后重跑 dump-config 与召回测试 |
| 9 | Codex 第三方 provider 兼容性 | 工具调用/补丁行为差异 | 用 DeepSeek 官方集成；先跑只读任务、再跑写任务；保留 OpenAI 官方路径备选 |
| 10 | Codex 沙箱失败 | 无法安全执行命令 | bwrap 已装、userns 可用；失败则降级 `workspace-write` + approvals，禁止 full-access |
| 11 | 密钥进入记忆 | 泄密 | 写入前扫描；协议明令禁止；定期审计 |
| 12 | 服务故障 | 三端同时失去记忆 | systemd Restart=always；health 探针；故障时 MCP 工具报错而非假成功 |
| 13 | 数据丢失 | 记忆/知识不可恢复 | 每日 SQLite 备份 + vault git；季度恢复演练 |
| 14 | GPU 离线 | 无法做 GPU 侧联调 | 首期不纳入；GPU 上线后单独评估 |

---

## 9. 参考链接

- Hermes MCP 客户端（内置技能）：`native-mcp`
- Hermes memory providers 文档：https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers
- Codex MCP 文档：https://developers.openai.com/codex/mcp
- Codex 沙箱文档：https://developers.openai.com/codex/sandboxing
- Codex 自定义 provider（DeepSeek 官方）：https://api-docs.deepseek.com/quick_start/agent_integrations/codex/
- Codex AGENTS.md：https://developers.openai.com/codex/guides/agents-md
- dsh MCP 文档：https://deepseekdocs.com/en/docs/features/mcp
- dsh 记忆 MCP 指南：https://deepseek-harness.github.io/deepseek-harness/en/guide/mcp-memory
- dsh MCP client README（本地安装包内）：`@deepseek-ai/dsh-mcp-client`
- Memorix：https://github.com/AVIDS2/memorix
- Memorix 集成矩阵：https://github.com/AVIDS2/memorix/blob/main/docs/INTEGRATIONS.md
- Memorix 性能说明：https://github.com/AVIDS2/memorix/blob/main/docs/PERFORMANCE.md
- Basic Memory：https://github.com/basicmachines-co/basic-memory
- Basic Memory MCP 工具：https://docs.basicmemory.com/reference/mcp-tools-reference
- Basic Memory 语义搜索：https://docs.basicmemory.com/concepts/semantic-search
- Basic Memory 配置：https://docs.basicmemory.com/reference/configuration
- Basic Memory CJK 问题：https://github.com/basicmachines-co/basic-memory/issues/1294
- Engram：https://github.com/Gentleman-Programming/engram
- MCP Reference Memory：https://github.com/modelcontextprotocol/servers/tree/main/src/memory
- Graphiti MCP：https://github.com/getzep/graphiti/blob/main/mcp_server/README.md
- mem0 自托管：https://docs.mem0.ai/open-source/overview

---

## 10. 待拍板项

1. **是否按“Memorix 单层试点 → 双层目标”推进？**  
   - A：同意，先 Phase 0–1（安装 + 记忆中枢 + 三端接入），1 周后看验收再决定 Basic Memory。  
   - B：直接上双层（Memorix + Basic Memory），接受更高复杂度。  
   - C：只做评估，不安装。

2. **知识库是否采用 Basic Memory？**  
   - A：采用，接受 AGPL-3.0（内部使用）。  
   - B：先用 Memorix Knowledge Workspace，等它满足不了再上 Basic Memory。  
   - C：改用 Engram（MIT、更轻，但知识页能力弱）。

3. **Codex 的模型与沙箱策略**  
   - 模型：A：DeepSeek 官方 `deepseek-v4-pro`（推荐）；B：token-plan `qwen3.8-max`（需补模型元数据）；C：两者都配，按任务切换。  
   - 沙箱：A：`workspace-write` + `on-request`（推荐）；B：`danger-full-access`（不推荐）；C：先只读试跑，再开写。

4. **共享范围**  
   - A：仅云端 default profile + Codex + dsh（推荐首期）。  
   - B：同时接入 trader/gamedev。  
   - C：等 GPU 上线一起接。

5. **执行窗口**  
   - 是否现在执行 Phase 0–1？需要一次 gateway 重启（`/restart`）和两个 systemd 用户服务；预计 1–2 小时，期间不影响微信/cron 以外的现有功能。

---

## 11. 附录：本次实测记录摘要

```text
2026-10-20 14:4x CST
- Hermes v0.22.2 (2026.9.24) stable / git d923a5eb
- dsh 0.1.7-alpha.1；node_modules/@deepseek-ai/dsh-mcp-client 存在
- Codex 未安装；npm view @openai/codex version = 0.163.0
- node v24.9.0 / npm 11.6.0 / uv 0.11.7
- bwrap 0.4.0；unshare -Ur true 成功；SELinux Disabled
- 端口 3210/3211/3212 空闲；systemd user Linger=yes
- token-plan /chat/completions qwen3.8-flash = 200 (2.65s)
- token-plan /responses qwen3.8-flash = 200
- api.deepseek.com /chat/completions deepseek-v4-pro = 200 (1.18s)
- api.deepseek.com /responses deepseek-v4-pro = 200 (2.20s)
- api.deepseek.com vision-exp 图像输入 = 200
```

**未验证项（实施阶段必须补）**：
- Codex 在本机的实际安装、启动、沙箱、DeepSeek 工具调用与补丁行为。
- Memorix 在本机的中文检索质量、Hermes/Codex/dsh 三端 MCP 实际连通、SQLite 并发。
- Basic Memory 在本机的 HTTP MCP 启动、bge-small-zh 索引、中文召回。
- 三端在同一个项目上的锁/交接/任务状态同步。
- 资源占用（RSS、磁盘）与 72 小时稳定性。

---

*本文档为评估与实施方案，不构成已实施记录。所有安装、配置写入、gateway 重启均需用户明确批准后执行。*