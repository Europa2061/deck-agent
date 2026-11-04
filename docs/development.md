# 开发与构建

[English](development.en.md)

## 本机开发

需要 Node.js 22.19 或更新版本，以及 Python 3.11 或更新版本。

```sh
npm ci --ignore-scripts
npm ci --prefix runtime
npm run typecheck
npm run test:frontend
npm run build
npm test
```

在两个终端分别启动：

```sh
python3 scripts/dev_server.py
```

```sh
npm run dev
```

打开后端打印的带令牌本机链接。开发前端使用普通浏览器控件适配，业务请求仍然连接真实 Pi，不是原型模拟。生产构建使用 `@decky/ui` 原生控件。

开发数据放在项目 `.dev-data/`，与个人 Pi 配置分开。不要把这个目录或真实密钥提交到仓库。开发 HTTP 服务仅绑定 `127.0.0.1`，要求随机令牌；安装包不包含该服务或开发数据。

## 构建 Steam Deck 安装包

需要 Linux x64 环境。Mac 的运行依赖不会被标记为可发行构建。

```sh
npm ci --ignore-scripts
npm run typecheck
npm run test:frontend
npm run build
python3 scripts/prepare_runtime.py
npm test
npm run package
python3 scripts/smoke_package.py
python3 scripts/decky_compat_report.py
python3 scripts/verify_release.py
```

每次运行 `npm run package` 都自动升级修订号，并同步 `package.json` 与锁文件；新增功能用 `npm run package -- --bump minor`，不兼容变更用 `npm run package -- --bump major`。采用三段式语义版本 `主版本.次版本.修订号`，详见 [发布说明](releasing.md)。输出 `out/deck-agent-X.Y.Z.zip` 和同名的 `.zip.sha256` 校验文件。根目录只有一个 `deck-agent/` 文件夹，包含 Decky 需要的 `plugin.json`、`main.py`、`dist/index.js`、`build-info.json`，以及核心运行时、资源和公开 docs/ 文档。语音权重、参考仓库、设计稿、测试和密钥不进入安装包。

`prepare_runtime.py` 校验官方 Node / sherpa-onnx 下载的 SHA-256，在 Linux 安装锁定的 Pi 依赖，检查 Pi 与语音引擎能够启动后才写入发行标记。`package.py` 缺少标记时拒绝生成发行包。Decky 解压不保留符号链接和可执行权限，插件首次加载时按清单恢复，以保留 npm/npx 和共享库布局。`smoke_package.py` 在干净目录模拟解压、首次加载和一次实际 Pi 工具执行。

提交和 PR 由 `.github/workflows/ci.yml` 自动检查。手动运行 `.github/workflows/build.yml` 的 Release Deck Agent，可自动升级版本、提交、构建校验、打标签并生成带附件的 Release 草稿；真机验收后点击发布。详见 [发布说明](releasing.md)。

本地也可以在官方 Node 的 Linux 容器内运行上述准备、测试和打包步骤。应使用普通容器用户，并只挂载当前项目。


## Pi 运行依赖

Pi coding-agent 与 pi-ai 固定为 **1.5.0**，以 `runtime/package.json` 和锁文件为准。升级后需重新安装依赖、测试原生工具与会话恢复，并在 Linux x64 重新准备发行运行时。


## 会话显示回归

`npm run test:frontend` 包括会话过程分组检查：按用户请求分轮，执行中展开，结束后收起过程并保留最终答复；覆盖多轮、停止、错误、图片与缺少时间戳的历史。耗时优先使用原生消息时间戳和响应时长，没有记录时不估算。

界面验收时检查：最近会话最多 6 条；当前会话有明显背景和左侧标记；会话栏不显示返回 Steam 按钮；输入框为小圆角，单行和多行下三个按钮均居中且透明。执行结束后应自动收起过程，展开、收起都不能隐藏最终答复。手柄仍可用 B 返回。
