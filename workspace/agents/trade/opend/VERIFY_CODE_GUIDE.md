# 富途 OpenD 验证码处理指南

**创建时间**: 2026-03-25  
**更新时间**: 2026-03-25 13:37

---

## 📋 问题说明

富途 OpenD 首次登录需要输入图形验证码，但服务器是命令行环境，无法直接显示图片。

---

## 🛠️ 解决方案

### 方案 1: 使用交互式启动脚本 (推荐)

**脚本位置**: `~/.openclaw/workspace/agents/trade/opend/start-interactive.sh`

**使用步骤**:

```bash
cd ~/.openclaw/workspace/agents/trade/opend
./start-interactive.sh
```

**脚本功能**:
1. 自动启动 OpenD
2. 检测验证码图片生成
3. 提供多种查看验证码的方式
4. 指导完成登录

---

### 方案 2: 手动查看验证码

**验证码图片位置**:
```bash
~/.com.futunn.FutuOpenD/F3CNN/PicVerifyCode.png
```

**查看方式**:

#### 方式 A: Base64 编码 (推荐)

```bash
# 1. 输出 Base64 编码
base64 ~/.com.futunn.FutuOpenD/F3CNN/PicVerifyCode.png

# 2. 复制输出的 Base64 字符串

# 3. 在本地电脑解码 (Windows PowerShell)
echo "BASE64_STRING" | base64 -d > verify.png

# 4. 打开 verify.png 查看验证码
```

#### 方式 B: SCP 复制到本地

```bash
# 在本地电脑执行 (Mac/Linux)
scp user@server:~/.com.futunn.FutuOpenD/F3CNN/PicVerifyCode.png ./verify.png

# 然后用图片查看器打开
open ./verify.png  # Mac
xdg-open ./verify.png  # Linux
```

#### 方式 C: 使用查看工具脚本

```bash
cd ~/.openclaw/workspace/agents/trade/opend
./view-verify-code.sh
```

---

### 方案 3: 使用 GUI 版本 (最方便)

如果你有可以运行图形界面的电脑：

**Windows/macOS**:
1. 下载富途 OpenD GUI 版本
2. 运行并登录 (会显示验证码)
3. 登录成功后，账号信息会保存
4. 服务器端可以直接使用 API

**GUI 版本下载**:
- Windows: https://www.futunn.com/download/fetch-lasted-link?name=opend-windows
- macOS: https://www.futunn.com/download/fetch-lasted-link?name=opend-macos

---

## 📝 完整登录流程

### 步骤 1: 启动 OpenD

```bash
cd ~/.openclaw/workspace/agents/trade/opend
./start-interactive.sh
```

### 步骤 2: 查看验证码

脚本会提示验证码图片位置，选择查看方式：

```
查看方式:
1. 使用 eog 查看 (如果有图形界面)
2. 输出 Base64 编码 (可解码查看)
3. 跳过，直接测试连接 (可能已自动登录)
```

### 步骤 3: 输入验证码

**重要**: OpenD 命令行版本不支持直接输入验证码！

需要使用以下方法之一：

1. **GUI 版本登录** (推荐)
   - 在有图形界面的电脑运行 GUI 版本
   - 输入验证码完成登录
   - 登录状态会同步到服务器

2. **富途牛牛 APP**
   - 打开富途牛牛 APP
   - 搜索「OpenAPI」或「量化交易」
   - 完成 API 合规确认
   - 有时会自动激活 API 权限

3. **等待自动登录**
   - 有时 OpenD 会使用缓存的登录状态
   - 无需验证码即可连接

### 步骤 4: 验证连接

```bash
cd ~/.openclaw/workspace/agents/trade
source venv-futu/bin/activate

# 测试行情连接
python -c "
from futu import OpenQuoteContext, RET_OK
quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
ret, data = quote_ctx.get_global_state()
if ret == RET_OK:
    print('✅ 连接成功!')
    print(data)
else:
    print(f'❌ 连接失败：{data}')
quote_ctx.close()
"
```

---

## 🔧 常用命令

### 查看 OpenD 状态

```bash
# 检查进程
ps aux | grep FutuOpenD

# 检查端口
netstat -tlnp | grep 11111

# 查看日志
tail -f openD.log
```

### 停止 OpenD

```bash
pkill -f FutuOpenD
```

### 重启 OpenD

```bash
pkill -f FutuOpenD
sleep 2
./start-interactive.sh
```

---

## ⚠️ 常见问题

### Q1: 找不到验证码图片

**原因**: 
- OpenD 未启动
- 已经登录成功，无需验证码

**解决**:
```bash
# 检查 OpenD 是否运行
ps aux | grep FutuOpenD

# 检查端口是否监听
netstat -tlnp | grep 11111

# 如果端口在监听，说明已登录成功
```

### Q2: 验证码输入后仍然失败

**原因**: 
- OpenD 命令行版本不支持直接输入验证码

**解决**:
- 使用 GUI 版本登录
- 或使用富途牛牛 APP 完成 API 确认

### Q3: 连接超时

**原因**:
- OpenD 未启动
- 端口配置错误

**解决**:
```bash
# 重启 OpenD
./start-interactive.sh

# 检查日志
tail -f openD.log
```

---

## 📁 相关文件

| 文件 | 位置 | 说明 |
|------|------|------|
| **启动脚本** | `opend/start-interactive.sh` | 交互式启动 |
| **查看工具** | `opend/view-verify-code.sh` | 查看验证码 |
| **配置文件** | `opend/.env` | 账号配置 |
| **日志文件** | `opend/openD.log` | OpenD 日志 |
| **验证码** | `~/.com.futunn.FutuOpenD/F3CNN/` | 验证码图片 |

---

## 📞 需要帮助？

如果遇到问题：

1. **查看日志**: `tail -f openD.log`
2. **检查配置**: `cat .env`
3. **验证连接**: 运行测试脚本

---

*最后更新：2026-03-25 13:37*
