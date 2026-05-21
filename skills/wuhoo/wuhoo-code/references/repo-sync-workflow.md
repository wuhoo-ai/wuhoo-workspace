# 多仓库同步工作流

wuhoo 技能代码分布在 3 个仓库，修改后的同步规则如下。

## 仓库角色

| 仓库 | 分支 | 角色 | 内容 |
|------|------|------|------|
| `wuhoo-workspace` | `hermes-agent` | 主开发仓库 | 全部 skills（`skills/wuhoo/`下）、数据、脚本 |
| `wuhoo-skills` | `master` | 技能存档 | 独立的 skill 代码（与 workspace 的 skill 双存） |
| `wuhoo-agents` | `master` | Agent 编排 | debate/、trade/、main/、dev/ 业务代码 |

## 同步规则

### Skill 类改动（SKILL.md + Python 脚本）

**触发条件：** 修改了 `wuhoo-workspace/skills/wuhoo/<skill-name>/` 下的文件

**流程：**
```
1. cd ~/wuhoo-workspace
2. git add + git commit + git push
3. cp -r skills/wuhoo/<skill-name> ~/wuhoo-skills/<mapped-name>
   rm -rf ~/wuhoo-skills/<mapped-name>/__pycache__
4. cd ~/wuhoo-skills
5. git add + git commit + git push
```

### 命名映射

| workspace 名称 | wuhoo-skills 名称 |
|---------------|------------------|
| wuhoo-futuapi | futu-api |
| wuhoo-trade | wuhoo-stock-trade |
| wuhoo-debate | （无独立副本，在 wuhoo-agents） |
| wuhoo-futures-pick | wuhoo-futures-pick |
| wuhoo-futures-trade | wuhoo-futures-trade |
| wuhoo-code | wuhoo-code |
| wuhoo-stock-pick | wuhoo-stock-pick |
| wuhoo-stock-deep-analysis | wuhoo-stock-deep-analysis |
| wuhoo-trade-diagnose | wuhoo-trade-diagnose |
| wuhoo-news-rss | wuhoo-news-rss |

### 仅 workspace 独有的 skill

以下 skill 暂不在 wuhoo-skills 中（无需同步）：
- wuhoo-debate — 在 wuhoo-agents/debate/
- wuhoo-football-predictor
- wuhoo-lottery-ssq
- wuhoo-skill-testing

### Agent 代码改动

**触发条件：** 修改了 `wuhoo-agents/` 下的文件

**流程：**
```
1. cd ~/wuhoo-agents
2. git add + git commit + git push
```
（无需同步到其他仓库，agent 代码仅在 wuhoo-agents）

## 注意事项

- 排除 `__pycache__/` 目录（cp -r 后手动删除）
- 如果 workspace 中有新增的 reference 文件（`references/*.md`），同样要复制到 wuhoo-skills
- 同步后验证两边文件列表一致（排除 __pycache__）
