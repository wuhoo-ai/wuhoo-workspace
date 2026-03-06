# Data 目录 - 持久化存储与备份

## 目录结构

```
~/Data/
├── v2ray/              # V2Ray 配置（容器挂载点）
│   └── config.json
│
├── trendradar/         # TrendRadar 输出（容器挂载点）
│   ├── config/
│   └── output/
│
├── ai-trader/          # AI-Trader 数据（容器挂载点）
│   ├── data/
│   ├── configs/
│   ├── logs/
│   └── .env            # ⚠️ 敏感
│
└── backups/            # 备份数据
    ├── secrets/        # 加密的敏感配置
    │   └── *.enc       # age 加密文件
    └── data/           # 数据备份
```

## 敏感文件备份

### 自动备份
- **频率**: 每天凌晨 3:00
- **脚本**: `~/bin/backup-secrets.sh`
- **加密**: age 公钥加密
- **保留**: 30 天

### 备份的文件
- `~/.openclaw/.env`
- `~/.openclaw/openclaw.json`
- `~/.ssh/id_rsa`
- `~/Data/ai-trader/.env`
- `~/Data/ai-trader/configs/.env`
- `~/Data/v2ray/config.json`
- 等...

### 恢复文件
```bash
# 查看密钥
cat ~/.secrets-age-key.txt

# 恢复文件示例
age -d -i ~/.secrets-age-key.txt ~/Data/backups/secrets/_home_admin_.openclaw_.env.20260304_111052.enc > ~/.openclaw/.env
```

## 容器部署挂载

### V2Ray
```yaml
volumes:
  - ~/Data/v2ray/config.json:/etc/v2ray/config.json:ro
```

### TrendRadar
```yaml
volumes:
  - ~/Data/trendradar/output:/app/output
  - ~/Data/trendradar/config:/app/config
```

### AI-Trader
```yaml
volumes:
  - ~/Data/ai-trader/data:/app/data
  - ~/Data/ai-trader/logs:/app/logs
```

## 密钥管理

- **Age 密钥**: `~/.secrets-age-key.txt` (chmod 600)
- **公钥**: `age1rdammm8duw8hnewssrk9apwatwempxc6kcd6lpja0snul9903vasanaczy`
- **备份**: 将此密钥也备份到安全位置

---
最后更新：2026-03-04
