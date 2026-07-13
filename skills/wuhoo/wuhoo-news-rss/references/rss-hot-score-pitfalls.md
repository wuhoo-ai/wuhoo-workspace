# RSS 热点评分 — 关键陷阱

## 陷阱 1：`insert_article` 遗漏评分字段

**症状**：`calc_hot_score()` 正确计算了分数（打印验证 score=19），但数据库所有文章 `hot_score=0`、`is_alert=0`。

**根因**：旧版 `insert_article()` SQL INSERT 语句只包含 12 列（feed_name~hash），没有 `hot_score`、`is_alert`、`alert_keywords`。

```python
# ❌ 旧版：缺失 3 列
INSERT OR IGNORE INTO articles
(feed_name, source_url, title, summary, content, link,
 author, pub_date, fetched_at, category, tags, hash)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

# ✅ 修复：补全 15 列
INSERT OR IGNORE INTO articles
(feed_name, source_url, title, summary, content, link,
 author, pub_date, fetched_at, category, tags, hash,
 hot_score, is_alert, alert_keywords)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

**教训**：修改 `calc_hot_score` 时必须同步检查 INSERT 语句。`INSERT OR IGNORE` 让已有文章无法更新评分。

## 陷阱 2：`\b` 词边界 + 中文不兼容

英文关键词如 `PE`、`EV`、`AR` 在 `\b` 边界下防止了 "Ramos" → "PE" 的误匹配。
但中文关键词没有 Unicode 词边界 — `\b芯片\b` 在 "AI芯片突破" 中正常，在 "芯片" 独立出现时也正常，
但在 "芯片设计" 中因为 CJK 字符间无 `\b` 可能不匹配。

**当前方案**：接受 \b 对英文较好、中文较弱的折中，更准确的中文方案需用 jieba 分词。

## 陷阱 3：已有旧文章评分无法更新

`INSERT OR IGNORE` 意味着新 fetch 不会更新已存在文章的评分。
修复 INSERT 后首次运行只有新文章获得评分，旧文章需单独 UPDATE：

```sql
UPDATE articles SET hot_score = <base_weight> WHERE hot_score = 0;
```
