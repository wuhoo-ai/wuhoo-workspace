# Wan3.0 视频生成 API 契约（2026-11-17 核验）

出处（当日抓取）：
- 官方 API 参考：https://help.aliyun.com/zh/model-studio/wan3-video-generation-api-reference
- 使用指南：https://help.aliyun.com/zh/model-studio/wan3-video-generation-guide
- Token Plan 产品动态：https://help.aliyun.com/zh/model-studio/token-plan-product-updates
- QwenCloud 模型页（国际站 prime 计价）：https://www.qwencloud.com/models/wan3.0-video-prime
- cn-beijing 实时 catalog：GET https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/models
  （23 模型，含 wan3.0-video，无 wan3.0-video-prime；快照 ~/.hermes/cache/scratch/tokenplan-models-live.json）

## 模型与地域

| model id | 定位 | Token Plan cn-beijing | 国际站 QwenCloud |
|---|---|---|---|
| wan3.0-video-prime | 高速版，能力对齐标准版，端到端显著更快 | **catalog 未列但实际可调**（11-17 试产实证，task 26c944d4，5s/720P≈1.5min 出片） | 已上架（SG 等地域） |
| wan3.0-video | 标准版 | 已上架（产品动态 2026-10-10 公告；catalog created=2026-10-13） | 已上架 |

铁律：模型、Endpoint URL、API Key 必须同地域，跨地域调用失败。
**模型可用性以实际提交为准——/compatible-mode/v1/models 列表滞后/不全（prime 实证）。**
Token Plan 产品动态相关条目：2026-10-10「新增万相视频模型：个人版和团队版模型表新增 wan3.0-video」。
ratio 争议：API 参考列 adaptive/21:9/16:9/4:3/1:1，使用指南另列 3:4/9:16；
11-17 实证 adaptive+竖构图首帧 → 输出自动 9:16，竖屏漫剧走此正解。

## 提交任务

POST https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis
（Token Plan 场景 {WorkspaceId} 段即 token-plan，base 从 config 发现）

Headers（全部必选）：
- Content-Type: application/json
- Authorization: Bearer <API_KEY>
- X-DashScope-Async: enable（缺失报 "current user api does not support synchronous calls"）

Body：
- model（必选）：wan3.0-video-prime | wan3.0-video
- input（必选）：prompt 与 media 必填其一
  - prompt：≤20000 字符（汉字/字母各计 1），超出自动截断；中英文。
    全能参考模式下用「图1」「视频1」「音频1」指代 media 中对应顺序素材；
    图/视频/音频分别各自计数（可同时有图1、视频1）。
  - media：[{type, url}]，type 见下表；url 支持公网 HTTP(S)、OSS 临时 URL
    （须走官方上传文件接口获取）、Base64 data URL。
- parameters（可选）：见下表。

### media type 与限额

| type | 数量上限 | 限额 |
|---|---|---|
| first_frame | 1 | 严格作为视频第一帧 |
| last_frame | 1 | 严格作为视频最后一帧 |
| reference_image | 10 | 图像规格见下 |
| reference_video | 5 | 单段 [1,15]s，总 ≤15s；单边 [240,4096]px；单文件 ≤100MB |
| reference_audio | 5 | 单段 [1,15]s，总 ≤15s；≤15MB |
| file | 1 | 文档，≤100MB；与 link 互斥；prompt_extend 必须 true |
| link | 1 | 网页 URL；与 file 互斥；prompt_extend 必须 true |

图像规格：JPEG/JPG/PNG（不支持透明通道）/BMP/WEBP；单边 [240,8000]px；长宽比 ≤8:1；≤20MB。

### 素材组合规则（官方「素材组合」节，违规报错）

- 文生视频：仅 prompt，不支持 media。
- first_frame/last_frame 与 reference_image/reference_video/reference_audio/file/link 互斥。
- file 和 link 二选一，但均可与 reference_* 组合。
- reference_image/reference_video/reference_audio 之间自由组合。
- 视频编辑：必含 reference_video，prompt 写编辑意图，可配 reference_image/audio。
- 视频延长：必含 reference_video，prompt 写延长意图，ratio 必须 adaptive。
- 首尾帧模式不支持 driving_audio（与 wan2.7 图生视频系列的区别）；
  音频驱动改用 reference_image + reference_audio 全模态参考。

### parameters

| 参数 | 类型 | 默认 | 取值/说明 |
|---|---|---|---|
| resolution | string | 1080P | 1080P / 720P / 480P |
| ratio | string | adaptive | adaptive / 21:9 / 16:9 / 4:3 / 1:1（无 9:16、3:4；竖屏用 adaptive+竖构图输入） |
| duration | integer | 5 | 无视频输入 [2,30]；有视频输入：输入总时长+输出 ≤30s；-1=智能时长（模型按 prompt/内容/富媒体自动推荐） |
| audio | boolean | true | 输出是否含声音；开关同价 |
| prompt_extend | boolean | （官方未明示默认，示例均传 true） | 智能改写；file/link 输入时必须 true |
| seed | integer | 随机 | -1 或 [0,2147483647]；同 seed 不保证逐帧一致 |
| watermark | boolean | false | 是否加水印 |

## 查询任务

GET https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/tasks/{task_id}
Header：Authorization: Bearer <API_KEY>

- 轮询建议 15s 间隔；查询接口默认 RPS 20；可配异步回调（官方 manage-asynchronous-tasks）。
- task_id 有效期 24h，过期返回 UNKNOWN。勿重复创建任务。
- 状态机：PENDING（排队）→ RUNNING（处理）→ SUCCEEDED / FAILED / CANCELED / UNKNOWN。
- 生成耗时通常 1-5 分钟（30s 高分辨率标准版可能更长；prime 显著更快）。

成功响应要点：
- output.task_id / task_status / submit_time / scheduled_time / end_time / orig_prompt
- output.video_url：MP4（H.264），**24h 有效，立即下载转存**
- usage：video_count=1、duration（有参考视频时=输入+输出之和）、input_video_duration、
  output_video_duration、fps=30、SR（如 720）、ratio（如 16:9）
- request_id：溯源排查用

失败响应：code + message（错误码表 https://help.aliyun.com/zh/model-studio/error-code）。

## 计价与限流（国际站 prime 公示，2026-11-17）

- 480P $0.068/s；720P $0.14/s；1080P $0.28/s（audio 开关同价）
- 并发 10；异步队列 500 任务；RPM 300
- Token Plan cn-beijing 按套餐 Credits 计（个人版/团队版模型表含 wan3.0-video）；
  2026-11-09 产品动态：个人版四档套餐额度上调、Pro 套餐降价。

## 与旧 HappyHorse 的差异（迁移注意）

- happyhorse-1.1-t2v/i2v/r2v 已从 token-plan catalog 消失（11-17 实测），旧技能失效。
- wan3.0 统一模型 id 自动路由，不再按模式换模型名。
- 帧率 24→30；时长上限 15→30s；新增原生音频/首尾帧/文件网页/视频编辑延长。
- i2v 的 media type 仍叫 first_frame，base64 data URL 用法不变。