# 多仓库同步工作流

wuhoo 技能代码分布在 3 个仓库，修改后的同步规则如下。

## 仓库角色

| 仓库 | 分支 | 角色 | 内容 |
|------|------|------|------|
| `wuhoo-workspace` | `hermes-agent` | 主开发仓库 | 全部 skills（`skills/wuhoo/`下）、数据、脚本 |
| `wuhoo-skills` | `master` | 技能存档 | 独立的 skill 代码（与 workspace 的 skill 双存） |
| `wuhoo-agents` | `master` | Agent 编排 | debate/、trade/、main/、dev/ 业务代码 |

## 同步规则

### 标准流程（推荐）

```
1. 检查三仓库状态：git branch --show-current && git status --short
2. 将改动按功能分组 commit（feat/docs/data/fix 前缀）
3. cd ~/wuhoo-workspace → git add + commit + push
4. 识别「共享 skill」— 即同时在 workspace 和 skills 仓库存在的 skill
5. 只同步共享 skill 中实际改动的文件（SKILL.md + 新增 references/scripts）
6. cd ~/wuhoo-skills → git add + commit + push
7. wuhoo-agents 通常无需操作（仅 agent 代码改动时才介入）
```

### 同步步骤（详细）

**步骤 1：识别共享 skill**

workspace 和 skills 仓库并非简单镜像。以下 skill **共享**（需同步）：
| workspace 名称 | wuhoo-skills 名称 |
|---------------|------------------|
| wuhoo-futuapi | futu-api |
| wuhoo-trade | wuhoo-stock-trade |
| wuhoo-code | wuhoo-code |
| wuhoo-stock-pick | wuhoo-stock-pick |
| wuhoo-stock-deep-analysis | wuhoo-stock-deep-analysis |
| wuhoo-trade-diagnose | wuhoo-trade-diagnose |
| wuhoo-news-rss | wuhoo-news-rss |
| wuhoo-futures-pick | wuhoo-futures-pick |
| wuhoo-futures-trade | wuhoo-futures-trade |

以下 skill **仅 workspace**（无需同步）：
- wuhoo-debate — 在 wuhoo-agents
- wuhoo-football-predictor
- wuhoo-lottery-ssq
- wuhoo-skill-testing

以下 skill **仅 skills 仓库**：
- install-futu-opend

**步骤 2：提交 workspace 改动**

```bash
cd ~/wuhoo-workspace

# 按功能分组 add（不要一把 git add -A）
git add <football files>           # feat:
git add <skill SKILL.md files>     # docs:
git add <data files>               # data:

git commit -m "feat(football): v2.3 — ..."
git commit -m "docs: SKILL.md updates + new references"
git commit -m "data(lottery): update SSQ"

git push origin hermes-agent
```

**步骤 3：定向同步到 wuhoo-skills**

⚠️ **不要用 `cp -r` 整体复制目录** — 会带入仅 workspace 独有的数据文件（football data、lottery CSV 等）。

而是**只复制实际改动的文件**：

```bash
WORKSPACE_SKILLS=~/wuhoo-workspace/skills/wuhoo
SKILLS_REPO=~/wuhoo-skills

# 1. 复制 SKILL.md
for skill in wuhoo-code wuhoo-stock-pick wuhoo-trade-diagnose \
             wuhoo-news-rss wuhoo-futures-pick wuhoo-futures-trade; do
    cp $WORKSPACE_SKILLS/$skill/SKILL.md $SKILLS_REPO/$skill/SKILL.md
done

# 2. 复制新增的 references/scripts（按需）
cp $WORKSPACE_SKILLS/wuhoo-code/references/repo-sync-workflow.md \
   $SKILLS_REPO/wuhoo-code/references/
cp $WORKSPACE_SKILLS/wuhoo-trade-diagnose/scripts/akshare_tech_factors.py \
   $SKILLS_REPO/wuhoo-trade-diagnose/scripts/

cd ~/wuhoo-skills
git add -A
git commit -m "docs: sync SKILL.md and references from wuhoo-workspace"
git push origin master
```

### 注意事项

- **排除 `__pycache__/`** 目录
- **排除数据文件**：`data/` 下的 JSON/CSV（如 elo_ratings.json、ssq_history.csv）仅 workspace 维护
- **排除 workspace 独有 skill**：football、lottery、debate 不在 wuhoo-skills 中
- 同步后验证：`cd ~/wuhoo-skills && git status` 应只有预期的文件变更
- 如果同步了命名映射不同的 skill（futu-api ↔ wuhoo-futuapi），手动处理路径差异


