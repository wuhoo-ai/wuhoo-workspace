---
name: wuhoo-game-ci
description: "Use when Unity CI fails. Pitfalls, lint, Release."
version: 2.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, unity, ci, cd, github-actions, game-ci, pitfalls]
    related_skills: [wuhoo-game-debug, wuhoo-game-scene, wuhoo-game-gates]
---

# wuhoo-game-ci — Unity CI/CD 全链路

> wuhoo-game 系列**唯一 CI 知识入口**。合并自: daily-build + unity-ci-pitfalls(15) + unity-ci-diagnosis(12) + unity-ci-ui-builder。

## 触发条件

- CI 红了（任何 job 失败）
- 需要触发/监控构建
- EditMode 测试失败
- Release/APK 交付问题
- 新增 Editor 脚本需要 CI 兼容

## 1. 构建管线架构

```
Push to v1.1-dev
  ├── Quality Gates (EditMode tests + lint)
  ├── Build StandaloneWindows64
  └── Build Android (Debug)
```

### 触发与监控

```bash
# 查看最近运行
gh run list --branch v1.1-dev --limit 5 --json databaseId,headSha,status,conclusion,workflowName

# 查看单个运行的所有 job
gh run view <id> --json jobs -q '.jobs[] | "\(.name) [\(.conclusion)]"'

# 提取编译错误（action summary 不含行号！）
gh run view <id> --log-failed | grep "error CS"

# 下载产物
gh run download <run_id> --name Build-Android --dir /tmp/apk
```

### ⚠️ 矩阵 Job 可见性

`gh run list` 可能显示 Build conclusion 为 blank 而部分 matrix job 已失败。**必须检查每个 job**:
```bash
gh run view <id> --json jobs -q '.jobs[] | "\(.name) \(.conclusion)"'
```
只有 ALL jobs 都 success 才是真绿。2026-07-21 曾因部分绿就声称 CI 通过，被用户纠正。

## 2. Pitfall 库（27 个，按频率排序）

### 高频（每次迭代可能遇到）

#### P01: 场景过期 — 运行时功能缺失
**症状**: 编译✅ CI✅ 但运行时按钮不存在、UI 缺失、新功能全部不生效。
**根因**: SceneAuthor 是手动 MenuItem，不是 IProcessSceneWithReport。代码改了 .unity 没更新。
**诊断**:
```bash
git log --oneline -1 -- Assets/Scenes/Surface.unity
git log --oneline -1 -- Assets/Editor/SceneAuthoring/SceneKit.cs
# SceneKit 比 Scene 新 → 场景过期
grep -c "AttackBtn" Assets/Scenes/Surface.unity  # 0 = 缺失
```
**修复**: GPU 节点重新 Author 所有场景。
**预防**: pre-commit-lint.sh 自动检测；CI Gate 2 场景完整性检查。

#### P02: 隐藏编译错误
**症状**: Build summary 只显示 "Scripts have compiler errors"，无行号。
**修复**: `gh run view <id> --log-failed | grep "error CS"`

#### P03: Runner 磁盘空间
**症状**: `no space left on device` 或 exit code 101。
**诊断**: Win64✅ + QG✅ + 无 CS 错误 → infra 问题，不改代码，重试。
**修复**: CI 已加 disk cleanup step:
```yaml
- name: Free disk space
  run: |
    sudo rm -rf /usr/share/dotnet /usr/local/lib/android /opt/ghc /opt/hostedtoolcache/CodeQL
    sudo docker image prune --all --force || true
```

#### P04: EditMode 测试限制（Unity 6 batch mode）
**核心规则**: batch mode 下 `AddComponent<T>()` 不触发 `Awake()`。
- Instance 单例为 null
- SerializeField 未初始化
- 协程不可用
- FixedUpdate 不运行
**只能测**: 纯逻辑 / 静态方法 / null 安全 / 默认值 / 手动调用 Init()。
**实战**: 2026-07-24 19个新测试9个因此失败→重写为纯逻辑后 163/163 全绿。

#### P05: asmdef 缺引用 — CS0246
**症状**: CS0246 for URP 类型 (Volume, Bloom 等) 尽管 using 正确。
**根因**: asmdef 缺 assembly reference。URP 需要两个:
```json
"references": [
    "Unity.RenderPipelines.Core.Runtime",
    "Unity.RenderPipelines.Universal.Runtime"
]
```
**Unity 6 内置模块格式**: `com.unity.modules.particlesystem`（非 `UnityEngine.ParticleSystemModule`）。
常见: particlesystem, audio, physics2d, animation2d, ui, imageconversion。

#### P06: Unity 6 API 废弃 (CS0618)
`FindObjectOfType<T>()` → `FindAnyObjectByType<T>()`
`GetInstanceID()` 比较 → `AreSame()`
2026-07-24: 12 处跨 8 文件，单次 commit 全部替换。

### 中频

#### P07: Android Package Name
非 ASCII productName → 无效 bundle identifier。
修复: `applicationIdentifier: {Android: com.minerswatch.game}`

#### P08: 测试阈值一致性
改配置值(500→50)后必须 `search_files` 更新 Tests/ 中所有硬编码值。

#### P09: 缺 `using UnityEngine.UI`
Editor 脚本添加 Text/Image/Button 需要此 using。

#### P10: Resources.Load 路径
只搜索 `Assets/Resources/`。`Assets/Audio/` 不可运行时访问。

#### P11: 重复 CI 运行
push + pull_request 双触发。修复: 移除 pull_request 或加 if guard。

#### P12: Release Assets 为空
CI 只 upload-artifact（7天过期），不上传到 Release。
修复: 加 softprops/action-gh-release step。
验证: `gh release view <tag> --json assets -q '.assets | length'` > 0

#### P13: 冷构建
ProjectSettings 变更 → cache key 失效 → 构建时间 2-3x。正常，等待即可。

#### P14: 波次索引间隙
`_wavesPerNight=3` 但 Guardian 在 index 3/4 → 死分支。
修复: 索引连续 + 按深度设 `_wavesPerNight`。

#### P15: Volume NRE
`VolumeProfile.TryGet<T>()` 返回 false 时 out 变量为 null。必须 null-check。

#### P16: Font 泄漏
`Font.CreateDynamicFontFromOSFont()` 每次分配新实例。用 `static Font _cached` 缓存。

#### P17: Lambda onClick 不序列化
`IProcessSceneWithReport` 中 `button.onClick.AddListener(() => ...)` 不会序列化到 player。
修复: 创建运行时 MonoBehaviour 在 Awake() 中绑定。

#### P18: 过期 EditorBuildSettings
删除 .unity 文件后未从 EditorBuildSettings.asset 移除条目。

#### P19: 过期私有方法
替换功能后旧方法无调用者但编译通过。search_files 确认后删除。

#### P20: GameRoot FindObjectOfType 竞态
DontDestroyOnLoad 对象 Awake() 时 additive 场景未加载 → FindObjectOfType 返回 null。
修复: Update() 中 lazy discovery 或 SceneManager.sceneLoaded 事件。

### 低频（Unity 6 特有）

#### P21: ParticleSystemShapeArcMode 不存在
Unity 6 移除了此 API。直接使用默认值。

#### P22: DontDestroyOnLoad 在 EditMode
EditMode 测试中调用 DontDestroyOnLoad 会报错。加 `if (Application.isPlaying)` guard。

#### P23: Texture2D.whiteTexture 4x4
Unity 6 中 whiteTexture 是 4x4 不是 1x1。Sprite rect 需适配。

#### P24: Dictionary 遍历中修改
先 snapshot Keys 到新 List 再遍历。

#### P25: FixedUpdate 状态在 batch mode
isGrounded 等由 FixedUpdate 更新的字段在测试中必须手动镜像。

#### P26: Shop.Init null 链
Shop.Init(null, upgrades) → _Upgrades 为 null → 跨系统 NRE。
所有跨系统引用链需防御性 null 检查。

#### P27: CS1069 缺 using
新文件缺少 `using UnityEngine;` 等基础 using。

## 3. IProcessSceneWithReport 模式（CI 时构建 UI）

```csharp
public class MainMenuBuilder : IProcessSceneWithReport
{
    public int callbackOrder => -100;
    public void OnProcessScene(Scene scene, BuildReport report)
    {
        if (scene.name != "MainMenu") return;
        if (GameObject.Find("MainCanvas") != null) return; // 幂等
        BuildMainMenuUI();
    }
}
```

**关键技术**:
- `SerializedObject` 绑定 SerializeField:
  ```csharp
  var so = new SerializedObject(menuUI);
  so.FindProperty("_newGameButton").objectReferenceValue = btn.GetComponent<Button>();
  so.ApplyModifiedProperties();
  ```
- `Resources.GetBuiltinResource<Font>("Arial.ttf")` — batchmode 唯一保证字体
- Lambda onClick 不序列化 → 用运行时 MonoBehaviour Awake() 绑定
- 场景 GUID `0000000000000000e000000000000000` 可用（Unity 按路径解析）

**适用**: MainMenu（自动）。Surface/Cave 场景当前是手动 MenuItem（需迁移，见 wuhoo-game-scene）。

## 4. 预防性 Lint（pre-commit-lint.sh）

每次 commit 前自动运行，检查:
1. 场景新鲜度（SceneKit vs Scene 最后修改时间）
2. Unity 6 API 兼容性（FindObjectOfType 等）
3. Resources.Load 路径存在性
4. asmdef 引用完整性

详见仓库 `Tools/pre-commit-lint.sh`。

## 5. Release 管理

**规则**: 不自动 Release。用户明确指示时才发布。
**发布后验证**: `gh release view <tag> --json assets -q '.assets | length'` 必须 > 0。
