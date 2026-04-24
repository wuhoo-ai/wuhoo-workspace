# Wuhoo Skill 命名与分类约定

> 最后更新：2026-04-24

## 命名规则

所有为 wuhoo 业务服务的 skill 必须遵循以下约定：

### 1. 前缀约定
- **目录名** 和 **SKILL.md frontmatter 中的 `name` 字段** 必须以 `wuhoo-` 为前缀
- 示例：`wuhoo-trade`、`wuhoo-stock-pick`、`wuhoo-futuapi`
- 目录名与 frontmatter name 必须完全一致

### 2. 分类标签
- 所有 wuhoo skill 的 SKILL.md frontmatter 必须包含 `tags: ["wuhoo"]`
- 所有 wuhoo skill 的 SKILL.md frontmatter 必须包含 `category: wuhoo`
- 用于筛选和分组所有 wuhoo 相关的 skill

### 3. 适用范围
- 自研 skill：所有为 wuhoo 业务自主开发的 skill
- 开源引入：为 wuhoo 业务服务的开源引入 skill（如 futuapi），同样适用此约定

## 路径约定

- 所有 skill 源码位于 `~/wuhoo-workspace/skills/wuhoo/` 下（category 子目录）
- 目录结构：
  ```
  skills/wuhoo/wuhoo-{skill-name}/
  ├── SKILL.md          # Skill 描述与使用指南
  ├── scripts/          # 脚本文件（如适用）
  ├── tests/            # 单元测试
  └── data/             # 数据文件（如适用）
  ```
- external_dirs 配置指向 `~/wuhoo-workspace/skills`，Hermes 按 `category/skill-name/SKILL.md` 路径加载

## 内部引用

- Skill 内部引用自身或其他 wuhoo skill 时，必须使用完整的前缀路径
- 示例：`skills/wuhoo-futuapi/scripts/` 而非 `skills/futuapi/scripts/`
- 其他 wuhoo skill 文件（如 cron-plan.md、测试文件）引用 wuhoo skill 时同样需要使用前缀

## 当前 Wuhoo Skill 清单

| 目录名 | frontmatter name | 功能描述 |
|--------|-----------------|---------|
| wuhoo-debate | wuhoo-debate | 多空辩论分析模块 |
| wuhoo-stock-deep-analysis | wuhoo-stock-deep-analysis | 单股深度分析与决策建议 |
| wuhoo-trade-diagnose | wuhoo-trade-diagnose | 持仓诊断与调仓建议 |
| wuhoo-news-rss | wuhoo-news-rss | RSS 资讯采集与检索引擎 |
| wuhoo-stock-pick | wuhoo-stock-pick | 可配置因子组合的多市场选股 |
| wuhoo-trade | wuhoo-trade | 多市场交易执行 |
| wuhoo-futuapi | wuhoo-futuapi | 富途 OpenAPI 交易与行情助手 |
| wuhoo-football-predictor | wuhoo-football-predictor | 足球赛事预测系统 |
| wuhoo-lottery-ssq | wuhoo-lottery-ssq | 双色球数据分析与预测工具 |

另有 `wuhoo-skill-testing` 位于 `~/.hermes/skills/software-development/`，用于 wuhoo skill 的单元测试规范。

## 新增 Skill 流程

1. 在 `~/wuhoo-workspace/skills/` 下创建 `wuhoo-{skill-name}/` 目录
2. 编写 SKILL.md，frontmatter 必须包含：
   ```yaml
   ---
   name: wuhoo-{skill-name}
   description: <描述>
   tags: ["wuhoo"]
   category: wuhoo
   version: 1.0.0
   ---
   ```
3. 更新本文件中的 Skill 清单
4. 更新 memory 中的 wuhoo skill 记录
