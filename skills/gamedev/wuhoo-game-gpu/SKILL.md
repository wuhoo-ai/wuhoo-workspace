---
name: wuhoo-game-gpu
description: "Use for GPU node ops: health, MCP, sync, remote env."
version: 3.6.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, gpu, remote, mcp, frp, ssh, unity-editor, comfyui]
    related_skills: [wuhoo-game-ci, wuhoo-game-debug, wuhoo-game-scene]
---

# wuhoo-game-gpu — GPU 节点运维

> GPU 节点 = Windows PC (RTX 4070Ti) + frp 隧道 + 双 Unity 项目 + C:\ai 常驻服务。
> GDD 依据(权威): guimei 09-ai-production-pipeline.md 第十一章(决策97/99/106) + 10-gpu-node-setup.md v1.0(详细版)。
> 本 skill 与 10-gpu-node-setup.md 冲突时以 GDD 文档为准。

## 触发条件

- GPU 节点上线/下线/开机后状态检查
- MCP 连接断开
- 需要远程 Unity 操作（Author/截图/PlayMode）
- 代码同步（云端→GPU 或反向）
- guimei 管线部署（ComfyUI/kohya_ss/guimei-lab; LivePortrait/Spine 已被决策110否决, 见§7废弃标记）

## 1. 连接信息

```bash
# SSH 通过 frp 隧道
ssh -i ~/.ssh/hermes-gpu -p 2222 -o ServerAliveInterval=15 -o ConnectTimeout=10 haohaijiao@localhost "command"
```

| 项目 | 路径 (Windows) |
|------|----------------|
| miners-watch | C:\Users\haohaijiao\miners-watch (Unity 6000.5.4f1) |
| guimei-lab | C:\ai\guimei-lab (Unity 6000.5.4f1, 与 miners-watch 同版本; 决策订正 2026-08-11 弃 6.2) |
| AI 工具根 | C:\ai\ (ComfyUI/kohya_ss, 短路径无中文; LivePortrait 已否决不部署) |

## 2. 健康检查清单（一键）

```bash
# Windows cmd 注意: 没有 head/tail/grep! 用 findstr / dir; 中文输出为 GBK 乱码属正常, 用英文标记定位
ssh -i ~/.ssh/hermes-gpu -p 2222 haohaijiao@localhost "
  echo === SSH === && whoami
  echo === UNITY === && tasklist | findstr Unity
  echo === FRPC === && tasklist | findstr frpc
  echo === GIT === && cd C:\Users\haohaijiao\miners-watch && git branch --show-current && git status --short && git log --oneline -1
  echo === GPU === && nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu,driver_version --format=csv,noheader
  echo === DISK === && fsutil volume diskfree C:  # wmic 已被 Windows 移除(2026-08-30实测 \"'wmic' 不是内部或外部命令\"); fsutil 内置可用, 输出含字节数(中文行 GBK 乱码但数字可读); PowerShell 备用: powershell -NoProfile -Command \"Write-Host ([math]::Round((Get-PSDrive C).Free/1GB,1))\"
  echo === AI_DIR === && if exist C:\ai (dir C:\ai /b) else (echo C:\ai NOT_EXISTS)
  echo === POWER === && powercfg /getactivescheme | findstr /i GUID
"
```

| 检查项 | 期望 | 失败处理 |
|--------|------|---------|
| SSH 隧道 | 连接成功 | 检查 frpc / 用户 PC 是否开机未睡眠 |
| frpc | 进程存在 | 重新配置 schtasks 自启 |
| Unity Editor | 进程存在 | 手动启动或 MCP 重连 |
| MCP 连接 | read_console 可执行 | 重启 Unity AI Assistant 插件 / MCP bridge |
| Git 工作区 | 干净或仅未跟踪 meta + 与远程同步 | `git pull --rebase origin v1.1-dev`; 未跟踪 .meta 必须 add+commit(场景引用依赖) |
| GPU | 显存有余量, 温度正常 | 检查是否有训练/烘焙抢占 |
| 磁盘 | C 盘 ≥50GB 空闲 | 清理模型缓存 |
| 驱动 | ≥545 (CUDA 12.1 兼容) | 升级驱动 |
| C:\ai | 存在且含 ComfyUI | guimei 部署未开始, 见 §7 |
| 电源方案 | 从不睡眠 (休眠超时=0) | `powercfg /change standby-timeout-ac 0` (远程可设) |

## 3. 代码同步

```bash
# 云端 push 后，GPU 拉取
ssh -i ~/.ssh/hermes-gpu -p 2222 haohaijiao@localhost \
  "cd C:\Users\haohaijiao\miners-watch && git pull --rebase origin v1.1-dev 2>&1"

# GPU push 后（场景 Author 等），云端拉取
cd /home/admin/miners-watch && git pull --rebase origin v1.1-dev
```

Pitfall: Windows cmd 无 head/tail——git 输出大时直接全量输出或用 `findstr` 过滤，别在远程命令里用 Unix 管道。

## 4. MCP 操作（决策106: MCP for Unity 主通道）

工具经 tool_search/tool_describe 加载, 实际工具名为 `mcp__unity__*`:

| 操作 | 工具 |
|------|------|
| 读 Unity Console | mcp__unity__read_console (action=get, types=["error"]) |
| 执行 C# 代码 | mcp__unity__execute_code |
| 执行菜单项 | mcp__unity__execute_menu_item "Hermes/Author Surface Scene" |
| 资源导入/场景组装 | mcp__unity__manage_asset / manage_scene / manage_gameobject |
| 刷新资源 | mcp__unity__refresh_unity |
| 截图 | mcp__unity__manage_camera 或 capture 相关 |
| 切换活动实例 | mcp__unity__set_active_instance (Name@hash) |

### 多实例切换（miners-watch ↔ guimei-lab 并存时, 2026-08-14 实测）

两项目都装 mcp-for-unity 插件(都监听 6400, frp unity-mcp proxy 转发), MCP server 会记着上次连的实例。关一个开另一个后, execute_code 报错:
`instance 'miners-watch@xxx' not found. Available instances: ['guimei-lab@xxx']`。处理:
1. 从报错信息拿新实例名(Name@hash)
2. `mcp__unity__set_active_instance` 传 `guimei-lab@xxx`
3. execute_code 验证 `Application.dataPath` 指向目标项目

### 退出 Unity（关编辑器）

- `mcp__unity__manage_editor` **无 quit/exit 动作**(只有 play/pause/stop 等)
- 用 execute_code 调 `UnityEditor.EditorApplication.Exit(0)`, 但 **safety_checks 默认会拦 `EditorApplication.Exit`**(Blocked pattern), 需 `safety_checks=false`
- 退出前先 `if(scene.isDirty) EditorSceneManager.SaveOpenScenes()` 防丢场景改动

## 5. 场景 Author（GPU 专属操作）

```
Hermes → Author Surface Scene
Hermes → Author Shallow Cave Scene
Hermes → Author Mid Cave Scene
Hermes → Author Deep Cave Scene
```

- 场景改后必须重新 Author 所有场景（CLAUDE.md 铁律）
- Author 后必须 commit + push .unity 文件（CI Gate 2 scene-integrity-check 依赖）

## 6. 用户离开前准备清单

1. 确认 frpc 自启已配置（schtasks）
2. 确认 Unity Editor 保持运行（miners-watch 或 guimei-lab）
3. 确认 git 工作区干净
4. 确认 SSH 隧道可连通
5. 关闭显示器但**不关机不休眠**（锁屏 OK）

## 7. guimei 侧部署（GDD 10-gpu-node-setup.md 要点, 详细操作看 GDD）

> 状态标记: [x]=已完成 / [ ]=待执行。C:\ai 不存在 = 全部未开始 (2026-08-07 实测)。

### 阶段 0: 账号与支付（用户手动, 30分钟）
火山方舟 API Key(Seedream/Seedance) / 即梦会员 / 哩布哩布+吐司(模型下载)。Key 交 Hermes 存配置不入 git。
~~Spine 购买~~ —— **决策110 否决**(2026-08-10): 纯皮影美学+Unity 2D Animation 部件补间唯一, Spine 不再需要。

### 阶段 1: GPU 节点基础（远程可执行）
- [x] frp 隧道（已有, 矿工守夜在用）
- [ ] Python 3.10-3.12 装到 C:\ai\python（短路径, 不装系统路径; 2026-08-07 实测系统无干净 Python）
- [x] Git（已有）
- [ ] Unity 6.2 安装（Hub, URP 2D 模板; 与 6000.5.4f1 并存）
- [x] 磁盘 ≥50GB（实测 350GB 空闲 ✓）
- [x] 驱动 ≥545（实测 610.62 ✓）
- [ ] 电源从不睡眠: `powercfg /change standby-timeout-ac 0` + `powercfg /change hibernate-timeout-ac 0`（远程可设）

### 阶段 2: ComfyUI（核心常驻, 远程可执行）
```powershell
cd C:\ai
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI
python -m venv venv
venv\Scripts\activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
# pip 慢 → 清华源: pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```
- 启动: `.\run_nvidia_gpu.bat` 常驻最小化; 验证: `curl http://127.0.0.1:8188/system_stats`
- 模型: models/checkpoints 放 sd_xl_base_1.0 + DreamShaper/Juggernaut XL; ControlNet: 线稿/深度/IP-Adapter (SDXL 版); 自定义节点: ComfyUI-Manager → IPAdapter_plus/ControlNet_Aux/LayerDiffuse
- 接口: Local MCP 为主(决策99) + REST 兜底

### 阶段 3: kohya_ss（LoRA 训练, 远程可执行）
```powershell
cd C:\ai
git clone https://github.com/bmaltais/kohya_ss
.\setup.bat
# dataset: 20-30 张图 + 同名 .txt caption
```
- 长训练禁用 SSH 直挂: `Start-Process -WindowStyle Hidden` 分离或计划任务

### 阶段 4: LivePortrait —— 【已废弃, 禁止部署】
~~立绘说话(远程可执行): git clone KwaiVGI/LivePortrait~~
**决策110 否决**(2026-08-10): 表情=换头茬+活眼活口(纯皮影美学), 不用 LivePortrait/网格畸变类立绘驱动; 过场视频保留 Minimax H3/HappyHorse(见 §10.7), 与本阶段无关。

### 阶段 5: Unity guimei-lab（远程可执行, 最耗时）
- 项目已建好(2026-08-14 实测): C:\ai\guimei-lab, 6000.5.4f1 + URP 2D(17.0.3) + MCP embed 包(com.coplaydev.unity-mcp) 就位
- 启动(SSH 下 GUI 程序必须 schtasks 分离, 否则假启动):
  `schtasks /create /tn wuhoo_guimei_lab /tr "\"C:\Program Files\Unity 6000.5.4f1\Editor\Unity.exe\" -projectPath C:\ai\guimei-lab" /sc once /st 00:00 /f & schtasks /run /tn wuhoo_guimei_lab`
  (注意 /st 过去时间会警告但不影响 /run 强制运行; 首次加载几分钟, 验证标志=6400 端口 LISTENING + execute_code dataPath=C:/ai/guimei-lab/Assets)
- MCP: 决策106 = MCP for Unity(CoplayDev/unity-mcp) 主通道; 备路 = miners-watch 的 Unity AI Assistant 插件(MCP Bridge)复用
- Run In Background 勾上(Project Settings → Player, 防失焦暂停)
- 验证: 云端 read_console → 0 errors

### 阶段 6: Spine —— 【已废弃, 不再执行】
~~官网下载试用 → 导入分层角色图绑定导出~~
**决策110 否决**(2026-08-10): 绑定走 Unity 2D Animation 硬关节(锚点配对制), Spine 购买/部署/导出全链路废弃。

### 阶段 7: 端到端验证（周末与用户协作）
- [x] 三版方向图(即梦 vs 本地 SDXL vs 万相), 用户拍板色彩方向 —— 已完成(风格圣经 v3.1 验收, 决策110 后为皮影部件图基准)
- [x] 「桥上超度」AI 视频初试 —— 已过时(决策110/113-115: 过场走 H3/HappyHorse, 见 §10.7)
- [ ] 吴守桥锚定卡 → 立绘说话 demo —— LivePortrait 路线已废(决策110), 如重启需按换头茬+活眼活口重立题
- [ ] 回收待验证: ~~Spine 支付~~(已废) / godmodeai / Mirage2 / 模型站下载速度

### 常驻服务存活铁律
- 所有常驻服务不要挂在 SSH 会话启动（断连即死）: 用户本地启动 / 计划任务 / `Start-Process -WindowStyle Hidden`
- 开机自启建议: ComfyUI 注册计划任务（开机启动, 隐藏窗口）

## 8. 防呆与故障排查（GDD 10 文档, 全部已踩坑验证）

### 三条禁令（愚蠢问题高发区）
1. **别用鼠标点黑色终端窗口**——Windows 控制台快速编辑模式: 鼠标选中文本会挂起正在跑的进程!
2. **别点窗口 X 关闭**——关窗口=杀进程。停服务用 Agent 命令/任务管理器。
3. **别注销/别睡眠/别休眠**——锁屏和关显示器完全 OK, 睡眠断 SSH 和所有服务。

### 故障排查表
| 症状 | 排查 |
|------|------|
| 云端 SSH 不通 | frpc 在跑? 节点睡眠? `tasklist | findstr frpc` |
| ComfyUI 不响应 | 本地浏览器开 8188? 黑窗口被鼠标点中挂起? |
| 训练/生图很慢 | nvidia-smi 看 GPU 占用; 被 Unity 烘焙抢占? |
| Unity MCP 断 | 编辑器被关闭? 重启编辑器后 MCP 重连 |
| 磁盘满 | 模型缓存清理; 生图输出定期归档到 guimei 仓库 |
| 远程命令中文乱码 | GBK 输出正常现象, 用英文标记定位, 别依赖中文匹配 |

## 9. 远程环境搭建（新节点）

1. 安装 Unity Hub + Unity 6000.5.4f1 (miners-watch) / 6.2 (guimei-lab)
2. 安装 Git + 配置 SSH key
3. 安装 frpc + 配置隧道（SSH 端口 2222）
4. 配置 schtasks 自启 frpc
5. 安装 Unity AI Assistant 插件（MCP Bridge）
6. 克隆仓库 + 打开项目
7. 验证: 云端 SSH → MCP read_console → 0 errors

## 10. GPU 批处理任务（FUTURE）

> 当前未启用。GPU 节点空闲时可运行:
> - HeartMuLa 音乐生成
> - Blender headless 3D 建模
> - 批量 AI 生图后处理
>
> 启用条件: 用户明确指示 + 节点空闲 > 2h。

## 10.5 部署实战经验（2026-08-07 全量部署验证）

### 网络通道矩阵（用户机器实测，GitHub 主站不通）
| 目标 | 状态 | 用途 |
|------|------|------|
| github.com | ✗ 不通 | 主站全挂 |
| api.github.com | ✓ 直连 200 | API 可用（release 信息） |
| codeload.github.com | ✓ 可达(301→200) | 仓库 zip 下载，大仓库打包慢易超时 |
| ghfast.top 代理 | ✓ 快 | `https://ghfast.top/https://github.com/...`（archive zip 38MB/40s） |
| gitee.com/mirrors/ComfyUI | ✓ | ComfyUI 镜像（git clone 正常） |
| modelscope.cn | ✓ 快 | 模型下载主力（SDXL/LivePortrait 权重） |
| 清华 PyPI | ✓ | pip 源 |
| mirrors.aliyun.com/pytorch-wheels | ✓ | **cu121 wheel 下载**（比 pytorch.org 快） |
| hf-mirror.com / liblibai / ghproxy 系列 | ✗ | 全不通 |
| 本地代理 127.0.0.1:10809 | 存在 | **pip 走代理会卡死/失败，curl 直连反而通** |

### 关键坑（全部实测踩过）
1. **PyPI 的 Windows torch wheel 是 CPU 版**（203MB，"Torch not compiled with CUDA"）——CUDA 版必须从 cu121 index 下：`mirrors.aliyun.com/pytorch-wheels/cu121/torch-2.5.1%2Bcu121-cp311-cp311-win_amd64.whl`（2.4GB）
2. **Start-Process 在 SSH 会话下假启动**（子进程不存活）——所有长任务用 `schtasks /create + /run`（计划任务分离，SSH 断开不影响）
3. **schtasks /tr 里 `&&` 转义失败**（"系统找不到指定的路径"）——用绝对路径单命令，或多命令写 bat 文件
4. **bat 文件 URL 里 `%2B` 必须写 `%%2B`**（cmd 批处理变量解析会吞掉 %2B 导致 404）
5. **modelscope 文件下载**：`repo/files?Recursive=true` 返回的 JSON 有 `Path` 字段（含子目录）；下载 URL = `repo?Revision=master&FilePath=<Path>`（302 跳转需 curl -L；cmd 里 & 要 ^& 转义）
6. **Unity Hub CLI 无 create 命令**（Hub 3.15.2 报 "create is not a Hub command"）——用 `Unity.exe -createProject <path> -batchmode -quit -nographics` 创建默认项目
7. **默认项目是内置管线**：manifest.json 加 `com.unity.render-pipelines.universal: 17.0.3`（版本参照 miners-watch）+ 编辑器脚本（base64 传远程写 Assets/Editor/Setup2D.cs）`-executeMethod Setup2D.Run` 创建 Renderer2DData + UniversalRenderPipelineAsset 并设 GraphicsSettings
7b. **默认项目缺 UGUI 包**（2026-08-14 实测）: createProject 默认项目只有内置 `com.unity.modules.ui`(Canvas/RectTransform 底层), **不含 `com.unity.ugui`**(提供 UnityEngine.UI 命名空间的 Text/Image/Button/EventSystem)。脚本 `using UnityEngine.UI` / `AddComponent<Text>()` 必报 `error CS0234: 'UI' does not exist in namespace 'UnityEngine'` + 连带 Bee ScriptUpdater "failed to produce updates.txt" 假报错, 且 Assembly-CSharp.dll 不生成(类型找不到, CleanBuildCache 无效)。修复: MCP `manage_packages add_package com.unity.ugui@2.0.0`(Unity 6000.5 resolve 到 2.5.0) + refresh 编译。竖排文字/对话 UI 凡用 UGUI/TMP 都需显式加对应包(com.unity.ugui / com.unity.textmeshpro)。诊断: Editor.log 在项目相对路径 `C:\ai\guimei-lab\Logs\Editor.log`(非 %LOCALAPPDATA%, 日志里写"Logs moved to project-relative"), 用 findstr 找 "error CS" 拿真编译错误。
8. **MCP for Unity 包**：OpenUPM registry（scope com.coplaydev.unity-mcp）；离线方案=复制已有项目 `Library/PackageCache/com.coplaydev.unity-mcp@<hash>` 到新项目 `Packages/` 作 embed 包 + manifest 写 `file:Packages/com.coplaydev.unity-mcp`
9. ProjectSettings.asset 里字段是小写 `runInBackground: 0`（不是 m_RunInBackground）
10. **Unity.exe -help 会挂起进程**（Electron/license 弹窗）——别跑，超时后 taskkill
11. Unity batchmode 首次打开项目要几分钟（下载 URP 包），验证标志=`Exiting batchmode successfully now!`
12. ComfyUI 首次启动 ~90s，验证=`curl 127.0.0.1:8188/system_stats` 返回 devices 含 cuda

### 部署验证命令速查
```bash
# CUDA 验证
C:\ai\ComfyUI\venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# ComfyUI 服务
schtasks /run /tn wuhoo_comfy; curl http://127.0.0.1:8188/system_stats
# 文件完整性（对照 modelscope API 的 Size 字段，字节精确匹配）
dir C:\ai\ComfyUI\models\checkpoints\sd_xl_base_1.0.safetensors  # 6,938,078,334 字节
```

## 10.6 Wan2.1 i2v + Video-Retalking 视频管线（2026-08-08 全链路验证）

> 链路: 正式立绘 → Wan2.1 i2v 分段续帧 → Video-Retalking 口型同步 → ffmpeg 合成 → WebDAV 上传 NAS
> **铁律: Video-Retalking 的 face 输入必须用 Wan 输出视频, 不是 LivePortrait 产物!** 否则苏小小脸会被替换(用户实测出现"男人脸")。

### Wan2.1 i2v 关键配置（ComfyUI 0.28, GPU 4070Ti 16GB）
- 模型: `wan2.1-i2v-14b-480p-Q5_K_M.gguf` (UnetLoaderGGUF, weight_dtype=default) + `Wan2.1_VAE.pth` + **umt5 必须用 Comfy-Org repackaged `umt5_xxl_fp8_e4m3fn_scaled.safetensors`**（modelscope 的 pth 格式 ComfyUI 不认; 768维/4096维错误 = 编码器不对）
- 参数: 832x480, length=81 (单次上限), fps=25, steps=20, cfg=6.0, euler/simple
- **长视频方案**: 单次最多 81 帧=3.24s。9.73s 对白 → 3 段各 81 帧, 每段用上段尾帧作 start_image 续帧, 最后 concat。脚本: `/tmp/wan_multi_seg.py` (seed 递增避免重复)
- 抽尾帧: `ffmpeg -y -sseof -0.1 -i seg.mp4 -frames:v 1 last.png` (Windows 无 tail, 用 findstr)
- 耗时: 81帧约 25 分钟 (GPU 满载 100%, 9.8GB)
- SaveVideo 输出在 ComfyUI 0.28 的 outputs 里是 `images` 字段 (animated=true), 不是 gifs/videos

### Video-Retalking 配置
- venv: `C:\ai\video-retalking\venv`, 推理: `inference.py --face <视频> --audio <wav> --outfile out.mp4 --tmp_dir p0 --LNet_batch_size 8`
- 19 个权重文件在 `C:\ai\video-retalking-main\checkpoints\` (DNet/ENet/LNet/GFPGAN/GPEN-BFR-512/ParseNet/RetinaFace/face3d/shape_predictor/expression.mat/BFM 9件)
- 音视频合成: `ffmpeg -y -i retalk.mp4 -i voice.wav -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest -movflags +faststart final.mp4`
- 口型质量依赖 face 视频清晰度——Wan 输出 832x480 直接可用

### 权重中转链（GPU 无法直连 HF/Google）
```
云端新加坡: hf download → GitHub release (public repo, 需先 bootstrap commit)
GPU: gh-proxy.com 前缀下载 (3.1MB/s, 比 ghfast 0.15MB/s 快 20x)
兜底: HF 链接发给用户, 他家宽可能直连; 或 NAS WebDAV 中转 (10MB/s)
```
- 私有 repo 的 release 资产 GPU 无 token 拉取返回 404 → **必须 public**
- 空 repo 不能发 release → 先提交 README

### 素材一致性校验
- 立绘/音频传到 GPU 后必须 MD5 校验: 云端 `md5sum`, GPU `certutil -hashfile X MD5 | findstr /v hash`

## 10.7 H3 (MiniMax-H3) Ref2VA 视频管线（2026-08-08 全链路验证）

> 链路: 立绘(身份) + 风格标杆图(风格) + 对白 → H3 Ref2VA 音画生成 → 音频环境音 → ffmpeg 合成对白 → WebDAV 上传 NAS
> **铁律 1: ref_images 只做"身份"参考, 风格必须写进 prompt**(风格圣经语言: 中唐水墨重彩志怪/墨线为骨·重彩为肉/纸绢质感/禁忌照片写实)
> **铁律 2: 素材上传必须 MD5 校验**(scp 静默损坏: GPU MD5 ≠ 云端 MD5 → 生成结果与参考图毫无关系)
> **铁律 3: 成品只传 NAS 不发微信**

### H3 部署关键（ComfyUI 0.31.0, GPU 4070Ti 12GB）
- 四件套权重(modelscope `Comfy-Org/MiniMax-H3`): audio_vae 605MB / video_vae 5.2GB / text_encoder qwen3vl nvfp4_awq 15.7GB / diffusion ref2va pruned_int8 20.97GB
- **kitchen 版本必须锁 `comfy-kitchen==0.2.27`**: 0.2.28 需 torch2.6+ 启动崩溃; 0.2.22 缺 AsymW4A8Int8Layout → nvfp4 加载失败 (`'NoneType' object has no attribute 'Params'` @ ops.py:1616)
- 启动: schtasks `wuhoo_comfy8188` + bat (`C:\ai\start_comfy8188.bat`), 日志 `C:\ai\logs\comfy8188.log`
- H3 节点: `EmptyMiniMaxH3LatentAV` / `MiniMaxH3ImageToVideo` / `MiniMaxH3ReferenceToVideo` / `MiniMaxH3SigmaShift`

### Ref2VA workflow 要点（0.31 API）
- 链路: CLIPLoader(type=minimax) → UNETLoader → 双 VAELoader(video_vae + audio_vae) → Ref2VA → SigmaShift(shift_video=12.0/shift_audio=3.0) → KSampler(cfg=1.0, euler/simple, 20 steps) → VAEDecode → CreateVideo(fps=24) → SaveVideo(format=mp4, **codec=h264 必填**)
- 音频: VAEDecodeAudio(vae=audio_vae) → SaveAudio (flac)
- **0.31 Autogrow 用复数容器**: `ref_images: [["7",0],["18",0]]` (不是 ref_image_0 单数)
- negative: ConditioningZeroOut (Ref2VA 只输出 positive, cfg=1.0 时 negative 不参与)
- ref_image_size: **match**=缩到生成分辨率(快4.5倍, 身份"神似"); **max**=2048px短边(慢~133s/it, 身份"形似")

### 风格 prompt 模板（guimei 风格圣经 v2.0）
```
Zhong-Tang ink-wash heavy-color zhiguai style, like <Picture 2>. The woman from <Picture 1> stands...
Ink line as skeleton: fine brush strokes... Heavy color as flesh: mineral pigments - azurite blue dyes the river,
ochre dyes the muddy bank, cinnabar touches the paper lantern... Paper and silk texture, silk grain visible...
Light accent: warm lantern glow... Sparse-dense contrast composition. Forbidden: no photorealism,
no western illustration style, no modern elements.
```

### 性能实测（4070Ti 12GB 层卸载）
| 配置 | 速度 | 备注 |
|------|------|------|
| 无音频 + match | ~29-35s/it, 12min/5s | 最快 |
| 带 ref_audios + match | ~115-130s/it, ~40min/5s | 音频参考显著拖慢 |
| max 模式 | ~133s/it, ~44min/5s | 最慢, 身份保真最高 |
| length=243 (10s) | **OOM** | 12GB 显存装不下, 需降分辨率或分段 |

### 长视频方案（10s 完整对白）
- **分段拼接**: 2×5s (124帧) 各自生成, 段2 用段1尾帧作 ref 续帧, 最后 concat — 当前方案
- 或降分辨率 512x288 单段 (未验证)

### 已踩坑清单
1. **frpc `transport.tcpMux=false` 导致 login EOF**: frp 0.70.0 组合下握手即断 (`connect to server error: EOF`), 去掉即恢复; 心跳 heartbeatInterval=10/heartbeatTimeout=30 + log.to 落盘已配
2. SaveVideo 缺 codec → `missing 1 required positional argument: 'codec'`
3. VAEDecodeAudio 参数名是 `vae` 不是 `audio_vae`
4. 采样完成后 SaveVideo 崩溃 (`Fatal Python error: Aborted` 在 Pin error 后) — 重跑同 workflow 缓存命中可跳过采样, 只补保存
5. 参考图损坏 → 生成结果与参考毫无关系 (scp 传输中断静默损坏, 必须 MD5)
6. 完整版 243帧 OOM → 分段
7. 音频参考拖慢采样 ~3-4 倍

## 10.8 Z-Image + SenseNova U1.5 本地生图双轨（2026-08-22 部署验证）

> 双轨 POC: Z-Image Turbo (通义, GGUF Q8) + SenseNova-U1.5-8B-MoT-Preview (商汤, GGUF Q4) 本地出图,
> 走 ComfyUI GGUF 管线。权重从 NAS `/public/Backup/guimei-transfer/model/` WebDAV 拉取。

### 部署状态
- 模型: `z_image_turbo-Q8_0.gguf`(7.2GB)→`models/diffusion_models/`; `SenseNova-U1.5-8B-MoT-Preview-Q4_0-v2.gguf`(10.9GB)→`models/gguf/`; VAE `ae.safetensors`=GPU 已有 `zimage-ae.safetensors`(同一文件, 335,304,388 字节, 跳过); text encoder `Qwen3-4B-UD-Q5_K_XL.gguf` 已有
- 节点: `ComfyUI_SenseNova_U1` (smthemex, gh-proxy 下载 161MB zip; 注册 `SenseNova_SM_Model`/`SenseNova_SM_Sampler`)
- 依赖: diffusers + accelerate + **transformers>=4.57.1,<4.58.0**(transformers 5.x 不兼容节点; 已锁 4.57.2)
- workflow 参考: NAS `zimage-gguf-workflow.json` → `ComfyUI/user/default/workflows/`(UNETLoader + SageAttention(KJNodes) + ModelSamplingAuraFlow shift=3)

### 关键坑（2026-08-22 全部实测）
1. **venv python 是 shim, wmic 会看到父子两个进程**——`C:\ai\ComfyUI\venv\Scripts\python.exe` 启动后会 spawn 真实解释器(`uv\python\cpython-3.11...\python.exe`)子进程, 命令行都含脚本名。**看到两个同名进程 ≠ 双实例**, 查 `ParentProcessId` 确认父子再判断。误杀 real 进程 = 下载中断(本日白下 7GB 的教训)
2. **`set PYTHONUTF8=1` 会让 python 静默启动失败**(无任何输出, 退出码 1)——只设 `set PYTHONIOENCODING=utf-8` + `chcp 65001` 即可解决 GBK/emoji 崩溃
3. **schtasks /ru SYSTEM 跑服务**: 需要先 `icacls <目录> /grant *S-1-5-18:(OI)(CI)F /T`(SYSTEM 默认无 C:\ai 写权限, 报 PermissionError); /ru 不带时默认当前 SSH 用户(hermes-agent)+"只使用交互式"限制 → **SSH 非交互登录下任务永不触发**(Last Result 267011=从未运行)
4. **start_comfy8188.bat 会丢**(曾丢失导致 ComfyUI 无法重启): 已重建在 C:\ai\start_comfy8188.bat(SYSTEM 版), 日志 `C:\ai\ComfyUI\comfy8188.log`(SYSTEM 无 C:\ai 根写权限, 日志放 ComfyUI 目录内)
5. **GPU 上的 pythonw 进程 = Hermes gateway**(`-m hermes_cli.main gateway run`)——**不是 ComfyUI!** 杀进程前必须 wmic 查 CommandLine, 别 taskkill 17688(会断 GPU Hermes 服务)
6. SenseNova 节点 import 时 transformers auto_docstring 打印 emoji → GBK logger 崩溃(`UnicodeEncodeError \U0001f6a8`)→ 整个节点 IMPORT FAILED。修复 = bat 加 PYTHONIOENCODING=utf-8 后重启
7. 大文件 WebDAV 下载正常速度 ~5MB/s(实测 4.7GB/16min); 用 Python urllib + Range resume + `.part` + 大小精确校验, 脚本模式见 dl_models.py 经验

### 双轨 POC 验证要点（下载完成后）
- Z-Image: UNETLoaderGGUF(z_image_turbo-Q8_0.gguf) + CLIPLoaderGGUF(Qwen3-4B-UD-**Q6**_K_XL.gguf, type=lumina2) + VAELoader(zimage-ae) + ModelSamplingAuraFlow(shift=3) + KSampler(8步,cfg=1,euler/simple), 20s/张 1024²。**Q5_K_XL 必失败**(reshape 249M≠319M), 必须 Q6(modelscope unsloth/Qwen3-4B-GGUF 3.66GB)
- SenseNova U1.5: SenseNova_SM_Model(gguf=文件名, diffusion_models=none, attn_backend=auto) + SenseNova_SM_Sampler(img_mode=interleave 文生图/edit 图编辑/vqa), ~10min/张(4图/次, MoT 慢)

### SenseNova U1.5 适配坑（2026-08-22 实测, 4 处代码修改才能跑）
1. transformers 4.57.2 bug: tokenization 加载 `_config.model_type` 对 dict 属性访问崩溃 → 模型目录 config.json `transformers_version` 改 "4.58.0" 绕过(该字段≤4.57.2 才触发 bug)
2. trust_remote_code 三连: AutoConfig.from_pretrained / AutoTokenizer(改为 `Qwen2Tokenizer.from_pretrained`, AutoTokenizer 的 elif 分支不传 trust) / AutoModel.from_config 全部显式 `trust_remote_code=True`
3. 模型目录 config.json 加 `"trust_remote_code": true`(config 级放行)
4. **modeling_neo_chat.py bug: interleave_gen 调 `_t2i_predict_v` 漏传 image_size**(10 处)→ 补 `image_size=image_size`, 否则 `'NoneType' object is not subscriptable`
5. 模型代码完整性: `SenseNova-U1.5-8B-MoT-Preview/` 目录需 9 个 py(从 `SenseNova/src/sensenova_u1/models/neo_unify/` 复制: configuration/modeling/conv 等)
6. **HF 动态模块缓存**(SYSTEM): `C:\WINDOWS\system32\config\systemprofile\.cache\huggingface\modules\transformers_modules\`——改源文件后必须删该目录缓存, 否则跑旧代码
7. 定位坑时看 `C:\WINDOWS\system32\config\systemprofile\.cache\huggingface\modules\transformers_modules\SenseNova_hyphen_...\modeling_neo_chat.py`(trust_remote_code 动态加载的副本, 与节点目录源文件对应)

## 10.9 frpc 服务化（NSSM, 2026-08-22 落地）

> frpc 曾是"登录时计划任务+可见 cmd 窗口"——被误关窗口 = 隧道断（上次结果 0xC000013A Ctrl+C）。已服务化根治。

### 现状（服务方式运行, 无需任何人工操作）
- 位置: `C:\ai\frp\`（frpc.exe + frpc.toml, 自 Downloads 迁出; 旧目录 Downloads\frp_0.70.0_windows_amd64 可删）
- 服务名: `frpc`（NSSM 2.24, `C:\ai\nssm.exe`; zip 已删, nssm.exe 保留）
- 特性: 无窗口 ✅ 开机自启(SERVICE_AUTO_START) ✅ **崩溃/被杀自动重启**（AppExit Default Restart, 实测杀进程 15s 内拉起）✅
- 常用命令: `nssm start/stop frpc` | `sc query frpc` | `sc failure` 由 NSSM 管理
- 日志: `C:\ai\frp\frpc-service.log`（NSSM stdout/stderr）+ frpc.toml log.to = `C:\ai\frp\frpc.log`

### 坑（全部实测）
1. **frp 0.70 不能 sc 直注册服务**（`sc create frpc binPath= ...` + `sc failure`）→ 启动 1053 超时: frpc 不响应 SCM 协议（服务实例能连云端但 SCM 判失败, 会与手动实例冲突循环）。**必须 NSSM 包装**（frpc 作子进程, 无服务协议要求）
2. **bat 里 `timeout /t N` 在 SSH 非交互环境报错** "Input redirection is not supported, exiting the process immediately" → 用 `ping 127.0.0.1 -n N >nul` 代替
3. **改 frpc.toml 路径用 PowerShell -replace 易失败**: toml 里路径是字面双反斜杠（`C:\\Users\\...`）, 单反斜杠匹配不到 → 用 Python `s.replace()`（匹配 `\\\\` 双反斜杠文本）最稳
4. **改 frpc 的顺序铁律**: 先建好新实例（服务）→ 最后才杀旧实例。杀 frpc = 断掉 SSH 隧道自身, 操作中断（本次 20:20 曾因此把会话切断, 服务没建完）
5. 杀手动实例按 PID 或按路径过滤（`wmic process where "name='frpc.exe' and ExecutablePath like '%Downloads%'"`）, 勿误杀服务实例（同路径 C:\ai\frp 时按 PID）

### 启动项排查（2026-08-22, 重启后黑窗口来源）
- **曾存在 `启动文件夹\frpc.exe.lnk`**（指向旧 Downloads 路径, 登录弹黑窗口+双重启动）→ 已删。启动文件夹现仅: Hermes_Gateway.vbs（sh.Run ...,0 隐藏窗口, 保留）+ v2rayN.exe.lnk（GUI 代理, 用户工具, 保留）
- **wuhoo_comfy_autostart（Logon+Hidden:False+直接跑 bat）= 弹黑窗口** → 已禁用（ComfyUI 由 wuhoo_comfy8188 SYSTEM 任务负责自启, 冗余）
- 查启动项三板斧: `schtasks /query /fo csv` + 启动文件夹 dir + `reg query ...\Run`; 触发器用 PowerShell `Get-ScheduledTask | %{ $_.Triggers.CimClass.CimClassName }` 筛 Boot/Logon; 窗口判定看 `Settings.Hidden` + 动作是否 bat/console exe; SYSTEM 任务窗口在会话0不显示, Hidden:False 也无妨
- wuhoo_comfy8188 是 SYSTEM 运行（会话0无可见窗口）✅; 第三方 Logon 任务（ZJRC 签名/ASUS/WPS/OneDrive/Edge）均为 GUI/托盘, 不干扰 frpc

## 变更历史

- v3.6.0 (2026-09-01): §2 健康检查磁盘命令 wmic→`fsutil volume diskfree C:`(wmic 已被 Windows 移除, 健康检查 cron 每轮失败兜底的实测故障, PowerShell 降为备用); §7 清理决策110 否决的部署残留: 阶段4 LivePortrait/阶段6 Spine 标废弃禁部署, 阶段0 移除 Spine 购买, 阶段7 验证清单标注过时项
- v3.5.0 (2026-08-22): §10.8 增补双轨 POC 验证结果(Z-Image 20s/张可用, SenseNova ~10min/张风格跑偏) + SenseNova U1.5 适配 7 坑(transformers 4.57.2 model_type bug/trust_remote_code 三连/config trust 字段/modeling 漏传 image_size/模型代码 9 py 完整性/HF SYSTEM 动态缓存/定位副本路径)

- v3.4.0 (2026-08-22): 新增 §10.8 Z-Image + SenseNova U1.5 本地生图双轨部署 — 模型/节点/依赖清单 + 7 个实测坑(venv shim 父子进程误判/PYTHONUTF8 静默失败/schtasks SYSTEM 需 icacls/交互式任务 SSH 不触发/start_comfy8188.bat 重建/pythonw=Hermes gateway 勿杀/GBK emoji 节点崩溃)

- v3.3.0 (2026-08-08): 新增 §10.7 H3 (MiniMax-H3) Ref2VA 视频管线 — 部署关键(kitchen锁0.2.27/四件套权重/schtasks启动)/Ref2VA workflow要点(0.31复数容器/SaveVideo codec必填/VAEDecodeAudio用vae参数)/风格prompt模板(铁律: ref_images只做身份, 风格必须写prompt)/性能实测表(match vs max/音频参考拖慢3-4倍/243帧OOM)/长视频分段方案/7个已踩坑(frpc tcpMux=false EOF/SaveVideo崩溃缓存跳过/参考图损坏MD5校验)
- v3.2.0 (2026-08-08): 新增 §10.6 Wan2.1 i2v + Video-Retalking 视频管线 — 全链路配置(umt5必须Comfy-Org repackaged/SaveVideo输出在images字段/单次81帧上限/分段续帧脚本)/19权重清单/口型铁律(face必须用Wan输出非LivePortrait)/权重中转链(gh-proxy 3.1MB/s)/MD5校验
- v3.1.0 (2026-08-07): 全量部署验证后新增 §10.5 实战经验 — 网络通道矩阵(ghfast/modelscope/阿里云pytorch-wheels) + 12 个实测坑(PyPI torch=CPU版/Start-Process假启动/schtasks转义/bat%%2B/modelscope Path字段/Hub无create/URP2D脚本/MCP包复制/runInBackground小写/-help挂起) + 部署验证命令速查
- v3.0.0 (2026-08-07): 对齐 GDD 09 第十一章(决策97/99/106) + 10-gpu-node-setup.md v1.0 — 新增 §7 guimei 侧 C:\ai 分阶段部署(含完成状态勾选) + §8 防呆三禁令/故障排查表; MCP 工具名更新为 mcp__unity__*(决策106 MCP for Unity 主通道); 健康检查加入 GPU/磁盘/驱动/C:\ai/电源; 记录 Windows 无 head/grep、GBK 乱码等实测坑
- v2.0.0: 合并 gpu-ops + remote-env + gpu-batch(FUTURE)
