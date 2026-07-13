---
name: wuhoo-game-dev-daily-build
description: "Use when you need to trigger the daily CI/CD build pipeline, monitor build status, fetch artifacts, and notify the user via WeChat. This is the bridge between the Hermes development loop and the GameCI/GitHub Actions build infrastructure. Also handles build failure diagnosis and retry."
version: 1.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo, game-dev, ci-cd, build, gameci, github-actions, dogfooding]
    related_skills: [wuhoo-game-dev-gdd-to-tasks, wuhoo-game-dev-review-task, cronjob]
---

# Wuhoo Daily Build

触发 CI/CD → 监控状态 → 下载产物 → 通知用户。

## When to Use

- 每日构建时间到 (cron 触发)
- Agent 完成了一组 task, 需要验证构建
- 构建失败需要诊断
- 用户说: "构建今天的版本"、"发个构建给我"

## Workflow

### Step 0: 峰谷检查

```python
# 日间高峰触发构建 → 入队, 等凌晨 GPU 节点
guard_result = peak_hour_guard(
    task_type='unity-build',
    task_id=f'build_{timestamp}',
    task_context={
        'spec': 'Unity Win+Android multi-platform build',
        'params': {'targets': ['StandaloneWindows64', 'Android']},
        'output': 'build/'
    }
)
if guard_result == 'deferred':
    print('⏳ Build 已入队, 凌晨 GPU 批处理时构建')
    return
```

> 紧急覆盖: 用户说 "现在构建" → 跳过, 直接触发 GameCI（即使高峰也执行）

### Step 1: 触发构建

两种触发方式:

**A. 自动触发 (git push)**:
```bash
# 代码已 push 到 main, GitHub Actions 自动触发
# 无需额外操作, 跳到 Step 2 监控
```

**B. 手动触发 (workflow_dispatch)**:
```bash
# 通过 GitHub CLI 触发
gh workflow run nightly-build.yml --repo <owner>/<repo> --ref main
```

### Step 2: 监控构建状态

```bash
# 获取最新 workflow run
gh run list --repo <owner>/<repo> --workflow nightly-build.yml --limit 1 --json status,conclusion,url

# 如果还在运行, 等待
# 轮询间隔: 30s, 最多等 30 分钟
```

```python
# Hermes 可以用 terminal + 循环
import time, json, subprocess

def wait_for_build(timeout_minutes=30):
    for i in range(timeout_minutes * 2):  # 每 30s 检查一次
        result = subprocess.run(
            ['gh', 'run', 'list', '--repo', repo, '--workflow', 'nightly-build.yml',
             '--limit', '1', '--json', 'status,conclusion'],
            capture_output=True, text=True
        )
        data = json.loads(result.stdout)[0]
        if data['status'] == 'completed':
            return data['conclusion']  # 'success' or 'failure'
        time.sleep(30)
    raise TimeoutError("Build did not complete within timeout")
```

### Step 3: 下载产物

```bash
# 下载所有 artifact
gh run download <run-id> --repo <owner>/<repo> --dir /tmp/build-output/

# 产物结构:
# /tmp/build-output/
#   Build-StandaloneWindows64/MyGame_v1.2.3.zip
#   Build-Android/MyGame_v1.2.3.apk
#   Build-iOS/MyGame_v1.2.3.ipa (仅在 macOS runner)
```

### Step 4: 验证产物完整性

```bash
# 检查文件存在且非空
for file in /tmp/build-output/Build-*/MyGame*; do
    if [ ! -s "$file" ]; then
        echo "ERROR: $file is missing or empty"
        exit 1
    fi
    echo "OK: $file ($(du -h "$file" | cut -f1))"
done
```

### Step 5: 分发 + 通知

```markdown
# WeChat 通知模板

🏗️ **矿工守夜 Nightly Build #42**

✅ Windows: MyGame_v1.2.3.zip (45MB)
✅ Android: MyGame_v1.2.3.apk (38MB)
⚠️ iOS: Build skipped (runner quota exceeded)

📝 Changes:
  - T003 采矿系统 added
  - T011 主角 idle sprite added
  - balance: 镐 Lv3 费用 $800 → $600

🔗 Download: [Windows] [Android QR]
🕐 Build time: 12m 34s
```

使用 Hermes 的 WeChat gateway 发送:

```python
# 通过 send_message tool 或 gateway API
send_message(
    target='wechat',
    message=notification_text,
    # 附件在 WeChat 上需要特殊处理:
    # 小文件 (<100KB) → 直接发送
    # 大文件 → 上传到服务器 → 发送下载链接
)
```

### Step 6: 构建失败处理

```markdown
❌ **矿工守夜 Nightly Build #42 FAILED**

失败平台: Android
错误: `error CS0246: The type or namespace name 'MiningSystem' could not be found`

诊断:
  1. T003 合并后忘记 git add Scripts/Systems/MiningSystem.cs
  2. 文件存在于本地但未提交

建议:
  - 检查 `git status` → 确认缺失文件
  - `git add` + `git commit --amend` + `git push -f`
  - 重新触发构建
```

## 与 Hermes Cron 集成

创建 cron job (在正式项目中使用):

```
cronjob(action='create',
  schedule='0 6 * * *',  # 每天 UTC 6:00
  prompt='加载 wuhoo-game-dev-daily-build skill, 触发今天的每日构建, 下载产物, 微信通知用户',
  skills=['wuhoo-game-dev-daily-build'],
  deliver='wechat'
)
```

## 构建频率建议

| 阶段 | 频率 | 原因 |
|------|------|------|
| 热身项目 | 每天 1 次 | 快速迭代, 每天有新版本测试 |
| 正式开发 | 每天 1-2 次 | 早上一版, 晚上关键改动后一版 |
| 外部测试前 | 按需 | 手动触发稳定版本 |
| 发布前 | 按需 | 冻结功能, 只修 bug 后构建 |

## 平台特定注意事项

| 平台 | runner | 免费额度 | 构建时间 |
|------|--------|---------|---------|
| Windows | ubuntu-latest | 2000 min/月 | ~10-15 min |
| Android | ubuntu-latest | 同上 | ~10-15 min |
| iOS | macos-latest | 2000 min/月 | ~15-25 min (需 Xcode) |

iOS 构建消耗最快 → 日常迭代可跳过 iOS (只周末构建), 节省免费额度。

## Pitfalls

1. 不检查产物 → 构建 "成功" 但 .apk 是 0 字节 → 必须验证文件大小
2. Library 缓存过期 → 构建突然变慢 → 定期清理 `Library/` 缓存 (每月一次)
3. Unity 许可证过期 → 构建静默失败 → 提前检查 `UNITY_LICENSE` secret 有效期
4. Git LFS 带宽超限 → 大文件拉不下来 → 监控 LFS 使用量, 清理旧二进制
5. 通知淹没 → 每天发太频繁用户会忽略 → 只发失败通知 + 成功通知合并

## Verification

- [ ] 所有目标平台产物已下载且非空
- [ ] 版本号正确 (与上一次不重复)
- [ ] 通知已送达 (WeChat 消息确认)
- [ ] 构建日志无异常 (失败时检查)
