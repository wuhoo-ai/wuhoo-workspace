#!/bin/bash
# 测试 Heartbeat 新闻推送 (拆分多条 + 保留链接)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/../logs/heartbeat-news-test.log"

echo "=========================================="
echo "🧪 Heartbeat 新闻推送测试"
echo "=========================================="
echo ""

# 白名单用户
DINGTALK_USER_ID="01443329476136537748"
WECOM_USER_ID="haohaijiao"

# 测试消息 1: TrendRadar 热榜格式
TEST_MESSAGE_1="📰 TrendRadar 热榜 Top20

时间：$(date '+%Y-%m-%d %H:%M:%S')

【今日头条 | 2026-03-13】
1. [OpenAI 发布 GPT-5.4，超越人类水平](https://example.com/news1)
2. [量化交易新趋势：AI 多模型竞争](https://example.com/news2)
3. [跨境电商 AI 直播成主流](https://example.com/news3)
4. [伊朗局势升级，油价突破 100 美元](https://example.com/news4)
5. [特斯拉 Optimus 机器人量产](https://example.com/news5)

【华尔街见闻 快讯 | 2026-03-13】
1. [美联储维持利率不变](https://example.com/news6)
2. [纳斯达克指数创新高](https://example.com/news7)
3. [AI 概念股持续上涨](https://example.com/news8)
4. [比特币突破 75000 美元](https://example.com/news9)
5. [中金公司上调 A 股目标价](https://example.com/news10)

---
推送渠道：钉钉、企业微信
测试模式：✅ (消息 1/2)"

# 测试消息 2: 主题新闻格式
TEST_MESSAGE_2="📰 主题新闻 Top20

时间：$(date '+%Y-%m-%d %H:%M:%S')

🤖 AI 主题 Top5
1. [阿里云百炼发布 coding-agent](https://example.com/ai1)
2. [OpenClaw 多代理系统实战](https://example.com/ai2)
3. [Python 量化交易框架对比](https://example.com/ai3)
4. [AI Agent 市场规模达 491 亿美元](https://example.com/ai4)
5. [多因子选股模型实战分享](https://example.com/ai5)

📈 量化交易 Top5
1. [AI-Trader 开源项目更新](https://example.com/trade1)
2. [残差波动率因子优化](https://example.com/trade2)
3. [中证 1000 成分股筛选](https://example.com/trade3)
4. [VectorBT 回测框架教程](https://example.com/trade4)
5. [多模型竞争交易策略](https://example.com/trade5)

💻 科技主题 Top5
1. [科技巨头 AI 投资竞赛](https://example.com/tech1)
2. [创业公司融资动态](https://example.com/tech2)
3. [IPO 市场回暖](https://example.com/tech3)
4. [大模型技术突破](https://example.com/tech4)
5. [云计算市场增长](https://example.com/tech5)

🏭 大宗商品 Top5
1. [原油价格波动分析](https://example.com/commodity1)
2. [黄金避险需求上升](https://example.com/commodity2)
3. [铜价创历史新高](https://example.com/commodity3)
4. [大豆进口量增加](https://example.com/commodity4)
5. [铁矿石供应紧张](https://example.com/commodity5)

---
数据来源：Jina AI Search
推送渠道：钉钉、企业微信
测试模式：✅ (消息 2/2)"

echo "📱 测试钉钉推送 (消息 1/2)..."
openclaw message send \
    --channel dingtalk \
    --target "$DINGTALK_USER_ID" \
    --message "$TEST_MESSAGE_1" \
    2>&1 | tee -a "$LOG_FILE"

echo ""
echo "💼 测试企业微信推送 (消息 1/2)..."
openclaw message send \
    --channel wecom \
    --target "$WECOM_USER_ID" \
    --message "$TEST_MESSAGE_1" \
    2>&1 | tee -a "$LOG_FILE"

echo ""
echo "等待 2 秒..."
sleep 2

echo ""
echo "📱 测试钉钉推送 (消息 2/2)..."
openclaw message send \
    --channel dingtalk \
    --target "$DINGTALK_USER_ID" \
    --message "$TEST_MESSAGE_2" \
    2>&1 | tee -a "$LOG_FILE"

echo ""
echo "💼 测试企业微信推送 (消息 2/2)..."
openclaw message send \
    --channel wecom \
    --target "$WECOM_USER_ID" \
    --message "$TEST_MESSAGE_2" \
    2>&1 | tee -a "$LOG_FILE"

echo ""
echo "✅ 测试完成！请检查钉钉和企业微信是否收到 2 条消息。"
echo ""
echo "日志文件：$LOG_FILE"
