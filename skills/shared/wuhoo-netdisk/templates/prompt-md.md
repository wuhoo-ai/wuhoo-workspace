# prompt.md 模板（产物配对提示词文档，自包含）

> 规范：每个网盘产物文件夹内恰好 1 个 prompt.md + 1 个素材文件（可加留证附件）。
> 打开文件夹即可知道：这个产物用什么提示词、什么参数、从哪来、谁验收的。

```markdown
# <产物名>

## 产物信息
- 类型: 视频/图片/音频/文档
- 素材文件: <文件名>（时长/尺寸/大小）
- 生产时间: <YYYY-MM-DD HH:mm>
- 生产方: <模型/工具链，如 wan3.0-video-prime via wuhoo-video-generation v2>
- 来源: <GDD 章节/场景号 或 需求描述>

## 完整提示词（逐字，可直接复投）
<生产用的完整 prompt 正文>

## 参数单
model / resolution / ratio / duration / audio / prompt_extend / seed /
首帧或参考素材（如有，写明来源路径）

## 生成元数据
task_id / request_id / usage（duration/fps/SR/ratio）/ 提交与完成时间 / 耗时

## 验收记录
- 人工审核: <用户结论 PASS/FAIL + 意见，日期>
- 辅助指标: ffprobe 流信息 / frame_diff 数值（如跑了）
- 迭代历史: v1 <改动+结果> → v2 …

## 备注
<偏差/摩擦/后续迭代方向>
```