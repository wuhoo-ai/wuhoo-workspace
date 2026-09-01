矿工守夜: wuhoo-ai/miners-watch(~/miners-watch), Unity 6000.5.4f1, v1.1-dev; 场景改后须手动Author重创; 验证清单~/.hermes/plans/miners-watch-verification-checklist.md
§
Skill托管: wuhoo-game-*17个在~/wuhoo-workspace/skills/wuhoo-game-dev/(external_dirs直接加载,git→wuhoo-ai/wuhoo-workspace); 发布仓库~/wuhoo-skills(改后sync+push); 新skill须git托管; 不在~/.hermes/skills建wuhoo skill; desc≤60字符。UnityCsReference: 云端~/unity-csref+GPU C:\ai\ref(6000.5分支, master=alpha勿用, 只读禁拷贝, 见wuhoo-unity-reference)
§
音频管线(决策110): ACE-Step 1.5主力+HeartMuLa兜底, 音效=Stable Audio Open, 锣鼓点睛≤5处; 音乐色彩=每章主色→音色家族; 零外部素材
§
guimei设计哲学(用户定调): 无数值(胜率对白/装备性情相性); 装备永久制(不坏不修不丢不刷); 楮钱只能点燃不能花(仪式非交易); 时间历法无UI环境感知,鬼节惊喜不预告; 不刷图不氪金; 经济服务叙事; 魂器释念=铜鉴仪式
§
创作生产工作流: 阶段门控(stage-gate). 文生图→用户review→确认后图生视频→review. 先短demo再全量. prompt/关键帧必须先给用户看再执行; prompt须含人物身份/个性/剧情/意境段(纯规格清单被用户否, 模型据人物背景增强意境). 系统/文档设计同理: 先呈现核心决策→用户逐点确认→才落盘commit(2026-08-06用户重申). 每阶段产物commit+push到GitHub.
§
guimei战斗容器(决策78-83): 三步傩仪回合(请傩→行傩→守神→傩成送神)+QTE时机增强(非音游), 四法器(桃木剑/符箓/铜铃/铜镜), 连击2/3/4档傩成按需释放, 喘息无时限, 特色规则六案选材=仪式行为库, 易懂难精; 详见03-combat-system.md
§
guimei对白规范(决策87, GDD/08定稿): 中唐818-820语言基准, 称呼=吴郎/吴生/郎君/守桥/阿翁, 穿帮词17处已清, 浓度90%C2+10%C3(超度锁C2/市井C1-C2/判官C3/鬼魂C2-C3摆动), 古语控制量
§
guimei仓库: Codeup主+GitHub镜像(双remote两端push, 分叉pull --rebase勿force); GPU主战场C:\ai\guimei-codeup, Unity拼装=C:\ai\guimei-lab(RigBuilder在此); 门禁=pre-commit L1+TestRunnerApi(云效暂停); 云端pull新LFS须GIT_LFS_SKIP_SMUDGE=1+git lfs pull codeup; 旧脚本归档_archive\2026-08-21(PowerShell转义坑→一律脚本文件)
§
GPU节点(08-20+08-30): SSH=hermes-agent; Unity 6000.5.4f1路径含空格(ssh引号坑→一律写bat执行, CRLF+chcp65001); ssh串联用&(cmd不认;); python3.11(uv shim坏)→C:\ai\ComfyUI\venv\Scripts\python.exe; APK: SDK=C:\ai\android-sdk+JDK=C:\ai\jdk\jdk-17; Unity许可证复制自haohaijiao(batchmode必需); Codex App+DeepSeek V4 pro/flash已配通(08-30, 见codex-deepseek-setup技能)
§
交付规范(08-08+08-22): 成品视频→NAS极空间guimei-transfer/不发微信; 图片/图集→推Codeup即可(用户Codeup看,不微信发图); GitHub周同步一次(日常只推Codeup); 微信仅进度+路径
§
frpc(08-22): NSSM服务名frpc, C:\ai\frp, 无窗/自启/被杀15s自愈; 勿手动起杀(杀=断SSH隧道); frp0.70须NSSM注册(1053超时)
§
GDD三层规格(08-10): 设计/美术(资产卡6类BG/LK/OB/AN/VD/FX)/技术(schema); 拍板三档=用户基调/我实现/测试参数; 改GDD必跑tools/gdd_linter.py; 38索引=事实源(R1:引用决策须MASTER有该字样); 穿帮词lint+静默预算≤3/章
§
guimei美术动画定调(决策110, 08-10拍板+08-21增补): 皮影柔情国风=皮影部件工艺×剪纸东方×唱诗班表演×重彩志怪; 纯皮影美学+数字头茬替换(表情库Sprite Swap)+多层重彩景片; Unity 2D Animation部件补间唯一(关Spine/AI视频/LivePortrait, 但Minimax H3保留供过场动画, 勿清理); 表情=换头茬(大表情)+活眼活口部件(微表情), 否网格畸变; 运动语言5条(悬挂晃/铰链摆/呼吸/飘动/节奏跟鼓点); 透光染色调和重彩×皮影
§
guimei决策109/111(08-10): 探索=饥荒式斜俯视2.5D(双镜头), 记忆地图+examine判词; 终章=自由模式
§
谷时模式(08-24拍板): 多棒接力已停(代码/构建/晨复盘cron全删), 谷时=单一批量生产一次性cron(22:15, 自包含prompt, 完成微信汇报, 样板见valley-hour-development技能references/batch-production-prompt.md); cron create的model参数不生效→直接改~/.hermes/cron/jobs.json的job.model/provider
§
guimei决策113-115(08-29): 分层演出S/A/B/C(全骨骼仅主角)+过场混合(H3/HappyHorse)+部件生产云端出图本地抠图; 详见GDD-MASTER决策表
§
皮影锚点体系(决策116, 08-30): 多锚点专用不混配(躯干6/头茬2/四肢2), 锚点在图形内部留重叠余量(qwen孔=装饰已去孔化), AI语义标定+用户审核, 拼装=锚点配对制(BFS+旋转支点=锚点对), pivot归一化须y翻转(图像y下→Unity y上); scale: 头0.35/四肢0.62/躯干0.72/袍摆0.67; 表演语言: 微颤±1-3°/幅度分级/换头遮挡帧+透光闪/离幕光效/口型眨眼联动/五分相默认; 详见research/31+06 1.2.6; 拼装场景须资产Sprite(Sprite.Create不持久化), Refresh循环调用卡编辑器, batchmode重跑前须用户关Unity(开着锁项目)
§
OPC铁律(08-30): AI独立完成标定/生产后台执行, 用户只审核修正; 先严谨调研第一性原理再动手; 用户休息时连续干完再汇报
§
GPU节点(09-01): wmic已被Windows移除(命令不存在), 磁盘检查改用 `fsutil volume diskfree C:`(输出GBK乱码但数字带GB单位可读)