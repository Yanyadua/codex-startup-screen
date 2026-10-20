# 实现与验证范围

## 动画与宿主

`lib/splash.js`、`lib/splash.css` 来自上游的零依赖浏览器运行时，保留 `__DSH_STARTUP__` 配置协议与完成事件。Codex 版改写了显示文案、终端图形、默认配置和交互前音频行为。没有采用上游 DSH 的宿主插件代码、设置页或媒体文件。

浏览器预览把动画根节点放在示例 `#root` 外。`preview.js` 会模拟替换 React 根节点的内容，动画不应因此消失。

## 原生接入位置

1. early bootstrap 生成当前进程的动画 session ID。
2. 首个 primary BrowserWindow 获得 eligibility 与 session ID 参数，其余窗口不获得播放资格。
3. preload 通过 `contextBridge` 暴露一个只含这两项信息的对象。
4. `webview/index.html` 在原模块入口前加载配置与 `boot.js`，保留原入口及 CSP。
5. `boot.js` 把覆盖层加在 React 根节点之外，按 session 防止刷新重复播放，并在完成时移除。

初始化失败 8 秒后放行，Esc 在初始化期间也能解除覆盖；解除后迟到的脚本不会重新遮住界面。动画正常运行且等待用户时不会套用 8 秒总时长限制。完成事件同时清理滚动锁。默认不修改账号、用户数据路径、更新器、协议注册、CODEX_HOME 或后端功能开关。

## 如何复核

```bash
npm run check
npm test
python3 tools/macos/verify_asar.py /absolute/path/to/ChatGPT-ready.app/Contents/Resources/app.asar
codesign --verify --deep --strict /absolute/path/to/ChatGPT-ready.app
```

生命周期回归覆盖非主窗口、重复会话、脚本加载失败、初始化超时、Esc 与 DOM 尚未就绪的竞态。ASAR 回归覆盖跨块校验、空文件、数据篡改和越界元数据。测试使用合成归档，不需要官方应用，也不分发其内容。

## 已有证据与边界

2026-10-20 的本机实验在上述固定版本上验证过真实 Electron 窗口播放、两次确认、Esc 跳过、第二窗口不重复、完全退出再开后重播；之后将同一路径的动画接入正式安装，确认应用重开及签名自洽。公开版整理时另行构建副本、核对归档和签名，不再次替换已安装应用。

这些证据来自单台 Apple Silicon Mac，不能外推到其他版本和设备。没有完成登录、通知、钥匙串、系统权限、终端、CUA、MCP 等完整生产功能的逐项验证。浏览器预览通过不意味着原生集成通过，短期进程存活也不等于完整可用。

## 上游与官方资料

- [上游项目与 MIT 许可证](https://github.com/6shenhonghong9/dsh-startup-screen)
- [Electron ASAR integrity](https://www.electronjs.org/docs/latest/tutorial/asar-integrity)
- [Electron fuses](https://www.electronjs.org/docs/latest/tutorial/fuses)
- [Electron contextBridge](https://www.electronjs.org/docs/latest/api/context-bridge)

本仓库仅包含动画、接入逻辑与重建工具。原始包与构建出的副本由使用者在本机提供和保存。
