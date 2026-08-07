---
name: wuhoo-game-gpu
description: "Use for GPU node ops: health, MCP, sync, remote env."
version: 3.0.0
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
- guimei 管线部署（ComfyUI/kohya_ss/LivePortrait/guimei-lab）

## 1. 连接信息

```bash
# SSH 通过 frp 隧道
ssh -i ~/.ssh/hermes-gpu -p 2222 -o ServerAliveInterval=15 -o ConnectTimeout=10 haohaijiao@localhost "command"
```

| 项目 | 路径 (Windows) |
|------|----------------|
| miners-watch | C:\Users\haohaijiao\miners-watch (Unity 6000.5.4f1) |
| guimei-lab | C:\ai\guimei-lab (Unity 6.2, 决策106, 未创建则先部署) |
| AI 工具根 | C:\ai\ (ComfyUI/kohya_ss/LivePortrait, 短路径无中文) |

## 2. 健康检查清单（一键）

```bash
# Windows cmd 注意: 没有 head/tail/grep! 用 findstr / dir; 中文输出为 GBK 乱码属正常, 用英文标记定位
ssh -i ~/.ssh/hermes-gpu -p 2222 haohaijiao@localhost "
  echo === SSH === && whoami
  echo === UNITY === && tasklist | findstr Unity
  echo === FRPC === && tasklist | findstr frpc
  echo === GIT === && cd C:\Users\haohaijiao\miners-watch && git branch --show-current && git status --short && git log --oneline -1
  echo === GPU === && nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu,driver_version --format=csv,noheader
  echo === DISK === && wmic logicaldisk get caption,freespace
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
火山方舟 API Key(Seedream/Seedance) / 即梦会员 / 哩布哩布+吐司(模型下载) / Spine 购买(esotericsoftware.com, 国际信用卡)。Key 交 Hermes 存配置不入 git。

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

### 阶段 4: LivePortrait（立绘说话, 远程可执行）
```powershell
cd C:\ai
git clone https://github.com/KwaiVGI/LivePortrait
pip install -r requirements.txt
```

### 阶段 5: Unity guimei-lab（远程可执行, 最耗时）
- Unity Hub CLI 装 6.2 → 新建 URP 2D 项目 C:\ai\guimei-lab（无中文路径）
- MCP: 决策106 = MCP for Unity(CoplayDev/unity-mcp, 47工具) 主通道; 备路 = miners-watch 的 Unity AI Assistant 插件(MCP Bridge)复用
- Run In Background 勾上(Project Settings → Player, 防失焦暂停)
- 验证: 云端 read_console → 0 errors

### 阶段 6: Spine（用户手动, 需购买）
官网下载试用 → 导入分层角色图绑定导出。Spine JSON/atlas = Hermes 可程序化格式, GUI 精修是唯一手动残留。

### 阶段 7: 端到端验证（周末与用户协作）
- [ ] 三版方向图(即梦 vs 本地 SDXL vs 万相), 用户拍板色彩方向
- [ ] 「桥上超度」AI 视频初试(万相/火山 Seedance)
- [ ] 吴守桥锚定卡 → 立绘说话 demo
- [ ] 回收待验证: Spine 支付 / godmodeai / Mirage2 / 模型站下载速度

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

## 变更历史

- v3.0.0 (2026-08-07): 对齐 GDD 09 第十一章(决策97/99/106) + 10-gpu-node-setup.md v1.0 — 新增 §7 guimei 侧 C:\ai 分阶段部署(含完成状态勾选) + §8 防呆三禁令/故障排查表; MCP 工具名更新为 mcp__unity__*(决策106 MCP for Unity 主通道); 健康检查加入 GPU/磁盘/驱动/C:\ai/电源; 记录 Windows 无 head/grep、GBK 乱码等实测坑
- v2.0.0: 合并 gpu-ops + remote-env + gpu-batch(FUTURE)
