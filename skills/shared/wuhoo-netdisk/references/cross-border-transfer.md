# 跨境媒体投递选型与百度离线下载 API

境外服务器（如阿里云 SG）→ 百度网盘的媒体投递。客户端直传（BaiduPCS-Go upload）在跨境
上传方向对 ≥4MB 固定分片被 policing/重置（进度锯齿回退，永不完成），<1MB 小文件正常。
大文件改走「让百度服务器自己来取」或「国内出口」，不要硬磨客户端上传。

## 选型决策表（按验证状态标注，勿把未测路线当已验证）

| 路线 | 机制 | 验证状态 | 适用 |
|---|---|---|---|
| 客户端直传 | BaiduPCS-Go upload | ≥4MB 跨境实测阻断 | 仅 <1MB 小文件 |
| 百度离线下载 cloud_dl | 临时 HTTPS 链接→add_task→百度服务器回源入库 | **端到端已实证（11-18，自有 SG nginx 回源）** | 大文件首选 |
| 极空间远程下载 | NAS 内置下载中心支持 URL 直链，App/PC 远程建任务 | 厂商能力（文档），未自测 | 归档到 NAS |
| 极空间 zspace-cli | 社区 CLI/SDK/MCP，download-add <URL> <NAS路径> | 社区项目，未自测 | NAS 路线自动化 |
| 阿里云 OSS 内网 | 同区 ECS→OSS internal 端点 LAN 速度零跨境 | 端点连通已实证(~18ms)，上传需 AK/RAM 角色 | 长期 staging 架构 |
| 小分片改造 | BaiduPCS-Go 4MB→256KB 重编译绕开重置阈值 | 设想，未测（cloud_dl 已打通，优先级低） | 无暴露/无国内节点时 |

## 端到端实证记录（2026-11-18，SG 阿里云 → 百度网盘）

载体=本机 nginx `/media-temp/<32hex token>/`（wuhoo.shanavasa.click，LE TLS，location 已持久化）。
生产脚本=`scripts/offline_deliver.py`（单链接入库）+ `scripts/upload_deliverable.py --offline`（配对一条命令）。

- 36B 探针：add_task→完成约 15s（任务建立+调度是主要延迟）。
- 45.6MB mp4：约 4 分钟完成，meta size 精确匹配，回传 sha256 逐字节一致。
- 4.6MB mp4：**首个任务卡死**——status=1 但 file_size/finished_size 长时间 0/0，
  nginx 日志只见单个 206 分片（423KB）后数分钟静默=分到坏节点。
  `cancel_task` 取消→重新 add_task 换新节点群→约 8 分钟完成（含重试等待）。
- 回源行为：百度用**多个国内节点**（112.46.x/113.133.x/119.249.x/124.237.x 等）
  先 HEAD 再 Range GET（206）分片并行拉取；nginx access.log 是判断回源真实进度的
  第一证据（任务 API 进度可能滞后或长期 0/0，日志有持续 GET=还活着，静默=卡死）。
  **中途平台期属正常**（e2e 实测 1MB/5MB 处停约3分钟后继续完成）——分片调度间隙，
  不要见进度不动就 cancel；只有「长期 0/0 + 日志静默」才是坏节点卡死。
- 下载方向（网盘→SG）不限速实测 1.1-1.7MB/s：回传 sha256 校验成本低，值得做（金标准）。
- **任务服务端独立存活**：轮询进程死掉（如 execute_code 300s 超时杀内核）不影响百度侧任务，
  用 list_task 找回 task_id 再 query_task 即可，勿盲目重复 add_task（会落重复文件）。

## 百度离线下载 cloud_dl API（已实证契约）

认证：BDUSS cookie（+STOKEN 可选），凭证只读不打印。先取 bdstoken：

    GET https://pan.baidu.com/api/gettemplatevariable?clienttype=0&app_id=250528&web=1&fields=["bdstoken"]
    → JSON result.bdstoken（32 hex）
    回退：GET https://pan.baidu.com/disk/home 正则 "bdstoken":"<32hex>"

基址 `https://pan.baidu.com/rest/2.0/services/cloud_dl`，公共参数
`app_id=250528&bdstoken=<t>&clienttype=0&web=1`：

- 添加：`method=add_task&save_path=<网盘目录>&source_url=<URL>` → `{task_id, rapid_download, save_path}`。
  `rapid_download=1`=秒传（百度已有缓存，瞬时）；`=0`=需真实回源。
- 查询：`method=query_task&task_ids=<id>&op_type=1` → `task_info[id]{status,file_size,finished_size,finish_time,save_path,...}`。
- 列表：`method=list_task&status=255&start=0&limit=N&need_task_info=1`。
- 取消：`method=cancel_task&task_id=<id>`（11-18 实测此形式有效，返回仅 request_id；
  卡死任务取消后重新 add_task 即换新节点群）。
- 并发上限约 4-5，超出返回 409。
- list_task 的 file_size/finished_size 可能为 null，精确进度以 query_task 为准。

### 状态语义与陷阱（务必遵守）

- **所有数值字段是字符串**（"0"/"1"/"15444"）。比较前必须 `int()` 转换：`"0"` 是真值字符串，
  `fs and fin>=fs` 在 fs="0" 时恒真 → 假完成。先 int 再判。
- 真完成 = `status==0` 且 `file_size>0` 且 `finished_size>=file_size`，且 file_size 与源文件实际大小相符；
  落盘以 `pcs.sh ls` 文件名+大小复核。
- `status==5` = 终态失败/取消。
- **假完成识别**：`file_size==1` + 秒级 finish_time + status 非0 = 回源失败（百度只取到 1 字节），
  不是完成。不能只看 `finished>=file_size`（1>=1 会误判）。
- **境外源可达性因源而异**：raw.githubusercontent.com 百度节点取不到（假完成 1 字节）；国内源正常。
  自有境外服务器回源连通性必须先用无 IP 探针实测，不要假定可达。
- save_path 目录建议先 `pcs.sh mkdir` 建好。测试产物用后 `rm` + `cancel_task` 清理。

## 临时 HTTPS 链接载体（nginx secret-token location，本机已持久化）

供百度回源/极空间下载用的临时投递位置。**本机已部署并端到端实证（11-18）**；
其他主机复刻时配置结构如下（插入逻辑已 ad-hoc 验证）。
在现有 TLS server 块内、proxy `location /` 之前插入：

    location /media-temp/ {
        alias /var/www/media-temp/;
        autoindex off;
        limit_except GET HEAD { deny all; }
        try_files $uri =404;
        add_header X-Robots-Tag "noindex, nofollow" always;
        add_header Cache-Control "no-store" always;
        add_header X-Content-Type-Options nosniff always;
    }

- 文件放 `/var/www/media-temp/<32hex随机token>/<file>`，token 用 `secrets.token_hex(16)` 不可猜。
- 服务目录用 `/var/www/...`（nginx worker 可读）；不要用 /home/admin 下 scratch（可能 700 不可 traverse）。
- 先投无 IP 探针测连通，再投真实素材；用后即清文件，空目录 location 无暴露面。
- 改 nginx 需 root：备份 conf → 幂等插入 → `nginx -t` → `systemctl reload nginx` → `curl -sI` 验证 200。
- 本机免密 sudo 可用（`sudo -n`），布点/清理可全自动；token 目录 chown 给运行用户，
  素材拷入后 chmod 644（nginx worker 可读）。

## 生产脚本用法（scripts/）

    S=~/wuhoo-workspace/skills/shared/wuhoo-netdisk/scripts

    # 配对一条命令（推荐）：prompt+附件直传，素材自动布点→离线下载→落盘验证→清布点
    python3.11 $S/upload_deliverable.py --type 视频 --name <slug> --date YYYYMMDD \
        --prompt /path/prompt.md --asset /path/big.mp4 --extra sidecar.json --offline

    # 单链接入库（素材已在可回源的 HTTPS 直链上）
    python3.11 $S/offline_deliver.py --url <https直链> --save-path <网盘目录> \
        --name <文件名> --size <字节数> [--timeout 900]

退出码：0 成功且验证过；2 任务失败/验证不符；3 超时（task_id 保留可续查）；4 凭证问题。
卡死判读与重试：status=1 长期 0/0 + nginx 日志静默 → cancel_task + 重跑（换节点群）。

## Hermes 工具层坑（本工作流实测）

- terminal 命令里 `$(...)` 命令替换会被安全过滤层替换成 `***`（含写 .sh 文件时）→
  编排逻辑一律走 execute_code 或纯 Python 脚本文件，token 等动态值用文件传递。
- execute_code 有 300s 硬超时（超时杀内核连带子进程）→ 长轮询用 terminal background
  跑脚本+日志文件，或拆成多次短 query_task；百度侧任务不受轮询进程死亡影响。
- notify=true 参数偶发序列化失败 → 可省略 notify 改主动 poll 日志。

## 极空间（Zspace）NAS 能力（研究事实，供 NAS 路线）

- 内置远程下载/下载中心支持 URL 直链+磁力+BT，手机 App/PC 均可远程创建任务（不依赖 frp）。
- 官方免费内网穿透/中继；WebDAV 服务端口 5005；Docker（Aria2/Alist/CloudDrive2）。
- 原生百度网盘集成（cloud-down baidu：Baidu→NAS）；远程挂载支持 FTP/SFTP/Amazon S3（OSS S3 兼容可挂）。
- zspace-cli 社区项目（CLI/SDK/MCP，逆向官方 2000+ API）：`download-add <URL> <NAS路径>` 自动化远程下载。
