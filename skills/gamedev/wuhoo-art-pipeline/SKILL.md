---
name: wuhoo-art-pipeline
description: guimei 皮影角色部件生产管线(云端qwen出图→GPU CUDA抠图/姿态检测→Unity拼装动画)。Use when 生产皮影角色部件/骨骼/动画。
---

# wuhoo-art-pipeline — 皮影资产生产管线 SOP

> 2026-09-01 修订(盘点卡 t_e592af46, 用户反馈驱动)。目标: 执行者只走已验证路线。
> ⚠️ **主 SOP = 「参考图直切 v3 + 锚点配对制」**(下文 §1-§5)。
> 开头旧版"双图管线总览"已废弃并下沉到文末附录, 禁止按附录执行。

## 当前管线状态(2026-09-01 用户反馈, 生产边界)

- ✅ 出图层达标: 风格圣经 v3.1 约 85 分, qwen3.0-image-pro 部件图细节到位
- ❌ 下游未及格: 锚点标定/拼装/空闲·战斗·对话动画设计——**本管线当前瓶颈在拼装与动画, 不在出图**
- 拼装定位/审美对位靠代码模板只能给初值, **用户手动精调是正式工序**(见 §4, 已验证先例: 吴守桥 7 处调整=标准挂法)
- 门禁唯一入口: `tools/asset_check.py`(G1 元数据 + --quality-gate 部件质量门, 2026-09-01 合一); 动画验收必跑 `tools/frame_diff.py` 帧差断言

## §1 主 SOP 总览(唯一现行路线)

```
云端: qwen-image-3.0-pro
  ① 部件网格图出图(单图多件, 竖直/白底/间隔/连接孔, prompt见gen_wsq_batch.py模板)
     ——部件图=最终部件来源(抠图提取), 不再另出"参考图"
传输: frp 隧道禁大文件 -> GitHub release relay(guimei-transfer repo, gh-proxy 3.1MB/s)
GPU(4070Ti, C:\ai\guimei-prod\):
  ② rembg/墨线floodFill 抠图 -> 透明PNG
  ③ 门禁唯一入口: asset_check.py --quality-gate(连通域件数/垂直度/连接孔)
     ——直切形态(整图切分)另走 direct_cut3.py(见 §2)
  ④ 提取单件 + 连接孔中心标定(锚点)
Unity:
  ⑤ 锚点配对拼装(连接表+BFS位置传播+旋转支点=锚点对)
  ⑥ 用户手动精调(正式工序) -> 帧差断言+vision -> 及格判定
```

## §2 直切算法 v3(direct_cut3.py, 2026-08-27 全实测)

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

适用边界(盘点卡 §3.1): 直切 v3 = "标准皮影站立姿势"专用算法。贴体臂/坐姿/长飘带/非人形均退化到人工; 每个新角色首图先对照边界表。

## §3 锚点配对制(决策116, 2026-08-30 首验通过)

- **多锚点专用不混配**: 躯干 6 / 头茬 2 / 四肢 2 锚点, 各部位锚点专用
- **拼装 = 锚点配对**: 连接表(child.锚点对齐parent.锚点) + BFS 位置传播 + 旋转支点=锚点对
- **pivot 归一化须 y 翻转**(图像坐标 y 向下 → Unity 纹理 y 向上)
- **资产 Sprite 化**: pivot 写入 TextureImporter 导入设置(场景保存后引用持久化); Sprite.Create 运行时对象保存场景引用丢失, 禁用
- **AI 语义标定已知失败模式**: 距离变换"最内部点"偏向宽区(下巴/脸)——颈部锚点用底部质心法(y>85%脖子区域); 每个锚点仍需人工终审
- **拼装场景须资产 Sprite**(Sprite.Create 不持久化), Refresh 循环调用卡编辑器; batchmode 重跑前须用户关 Unity(开着锁项目)
- 旧 adjust 救火文件叠加锚点制会拼装错乱——锚点制下 adjust 清空

## §4 用户手动精调 = 正式工序(2026-09-01 制度化)

拼装初值 → 用户手动审美精调 → 及格判定。**精调不是失败, 是管线环节**。
- 已验证先例: 吴守桥 7 处手动调整 = 标准挂法(永久生效), 落盘
  review/2026-08-30-anchor-pairing/final/wsq_adjust_user_manual.json
- 精调内容: localPosition 偏移/sortingOrder 图层/骨骼初始 rotation/摆动幅度相位
- 证据落盘规范: review/日期-主题/ + preview/*.jpg 走普通 git + PNG/GIF 走 LFS + commit
- 动画验收必须带帧差程序化断言: `tools/frame_diff.py <gif或帧目录>`(防 vision 误判静止图)

## §5 非人形/手工关节标注(P0-2, 2026-08-27)

- 场景: 鬼怪/动物/器物角色——YOLO COCO 17点只覆盖人体
- 流程: 出图→annotate_helper.py生成标注工作图(13点编号圆点) →
  vision/人工估计关节坐标 → 编辑 pose_manual.json ({"l_shoulder": [x,y], ...}) →
  direct_cut3.py 自动优先读 pose_manual.json(YOLO pose.txt 兜底), 切分算法零改动
- 13点集 = direct_cut3 实际使用: nose/肩/肘/腕/髋/膝/踝(左右)
- 半自动路径: GPU跑YOLO出pose.txt→转pose_manual.json→标注图核对→微调, 人形角色可跳过标注

## 关键文件

- 出图模板: review/2026-08-29-wsq-first-rig/scripts/gen_wsq_batch.py(qwen prompt+质量门调用)
- 直切: review/2026-08-27-pants-skirt/direct_cut3.py(GPU C:\ai\guimei-prod 有部署)
- 锚点标定: review/2026-08-30-anchor-pairing/assets/anchor_ai.py
- 拼装: review/2026-08-30-anchor-pairing/assets/RigBuilder_wsq.cs(资产Sprite版)
- 门禁唯一入口: tools/asset_check.py | 帧差断言: tools/frame_diff.py
- 权重: C:\ai\u2net.onnx + C:\ai\yolov8n-pose.pt(relay 预置)

## 坑(全部实测)

- Unity 首次启动: 先 batchmode 建 Library, 否则 GUI 卡 Rebuilding Library(35MB僵尸)
- batchmode 与 GUI 互锁: 项目被锁则 return code 1, 必须先 taskkill(或用户关 Unity)
- Unity 新 PNG 资产: textureType 设 Sprite 后 LoadAssetAtPath<Sprite> 仍可能 null -> 资产 Sprite 化(pivot 入导入设置)
- frp scp 大文件必断: 389KB都失败(22B成功) -> 一律 GitHub release relay:
  重建 wuhoo-ai/guimei-transfer 公开repo(gh api contents 建 README 绕过 git push 认证),
  参考图转 q90 jpg(白底RGB无需alpha, ~390KB), GPU curl ghfast.top 下载(427KB/s), 用完删repo
- schtasks 重定向 >log 不生效: 用 schtasks /tr 内嵌 cmd /c 或写日志到文件
- 证据图预览: 必须 review/**/preview/*.jpg(普通git), 根目录 jpg 也走 LFS 网页不可见; git mv 保留 LFS 指针blob -> rm --cached + add 重入库
- make_gif.py 旧版硬编码 anim/ 目录+idle.gif, 参数被忽略(误用旧帧合成) -> 新版支持 [帧目录] [输出]; 合成前确认帧目录
- GIF交付: GPU直接git提交Codeup LFS(idle_v12.gif 4.1MB, GPU仓库有Codeup认证), 网页可见预览, 无需绕云端
- 锚点 JSON 元数据脆弱: json.dump(indent=1)多行格式曾让自写解析器全读出NULL; 正则解析有同名锚点串写问题——解析用缩进+跨行状态机(见 8/30 踩坑表)
- 表情件(眉/眼/嘴贴面件)主轴天然水平: 质量门垂直度检查须 --skip-vertical; 眉+眼组合拆碎 → 按格合并提取

## 验证清单

- [ ] 部件网格图: 门禁唯一入口 --quality-gate(连通域件数/垂直度/连接孔) PASS
- [ ] 表情/贴面件: --skip-vertical --no-holes 时件数达标
- [ ] 直切形态: pose_annotated.jpg 关节落在黑色转轴盘上(vision)
- [ ] 拼装渲染: 头/躯干/四肢层级正确, 无悬浮(vision)
- [ ] 动画: tools/frame_diff.py 断言 PASS(均值>1.0, 防 vision 误判静止) + 用户精调后及格判定

---

## 附录: 【已废弃】双图管线总览(8/26 方案, 禁止执行)

> ⚠️ **废弃标记(2026-09-01)**: 本节是被 2026-08-27 全盘复盘否决的旧路线, 仅作历史存档。
> 否决依据: review/2026-08-27-pipeline-audit/(五环节单步证据, commit 98cb6b0)——
> 双图方案有结构性缺陷(部件图与参考图两次独立生成, 比例体系不同, 拼装被迫非均匀缩放:
> 头横向拉宽/臂纵向拉长近2倍), 三条铁律: 非均匀缩放=禁止项 / 语义必须"结构确定"不能猜 /
> 部件语义靠猜必错(上臂/下臂/大腿外观几乎一致)。用户原话(08-27): "部件比例被拉伸缩放,
> 非常不协调, 先不要再动手修改了"。正确路线 = §1 主 SOP(参考图直切消灭比例鸿沟: 零缩放/零错位/零猜测)。

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

(旧版关键文件: 云端出图 /tmp/guimei-prod/gen_v2.py / GPU C:\ai\guimei-prod\pipeline.py / build_grid.py / RigBuilder v12——v12 的裙摆双层/层级骨骼/帧差验证细节如仍需, 查 review/2026-08-27-pants-skirt/。)
