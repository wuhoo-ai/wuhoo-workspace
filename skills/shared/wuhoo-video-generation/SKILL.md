---
name: wuhoo-video-generation
description: "Use when 生成视频(漫剧/分镜/宣传片/过场). Wan3.0-Video(-Prime) via Token Plan DashScope API: t2v/首帧/首尾帧/全模态参考, 2-30s, 原生音频."
version: 2.0.0
category: shared
tags: ["wuhoo"]
dependencies: "python3.11, httpx, pyyaml, pillow"
---

# Video Generation (Wan3.0-Video / Wan3.0-Video-Prime)

通过 Token Plan 的 DashScope 原生异步接口生成视频。万相3.0 是 All-in-One 全能参考模型：
文生视频、图生视频（首帧/首尾帧）、参考生视频（图/视频/音频自由组合）、文件/网页生视频、
视频编辑与延长，统一一个模型 id，按 `input.media` 的 type 与提示词意图自动路由。

- 最长 30 秒，输出 30fps，MP4 (H.264)
- 原生音频：`audio=true` 默认开（含声音），开关同价
- 模型：`wan3.0-video-prime`（高速版，能力对齐标准版）/ `wan3.0-video`（标准版）

## Trigger

用户要求生成视频（漫剧分镜试产、故事视频、游戏宣传片、过场、动态立绘等），
或需要把静态关键帧变成动态镜头时激活。分镜提示词脚本的编写见姊妹技能
`~/wuhoo-workspace/skills/default/wuhoo-manju-storyboard`（GDD 故事线 → 分镜脚本）。

## 可用性事实（2026-11-17 实测，含当日试产修正）

- Token Plan cn-beijing（`token-plan.cn-beijing.maas.aliyuncs.com`）实时 catalog（23模型）含
  `wan3.0-video`（2026-10-10 产品动态公告上架），**未列 `wan3.0-video-prime`**。
- **但 prime 实际可调**：11-17 试产以 model=wan3.0-video-prime 直接提交 DashScope 原生端点
  成功出片（task 26c944d4-7b4c-4300-8c37-e4af1a0d8eac，5s/720P/9:16，≈1.5min，未触发回退）。
  catalog 列表滞后/不全，**模型可用性以实际提交为准**。
- 脚本默认 model=prime；若提交被拒（模型不可用类错误，未计费）自动回退标准版并打印提示，
  回退事件记录在 sidecar JSON。国际站 QwenCloud（新加坡等）prime 已公示上架（USD 计价）；
  模型/Endpoint/Key 必须同地域，cn-beijing key 不能调国际站。

## Usage

```bash
S=~/wuhoo-workspace/skills/shared/wuhoo-video-generation/gen_video.py

# 文生视频（t2v）
python3.11 $S --prompt "月下屋顶，一只猫奔跑，远处城市霓虹闪烁，电影质感，运镜流畅" \
  --resolution 720P --duration 5 --ratio 16:9

# 首帧驱动（i2v）：关键帧图 → 动态镜头（漫剧主用法）
python3.11 $S --prompt "镜头缓慢推近，人物衣摆随风轻摆，烛光摇曳" \
  --image /path/keyframe.jpg --resolution 1080P --duration 5

# 首尾帧：两张关键帧之间补间
python3.11 $S --prompt "人物从坐姿缓缓起身" \
  --image first.jpg --last-frame last.jpg --duration 4

# 参考生视频（r2v）：角色/场景参考图锁一致性，prompt 用"图1/图2"指代
python3.11 $S --prompt "图1中的角色站在图2的场景里，拱手行礼，镜头固定" \
  --ref-image character.png --ref-image scene.jpg --duration 5

# 参考音频驱动（口型/节奏）：reference_image + reference_audio 组合
python3.11 $S --prompt "图1角色按音频1的台词说话，口型同步" \
  --ref-image character.png --ref-audio line.mp3

# 长任务纪律：只提交拿 task_id，之后有界等待/独立进程续查
python3.11 $S --prompt "..." --image kf.jpg --submit-only
python3.11 $S --task-id <task_id> --output out.mp4   # 续查+下载（24h 内有效）
```

## Parameters

| 参数 | 默认 | 说明 |
|---|---|---|
| --prompt / -p | 必填(除 --task-id) | ≤20000 字符，中英文；参考模式用"图1/视频1/音频1"指代 media（按类型各自计数） |
| --model / -m | wan3.0-video-prime | 或 wan3.0-video；prime 不可用自动回退 |
| --image / -i | 无 | 首帧图（本地路径自动 base64；自动转 JPEG 压缩） |
| --last-frame | 无 | 尾帧图，与 --image 成对 |
| --ref-image | 无，可重复 | 参考图 ≤10 张 |
| --ref-video | 无，可重复 | 参考视频 ≤5 段，总时长 ≤15s |
| --ref-audio | 无，可重复 | 参考音频 ≤5 段，总时长 ≤15s |
| --file / --link | 无 | 文档/网页生视频（二选一；须公网 URL；prompt_extend 强制 true） |
| --resolution / -r | 720P | 480P / 720P / 1080P（API 默认 1080P，本脚本为成本默认 720P） |
| --ratio | adaptive | adaptive / 21:9 / 16:9 / 4:3 / 1:1（**无 9:16**，竖屏用 adaptive+竖构图首帧） |
| --duration / -d | 5 | [2,30] 整数；-1=智能时长；有视频输入时 输入+输出≤30s |
| --audio / --no-audio | audio=true | 原生音频开关，同价 |
| --prompt-extend / --no-prompt-extend | false | 智能改写。精细分镜提示词建议关（保意图）；file/link 模式强制 true |
| --watermark | false | 水印 |
| --seed | 随机 | [0,2147483647]；同 seed 不保证逐帧一致 |
| --output / -o | ~/.hermes/video_cache/wan3_<ts>.mp4 | 输出路径；同目录落 <name>.json sidecar（task_id/参数/usage/回退记录） |
| --max-wait | 1200 | 轮询上限秒数（15s 间隔）；30s 1080P 标准版可能 >5min |
| --submit-only | false | 只提交打印 task_id 即退出（长任务纪律） |
| --task-id | 无 | 跳过提交，续查已有任务并下载 |

## 素材组合铁律（客户端预检，违规不提交）

- t2v：仅 prompt，不带任何 media。
- first_frame/last_frame 与 reference_*/file/link **互斥**，不可混用。
- file 与 link 二选一；两者都可与 reference_image/video/audio 组合。
- reference_image/video/audio 之间自由组合。
- 首尾帧模式**不支持** driving_audio（wan2.7 的玩法）；要音频驱动改用
  reference_image + reference_audio 全模态参考模式。
- 视频编辑/延长：必含 reference_video + 提示词写明编辑/延长意图；延长须 ratio=adaptive。

## 输入素材限制

- 图像：JPEG/JPG/PNG(**不支持透明通道**)/BMP/WEBP；单边 [240,8000]px；长宽比 ≤8:1；≤20MB。
  脚本自动：RGBA→白底合成 RGB、超尺寸缩放、>4MB 或带 alpha 的 PNG→JPEG q85（防 WriteTimeout）。
- 视频：单边 [240,4096]px；单段 [1,15]s，总 ≤15s；≤100MB。
- 音频：单段 [1,15]s，总 ≤15s；≤15MB。
- 大视频/音频建议公网 URL 直传（本地 base64 体积膨胀 ~33%，写超时风险）。

## Pipeline: 故事线 → 分镜 → 关键帧 → 视频（漫剧主产线）

1. GDD 章节 → 分镜提示词脚本：`wuhoo-manju-storyboard` 技能。
2. 关键帧出图：`~/.hermes/skills/image-generation/gen_image.py`
   （wan2.7-image-pro / qwen-image-3.0-pro，竖屏 9:16 用 1152x2048 或同比例）。
   角色一致性：族系特征（发色/结饰/磷光等）跨镜头锁定写死在 prompt；
   手部写"五指并拢可读"+单手势；物件-场景空间关系显式声明（K2 批次已验证对策）。
3. 关键帧 → 镜头：本技能 i2v（首帧）或首尾帧；角色参考图锁脸用 r2v。
4. 镜头拼接：ffmpeg concat；配乐/台词混音另走音频管线。
5. 验收：sidecar JSON 数值 + vision 逐关键帧复核（双闸方法论，
   见 gamedev 域 ai-2d-rig-pipeline 技能 references；worker 自报视觉结论不可信）。

## API Details

- 提交：POST {base}/api/v1/services/aigc/video-generation/video-synthesis
  Headers：Authorization: Bearer TOKEN_PLAN_API_KEY（~/.hermes/.env）、
  Content-Type: application/json、**X-DashScope-Async: enable（必选，缺了报
  "current user api does not support synchronous calls"）**
- 查询：GET {base}/api/v1/tasks/{task_id}，建议 15s 间隔，查询 RPS 上限 20。
- 状态机：PENDING → RUNNING → SUCCEEDED / FAILED / CANCELED / UNKNOWN。
- task_id 与 video_url 均 **24h 有效**；成功后立即下载转存；**勿重复创建任务**。
- 成功响应：output.video_url + usage{video_count=1, duration, fps=30, SR, ratio}。
- base_url 发现：config.yaml 扫 token-plan（fallback_model/llm/auxiliary.vision/custom_providers），
  剥掉 /compatible-mode/v1 或 /v1 后缀得 DashScope 根；env TOKEN_PLAN_BASE_URL 可覆盖。
- 完整契约与出处：references/wan3-api-contract.md。

## 计价参考（预算用）

- QwenCloud 国际站 prime 公示价：480P $0.068/s、720P $0.14/s、1080P $0.28/s。
  5s 720P ≈ $0.70 等值；5s 1080P ≈ $1.40 等值。
- Token Plan cn-beijing 按套餐 Credits 计，audio 开关同价；duration 越长越贵，
  试产先用 5s/720P 验证方向再上强度。并发 10、异步队列 500、RPM 300（国际站公示）。

## Pitfalls

- **PNG 透明通道不支持**：首帧带 alpha 会被拒或出黑底；脚本自动白底合成（guimei 白底惯例）。
- **大 PNG base64 写超时**：4.2MB PNG→5.6MB base64 曾致 httpx.WriteTimeout；
  脚本 >4MB 自动转 JPEG q85，勿手工传大 PNG。
- **ratio 无 9:16/3:4**：竖屏漫剧用 adaptive + 竖构图首帧图驱动，不要硬传 9:16（报错）。
- **prompt_extend 会改写意图**：精细分镜脚本默认关；只有 file/link 模式强制 true。
- **同 seed 不逐帧确定**：复现靠 sidecar 记录参数+原片归档，不靠 seed 玄学。
- **模型可用性随区域/时间变，以实际提交为准**：prime 在 cn-beijing catalog 未列但实测可调
  （11-17 试产实证）；catalog 滞后不代表不可用。被拒时自动回退标准版，能力对齐只是慢，
  别把回退当失败。
- **24h 双有效期**：task_id 过期查不到（UNKNOWN），video_url 过期下载 404；
  提交后当天必须完成下载归档。
- **旧 happyhorse 已退役**：token-plan catalog 已无 happyhorse-*（11-17 实测 23 模型），
  旧 video-generation 技能（v1.x）的模型 choices 全部失效，以本技能为准。

## Error Handling

- 提交非 200：打印 HTTP 状态+响应体；prime 模型不可用类错误自动回退 wan3.0-video 重试一次。
- 任务 FAILED：打印 output.message；内容审核类失败改提示词，不要原样重试烧钱。
- 轮询超时：打印 task_id，用 --task-id 续查（勿重新提交）。
- 下载失败：3 次指数退避重试（此时 Credits 已花，绝不轻易放弃）。

## Changelog

- v2.0.0 (2026-11-17): Wan3.0-Video(-Prime) 全面重写。新增首尾帧/全模态参考/文件网页模式、
  原生音频、智能时长、submit-only/task-id 续查、sidecar JSON 留证、prime→标准版自动回退、
  图像自动预处理（alpha/尺寸/压缩）、素材组合客户端预检。移除 happyhorse（catalog 已退役）。
  修复 v1 get_config() env_vars 先用后定义的 NameError 隐患。
  依据：官方 API 参考 + Token Plan 产品动态 + cn-beijing 实时 catalog（references 有出处）。
- v1.x: HappyHorse t2v/i2v/r2v（已退役，归档于 ~/.hermes/skills/.archive/video-generation）。