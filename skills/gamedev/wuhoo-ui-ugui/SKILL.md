---
name: wuhoo-ui-ugui
description: "Use when building/fixing uGUI UI or TMP text. Canvas布局规范+TMP字体预算+竖排文字专项。"
version: 1.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, unity, ugui, ui, textmeshpro, vertical-text]
    related_skills: [wuhoo-game-arch, wuhoo-unity-reference, wuhoo-unity-headless]
---

# wuhoo-ui-ugui — uGUI/TMP UI 规范(含竖排文字专项)

> 2026-08-20 建立。改编自 Unity-Technologies/skills 官方 ui-ugui + optimize-text-mesh-pro。
> guimei 竖排文字 = 命脉级需求, 本 skill 预留专项。

## uGUI 铁律

- 类型全限定: `UnityEngine.UI.Image` / `UnityEngine.UI.Button`, 裸名会歧义报错
- 改前必查现状(场景/hierarchy 先读后改), 禁止假设
- **增量修复, 禁止销毁重建** — 销毁级联 null 引用; 修复失败先回滚再换方案
- 一次一改一验, 禁止 shotgun debugging
- 新元素可见性检查: size > 0、在父边界内、Image 有 sprite/alpha>0
- 用户给精确值(像素/色值/间距)就精确执行, 不近似

## Canvas 设置

- Canvas + CanvasScaler(Scale With Screen Size 优先) + GraphicRaycaster
- 参考分辨率跟项目标准(如 1920x1080), Match=0.5
- 锚点/布局组优先于绝对坐标; 锚点与 pivot 对齐("右上角"元素 pivot 在右上)

## 布局组件冲突规则

- 父有 LayoutGroup 时子 anchor/sizeDelta 被接管, 别手动改子
- 同一物体上 ContentSizeFitter + LayoutGroup(Control Child Size 开)= 冲突
- 子有 CSF 且父开 Control Child Size = CSF 被覆盖(浪费)
- ScrollView Content 标准: ContentSizeFitter + VerticalLayoutGroup(父控子, CSF 控自身)
- Grid 布局: Cell Size 必须显式设置

## TMP 字体规范(对话 UI 刚需)

- **主字体 = 静态 asset(常用字形烘焙), 其他走动态 fallback 链**, 动态图集 512-1024
- 动态 fallback 字体必须开 **Clear Dynamic Data On Build**(否则编辑器烘焙字形进包)
- **Padding/采样比全链一致**(10% 安全默认: Padding9/采样90)
- 采样: 拉丁 70-90, **CJK 36-50**(字形密集, 小采样也干净, 省图集内存)
- Font Asset Scale = 1(导入常带 0.9, 破坏字号换算)
- AutoSize 运行时关掉(锁定布局后硬编码字号), 防 CPU 尖峰
- 频繁变动的 TMP 文本挂独立子 Canvas, 隔离 rebuild 成本
- 样式(描边/发光)用 Material Preset, 不复制字体资产
- TMP 资源安装: 用 `TMP_PackageResourceImporter.ImportResources()`;
  **禁止** `ExecuteMenuItem("Window/TextMeshPro/Import TMP Essential Resources")`(模态阻塞)
- 中英混排对齐: TMP_TextInfoDebugTool + ShowLines 调 ascender/descender

## 交互就绪检查

EventSystem 恰好一个 / GraphicRaycaster 在 Canvas / 交互元素 Raycast Target=true(非交互 false)/
Button.onClick 已接。缺前三条 = 视觉在但点了没反应。

## 竖排文字专项(guimei 命脉, 待实现)

- TMP 无原生竖排支持 → 候选路线(未验证, 需原型测试):
  1. 逐字手动换行(最简单, 标点/避头尾要处理)
  2. 自定义排版组件重写字符网格(参考 TextCore 源码)
  3. 旋转容器(不适合长文)
- 研究源: UnityCsReference 6000.5 的 TextCoreFontEngine / TextRendering / UI 模块(查询方法见 wuhoo-unity-reference, 云端 ~/unity-csref 直接搜)
- 中唐基准: 字体选型 + 竖排标点规范(GDD 08 对白规范联动)
- 落地前先出原型验证 3 个关键点: 避头尾、标点悬挂、行距控制
