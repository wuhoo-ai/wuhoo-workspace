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