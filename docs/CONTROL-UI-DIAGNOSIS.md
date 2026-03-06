# Control UI 配置问题诊断

## 问题现象
- 控制台"配置"页面加载很慢
- 无法看到具体配置信息

## 已完成的修复

### 1. 添加本地访问来源
```json
"controlUi": {
  "allowedOrigins": [
    "http://47.79.255.24:18789",  // 公网 IP
    "http://127.0.0.1:18789",     // ✅ 新增
    "http://localhost:18789"      // ✅ 新增
  ]
}
```

### 2. 配置热重载
```json
"gateway": {
  "reload": {
    "mode": "hybrid",
    "debounceMs": 300
  }
}
```

## 可能的原因

### 1. CORS 跨域问题
如果通过浏览器访问 `http://localhost:18789` 但 `allowedOrigins` 中没有配置，会导致请求被阻止。

**症状**: 浏览器控制台显示 CORS 错误

**解决**: 已添加所有可能的访问来源

### 2. 配置 RPC 接口响应慢
Control UI 通过 RPC 调用 `config.get` 获取配置，如果配置较大或模型列表较多，可能导致加载慢。

**优化建议**:
- 检查 `agents.defaults.models` 是否配置过多模型
- 当前配置有 8 个模型，属于正常范围

### 3. 浏览器缓存问题
浏览器可能缓存了旧的配置页面

**解决**:
```bash
# 强制刷新页面
Ctrl + Shift + R (Windows/Linux)
Cmd + Shift + R (Mac)

# 或清除缓存后重新加载
```

### 4. 网络延迟
如果通过公网 IP (`47.79.255.24`) 访问，网络延迟可能导致加载慢

**建议**: 优先使用 `http://127.0.0.1:18789` 本地访问

## 诊断步骤

### 1. 检查网关状态
```bash
openclaw status
```

### 2. 查看网关日志
```bash
openclaw logs --tail 100
```

### 3. 测试配置 API
在浏览器控制台或 curl 测试:
```bash
curl http://127.0.0.1:18789/api/config.get -H "Content-Type: application/json" -d '{}'
```

### 4. 检查浏览器控制台
打开浏览器开发者工具 (F12)，查看:
- Network 标签：是否有失败的请求
- Console 标签：是否有 JavaScript 错误
- 检查 `config.get` 请求的响应时间

## 临时解决方案

如果问题持续，可以使用 CLI 查看配置:

```bash
# 查看完整配置
openclaw config get

# 查看特定配置
openclaw config get agents.list
openclaw config get models.providers
openclaw config get channels.dingtalk
```

## 配置验证

当前配置已优化:
- ✅ allowedOrigins 包含所有可能的访问地址
- ✅ 热重载模式已启用
- ✅ 工具权限配置正确
- ✅ agents.list 配置结构正确

## 下一步

1. **重启网关** (如果配置未自动热重载):
   ```bash
   openclaw gateway restart
   ```

2. **清除浏览器缓存** 并重新访问

3. **使用本地地址** 访问：`http://127.0.0.1:18789`

4. **如果仍然缓慢**，请提供:
   - 浏览器控制台的错误信息
   - Network 标签中 `config.get` 请求的响应时间
   - `openclaw status` 的输出

---

*诊断时间：2026-03-01 14:20 GMT+8*
