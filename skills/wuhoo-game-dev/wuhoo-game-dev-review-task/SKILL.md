---
name: wuhoo-game-dev-review-task
description: "Use after Agent completes any task (code/art/audio) to perform quality review against the original task.spec. Provides a structured checklist aligned with each task type, flags non-compliant outputs, and generates a review report. This is the quality gate between Agent output and merge."
version: 1.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo, game-dev, review, quality-gate, verification]
    related_skills: [wuhoo-game-dev-code-from-task, wuhoo-game-dev-sprite-from-task, wuhoo-game-dev-music-from-task, wuhoo-game-dev-gdd-to-tasks]
---

# Wuhoo Review Task

Agent 产出 → 对照 task.spec 逐项审查 → ✅/❌ + 修改建议。

## When to Use

- Agent 完成任何 task 后
- 合并到 main 前
- 每日构建前的最终检查

## Review Checklist: Code Task

```
□ 编译: Unity Console 显示 0 errors, 0 warnings (可接受 ≤3 warnings)
□ 测试: 所有新测试通过 (EditMode + PlayMode)
□ 路径: 所有 output 文件存在于指定路径
□ 边界: 处理了 null/0/empty/极限值
□ 序列化: [System.Serializable] 标记了所有数据类
□ 命名: PascalCase 类/方法, camelCase 变量, 无拼音无缩写
□ 依赖: 正确引入了 depends_on task 的接口
□ 性能: 无 Update() 中的 Find/GetComponent/Resources.Load
□ 日志: Debug.Log 仅在调试需要时保留, 无泄露敏感信息
□ 代码量: ≤ 300 行/文件 (超标需说明理由)
```

## Review Checklist: Art Task

```
□ 分辨率: 与 task.params 一致
□ 帧数: spritesheet 帧数正确
□ 调色板: 颜色在指定 palette 范围内
□ 格式: .png 24/32-bit, 无 JPG 压缩伪影
□ Unity 配置: Point filter + Uncompressed
□ 切片: spritesheet 已正确切片
□ 命名: 文件名符合 task.output 路径
□ 一致性: 与已有资产风格不冲突 (线条粗细/阴影方向/颜色饱和度)
```

## Review Checklist: Audio Task

```
□ 时长: 在 task.params 范围内
□ BPM: 符合 spec (BGM only)
□ 循环: 无缝循环 (BGM only, 听开头和结尾)
□ 音量: 峰值 -3dB 到 -6dB (不削波)
□ 格式: BGM=MP3 Vorbis / SFX=WAV PCM
□ 变体数: 达到 task 要求的最少变体数
□ 文件大小: BGM < 5MB each, SFX < 500KB each
□ 版权: 已确认为 Suno/Udio 授权
```

## Review Decision

```
✅ PASS — 所有清单项通过 → 可以 merge
⚠️ PASS WITH NOTES — 非阻塞问题, 记录但不阻止 → merge + 开 issue
❌ FAIL — 阻塞问题 → 退回 Agent 修复, 附具体修改建议
```

## Review Report 格式

```markdown
# Task {id} Review — {task 名称}

**Reviewer**: Hermes (wuhoo-game-dev-review-task)
**Date**: 2026-07-13
**Decision**: ⚠️ PASS WITH NOTES

## Checklist

| # | 检查项 | 结果 | 备注 |
|---|--------|------|------|
| 1 | 编译通过 | ✅ | |
| 2 | 测试通过 | ✅ | 5/5 |
| 3 | 路径正确 | ✅ | |
| 4 | 边界处理 | ⚠️ | stamina<=0 已处理, 但 stamina>999 未处理 |
| 5 | Serialize | ✅ | |
| 6 | 命名规范 | ✅ | |
| 7 | 依赖 | ✅ | |
| 8 | 性能 | ✅ | |
| 9 | 日志 | ❌ | 3 处 Debug.Log 需移除 (调试代码) |
| 10 | 代码量 | ✅ | 85 lines |

## Issues

1. ❌ **BLOCKER**: 移除 MiningSystem.cs:42, 78, 112 的 Debug.Log 调用
2. ⚠️ **NON-BLOCKING**: 添加超大体力值 (>999) 的 clamp 处理

## Action

退回 Agent 修复 blocker, non-blocking 记录为 issue #12
```

## Pitfalls

1. 只跑测试不看代码 — 测试通过 ≠ 代码没质量问题。必须逐行审查
2. 放过 Debug.Log — 发货版本中的日志是性能杀手和安全隐患
3. 忽略编码规范 — 早期不统一规范后期要全部重构
4. 过度严格 — 独立开发的 review 重点是"能跑+不崩+不傻", 不是"完美代码"
5. 单人 review 盲区 — 如果怀疑某个产出有隐患, 派另一个 Agent 做独立 review

## 与 CI/CD 集成

review-task 输出报告后, CI/CD 可以:
1. 读取 review 决策 (PASS/FAIL)
2. FAIL → 阻止合并, 发送 WeChat 通知
3. PASS → 允许 merge, 触发构建

## Verification

- [ ] 所有清单项都已检查 (不跳项)
- [ ] ❌ 项目都附了具体修改建议 (不只是说 "不行")
- [ ] Review 报告已保存到 GDD 同级目录
