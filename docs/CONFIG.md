# 配置

修改 `lib/config.js` 后刷新预览。原生补丁需要重新构建，已经打包进应用的文件不会跟随仓库修改。

| 字段 | 默认 | 含义 |
| --- | --- | --- |
| `enabled` | `true`（默认配置） | 原生引导总开关；设为 `false` 不加载覆盖层 |
| `theme` | `light`（默认配置） | `light` 暖白或 `dark` 深色 |
| `speed` | `1.35` | 时间线速度，限制在 0.35–3 |
| `requireInteraction` | `true` | 前两步是否等待确认 |
| `allowSkip` | `true` | 动画自带 Skip 按钮；原生引导始终保留初始化阶段的 Esc 兜底 |
| `identity` | `OPERATOR` | 本地显示代号 |
| `identityId` | `0001` | 显示编号，仅保留英文字母和数字 |
| `accessLevel` | `BUILD` | 档案卡中的显示文字，不改变权限 |
| `sound` / `soundVolume` | `true` / `0.18` | 合成音效与音量 |
| `sfx` | `synth` | 使用合成音效；本仓库没有素材音效 |
| `voice` | `false` | 可选浏览器 TTS；可用声音和是否联网取决于系统语音服务 |
| `voiceSource` | `tts` | 本仓库未提供 `asset` 模式的人声文件 |
| `brand1` / `brand2` / `brand3a` / `brand3b` | CODEX 等 | 左上品牌文字 |
| `orgZh` / `orgEn` / `orgSub` | 空 / CODEX / 副标题 | 黑幕开场文字 |
| `welcomeBox` / `footer` | CODEX / 页脚 | 结尾与底部文字 |
| `accent` / `glitchA` / `glitchB` | 橙 / 红 / 蓝 | 强调色与揭幕色散 |

`window.__DSH_STARTUP__` 和 `dsh-startup:*` 命名保留自上游，便于比较改动。原生引导另外按进程 session ID 进行一次性播放控制；独立预览每次刷新会播放。内置运行时的 `mode` 字段不代表 Codex 原生安装器提供每日播放设置。

```js
window.__DSH_STARTUP__ = {
  theme: 'dark',
  identity: 'BUILDER',
  identityId: '0021',
  accessLevel: 'CREATE',
  speed: 1.5,
  requireInteraction: false,
  sound: false,
  voice: false,
  sfx: 'synth',
  voiceSource: 'tts',
  accent: '#e5753b'
};
```

保留 `sfx: 'synth'` 与 `voiceSource: 'tts'`，可避免访问上游宿主才有的 `/dsh-startup/asset/` 资源路径。默认关闭语音时，动画不需要外部音频请求。
