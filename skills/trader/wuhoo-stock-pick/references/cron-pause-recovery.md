# Cron Job 暂停恢复指南

## 现象

```bash
$ hermes cron list
No scheduled jobs.
```

所有定时任务似乎「消失」了，但实际是**被集体 pause**。

## 根因

`hermes cron list` CLI 命令只显示 `enabled=true` 且 `state != 'paused'` 的任务。Paused 任务在 CLI 中不可见。

## 检测方法

**正确做法**：使用 cronjob 工具的 `list` action 查看全部任务（含 paused）：

```
cronjob(action='list')
```

返回的 JSON 中检查 `state` 字段：
- `"state": "scheduled"` — 正常
- `"state": "paused"` — 已暂停，需恢复
- `"enabled": false` — 伴随 paused 状态

## 恢复步骤

### 1. 列出所有任务
```
cronjob(action='list')
```

### 2. 识别 paused 任务
筛选 `state: "paused"` 的 job_id。注意 `paused_at` 时间戳可帮助判断暂停时间。

### 3. 批量恢复
对每个 paused job 调用：
```
cronjob(action='resume', job_id='<job_id>')
```

### 4. 验证
再次 `cronjob(action='list')`，确认所有任务 `state: "scheduled"`。

## 2026-05-09 集体暂停事件

- **时间**: 2026-05-09 14:41
- **影响**: 全部 13 个 cron 任务同时被 pause
- **发现**: 2026-05-28（19 天后），因数据过期 3-4 周排查发现
- **恢复**: 2026-05-28，逐一 resume 全部 13 个任务
- **暂停原因**: 未知（可能为系统维护操作）

## 预防措施

1. **系统健康日报 cron** (`3d769a6a6225`) 应增加 cron 状态检查：统计 paused 任务数
2. **数据完整性扫描 cron** (`913eb9908d5d`) 应增加 cron 存活检查
3. 定期手动运行 `cronjob(action='list')` 确认无异常 paused 任务

## 教训

- ❌ 不要仅依赖 `hermes cron list` CLI 判断 cron 状态
- ✅ 始终用 `cronjob(action='list')` 获取完整清单
- ✅ 数据过期是最早的异常信号（cron 不运行 → 数据不更新）
