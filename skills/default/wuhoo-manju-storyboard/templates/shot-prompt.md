# 单镜头提示词脚本模板（shots/shot-NN.md）

> 一份 = 关键帧生图提示词 + 视频提示词 + 参数单 + 迭代记录。
> 视频提示词按官方公式（references/wan3-prompt-formula.md）；参数不进正文。

```markdown
# 镜NN：<镜头名>（源 S<N>）

## 0. 分镜行（照抄 storyboard.md）
景别/运镜/时长/画面/色彩/声音/台词/转场/13记号

## 1. 关键帧生图提示词（首帧，竖构图1152x2048或横构图2048x1152）
<主体具体描述(族系特征锁定句逐条) + 场景空间关系显式 + 构图(孤悬/占比)
+ 光影(背光透射/暖色平面色块/镂空透亮，禁发光体) + 风格(皮影柔情国风/重彩志怪)
+ 手部条款(五指并拢可读+单手势) + 负向(无现代元素/无文字水印/不要写实真人风)>

生图命令:
python3.11 ~/.hermes/skills/image-generation/gen_image.py --prompt "<上文>" ...

vision 审记录:
- 第1版: <构图/族系/手部/穿帮结论> → PASS/改prompt重出
- 定稿: keyframes/shot-NN-kf.jpg（sha256: <…>）

## 2. 视频提示词（Wan3.0，i2v 首帧驱动）
生成单镜头。
<总体描述：题材+风格+情绪+节奏，一句话>
<运动描述：13记号翻译——运镜大白话+主体动作(简单/缓慢/呼吸级)+时长内的变化(色变N秒渐变)>
<台词：无台词 / 她低语道："逐字原文" / 画外音："逐字原文">
<音效：环境音写清材质动作；指定音效单独成句(一声磬，清越短促)>
<BGM：无bgm，只生成环境音和动作音 / 明确指定句>
<风格情绪：皮影戏美学，重彩志怪国风，背光透射暖色平面色块，克制含蓄>
负向清单：无字幕水印，无现代元素，不要写实真人风，不要低幼卡通，不要人脸变形，
不要多余手指，不要肢体扭曲，不要穿模，不要夸张运镜，不要发光体霓虹描边光。

## 3. 参数单（不进 prompt 正文）
model: wan3.0-video-prime（不可用自动回退 wan3.0-video）
image: keyframes/shot-NN-kf.jpg
resolution: 720P | ratio: adaptive | duration: 5 | audio: true
prompt_extend: false | watermark: false | seed: <随机/记录>
预算: 本镜 ≤<N> 次迭代

试产命令:
python3.11 ~/wuhoo-workspace/skills/shared/wuhoo-video-generation/gen_video.py \
  --prompt "<§2正文>" --image keyframes/shot-NN-kf.jpg \
  --resolution 720P --duration 5 --ratio adaptive --no-prompt-extend \
  --output videos/shot-NN.mp4

## 4. 验收（双闸）
指标闸: sidecar usage duration=<…> fps=30 SR=<…> ratio=<…>；帧差<工具+数值>
vision闸: 抽帧(首/中/尾/峰值)逐帧审——族系一致?手部?穿帮?透光语义?构图?
结论: PASS / FAIL(<根因>) → 迭代记录

## 5. 迭代记录
| 版 | 改动 | 结果 | 花费 |
|---|---|---|---|
| v1 | 初版 | <FAIL: 根因> | <credits等值> |
| v2 | <对策> | <PASS> | |
```