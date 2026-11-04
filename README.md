# Deck Agent

**在 Steam Deck 游戏模式里，通过文字或语音让 AI 帮你处理文件、运行命令和完成任务。**

基于 Decky 和 [Pi](https://github.com/earendil-works/pi)，支持多会话、流式回复、Skills、扩展与 MCP。本地语音识别只把文字填入草稿，由你决定何时发送。

[English](README.en.md) · [安装与首次使用](docs/installation.md) · [权限与隐私](docs/privacy.md) · [开发与构建](docs/development.md) · [全部文档](docs/index.md)

## 可以用来做什么

- 整理指定目录中的文件：先让 AI 列出整理方案，确认后再操作。
- 在测试目录里编写脚本、生成说明文档、查看命令结果。
- 用语音输入任务，切换会话查看历史和执行进度。

这是具备文件和命令能力的通用 Agent；任务效果取决于你选择的模型、提示和设备环境。

## 使用前准备

- Decky Loader。
- 可用的 LLM API（接口地址、API Key 和模型）。

## 安装

当前仓库尚未绑定公开发行地址。公开发布后，请从仓库的 **Releases** 下载 `deck-agent-X.Y.Z.zip`，不要使用 Source code ZIP。

1. 打开 Decky 设置中的开发者选项，选择下载好的本地 ZIP 安装。
2. 打开 Deck Agent，添加供应商、填写 API Key、选择模型并测试连接。
3. 新建会话，先在 `~/DeckAgent/test` 这样的专用目录里尝试任务。
4. 需要语音时，在「语音输入」中下载模型并选择麦克风。

完整步骤、更新、卸载和故障排查见 [安装说明](docs/installation.md)。普通使用不需要 SSH，也不需要单独安装 Pi 或 Node。

## 当前状态

当前为测试版本，主要验证环境为 Steam Deck OLED 和 Decky 3.3.1。其他设备与版本，以及手柄、语音、休眠和游戏内体验仍需持续验证。

- [更新记录](docs/CHANGELOG.md)
- [已知限制](docs/installation.md#已知限制)
- [设备测试清单](docs/device-test.md)

## 权限与数据

Agent 可以在运行用户的权限内读写文件、执行命令。这不是文件沙箱；停止任务不会撤销已经完成的操作。首次使用请避开游戏存档和重要配置。

会话、API Key、设置和语音模型保存在 Decky 的独立数据目录。插件更新不主动覆盖它们；录音在转写或取消后清理。模型请求会把相关对话和工具结果发送给你配置的供应商；本地语音识别不代表后续聊天离线。

提交问题前请检查日志和截图中的隐私。详见 [权限与隐私](docs/privacy.md)。

## 反馈与参与

**遇到 Bug 或有功能建议，直接在本仓库提 Issue。** 请附插件版本、SteamOS / Decky 版本和复现步骤。只有可能泄露数据或绕过权限的安全漏洞，才参考 [安全说明](docs/SECURITY.md)；不要公开上传密钥或私人会话。

开发、测试与提交约定见 [贡献说明](docs/CONTRIBUTING.md)。

## 许可证与致谢

项目自有源码采用 [MIT](LICENSE)。Pi、Node、Decky API、sherpa-onnx、ONNX Runtime 与各语音模型分别遵循上游许可，见 [第三方来源](docs/THIRD_PARTY.md)。语音权重不随安装包分发。

本项目为社区项目，与 Valve 或 Decky 官方没有隶属关系。
