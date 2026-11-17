---
name: wuhoo-manju-storyboard
description: "Use when 把GDD故事线/剧情转成漫剧或故事视频的分镜提示词脚本. guimei叙事规范+万相3.0官方公式+关键帧→首帧→视频分层生产."
version: 1.0.0
category: default
tags: ["wuhoo"]
---

# 漫剧分镜提示词脚本（GDD 故事线 → 分镜 → Wan3.0 提示词）

把 guimei GDD 的章节剧本（已含 13 演出记号、08 对白规范、37 旁白规范）转成
可直接投喂 Wan3.0 视频模型的分镜提示词脚本。产物 = 分镜脚本表 + 每镜头
「关键帧生图提示词 + 视频提示词 + 生产参数单」，供 wuhoo-video-generation 技能试产。

## Trigger

用户要求：漫剧制作、故事视频、章节改编视频、结尾/宣传视频、分镜脚本、
把 GDD 剧情变成画面清单。纯视频生成（已有提示词）直接用 wuhoo-video-generation。

## 分层生产总路线（业界共识 + 官方能力，勿跳层）

```
GDD章节剧本 → ①选段立项 → ②分镜拆解(画面清单) → ③关键帧生图+vision审
→ ④视频提示词成型 → ⑤Wan3.0试产(i2v首帧驱动) → ⑥双闸验收 → ⑦归档
```

为什么分层：一次性 t2v 长叙事控不住角色一致性与构图；业界漫剧主流做法是
「高质量静帧定格关键帧 → 首帧参考驱动图生视频」（研究出处见 references/industry-research.md）。
Wan3.0 原生支持多镜头叙事（≤30s、序号+时间戳），但单镜头精控仍是漫剧主用法；
多镜头模式用于氛围空镜串烧等低一致性要求场景。

## 输入资产（guimei 仓 ~/wuhoo-workspace/games/guimei/）

| 资产 | 路径 | 用途 |
|---|---|---|
| 章节剧本 | GDD/chapters/chapter-0N-*-draft.md | 事实源：场景/对白/旁白/演出记号逐字取用 |
| 主线纲 | GDD/main-chapter-outline-draft.md | 六章结构/情感曲线/结局类型 |
| 演出语言 | GDD/13-cinematic-language.md | 记号体系4组/宿命感五要素/六模式（定稿） |
| 过场分镜 | GDD/29-c-cutscene-storyboards.md | 8条24镜五要素三镜结构（定稿，C档可直接复用） |
| 对白规范 | GDD/08-dialogue-style.md | L1-L4浓度/禁词25+/语气词/超度句锁C2 |
| 旁白规范 | GDD/37-narration-guide.md | 六通道分工/三问法则/四类句/三禁/每场景≤3句 |
| 角色表 | GDD/17-core-characters（见GDD-MASTER索引） | 角色外貌/族系特征/称呼 |
| 标杆图 | GDD/art-samples/routeA-bench-2026-09/、review/2026-09-17-k2-benchmark-batch/、review/2026-09-18-k4-*/ | 角色一致性参考（李章武LZW/渔夫YF/水鬼SG/吴守桥SB-13） |
| 风格圣经 | GDD/art-samples/style-bible-v3.1/（SB v3.1图集） | 风格锚定参考图 |
| Boss设计 | GDD/bosses/boss-suxiaoxiao-draft.md 等 | 角色动作/演出细节 |

## ① 选段立项

- 一集漫剧 = 一个情感弧，不是整章。1-2 分钟 ≈ 8-15 个分镜（业界经验），每镜头 2-5s。
- 选段标准：情感节拍完整（如第一章「苏小小·渡」弧：等待→被看见→不用等了）、
  视觉招牌强（雾/灯/钗/梳头）、资产就绪度高（有标杆图的角色优先）。
- 立项单写明：源章节+场景号、情感弧一句话、镜头数预算、角色资产清单、试产镜头候选。
- 章节选择属实现细节可自定，但**改动 GDD 剧情事实=设计基调，必须用户拍板**。

## ② 分镜拆解（画面清单）

每镜头一行，字段继承 29 定稿五要素（画面/时长/运动/色彩/声音）+ 13 记号：

```
镜号 | 源场景 | 景别 | 运镜 | 时长 | 画面(主体+场景+运动) | 色彩 | 声音 | 台词/旁白(逐字) | 转场 | 资产依赖
```

纪律：
- **忠实 GDD**：台词/旁白逐字照录（含标点断句，如「油壁车……夕相待。」「人不来……」），
  不扩写剧情、不加 GDD 没有的情节（wan3-pe 忠实性硬约束，见 references/wan3-pe-format.md）。
- **克制第一**（13 三基准）：拿不准时删对白留画面；留白是设计不是空洞——
  宿命感五要素（时间/空间/声音留白+色彩渐变+重复意象）至少占其一。
- 旁白按 37 规范：吴守桥视角 L2 浅文，四类句（状态/目标/身份/因果），每场景≤3句，
  三禁（上帝视角/解释情绪/重复对白）。
- 13 记号原样保留在分镜表（[驻留2s][色变:冷翠→金白,3s][单声:磬]…），
  ④阶段再翻译成视频提示词语言（映射表见 references/guimei-cinematic-mapping.md）。
- 景别/运镜用大白话+焦段（「大远景建立镜头，24mm广角，极低角度仰拍，摄影机静止」），
  避免模型控不住的高频动作（「一秒摇头3次」禁写）。
- 首尾帧相接不跳段不重叠；转场写「硬切转场/叠化转场/从上一分段最后一帧无缝衔接」。

## ③ 关键帧生图 + vision 审

- 每镜头一张关键帧（首帧），竖屏漫剧用 9:16 构图（如 720*1280）。
- **有权威母图的角色：关键帧优先=母图程序化竖裁（零重绘零成本）**——11-17 首试产实证：
  wan2.7 t2i 对布局硬约束（孤悬比例/篷塌露骨/破洞透光/下缘消散/皮影接缝）三轮迭代仍 FAIL，
  母图竖裁 vision 判定「可直接用」且锁定项全在。裁切前 vision 复核母图实际外观
  （旧 prompt 文本与母图可能有 K2 已知偏差，以母图为准），裁切后 vision 确认人物完整/背景协调。
- 无母图的新角色/新场景才走 t2i：~/.hermes/skills/image-generation/gen_image.py
  （wan2.7-image-pro / qwen-image-3.0-pro），留足 3-5 次迭代预算，布局类约束预期服从度低。
- **角色一致性三件套**（K2 批次已验证对策，MemPalace pitfall_c848e543）：
  1. 族系特征跨镜头锁定写死（发色/结饰/磷光/衣制），有标杆图的角色把特征逐条抄进 prompt；
  2. 手部条款：「五指并拢可读」+ 拱手/摊手等单手势，禁复杂手势；
  3. 物件-场景空间关系显式声明（「鱼在网内」不是「鱼和网」）。
- 风格锚：皮影柔情国风（决策110）= 皮影部件工艺×剪纸东方×唱诗班表演×重彩志怪；
  透光=背光透射（灯在幕布后，暖色/平面/色块/镂空透亮），**禁发光体语义**
  （glowing/neon/rim light/体积光）；参考 SB v3.1 图集。
- 关键帧必须过 vision 审（构图/族系/手部/穿帮），审不过改 prompt 重出，不带病进视频。
  程序化指标（剪影IoU类）对「角色+场景同框」不敏感，选型一律以 vision 为准（pitfall_b8199270）。

## ④ 视频提示词成型（Wan3.0 官方公式）

完整公式与语法规则见 references/wan3-prompt-formula.md（官方指南核验 2026-11-17）。骨架：

```
提示词 = [总体描述(题材+风格+情绪+节奏)]
       + [参考素材引用：图N/视频N/音频N（按上传顺序，图/视频/音频分别计数）]
       + [分镜N（起-止秒）：主体+场景+运动+美学控制]   ← 单镜头写「生成单镜头」
       + [台词：角色说："逐字原文"]                    ← 无台词显式写「无台词」
       + [音效/BGM]                                    ← 环境音靠画面动作材质自动匹配
       + [风格/情绪]
       + [负向清单]
```

- i2v（首帧驱动）主用法：首帧图承载构图/角色/风格，prompt 只写**运动与声音**
  （13 记号翻译：[缓推]→「镜头缓慢推近」；[驻留Ns]→「画面驻留N秒，主体近乎静止，仅呼吸级微动」；
  [色变:A→B,N秒]→「色调在N秒内从A缓慢渐变为B」；[环境渐弱→静]→「环境声渐弱至静默」）。
- 台词语法：`她低语道："……"`；旁白 `画外音："……"`；音色克隆 `音色参考音频N`；
  口型对齐追加 `口型同步`。**首试产选无台词镜头**（口型/配音是额外风险层）。
- BGM 三档：不写=模型自选；指定=「BGM转入低音区，大提琴极轻缓缓加入」；不要=「无bgm，只生成环境音和动作音」。
  guimei 默认保守：环境音为主，超度/点题时刻才进「一声磬」类指定音效（11 声音词典）。
- 负向清单标准项（guimei 漫剧）：无字幕水印、无现代元素、不要写实真人风、不要低幼卡通、
  不要人脸变形、不要多余手指、不要肢体扭曲、不要穿模、不要夸张运镜、不要频繁切镜。
  只写不想要的，不凑数，不重复正向内容。
- **参数分离**：resolution/ratio/duration/audio/seed 写进参数单，不写进 prompt 正文
  （用户原文自带的时间戳属创作内容，保留）。
- prompt_extend=false（精细分镜保意图；官方智能改写只对简短宽泛 prompt 有益）。
- 可选五段式：把成型 prompt 按 wan3-pe【核心任务】【情节概要】【音频风格】【运镜与核心约束】
  【负面提示词】重组（references/wan3-pe-format.md），用于多素材复杂请求；单镜头直写公式即可。

## ⑤ 试产（wuhoo-video-generation 技能）

```bash
S=~/wuhoo-workspace/skills/shared/wuhoo-video-generation/gen_video.py
python3.11 $S --prompt "<④成型提示词>" --image <关键帧.jpg> \
  --resolution 720P --duration 5 --ratio adaptive --no-prompt-extend \
  --output <归档目录>/shot-NN.mp4
```

- 首试产 5s/720P 验证方向，过了再上 1080P/更长时长（计价见视频技能）。
- 竖屏：首帧竖构图 + ratio adaptive（API 参考 ratio 表无 9:16，使用指南有——以 adaptive+竖首帧为稳妥正解）。
- 模型默认 wan3.0-video-prime，**cn-beijing 实测可调**（11-17 首试产 task 26c944d4，
  catalog 未列但提交成功，≈1.5min 出片）；被拒时自动回退 wan3.0-video（能力对齐，只是慢）。
- 竖屏实证：adaptive+竖构图首帧 → 输出自动 9:16，无需硬传 9:16。
- 长任务纪律：--submit-only 拿 task_id，有界等待续查；24h 内必须下载归档。
- 每镜头 3-5 次 prompt 迭代预算（29 生产纪律）；超预算停下复盘，不无限烧。

## ⑥ 双闸验收（ai-2d-rig-pipeline 方法论回收）

1. 指标闸：sidecar JSON（usage.duration/fps/SR/ratio）+ 抽帧帧差（动了吗/循环/断裂带）；
   工具可回收 guimei 仓 tools/frame_diff.py、frame_profile.py。
2. vision 装配闸：抽关键帧（首/中/尾+运动峰值帧）逐帧 vision 复核——
   角色族系一致？手部可读？穿帮？透光语义对（背光透射非发光体）？构图守住？
   **worker/模型自报视觉结论不可信，必须独立 vision 审**。
3. 帧差全 PASS ≠ 装配对；两闸都过才算镜头完成。

## ⑦ 归档（guimei 仓）

```
games/guimei/manju/<YYYY-MM-DD>-<章节 slug>/
├── episode-plan.md        # 立项单
├── storyboard.md          # 分镜脚本表(②)
├── shots/shot-NN.md       # 每镜头: 关键帧prompt+视频prompt+参数单+迭代记录
├── keyframes/             # 关键帧图(LFS)
├── videos/                # 成片mp4+sidecar json(LFS)
└── report.md              # 验收数值+vision结论+泛化摩擦清单
```

commit 信息带镜头号与验收结论；大文件走 LFS；双 remote（codeup+origin）都推。

## Pitfalls

- **跳层必翻车**：不钉关键帧直接 t2v 长叙事 → 角色换脸/构图漂移。分层是业界共识不是可选。
- **台词风险分层**：口型同步+音色克隆是进阶能力，首试产用无台词镜头；有台词镜头单独迭代。
- **高动态镜头后置**：超度金白爆亮过曝（C档1）、色变大幅渐变属高风险演出，
  先用静态微动镜头（模式1等待的静止）验证管线，再上强度。
- **ratio 9:16 文档冲突**：API 参考列 adaptive/21:9/16:9/4:3/1:1，使用指南另列 3:4/9:16；
  竖屏统一走 adaptive+竖构图首帧，不硬传 9:16 赌运气。
- **禁词穿帮**：台词照录 GDD 已过 lint 的原文；自己新写台词必跑 08 禁词检查
  （掌柜/姑娘/谢谢/怎么/为什么/已经…25+禁词；语气词用么/罢/耶/喏/唔）。
- **项目名只写 guimei**：禁止自造中文名（用户铁律）；GDD 原文里的注释性别称不改不传。
- **发光体语义污染**：wan 系模型爱把「透光」画成 neon/rim light；prompt 必须写
  「背光透射、暖色平面色块、镂空透亮」并在负向清单禁发光体。
- **旁白抢戏**：漫剧改编时旁白是吴守桥的「看见」，不是解说员；每场景≤3句，删对白留画面优先。
- **vision 工具间歇路由错误**（11-17 实测）：hermes vision_analyze 偶发报
  "supported API model names are deepseek-flash, deepseek-v4-pro, but you passed qwen4-max"
  （aux vision 被路由到 deepseek-only 端点）。对策：图先转 JPEG q85-92 小图再送审
  （成功率高）；兜底=token-plan compatible-mode chat/completions 直调 qwen3.8-max
  （input:[text,image]）。大 PNG base64 直传（>2MB payload）会 WriteTimeout，一律先转 JPEG。
- **t2i 布局硬约束服从度低**（11-17 三连败实证）：孤悬构图比例/物件破损细节/水墨消散/
  皮影接缝类约束，wan2.7 三轮迭代仍难达标，且可能姿态回归（坐→站）。有母图走母图裁切，
  无母图把布局约束当「尽力项」，验收以角色锁定+无穿帮为硬闸，场景级方向留人工修图/r2v 迭代。

## References

- references/wan3-prompt-formula.md — 官方完整公式/时间戳/台词/音效/BGM/负向清单语法（出处+核验日期）
- references/wan3-pe-format.md — 官方 wan3-pe 五段式请求结构与忠实性硬约束（wan3-pe.zip v0.2.0 摘录）
- references/guimei-cinematic-mapping.md — 13记号→提示词映射表/风格锚/对白旁白纪律速查
- references/industry-research.md — 业界漫剧与AI视频提示词案例/格式调研（出处列表）
- templates/episode-storyboard.md — 立项单+分镜表模板
- templates/shot-prompt.md — 单镜头提示词脚本模板（关键帧+视频+参数单）