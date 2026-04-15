# wecom-app 语音发送指南

本文专门说明 `wecom-app` 插件里“给用户发送微信语音”这件事应该怎么做、发什么文件，以及当前实现支持到什么程度。

## 一句话结论

如果希望用户侧尽量以“语音消息气泡”展示，而不是普通文件，**优先发送 `.amr`**。

建议格式：

- `.amr`
- `8kHz`
- 单声道
- `AMR-NB`

`.speex` 也属于企业微信 `voice` 常见可用格式，但本插件当前自动转码只产出 `.amr`，所以实践里优先推荐 `.amr`。

## 当前插件支持状态

当前 `wecom-app` 插件已经实现了语音发送链路：

- 支持把语音文件上传到企业微信素材接口
- 支持发送 `msgtype: "voice"` 消息
- 支持按 MIME/扩展名识别媒体类型

但要注意边界：

- **稳定推荐**：本地 `.amr`
- **默认自动处理**：常见音频（如 `.wav/.mp3/.ogg/.m4a/.aac/.flac/.wma`）会优先转成 `.amr`，再按 `voice` 发送
- **环境要求降低**：插件优先使用内置 `ffmpeg-static`；只有特殊环境下才需要依赖系统 `ffmpeg`
- **失败兜底**：如果转码后的 `voice` 上传/发送失败，会自动降级为普通文件发送
- **开发者注意**：如果直接调用仓库导出的 `sendWecomDM/sendWecom` 便捷 helper，当前 `mediaPath` 仍按图片路径处理，不适合作为语音发送入口

## 推荐发送方法

推荐直接发送一个**本地 `.amr` 文件路径**，并显式指定接收目标。

概念上需要这几个字段：

```yaml
channel: wecom-app
target: user:<UserId>
replyTo: <message_id>   # 可选但推荐；回复当前消息时建议带上
path: <本地 .amr 文件路径>
```

`target` 常见可用形式：

- `user:<UserId>`
- `wecom-app:user:<UserId>`
- `<UserId>`

多账号场景可写成：

- `user:<UserId>@<accountId>`

## 最稳的文件来源

### 1. 直接发送你准备好的 `.amr`

例如：

```text
D:\audio\hello.amr
```

### 2. 回发入站语音

如果这段录音本来就是从 wecom-app 收到的，优先复用入站归档目录里的原始语音文件，例如：

```text
%USERPROFILE%\.openclaw\media\wecom-app\inbound\YYYY-MM-DD\voice_xxx.amr
```

这类文件通常已经是适合企业微信语音发送的格式，成功率最高。

## 如果手里只有 WAV 或 MP3

有两种做法。

### 做法一：先手动转成 `.amr`

```bash
ffmpeg -i in.wav -ar 8000 -ac 1 -c:a amr_nb out.amr
```

转好后再发送 `out.amr`。

### 做法二：开启自动转码

当前默认就会自动转码；下面的配置更多用于显式声明或在多账号里覆盖行为：

```jsonc
{
  "channels": {
    "wecom-app": {
      "voiceTranscode": {
        "enabled": true,
        "prefer": "amr"
      }
    }
  }
}
```

自动转码大致生效条件：

- 输入被识别为音频，且不是企业微信原生更友好的 `.amr/.speex`
- 可以从文件扩展名或 MIME 判断出音频类型
- 插件能使用内置 `ffmpeg-static`，或回退到系统 `ffmpeg`

如果缺少这些条件，当前实现会直接改成“文件发送”兜底。

## 为什么 WAV/MP3 经常不行

企业微信自建应用的 `voice` 消息通常更偏向 `amr/speex` 这类格式。即使 `.wav/.mp3` 在其他播放器里很常见，也不代表它能稳定作为企业微信 `voice` 发送成功。

典型现象：

- 上传失败
- 返回 `ok=false`
- 客户端不显示为语音气泡
- 被系统当普通文件处理

## 排障建议

### 1. 明明是语音文件，却发成了文件

优先检查：

- 文件是否是 `.amr`
- 如果是常见音频，是否被显式配置了 `voiceTranscode.enabled=false`
- 当前运行环境是否能正常执行内置 `ffmpeg-static`，或回退到系统 `ffmpeg`
- 日志里是否已经出现“voice send failed ... fallback to file send”之类的回退提示

### 2. 报 `Unknown target` 或 `Action send requires a target`

优先改用：

- `user:<UserId>`
- `wecom-app:user:<UserId>`
- `user:<UserId>@<accountId>`

不要直接使用显示名或备注名。

### 3. 报 `Account not configured for active sending`

检查以下配置是否完整：

- `corpId`
- `corpSecret`
- `agentId`

## 推荐实践

- 只要你是为了“发语音消息”，就优先准备 `.amr`
- 如果你要回发用户刚发来的语音，优先复用 inbound 归档目录中的 `.amr`
- 如果业务上会产出 `.wav/.mp3/.ogg/.m4a` 等常见音频，默认配置通常已经够用
- 如果你明确不想转码，可以设置 `voiceTranscode.enabled=false`，此时不兼容格式会直接按文件发送
