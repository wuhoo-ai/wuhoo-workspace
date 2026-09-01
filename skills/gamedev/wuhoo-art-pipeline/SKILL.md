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

## 直切算法 v3(direct_cut3.py, 2026-08-27 全实测)

参考图要求: 裤子+双腿分开+裙摆同图竖放右侧+头巾短帽不遮脸无飘带(gen_v31.py prompt)。

1. **墨线floodFill抠图**: dark=gray<130为墙, 从边界floodFill扩散=外部背景;
   人物内部浅色(米白脸/浅纹样)被墨线包围自动保留。阈值法(45/25)浅色脸必碎。
2. **颈切割=肩弧椭圆**: 头部=头+帽+脸+脖整体(不拆帽!), 底部沿椭圆下半弧
   (cv2.ellipse center=neck, axes=(肩宽*0.55, 颈长), 0°,180°——注意OpenCV y向下,
   0-180°才是下半弧, 180-360°是上半弧会切错), 躯干顶=匹配肩窝。
   摇头时弧线在肩窝铰接不裂开(水平横切摇头必裂, 禁用)。
3. **圆头颜色=最近非白前景外扩**: distance_transform_edt到rgb.min<200的前景,
   取索引颜色。取img[add]是白底(全白圆片); 取任意前景会带边缘白毛刺。
   圆头区白色从100%→17%→1-5%。
4. **肩部**: 圆切割r=45挖关节圆盘 + 臂内侧分割线(沿臂长测外侧半宽,
   臂内侧表面画分割线; 圆内r_out=0用最近有效值外推; 有间隙无副作用, 连体强制分离)。
5. **肘**: 切线有效。**髋**: 切线hip+20px沿大腿方向 + 髋圆切割r=40。
6. **膝**: 膝部洞膨胀(环形圆盘中心被flood挖成洞+残留桥, 洞dilate 9x9吃掉桥)。
   膝切线/圆切割均失败; 洞膨胀一次解决大腿/小腿+左右腿分离。
7. **裤裆竖线**: 切min(top)到max(bot)全范围(x=hip中点, 起点在髋切线上方)。
   只切最长段会漏髋切线残留小桥。
8. **seg_mid命中**: torso的seg_mid避开竖线和髋切线(+12,-30偏移); 竖线会切掉hip中点。
9. A圆头(∪1.35r)补回圆切割挖掉的关节盘; 皮影关节重叠天然成立。

## RigBuilder v12(层级骨骼)

- 骨骼层级: hip>hip_l>knee_l>ankle_l, shoulder>elbow>wrist(大腿转带动小腿)
- 读 ref_meta2.json(正则解析!手写JSONReader对json.dump indent=1多行格式有bug)
- 裙摆挂hip: 顶部中心x对齐hip中点(人物中心, 不能对齐l_hip——人物偏侧会飘), 不能按部件中心
- 裙摆双层: skirt_b(后片sort 5, 腿后, 摆幅1.5°)/skirt_f(前片sort 8, 腿前, 摆幅3.5°相位错开),
  独立骨骼skirt_b_bone/skirt_f_bone, 同读skirt.png(metaName映射), 前片y-0.12
- idle: head±5°/headwear±7°(幅度太小vision看不出)/hip_l±2.5°交替/knee±1.5°/skirt±2°
- NPOT坑同v11: npotScale=None + maxTextureSize=4096
- 验证: 帧差程序化检测(头部区>1.0即动画生效), vision对压缩图会误判"静止"

## 非人形/手工关节标注(P0-2, 2026-08-27)

- 场景: 鬼怪/动物/器物角色——YOLO COCO 17点只覆盖人体
- 流程: 出图→annotate_helper.py生成标注工作图(13点编号圆点) →
  vision/人工估计关节坐标 → 编辑 pose_manual.json ({"l_shoulder": [x,y], ...}) →
  direct_cut3.py 自动优先读 pose_manual.json(YOLO pose.txt 兜底), 切分算法零改动
- 13点集 = direct_cut3 实际使用: nose/肩/肘/腕/髋/膝/踝(左右)
- 半自动路径: GPU跑YOLO出pose.txt→转pose_manual.json→标注图核对→微调, 人形角色可跳过标注

## 坑(全部实测)

- Unity 首次启动: 先 batchmode 建 Library, 否则 GUI 卡 Rebuilding Library(35MB僵尸)
- batchmode 与 GUI 互锁: 项目被锁则 return code 1, 必须先 taskkill
- Unity 新 PNG 资产: textureType 设 Sprite 后 LoadAssetAtPath<Sprite> 仍可能 null -> 用 LoadAssetAtPath<Texture2D> + Sprite.Create(运行时)
- frp scp 大文件必断: 389KB都失败(22B成功) -> 一律 GitHub release relay:
  重建 wuhoo-ai/guimei-transfer 公开repo(gh api contents 建 README 绕过 git push 认证),
  参考图转 q90 jpg(白底RGB无需alpha, ~390KB), GPU curl ghfast.top 下载(427KB/s), 用完删repo
- schtasks 重定向 >log 不生效: 用 schtasks /tr 内嵌 cmd /c 或写日志到文件
- 证据图预览: 必须 review/**/preview/*.jpg(普通git), 根目录 jpg 也走 LFS 网页不可见; git mv 保留 LFS 指针blob -> rm --cached + add 重入库
- make_gif.py 旧版硬编码 anim/ 目录+idle.gif, 参数被忽略(误用旧帧合成) -> 新版支持 [帧目录] [输出]; 合成前确认帧目录
- GIF交付: GPU直接git提交Codeup LFS(idle_v12.gif 4.1MB, GPU仓库有Codeup认证), 网页可见预览, 无需绕云端
- 部件语义映射(part_NN -> 骨骼): 需人工确认一次固化(部件图与参考图比例体系不同, 段长缩放只对齐高度)

## 验证清单

- [ ] 部件图: 无成对重复件/白底隔离/连接孔可见(vision)
- [ ] 参考图: 关节清晰/完整不裁切(vision)
- [ ] pose_annotated.jpg: 关节落在黑色转轴盘上(vision)
- [ ] 拼装渲染: 头/躯干/四肢层级正确, 无悬浮
- [ ] scale 系数: 段长/部件高 比值合理(0.2-1.2)
