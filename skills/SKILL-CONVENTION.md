# Wuhoo Skill 命名与分类约定

> 最后更新：2026-09-01（多 profile 拆分后 v2）

## 1. 仓库即权限边界

技能源码统一在 `~/wuhoo-workspace/skills/<域>/` 下，**目录 = profile 可见性**
（Hermes external_dirs 是整目录扫描、无 skill 级白名单，隔离只能靠切目录）：

| 目录 | 可见 profile | 内容 |
|---|---|---|
| `skills/shared/` | 全部 (default/trader/gamedev) | 跨域基础设施：wuhoo-infra、wuhoo-skill-testing |
| `skills/default/` | default | 资讯与个人线：wuhoo-news-rss、wuhoo-rss-briefing、wuhoo-football-predictor |
| `skills/trader/` | trader | 投资全家桶（10 个）|
| `skills/gamedev/` | gamedev | 游戏生产全家桶（18 个）|

每个 profile 的 `config.yaml` 固定两行：
`skills.external_dirs: [skills/shared, skills/<自身域>]`

## 2. 命名规则（不变）
- 目录名与 SKILL.md frontmatter `name` 完全一致，必须以 `wuhoo-` 为前缀
- frontmatter 必含 `tags: ["wuhoo"]`
- `category:` 字段 = 归属域目录名（shared/default/trader/gamedev）

## 3. 新技能落位流程
1. 判定归属域：只服务一个 agent 的业务 → 该域目录；跨域运维/工具 → shared
2. 放入 `skills/<域>/wuhoo-<name>/`，同步更新本文件表格（如新增业务域）
3. **禁止**在 `~/.hermes/skills/` 下建 wuhoo skill（那里只放社区技能与 profile 本地实验件）
4. 发布：跑 `scripts/sync_skills_to_publish.sh` 同步到 wuhoo-skills 镜像仓

## 4. 跨 profile 引用规则
- 技能文档/脚本内引用其他技能路径一律写 `~/wuhoo-workspace/skills/<域>/<name>`
- 技能需要兄弟 profile 的能力时，用 `hermes -p <profile> chat -q` 派发，不做跨目录 import
- cron job prompt 里的工作路径同样按 `<域>` 写（搬家时 grep `skills/` 一起改）

## 5. 数据文件
- `data/` 已在 .gitignore（news.db 等运行时数据不入库，路径随域目录走）
- 大二进制走 LFS（发布仓不含媒体原件）
