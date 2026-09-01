用户身份：Wuhoo公司首席Agent。业务领域：金融投资（股票期货交易）、数字内容生成与运营（插画、漫画、短视频）、Coding（plugin/skill编码）。交互方式：主要通过WeChat和CLI，不再使用其他辅助工具改动工作目录。
§
用户（Wuhoo 首席 Agent）工作风格：1）审计；2）根因分析再修复；3）数据驱动；4）休假后先扫描系统状态；5）先全貌调研再行动；6）A/B双轨制。交互：WeChat+CLI。Git：wuhoo-workspace→push→sync wuhoo-skills→push。推理延迟可接受，数据新鲜度优先。报告保留推理路径。
§
Wuhoo方法论：先全面扫描再修复。交叉污染检查、因子文件独立性、index格式、数据量覆盖度对比。展示用表格，给修复前后对比。数据排查规则学习优先于手工参数。
§
WC2026预测系统。中文沟通，东八区CST。零容忍PDF回退，已有功能不丢。<100KB微信PDF，/tmp/短ASCII名可靠。手动cron。Expert: spots anomalies, tactical+model analysis, rigorous audit. SF: France 80.8% vs Spain; England 7.0% vs Argentina 78.2%. Bellingham历史级状态, Messi依赖风险。
§
资深游戏玩家，独立游戏开发中。偏好: 先全貌调研→plan→执行。玩法设计亲自操刀。代码由Hermes直接写(禁用delegate_task)，遇阻塞果断止损(如T003放弃EditMode缠斗→去PlayMode测试→后移除PlayMode)。接受务实方案，不追求完美。GPU节点延后。工具链: Unity 6 URP, Aseprite 48px像素, Blender 3D, HeartMuLa音频。
§
工作风格追加: 7) 编码方案不利时果断止损换策略(如delegate_task→直接写C#); 8) 接受阶段性不完美方案(如移除PlayMode测试),后续再迭代; 9) 开发中实时审计: 每完成一个task记录CI迭代次数+新pitfalls+技术决策, 边前进边复盘。
§
用户 haohaijiao 杭州。RTX 4070Ti/Windows PC, Hermes阿里云新加坡。重授权,不喜盲目修改。技术强(PowerShell/SSH/Unity)。中英。游戏偏好: Dave the Diver/Terraria/收集经营。工作风格: "继续"即主动推进下一phase不等待指令; 每phase审计复盘; 美术接受务实方案不阻塞进度; Android手机优先测试触控(不满PC不稳定:"Windows真是让人无语")。
§
用户要求: 报告/plan/分析文档用中文输出。
§
大文件下载: 境外源用户自己下放NAS指定位置, 不用frp/scp中转(隧道上行大流量必断, 08-09用户明确"以后这种情况让我来下载"); 国内源modelscope GPU直连下载已获用户批准(08-22拍板)