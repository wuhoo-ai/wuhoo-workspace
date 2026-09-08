---
name: wuhoo-art-pipeline
description: guimei 皮影角色整图生产管线(决策122: 整身母版插画+头层→表演参数→Unity整图表演器; 部件/切块路线已废止)。Use when 生产皮影角色资产/表演参数/动画。
---

# wuhoo-art-pipeline — 皮影资产生产管线 SOP

> 2026-08-26 定稿(全链路实测)。目标: 输出可预期。
> 参考: review/2026-08-26-gpu-pipeline-verify/five-questions.md(5问落盘)
>
> **2026-09-03 路线升级(决策117-121)**: 主路线改为 B'——A-pose 整身定妆图 → 程序化切 10–14 主身大块 + 5–8 覆盖层 → 铰链骨骼锚点配对。旧 52 件/双图路线冻结。
>
> 2026-09-08 B' 试点：A-pose 切 10 块 + 合成 idle 复合帧画像 PASS；出图需强化双臂/双腿与躯干分离，Unity adapter 待接。
>
> **2026-09-08 决策122(现行 SOP)**: 皮影生产方式转整图表演——放弃分件/切块/铰链; 资产=整身母版插画+头层+表演参数JSON(分层底线b); "动"全部交给 Unity 整图表演器(四层运动语言: 顿挫/停息/延迟链/噪声)。B' 主线与历史 52 件路线均冻结/废止, 仅留档。

## 整图表演主线(2026-09-08 决策122 起)

```
已有/云端出图: 整身母版插画(皮影风: 剪纸刻痕/镂空纹样/透光画法/深色描边)
  → 质量门: 风格/姿态/构图(不再是切块完整性)
  → 头层: 同图裁出头部(允许 AI 蒙版粗分, 不追求独立件完美)
  → 表演参数标定: puppet.json performance(格式 docs/guimei-puppet-format-v0.2.md)
Unity(batchmode):
  整图表演器: root整体晃动/head头层点头摇头/呼吸区三通道 + 四层运动语言
  → 渲 1 帧试看(视觉闸1) → 渲 5 秒短视频(视觉闸2, 用户裁决) → 24帧 frame_diff 验收
```

- 母版起点(决策122 拍板④): 先用已有验收图做 1 张验证(B' 试点源图), 不新出图; 其余等验证可行+token 额度恢复。
- 姿态卡: 大幅姿态(坐/倒/睡/特殊动作)另出插画+整卡快切; S级8-15张/普通3-5张。
- 透光: Unity shader(呼吸式透光+URP 2D Light联动, 决策122 拍板③)。

## B' 主线〔2026-09-08 废止, 历史留档〕(2026-09-03 起)

```
云端: qwen-image-3.0-pro
  ① 1 张 A-pose 整身定妆图(双臂分离/透明或纯色底/禁杂物)
GPU(4070Ti, C:\ai\guimei-prod\):
  ② rembg(u2net, CUDA) 抠图
  ③ 沿铰链线切 10-14 主身大块 + 5-8 覆盖层
  ④ 质量门: 大块数/垂直度/接缝遮挡(asset_check.py)
  ⑤ AI 锚点标定 → anchors/<role>.json(用户终审)
Unity(batchmode):
  ⑥ RigBuilderWSQV2.BuildAndCapture: 铰链树 + 锚点配对 + idle 1帧试看 → 24帧验收
```

## 管线总览（历史 52 件/双图路线，已废弃留档）

```
云端: qwen-image-3.0-pro
  ① 部件库图(prompt v2: 基础件单件+多形态手脚, 镜像复用) 2048²
  ② 站立参考图(同角色同风格, 关节清晰) 1024×2048
传输: frp 隧道禁大文件 -> GitHub release relay(guimei-transfer repo, gh-proxy 3.1MB/s)
GPU(4070Ti, C:\ai\guimei-prod\):
  ③ rembg(u2net, onnxruntime-gpu CUDA) 抠图 -> 透明PNG
  ④ 连通域切分(闭运算核15px, min 3000px) -> parts/part_NN.png + parts.txt
  ⑤ YOLOv8n-pose(CUDA) 参考图关节检测 -> pose.txt(17点)
Unity(batchmode -executeMethod):
  ⑥ RigBuilder.BuildAndCapture: 骨骼(关节坐标) + 部件挂载(语义映射+段长缩放+旋转对齐) + idle 24帧渲染
```

## 关键文件

- 云端出图: /tmp/guimei-prod/gen_v2.py(qwen prompt v2)
- GPU 处理: C:\ai\guimei-prod\pipeline.py(rembg+连通域) / build_grid.py(连接孔检测)
- Unity: Assets/Editor/RigBuilder.cs(仓库 tools/art_pipeline/RigBuilder.cs)
- 权重: C:\ai\u2net.onnx + C:\ai\yolov8n-pose.pt(relay 预置)

## 执行步骤

1. 云端生成(gen_v2.py, ~3分钟/张): 部件库 + 参考图, vision 检查(部件隔离/连接孔/关节清晰)
2. relay 传 GPU: gh release vN -> GPU curl gh-proxy 下载
3. GPU 跑 pipeline.py: schtasks /run /tn wuhoo_pipe(输出 parts.txt/pose.txt)
4. parts 复制进 Unity Assets/Art/test-rig/parts/
5. batchmode: RigBuilder.BuildAndCapture(先杀 Unity 实例, 避免 Library 锁)
6. GPU 合成 GIF(make_gif.py), 拉回验证(vision 检查拼装/关节)
7. 证据落盘: review/YYYY-MM-DD-xxx/(preview/*.jpg 走普通git!PNG/GIF走LFS)

## 坑(全部实测)

- Unity 首次启动: 先 batchmode 建 Library, 否则 GUI 卡 Rebuilding Library(35MB僵尸)
- batchmode 与 GUI 互锁: 项目被锁则 return code 1, 必须先 taskkill
- Unity 新 PNG 资产: textureType 设 Sprite 后 LoadAssetAtPath<Sprite> 仍可能 null -> 用 LoadAssetAtPath<Texture2D> + Sprite.Create(运行时)
- frp scp 大文件必断: <1MB 才直传, 其余 relay
- schtasks 重定向 >log 不生效: 用 schtasks /tr 内嵌 cmd /c 或写日志到文件
- 证据图预览: 必须 review/**/preview/*.jpg(普通git), 根目录 jpg 也走 LFS 网页不可见; git mv 保留 LFS 指针blob -> rm --cached + add 重入库
- 部件语义映射(part_NN -> 骨骼): 需人工确认一次固化(部件图与参考图比例体系不同, 段长缩放只对齐高度)

## 验证清单

- [ ] 部件图: 无成对重复件/白底隔离/连接孔可见(vision)
- [ ] 参考图: 关节清晰/完整不裁切(vision)
- [ ] pose_annotated.jpg: 关节落在黑色转轴盘上(vision)
- [ ] 拼装渲染: 头/躯干/四肢层级正确, 无悬浮
- [ ] scale 系数: 段长/部件高 比值合理(0.2-1.2)
