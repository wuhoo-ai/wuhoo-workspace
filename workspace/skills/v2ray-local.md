# v2ray 本地代理服务

## 概述

v2ray 是一个网络代理工具，用于科学上网。本地使用 Docker 容器运行 vmess 协议代理服务。

## 项目路径

| 路径 | 说明 |
|------|------|
| `/home/admin/.config/v2ray/config.json` | 配置文件（标准位置） |
| `/home/admin/.openclaw/data/v2ray/logs` | 日志目录 |

## 快速开始

### 启动服务

```bash
# 使用 docker run 启动
docker run -d \
  --name v2ray \
  --restart always \
  --network host \
  -v /home/admin/.config/v2ray:/etc/v2ray:ro \
  -v /home/admin/.openclaw/data/v2ray/logs:/var/log/v2ray \
  docker.io/v2fly/v2fly-core:latest \
  v2ray -config=/etc/v2ray/config.json

# 验证服务状态
docker ps | grep v2ray
docker logs v2ray
```

### 停止服务

```bash
docker stop v2ray
docker rm v2ray
```

### 重启服务

```bash
docker restart v2ray
```

## 配置文件

配置文件位置：`/home/admin/.config/v2ray/config.json`

基本配置结构（vmess 协议）：
```json
{
  "inbounds": [
    {
      "port": 9281,
      "protocol": "vmess",
      "settings": {
        "clients": [
          {
            "id": "uuid-xxxx-xxxx",
            "alterId": 0
          }
        ]
      }
    }
  ],
  "outbounds": [
    {
      "protocol": "freedom",
      "settings": {}
    }
  ]
}
```

## 端口配置

默认端口：`9281`

验证端口监听：
```bash
netstat -tlnp | grep 9281
# 或
ss -tlnp | grep 9281
```

## 日志查看

```bash
# 实时日志
docker logs -f v2ray

# 持久化日志
tail -f /home/admin/.openclaw/data/v2ray/logs/access.log
tail -f /home/admin/.openclaw/data/v2ray/logs/error.log
```

## 健康检查

```bash
# 检查容器状态
docker inspect v2ray | grep -A 5 "State"

# 测试代理连接
curl -x socks5://127.0.0.1:9281 https://www.google.com
```

## 配置备份

配置文件备份位置：
- `/home/admin/.openclaw/data/v2ray/config.json.efs-backup`
- `/home/admin/.openclaw/data/v2ray/config.json.vmess-backup`

## 常见问题

### Q: 容器无法启动
**A**: 检查配置文件 JSON 格式是否正确，使用 `v2ray -test -config=/etc/v2ray/config.json` 验证。

### Q: 无法连接代理
**A**: 检查防火墙是否开放端口 9281，检查客户端配置是否与服务器匹配。

### Q: 连接速度慢
**A**: 检查服务器网络状况，尝试更换传输方式（tcp/ws）。

## 相关文件

- `/home/admin/.config/v2ray/config.json` - 主配置文件
- `/home/admin/.openclaw/data/v2ray/docker-compose.yml` - Docker Compose 配置（备用）
