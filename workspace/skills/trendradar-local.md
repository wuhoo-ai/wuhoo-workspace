# TrendRadar 热点雷达

## 概述

TrendRadar 是一个网络热点监控工具，自动抓取多平台热搜数据，进行关键词匹配和趋势分析，并通过 OpenClaw notify 模块推送结果。

## 项目路径

| 路径 | 说明 |
|------|------|
| `/home/admin/.openclaw/workspace/projects/TrendRadar` | 源码目录 |
| `/home/admin/.openclaw/data/trendradar` | 持久化数据目录 |
| `/home/admin/.openclaw/data/trendradar/config` | 配置文件 |
| `/home/admin/.openclaw/data/trendradar/output` | 输出结果 |

## 快速开始

### 构建镜像

```bash
cd /home/admin/.openclaw/workspace/projects/TrendRadar
podman build -t trendradar-local:latest .
```

### 执行搜索

```bash
# 使用运行脚本
cd /home/admin/.openclaw/workspace/projects/TrendRadar
./run-local.sh

# 或直接使用 docker run
docker run --rm \
  --name trendradar \
  -v /home/admin/.openclaw/data/trendradar/output:/app/output \
  -v /home/admin/.openclaw/data/trendradar/config:/app/config:ro \
  -e KEYWORDS="AI,人工智能,大模型" \
  trendradar-local:latest \
  --once
```

### 定时执行

通过 cron 配置定时任务：
```bash
# 编辑 crontab
crontab -e

# 每小时执行一次
0 * * * * /home/admin/.openclaw/workspace/projects/TrendRadar/run-local.sh
```

## 配置文件

### config.yaml

位置：`/home/admin/.openclaw/data/trendradar/config/config.yaml`

```yaml
# 搜索平台配置
platforms:
  - name: weibo
    enabled: true
  - name: zhihu
    enabled: true
  - name: baidu
    enabled: true
  - name: douyin
    enabled: true
  - name: bilibili
    enabled: true
  - name: toutiao
    enabled: true

# 关键词配置
keywords:
  - AI
  - 人工智能
  - 大模型
  - GPT
  - 机器学习

# 推送配置
push:
  enabled: true
  max_items: 30  # 每次最多推送条数
```

### keywords_queue.json

临时关键词队列，用于动态添加搜索关键词。

## 执行流程

```
┌─────────────────────────────────────────┐
│  TrendRadar                             │
├─────────────────────────────────────────┤
│  1. 加载配置和关键词                      │
│  2. 抓取多平台热搜数据                    │
│     ├─ 微博热搜                          │
│     ├─ 知乎热榜                          │
│     ├─ 百度热搜                          │
│     ├─ 抖音热点                          │
│     ├─ B站热门                           │
│     └─ 今日头条                          │
├─────────────────────────────────────────┤
│  3. 关键词匹配                           │
│     └─ 提取匹配项                        │
├─────────────────────────────────────────┤
│  4. 输出结果                             │
│     ├─ JSON 文件 (output/*.json)        │
│     └─ 推送通知 (notify.sh)             │
└─────────────────────────────────────────┘
```

## 输出结果

输出目录：`/home/admin/.openclaw/data/trendradar/output/`

文件格式：
```json
{
  "timestamp": "2026-03-06T18:00:00",
  "total_matched": 15,
  "platforms": {
    "weibo": [
      {
        "title": "AI大模型突破",
        "url": "https://...",
        "rank": 5
      }
    ]
  }
}
```

## 消息推送

TrendRadar 使用 OpenClaw 统一推送模块：

```bash
# 推送脚本位置
/home/admin/.openclaw/scripts/notify.sh

# 推送格式
每平台前5条热点，共30条新闻
```

## Docker 镜像管理

```bash
# 查看镜像
docker images | grep trendradar

# 重新构建
cd /home/admin/.openclaw/workspace/projects/TrendRadar
podman build -t trendradar-local:latest .

# 清理旧容器
docker rm -f trendradar
```

## 日志查看

```bash
# 容器日志
docker logs trendradar

# 输出文件
ls -la /home/admin/.openclaw/data/trendradar/output/
```

## 常见问题

### Q: 抓取失败
**A**: 检查网络连接，部分平台可能有反爬限制。

### Q: 推送失败
**A**: 检查 notify.sh 脚本权限和配置。

### Q: 关键词匹配不到结果
**A**: 检查关键词列表是否正确，尝试添加更多相关词。

## 相关文件

- `run-local.sh` - 本地运行脚本
- `Dockerfile` - 镜像构建文件
- `config/config.yaml` - 主配置文件
- `config/frequency_words.txt` - 频率词列表
