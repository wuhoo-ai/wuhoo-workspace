---
name: wuhoo-netdisk
description: "Use when 上传/下载非代码素材产物到百度网盘. BaiduPCS-Go CLI, 产物配对目录规范(类型/内容-时间/prompt.md+素材), 凭证零回显登录."
version: 1.0.0
category: shared
tags: ["wuhoo"]
dependencies: "BaiduPCS-Go v4.0.2 (~/tools/baidupcs/), python3.11, bash"
---

# 百度网盘素材产物库（wuhoo-netdisk）

存储分工（用户 2026-11-17 拍板）：**非代码素材产物以百度网盘为主，代码以 GitHub 为主**。
Codeup 全部内容后续考虑清理（未拍板前不动，guimei 仓双 remote 推送暂维持）。
git 仓只留文本产物（脚本/报告/提示词 md），媒体大文件进网盘，git 文档引用网盘路径。

## 目录规范（用户拍板，勿改结构）

```
/wuhoo-assets/                  ← 根（可 --root 覆盖）
├── 视频/                       ← 父文件夹 = 类型
│   └── guimei-ch01-shot02-李章武-20261117/   ← 子文件夹 = 内容 + 生产时间
│       ├── prompt.md           ← 1 个提示词 md（自包含，模板见 templates/prompt-md.md）
│       └── shot-02.mp4         ← 1 个素材文件
├── 图片/
├── 音频/
└── 文档/
```

- **提示词与产物必须成对提交**：上传素材时对应的 prompt.md 一并上传，统一命名 prompt.md。
- prompt.md 自包含：完整提示词逐字 + 参数单 + 来源 + 生成元数据（task_id/usage）+ 验收记录。
- 留证附件（sidecar json/接触表）可用 --extra 追加，不破坏「1 prompt + 1 素材」主结构。
- 类型可扩展（--type 当前限 视频/图片/音频/文档，新增改 upload_deliverable.py TYPES）。

## 登录（凭证零回显，永不进聊天）

工具无扫码登录；推荐 BDUSS+STOKEN（浏览器 Cookie 提取）。**用户自行操作**：
1. 浏览器登录 pan.baidu.com → F12 → Application → Cookies：
   复制 `BDUSS` 值；同域复制 `STOKEN` 值（不是 bdstoken！STOKEN 必含大写字母；
   仅分享转存需要 STOKEN，上传下载可不填）。
2. 用户自己在服务器写入（值不经聊天/不经 agent 工具）：
   ```bash
   mkdir -p ~/.config/baidupcs && umask 077
   cat > ~/.config/baidupcs/credentials.env <<'CRED'
   BDUSS=<值>
   STOKEN=<值>
   CRED
   chmod 600 ~/.config/baidupcs/credentials.env
   ```
3. 运行登录助手（读文件→login→who/quota 验证，输出过滤凭证值）：
   ```bash
   bash ~/wuhoo-workspace/skills/shared/wuhoo-netdisk/scripts/login.sh
   ```
- 用户名密码交互登录已长期不维护且验证码繁琐，禁用。
- 凭证文件 0600 强制检查；永不 echo、永不 commit、永不发聊天。
- 登录态存 ~/.config/baidupcs/（BAIDUPCS_GO_CONFIG_DIR 隔离，pcs.sh 自动设置）。
- BDUSS 过期表现为 who 失败/上传 401：用户重新提取写入，重跑 login.sh。

## Usage

```bash
S=~/wuhoo-workspace/skills/shared/wuhoo-netdisk/scripts

# 产物配对上传（自动建目录+统一 prompt.md 命名+ls 验证）
python3.11 $S/upload_deliverable.py --type 视频 \
  --name guimei-ch01-shot02-李章武 --date 20261117 \
  --prompt /path/prompt.md --asset /path/shot-02.mp4 \
  --extra /path/shot-02.json

# 先 dry-run 看计划
python3.11 $S/upload_deliverable.py ... --dry-run

# 通用 CLI 透传（配置目录已隔离）
bash $S/pcs.sh ls /wuhoo-assets/视频
bash $S/pcs.sh quota
bash $S/pcs.sh upload <本地文件> <网盘目录>
bash $S/pcs.sh d /wuhoo-assets/视频/xxx/shot-02.mp4 --saveto /tmp
bash $S/pcs.sh mkdir /wuhoo-assets/图片
```

## 与生产技能的咬合

- wuhoo-manju-storyboard / wuhoo-video-generation：产物验收（人工审核）后，
  写 prompt.md（模板）→ upload_deliverable.py 配对上传 → git 报告记录网盘路径。
- 出图/音频/文档类产物同规范入库；git 仓不再新增媒体 LFS 对象（历史存量待 Codeup 清理拍板后一并处置）。

## Pitfalls

- **跨境上传阻断（2026-11-18 实测，SG 阿里云→百度 PCS，硬坑）**：<1MB 小文件正常成功；
  ≥4MB 固定分片永远无法完成——实时进度呈锯齿重置（传到 600-800KB→0B/s 停滞→回退重传），
  shot-02 独占带宽 30min、t2v 11 分片并发 24min 均 0 分片完成。根因=跨境上传方向连接被
  policing/重置，非工具 bug；BaiduPCS-Go 无分片尺寸选项（4MB 固定），并发再高也救不了单分片。
  对策方向：①国内出口（config proxy 经 NAS/国内节点，或文件中转到国内再传）；
  ②百度离线下载（临时 HTTPS 链接→网盘 App 云添加，百度服务器→SG 的下载方向不受此限）。
  诊断法：直接前台跑 pcs.sh upload 看实时进度（upload_deliverable 子进程管道会吞输出）+
  pcs_uploading.json 分片 checksum 计数 + ss -tinp bytes_sent 差分测真实吞吐。
- **STOKEN 拿错**：必须是 pan.baidu.com 域下的 STOKEN（含大写字母），bdstoken 无效；
  拿错只影响转存，上传下载仍可用 BDUSS。
- **非 SVIP 下载限速**：上传不受会员限制（分片并发上传正常跑）；下载慢是账号侧限速，
  不要调高 max_parallel 硬抗（普通用户 >1 并发反而触发限速）。
- **分片上传 md5 记录可能错**：百度端 bug，文件完整性没问题；介意可 fixmd5 或
  禁用分片（--norapid，单线程）。验证上传成功以 ls 文件名+大小为准，不迷信 md5。
- **秒传已失效**（v4.0.2 sumfile 注明），不要依赖秒传链接 workflow。
- **上传断点续传**：v4.0.2 已恢复（Ctrl+C 优雅停止+续传）；大文件中断重跑同命令即可。
- **同名不覆盖目录**：upload 目标与网盘目录同名时不会覆盖目录（防丢数据）；
  重传同文件会生成重复名或跳过，先 ls 确认。
- **违规文件**：网盘端可能拦截违规内容（报错会明示），改内容或申诉，不要硬重试。
- **路径斜杠**：网盘路径用 /，Windows 本地路径反斜杠勿混入。

## 安装/升级

二进制：~/tools/baidupcs/BaiduPCS-Go（v4.0.2，2026-08-21 release，linux-amd64）。
升级：GitHub qjfoidnh/BaiduPCS-Go releases 下载 zip → python zipfile 解压替换 → --version 验证。
出处：https://github.com/qjfoidnh/BaiduPCS-Go （iikira 原版 v3.6.2 基础上加强，Apache-2.0）。