# macOS 原生接入与恢复

此方法修改本机应用副本并重新签名，属于实验性本体补丁。仅有当前版本的验证证据，不是官方支持的定制方式。

## 支持范围

| 条件 | 当前要求 |
| --- | --- |
| 系统与架构 | Apple Silicon macOS |
| 应用标识 | `com.openai.codex` |
| 应用版本 | 26.1013.40934 / build 20770 |
| 安装位置 | `/Applications/ChatGPT.app` |
| 原始 ASAR header SHA-256 | `b276579474c7f0413ae388aaf39d00337f7615a858774156f1268c68519ebab1` |
| 工具 | Python 3.9+、Apple Command Line Tools、可用的 `codesign`、`ditto`、`swiftc` |

构建和运行都不会下载 Codex。请自行使用合法安装的未修改应用。指纹不匹配意味着包内容不同，应重新适配，不能只改版本号跳过检查。

## 1. 构建，不替换

```bash
python3 tools/macos/prepare.py
```

构建器在仓库 `local-build/<时间>/` 下创建完整原版备份、修改副本、ASAR 校验结果、签名清单、替换工具及 `deployment.json`。这个目录已加入 `.gitignore`。完整复制应用需要数 GB 空闲空间。失败时保留构建目录供检查，不会自动替换应用。

也可用 `--output /绝对路径/新目录` 指定位置。安装时需与 `/Applications` 位于同一文件系统，并且当前用户有 `/Applications` 写权限。构建器不自动提权。`--app` 可用于针对一份独立原版备份构建检查，但部署工具仅允许替换固定的 `/Applications/ChatGPT.app`。

## 2. 检查并应用

先保存工作。设置下面的 `BUILD_DIR` 为本次构建器打印的绝对路径，然后运行检查；**apply 会正常退出并重新打开 Codex**，如果从 Codex 内部终端执行，退出过程可能中断命令，因此建议在独立 Terminal 中执行。

```bash
BUILD_DIR="/absolute/path/to/codex-startup-screen/local-build/时间目录"
"$BUILD_DIR/codex-startup-deploy" check "$BUILD_DIR/deployment.json"
"$BUILD_DIR/codex-startup-deploy" apply "$BUILD_DIR/deployment.json" --delay 10
```

替换器只发出正常退出请求，最多等 90 秒，不强制结束进程。它会再次核对原包指纹，把当前应用原样移入 `installed-original.app`，再放入修改副本、验证签名、重新启动并观察 15 秒。失败时尝试恢复替换前应用；如果修改版拒绝退出，保留备份并记录状态，等待人工处理。

可读取 `$BUILD_DIR/status.json`：`installed_and_running` 只表示进程通过短期存活检查，不能据此认定登录、通知、CUA、MCP 或全部功能正常。

倒计时期间可用 `touch "$BUILD_DIR/cancel"` 取消。该文件是持续生效的取消标记，重新尝试前需删除。副本被应用后会从构建目录移到安装目录，所以 apply 不是可重复执行的安装命令。

## 3. 恢复原版

保留整个构建目录，在独立 Terminal 执行：

```bash
"$BUILD_DIR/codex-startup-deploy" restore "$BUILD_DIR/deployment.json"
```

恢复工具正常退出当前修改版，从 `original.app` 复制一份原版，再替换应用并重开。当前修改版也会另行保留。若官方更新已改变安装包，恢复工具会拒绝覆盖该更新。工具不会回滚聊天、账号或偏好数据；代码没有读写这些数据目录的操作。

## 签名和完整性

主程序、被改框架及相关 helper 使用本地 ad-hoc 签名；无法保持 OpenAI 原厂签名身份、notarization 或受限 entitlement。需要原厂身份授权的 entitlement 会从这些重签组件移除，并添加 library-validation 兼容项。钥匙串、应用组、推送和系统权限可能因此要求重新授权或失效。未修改的内置 CodexCLI.app 保留原厂签名。

构建器更新 ASAR 内文件与分块 SHA-256、Info.plist 中的 header hash、框架原生完整性字典摘要，并保留完整性 fuse 开启。它不以禁用 ASAR 校验来运行修改包。`codesign --verify --deep --strict` 成功说明本地签名自洽，不等于恢复了官方信任身份。

官方更新可能覆盖动画。不要向他人分发本机构建出来的官方应用副本；分享本仓库的源码即可。
