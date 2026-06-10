# Cron Scheduler Silent Stall — 诊断与恢复

> **发现日期**: 2026-06-10
> **影响范围**: 所有 Hermes cron 任务
> **严重程度**: 🔴 高风险 — 无错误日志，静默失败

## 症状

1. `hermes cron status` 显示 `Next run` 时间停留在过去，不推进
2. `agent.log` 中无 `Running job` 日志（被跳过的 job 完全没有调度记录）
3. Gateway 进程正常运行，`hermes gateway status` 显示 `active (running)`
4. Gateway log 中**无** `Cron ticker stopped` 事件 — ticker 没有显式停止，只是不再触发

## 诊断步骤

```bash
# 1. 确认调度器卡死
hermes cron status
# → 如果 "Next run" 是过去的时间（如 09:30 而当前 >10:00），调度器已停

# 2. 确认 gateway 还在运行
hermes gateway status

# 3. 检查最近一次 job dispatch 的时间
grep "Running job" ~/.hermes/logs/agent.log | tail -5
# → 如果最近一次 dispatch 与当前时间差距 > 预期 tick interval，确认卡死

# 4. 检查是否有 cron ticker 重启或停止事件
grep -i "Cron ticker" ~/.hermes/logs/gateway.log | tail -10
# → 正常情况下不应看到异常的 stop/start 对
```

## 根因

Hermes cron ticker 在 gateway 进程中以 60s 间隔运行。在以下情况下可能**静默停止**（无日志）：

- DeepSeek API 频繁 `RemoteProtocolError (CloudFront peer closed)` 导致 stream 反复中断重试
- 前一个 cron job 完成后的 ticker 线程状态异常
- 多 cron job 并行执行时的线程池耗尽

**关键特征**: gateway 仍然运行，只是 ticker 不再触发新的 job dispatch。这与 `hermes update` 导致的显式 `Cron ticker stopped` 不同。

## 恢复

```bash
# 1. 备份当前 cron 状态
hermes cron list > /tmp/cron_state_$(date +%Y%m%d_%H%M).txt

# 2. 重启 gateway（会重置 cron ticker）
hermes gateway restart

# 3. ⚠️ 重启会杀掉 OpenD 等子进程，必须手动恢复
bash ~/wuhoo-workspace/scripts/start_opend.sh start

# 4. 等 2-3 分钟后验证调度器恢复
sleep 120
hermes cron status
# → "Next run" 应更新到未来的时间

# 5. 确认错过的 job 会在下一轮自动补跑
# 或手动触发: hermes cron run <job_id>
```

## 预防

- **每日监控**: 在「系统健康日报」(09:00) 中已包含 cron 状态检查。如发现 `Next run` 停滞，立即告警
- **DeepSeek API 稳定性**: stream 中断重试虽能恢复，但大量并发 cron job 的反复重试可能触发 ticker 线程异常
- **避免在 cron 密集时段（08:00-09:30）手动触发长任务**：用户请求会占用 gateway agent，虽不直接阻塞 ticker，但可能影响 job completion

## 已知案例

| 日期 | 受影响 job | 跳过时长 | 恢复方式 |
|------|-----------|---------|---------|
| 2026-06-10 | RSS简报(09:30) + A股/港股诊断(10:00) | 60min+ | gateway restart |
