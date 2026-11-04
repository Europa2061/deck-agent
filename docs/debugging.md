# 调试

[English](debugging.en.md)

先核对构建版本，再看日志；前端问题用浏览器或 CEF，设备行为在 Steam Deck 上验证。

## 构建和日志

在「设置 → 关于与更新」查看版本、构建编号和打包时间；「设置 → 通用 → 诊断信息」显示运行环境和目录。源码未提交时，打包标识会带 dirty，不能据此声称与某个提交完全一致。

常见路径：

| 内容 | 路径 |
| --- | --- |
| 插件 | `~/homebrew/plugins/deck-agent/` |
| 日志 | `~/homebrew/logs/deck-agent/deck-agent.log` |
| 设置和 Pi 认证 | `~/homebrew/settings/deck-agent/` |
| 会话、语音和更新缓存 | `~/homebrew/data/deck-agent/` |

实际路径以 Decky 和诊断信息为准。日志最多约 15 MB（三份，每份 5 MB），记录启动、任务、工具、语音和异常事件。默认不写完整对话、命令参数、工具输出或语音正文；第三方错误仍需人工检查隐私。

在 Deck 的 Konsole 执行：

```sh
bash ~/homebrew/plugins/deck-agent/resources/deck-diagnose.sh
tail -n 100 ~/homebrew/logs/deck-agent/deck-agent.log
```

诊断脚本只读；输出可能包含主机名、IP、路径、进程参数和日志，分享前遮盖个人信息。

需要详细日志时：

```sh
mkdir -p ~/homebrew/settings/deck-agent
touch ~/homebrew/settings/deck-agent/debug-log
```

重载插件生效。关闭时删除 `debug-log` 再重载；日志不可用时检查 Decky 自身的日志。

## 本机浏览器

按 [开发说明](development.md) 启动前后端。后端打印的带令牌链接使用真实 Pi；`?demo` 使用明确标记的演示数据，不调用真实模型。开发数据在 `.dev-data/`，不使用设备的个人配置。

浏览器可检查布局、请求、错误和草稿，不能证明 Steam 原生手柄、音效、麦克风或游戏中的表现。重点检查 854×534 和 1280×800 的弹窗、滚动和输入区。

## SSH 与 CEF

SSH 仅用于开发传包和查看设备，不是用户使用插件的前提。先在 Deck 桌面模式自行开启 SSH、配置认证并确认局域网地址，不在 Issue 或聊天中分享密码、私钥。

把 `DECK_IP` 和 `X.Y.Z` 换成设备地址及本次版本：

```sh
ssh deck@DECK_IP
scp out/deck-agent-X.Y.Z.zip deck@DECK_IP:~/Downloads/
```

传包后由 Decky 选择本地 ZIP 安装。CEF 是 Steam 内的浏览器调试环境；按 Decky 的实际设置开启远程调试，只在可信网络使用。

### 已验证的远程更新路径

先确认没有运行任务、待确认请求、录音或转写；核对 ZIP 的 SHA-256。通过 SSH 传包，再连接设备已开放的 CEF，操作 Decky 的本地安装入口和原生确认；重载后核对前后端版本、会话与配置。地址、端口以设备当前状态为准，不能把请求已提交当成安装成功。

需要从本机转发设备 CEF 时（示例设备端口为 8081）：

```sh
ssh -N -L 127.0.0.1:18081:127.0.0.1:8081 deck@DECK_IP
node scripts/check_gamepad_navigation.mjs http://127.0.0.1:18081
```

导航脚本只移动焦点，不点击或发送消息；仍需按 [设备测试](device-test.md) 检查实体手柄。

## 打包边界

本项目使用 `scripts/package.py` 打包，`smoke_package.py` 验证干净解压后的启动和工具执行，`decky_compat_report.py` 核对 Decky 加载条件。官方 CLI 的标准白名单不能直接覆盖本项目的 backend、runtime、resources 和 docs，不能直接替换本项目打包步骤。

参考：[Decky 模板](https://github.com/SteamDeckHomebrew/decky-plugin-template)、[Decky Wiki](https://wiki.deckbrew.xyz)、[Valve 设备调试](https://partner.steamgames.com/doc/steamhardware/loadgames)。
