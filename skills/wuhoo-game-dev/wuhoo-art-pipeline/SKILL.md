---
name: wuhoo-art-pipeline
description: guimei 皮影角色部件生产管线(云端qwen出图→GPU CUDA抠图/姿态检测→Unity拼装动画)。Use when 生产皮影角色部件/骨骼/动画。
---

# wuhoo-art-pipeline — 皮影资产生产管线 SOP

> 2026-08-26 定稿(全链路实测)。目标: 输出可预期。
> 参考: review/2026-08-26-gpu-pipeline-verify/five-questions.md(5问落盘)

## 管线总览

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
