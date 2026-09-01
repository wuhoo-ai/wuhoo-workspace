# 单场PDF报告交付策略 (2026-06-24)

## 背景

微信通道PDF上传CDN存在 ~100KB 隐形限制。6场全量报告（154KB）无法发送，需降级处理。

## 推荐方案：单场拆分

`generate_single_match_pdf.py` 每场比赛生成独立PDF，每份 ~50KB，远低于100KB限制。

```bash
cd ~/wuhoo-workspace/skills/default/wuhoo-football-predictor
python3.11 scripts/generate_single_match_pdf.py <N>  # N=1-6
# 输出: data/reports/single/report_<中文队>_vs_<中文队>.pdf
```

### 特点
- **ReportLab直出**: 无xhtml2pdf的emoji乱码，字体嵌入可靠
- **数据源标注**: 每层明确标注数据来源（elo_ratings.json、injuries.json (ESPN/BBC)、Open-Meteo API 等）
- **RSS报道**: 5天窗口 + 搜title+summary，含feed来源标签
- **推理路径**: emoji→纯文本映射（📋→[规则], ⚡→[修正]）
- **文件大小**: ~50KB/场（vs 全量154KB或分拆后95KB+84KB）

## 全量报告拆分（备选）

当需要完整全量报告时的拆分方法：

```python
import fitz
pdf = 'data/reports/report_2026-06-25.pdf'
doc = fitz.open(pdf)
mid = doc.page_count // 2  # 或按页数均分
# Part 1
d1 = fitz.open()
d1.insert_pdf(doc, from_page=0, to_page=mid-1)
d1.save('part1.pdf', garbage=4, deflate=True, clean=True)
# Part 2
d2 = fitz.open()
d2.insert_pdf(doc, from_page=mid, to_page=doc.page_count-1)
d2.save('part2.pdf', garbage=4, deflate=True, clean=True)
```

## WeChat CDN故障特征

- `CDN upload HTTP 500` = 文件超过100KB限制
- `hermes send` 超时 = 网关hang（需从外部shell `hermes gateway restart`）
- `hermes send` 成功但无推送 = iLink rate limit
