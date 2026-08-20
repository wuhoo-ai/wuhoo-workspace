---
name: wuhoo-unity-headless
description: "Use when headless/CI Unity ops: package install, batch build, editor drive. 不手改manifest。"
version: 1.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, unity, headless, batchmode, package, ci]
    related_skills: [wuhoo-game-ci, wuhoo-game-gpu, wuhoo-unity-reference]
---

# wuhoo-unity-headless — Unity 无头/批处理操作

> 2026-08-20 建立。改编自 Unity-Technologies/skills 官方 unity-cli + unity-package-management,
> 合并 guimei GPU 无头实战经验。官方仓库: https://github.com/Unity-Technologies/skills

## 通道选择(按优先级)

1. **MCP for Unity**(决策106, 主通道): 编辑器在跑时用 mcp__unity__* 工具(execute_code/manage_packages), 无需命令行
2. **batchmode -executeMethod**: 编辑器没开时, 直接跑 Unity.exe
3. 官方 Unity CLI(`unity` 命令): 新通道, 未在 guimei 环境验证, 谨慎使用

## 无头装包 — 禁止手改 manifest.json

手改 `Packages/manifest.json` 会导致依赖解析错误(官方 skill 明确警告)。正确姿势:

**Client API + 不 -quit 模式**(核心机制):
- `Client.AddAndRemove` 是异步的, 回调在 EditorApplication.update 上泵送
- `-executeMethod` 返回时若带 `-quit`, 编辑器立即退出 → 包永远装不上
- 正解: batchmode **不带 -quit**, 脚本内 Poll 完成后自己调 `EditorApplication.Exit(code)`

模板(写 Assets/Editor/ProjectBootstrap/PackageInstaller.cs):
```csharp
static AddAndRemoveRequest _request;
public static void Install()
{
    _request = Client.AddAndRemove(
        packagesToAdd: new[] { "com.unity.2d.tilemap.extras" },
        packagesToRemove: new string[0]);
    EditorApplication.update += Poll;
}
static void Poll()
{
    if (!_request.IsCompleted) return;
    EditorApplication.update -= Poll;
    if (_request.Status == StatusCode.Success)
        EditorApplication.Exit(0);
    else { Debug.LogError(_request.Error?.message); EditorApplication.Exit(1); }
}
```
运行: `Unity.exe -batchmode -projectPath <proj> -executeMethod ProjectBootstrap.PackageInstaller.Install`(无 -quit)
- 加多个包用 AddAndRemove 一次解析; 指定版本用 `pkg@1.2.3`
- 查包版本: `curl https://packages.unity.com/<包名>` 的 dist-tags.latest + dependencies
- 编辑器运行时外部改 manifest 不会即时生效, 需重载/重启编辑器(2026-08-20 实测)

## batchmode 通用姿势

```bash
# 建项目(默认内置管线, 需脚本加 URP)
Unity.exe -createProject C:\path\proj -batchmode -quit -nographics
# 跑测试: -runTests 失效 → 用 TestRunnerApi(见 wuhoo-game-ci)
# 长任务禁止 SSH 前台: schtasks 分离(见 wuhoo-game-gpu)
```

## 坑清单(全部实测)

1. `Unity.exe -help` 挂起进程 → 别跑, 超时后 taskkill
2. 默认新项目缺 com.unity.ugui → `using UnityEngine.UI` 报 CS0234; 显式装 com.unity.ugui / com.unity.textmeshpro
3. ProjectSettings.asset 里字段是小写 `runInBackground: 0`
4. 编译错误看 `Logs/Editor.log`(项目相对路径, 非 %LOCALAPPDATA%), findstr "error CS"
5. batchmode 首次打开项目要几分钟(下载包), 验证标志=`Exiting batchmode successfully now!`
6. GUI 程序(编辑器)从 SSH 启动必须 schtasks 分离, 否则假启动(见 wuhoo-game-gpu)
7. 无头改 sprite/UI 元数据 → ISpriteEditorDataProvider(见 wuhoo-sprite-pipeline)
8. 查引擎行为 → UnityCsReference 6000.5(见 wuhoo-unity-reference)

## 验证清单

- [ ] 装包后 `packages-lock.json` 含新包
- [ ] 无头任务留审计日志(文件大小/exit code)
- [ ] 一次性计划任务用完即删
