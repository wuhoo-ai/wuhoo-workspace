# OpenD CentOS 版本修复记录

## 问题描述

OpenD 错误安装了 Ubuntu 18.04 版本 (`Futu_OpenD_10.1.6108_Ubuntu18.04`)，但服务器使用的是 **Alibaba Cloud Linux 3**（基于 CentOS/RHEL 兼容）。

```bash
# 系统信息
NAME="Alibaba Cloud Linux"
VERSION="3 (OpenAnolis Edition)"
ID="alinux"
ID_LIKE="rhel fedora centos anolis"
```

## 修复步骤

### 1. 下载 CentOS 7 版本 OpenD

```bash
cd ~/.openclaw/workspace/agents/trade/opend
wget https://softwaredownload.futunn.com/Futu_OpenD_8.8.4808_Centos7.tar.gz -O Futu_OpenD_Centos7.tar.gz
tar -zxvf Futu_OpenD_Centos7.tar.gz
```

### 2. 配置 MD5 加密密码

Futu OpenD 要求密码使用 MD5 加密格式：

```bash
# 生成登录密码 MD5
echo -n "hj78520h" | md5sum
# 结果：f4ffb441422a211762131452a694b066

# 生成交易密码 MD5
echo -n "226286" | md5sum
# 结果：3671f8e1d528a1821cec3c84e5835b5c
```

### 3. 更新配置文件

编辑 `futu_config.xml`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<root>
    <login>
        <username>15088682042</username>
        <password>f4ffb441422a211762131452a694b066</password>
        <trading_password>3671f8e1d528a1821cec3c84e5835b5c</trading_password>
    </login>
    <network>
        <listen_port>11111</listen_port>
        <listen_ip>0.0.0.0</listen_ip>
    </network>
    <log>
        <level>info</level>
    </log>
</root>
```

### 4. 更新启动脚本

`start_opend.sh` 现在优先使用 CentOS 版本：

```bash
# 优先使用 CentOS 版本 (Alinux 3 兼容)
CENTOS_DIR="$SCRIPT_DIR/Futu_OpenD_8.8.4808_Centos7/Futu_OpenD_8.8.4808_Centos7"
UBUNTU_DIR="$SCRIPT_DIR/Futu_OpenD_10.1.6108_Ubuntu18.04/Futu_OpenD_10.1.6108_Ubuntu18.04"

if [ -x "$CENTOS_DIR/FutuOpenD" ]; then
    OPENDD_DIR="$CENTOS_DIR"
    VERSION="CentOS 7 (v8.8.4808)"
else
    OPENDD_DIR="$UBUNTU_DIR"
    VERSION="Ubuntu 18.04 (v10.1.6108)"
fi
```

### 5. 清理 Ubuntu 版本

```bash
rm -rf Futu_OpenD_10.1.6108_Ubuntu18.04
rm Futu_OpenD.tar.gz
```

## 验证结果

```bash
# 启动 OpenD
./start_opend.sh

# 检查进程
ps aux | grep FutuOpenD

# 检查端口
netstat -tlnp | grep 11111
```

### 成功输出

```
✅ OpenD 启动成功 (版本：CentOS 7 (v8.8.4808))
   PID: 1958704
   端口：11111
   日志：logs/opend.log
```

## OpenD 版本对比

| 特性 | Ubuntu 18.04 | CentOS 7 |
|------|--------------|----------|
| 版本号 | 10.1.6108 | 8.8.4808 |
| 架构 | x86-64 | x86-64 |
| 动态链接 | ✓ | ✓ |
| Alinux 3 兼容 | ❌ | ✓ |
| 文件大小 | ~425MB | ~138MB |

## 注意事项

1. **密码加密**: Futu OpenD 要求密码使用 MD5 加密，不是明文
2. **配置文件路径**: 使用相对路径 `futu_config.xml` 而不是绝对路径
3. **版本选择**: Alinux 3 使用 CentOS 7 版本，不是 Ubuntu 版本
4. **端口占用**: 启动前确保端口 11111 未被占用

## 参考链接

- [Futu OpenD 下载](https://www.futunn.com/download/OpenD)
- [Futu API 文档](https://www.futunn.com/opendoc)
