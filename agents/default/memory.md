坑:qwen3.7系不认re=max,qwen3.8已实测支持(flash/max均认,验证脚本见hermes-model-config技能scripts/verify_model_effort.sh)
§
用户决策铁律(08-04+08-10+08-22): 凡需拍板的问题必须停下等待回复(clarify_timeout=0, 绝不默认执行); 待拍板三档=设计基调≤5项用户拍/实现细节我定案可异议/验证参数测试定。微信上clarify工具投递失败→改普通文本消息+编号选项。自动化方案须防崩溃设计(任务切分≤3单元/棒+轮数上限60/90/120可配置+单元commit+锁3h超时), 不接受"崩溃后恢复"; 验证优先0成本(查配置/日志/state.db, 不试跑)
§
用户表达偏好(2026-08-04定调): 中文输出必须完整展开——讲清是什么/为什么/怎么落地, 禁止"名词+名词"堆叠简写; 设计讨论先讲机制人话(玩家语言), 文化术语只作设计师骨架不作玩家概念。被批"输出太过精简,字词句子无法准确理解"
§
Hermes调试铁律: 不改上游源码, 优先OS/配置层; gateway内不能自重启(terminal/systemctl被拦); 绕过=execute_code内subprocess或外部shell; iLink限流已配(08-08): send_chunk_delay_seconds=2.0+threshold=3/window=60/open=20/retries=2; 长任务静默+关键节点汇报(用户认可), 用户消息不中断任务只排队
§
GPU codex手机访问(08-31,未实施): 入口47.79.255.24:2222; codex全路径=C:\Users\haohaijiao\AppData\Local\OpenAI\Codex\bin\b99306303521e97e\codex.exe
§
LLM链路(09-01拍板,09-02改名): provider名 token-plan→qwen(端点不变), 死条目deepseek-nothink/vision已删, 剩deepseek/deepseek-flash/qwen; 主对话/aux15段/vision=qwen3.8-flash(max)@qwen; delegation=qwen3.8-max; fallback=qwen3.8-flash→deepseek-v4-flash; aux不思考=extra_body reasoning enabled:false; image_gen=wan2.7-image-pro@qwen; cron仅gamedev健康检查显式绑qwen; 切换5处联动=model.default/delegation/fallback_providers/providers.qwen/auxiliary; 视觉小图≥64px否则400; 云端3profile+GPU gpu-worker config已同步
§
多profile拓扑(09-01拆分): 单gateway multiplex, default=总控/微信/RSS简报, trader=15投资cron, gamedev=游戏线+GPU健康cron+Unity MCP; wuhoo技能按skills/{shared,default,trader,gamedev}目录切分=可见性边界, external_dirs=[shared,自身]; 运行时资产在wuhoo-workspace/agents/+夜间快照cron; GPU节点hermes已装v0.21(gpu-worker profile待建, api_server隧道28642已配frpc待重启生效); 详细见hermes-agent-architecture-audit技能+references/multiplex-contract-verified.md
§
游戏项目命名铁律(用户2026-09-01两次强调): 项目名只写作"guimei"(拼音),不存在"归魅"两个汉字,禁止在文档/kanban卡/文件名中自造中文名。Kanban: guimei/invest 两板已建, default 配 kanban 工具集(新会话生效); CLI 用法坑见 kanban-orchestrator 技能(--board 是全局参数放子命令前)
§
GPU改造部署(09-01晚完成主体, 09-02配置同步): gpu-worker profile+独立网关(gw_gpuworker_restart.bat, WMI拉起)+api_server 8642; 云→GPU经frp 28642(peer dm实测通); GPU→云 28643未持久化已断, 用户拍板暂缓; GPU网关重启坑: schtasks拉不起InteractiveToken任务(267009), 用WMI Win32_Process.Create+HERMES_HOME显式(gw_gpuworker_restart.bat); 09-02发现旧网关UNCLEANLY退出(SIGKILL/OOM, lifecycle_ledger记录)→8642无监听, WMI重启恢复; 09-02 GPU gpu-worker模型链路已与云端一致(qwen主+deepseek兜底), .env补DEEPSEEK_API_KEY+去重TOKEN_PLAN_API_KEY; wmic已从Win11移除→Get-CimInstance替代
§
系统体检(09-02): trader 15个投资cron自07-01全部有意暂停(非丢失,trader空转,恢复需逐个resume+钉模型); dashboard 9119公网开放+basic_auth弱口令H%emersAgent待拍板; api_server 8642公网安全组未开(peer实际走frp localhost:28642, config public_url失真); 大文本微信投递(64KB简报)会触iLink限流失败——判读法见hermes-fleet-ops §11
§
用户要审计 worker 完整推理过程(09-02 battle卡): 从执行 profile 的 state.db messages 表导出 md(思考+工具调用+返回)入 review 目录 commit 三端给路径; 卡"无产出"先区分诊断期 vs 停滞(heartbeat+文件mtime+工作区diff 三查联合判读)
§
guimei管线方向拍板中(09-03): 用户否52件分件拼装(拼接感/精修依赖/token贵/舍本逐末), 帕累托标准=传统味+表现力+AI舒适OPC; 已论证方案B'=A-pose整身定妆图→程序化切10-14主身大块→现有锚点+RigBuilder铰链重挂→覆盖层5-8件→表情Sprite Swap不变; Spine纯蒙皮被否(权重绑定GUI活非OPC, 皮影语汇=铰链刚体非柔体, 与决策110一致); idle四层/battle动画逻辑可复用; wsq battle v2.1渲染验收+idle执行卡已冻结; 试点卡(吴守桥定妆图1张→切块→idle重挂→帧差+用户目检)待批
§
web_search故障根因(09-03已定位未修): hermes-agent上游d6773cf2已删tavily后端, config残留backend: tavily→报no registered provider; brave插件注册名=brave-free且读BRAVE_SEARCH_API_KEY(.env只有旧名BRAVE_API_KEY); 修复命令待用户批准(审批超时): cp .env备份+sed改名BRAVE_API_KEY→BRAVE_SEARCH_API_KEY + hermes config set web.backend brave-free + extract_backend firecrawl(keyless ring), 执行后必实测search+extract各一次
§
guimei路线决策(09-03拍板): B'=A-pose整身定妆图→程序化切10-14大块→现有锚点/RigBuilder铰链树复用→覆盖层5-8(武器/面具)→表情换头茬不变; 皮影语汇=刚体铰链非蒙皮, Spine蒙皮对比待用户有额度时触发; 吴守桥battle v2.1渲染验收+idle执行卡冻结, 52件资产冻结保留; 试点卡暂停; battle两卡均timed_out于60轮迭代上限→续跑必须切"先渲1帧试看"级小卡, 程序验收(帧差/画像)测不了审美, 视觉闸门=用户看帧; 备忘=guimei/docs/route-decision-2026-09-03.md(commit已落, 未push)
§
web_search修复(09-03): 上游8/30删Tavily后端(d6773cf2, keyless ring=exa/parallel/firecrawl/keenable), config残留tavily→报no registered provider; 修复=backend brave-free + extract firecrawl + .env BRAVE_API_KEY改名BRAVE_SEARCH_API_KEY + env_passthrough同步; 已实测通; 旧TAVILY_API_KEY/plugins/web/tavily空目录为上游删除残留