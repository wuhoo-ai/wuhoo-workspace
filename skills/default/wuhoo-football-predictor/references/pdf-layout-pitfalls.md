# PDF 排版陷阱 — 战术模块实现教训

## 背景

2026-07-03，为 `generate_single_match_pdf.py` 实现 `_add_tactical_section()` 时，
第一版用 `make_table()` 渲染 3 列宽表（维度/主队/客队），每列填入 120 字攻防描述文本。
ReportLab `Table` 未设置 `col_widths` 时自动分配宽度 → A4 页面溢出 → 完全不可读。

## 根因

`make_table()` 函数（line 50）不设 `col_widths` 参数时，ReportLab 根据内容自动计算列宽。
3 列 × 120 字中文文本远超 A4 可用宽度（~270pt）。

## 修复方案

**段落式布局**：阵型/教练用窄表（`col_widths=[50, 110, 110]`），攻防优缺转为一个 Paragraph 块：

```python
# ✅ 正确：段落式，不会溢出
for tc, tac in [(na, tac_a), (nb, tac_b)]:
    parts = []
    if tac.get('style_summary'): parts.append(tac['style_summary'])
    if tac.get('attacking'): parts.append(f"进攻: {tac['attacking']}")
    # ... 
    story.append(P(f'【{tc}】', 'h3'))
    for line in parts:
        story.append(P(line, 'body'))
```

```python
# ❌ 错误：3 列宽表，必定溢出
rows = [['维度', na, nb],
        ['进攻', tac_a.get('attacking','')[:120], tac_b.get('attacking','')[:120]],
        ...]
story.append(make_table(['维度', na, nb], rows))  # 无 col_widths！
```

## 设计原则

1. **多列表仅用于短数据**（阵型名/教练名/数字/百分比）— 始终设 `col_widths`
2. **长文本用段落**（风格描述/攻防策略/优劣势）— 每队独立段落块
3. **永远先验证 PDF**：生成后检查 `[风格战术]` 表格是否在页面内，文本是否截断
