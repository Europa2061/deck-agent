# 发布新版本

[English](releasing.en.md)

日常提交和 PR 自动运行检查。发布时只需手动选择版本升级类型；CI 自动构建并生成带附件的 Release 草稿，设备验收后再点击发布。

## 首次配置

1. 确定公开仓库、公开历史和作者身份，将审查过的源码推送到默认分支，启用 Issues。
2. 确认仓库允许工作流请求 `contents: write`；如有分支保护或规则集，确认是否允许发行机器人提交版本。工作流不会绕过保护或强制推送；权限不允许时会失败，不会发布草稿。
3. 等 **Check Deck Agent** 通过。当前本地仓库尚无 remote，新的工作流还没有在 GitHub 实际运行。

使用仓库自动提供的 `GITHUB_TOKEN`，不需要额外配置个人令牌。[GitHub 认证说明](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)

当前 [Decky 官方规则](https://github.com/SteamDeckHomebrew/wiki/blob/main/plugin-dev/submitting-plugins.md#ai-llms-and-so-on) 拒收 LLM 核心插件，发行通过 GitHub Releases 和手动本地 ZIP 安装。

## 每次发布只做这些

1. 完成功能、中英文更新记录和代码审查，将改动合并到默认分支。
2. 打开 Actions → **Release Deck Agent** → Run workflow，选择默认分支、`patch / minor / major`，以及是否为测试版。修复选 patch，兼容新功能选 minor，不兼容改动选 major。
3. 等工作流完成。CI 会自动：
   - 检查类型、前端、Python 测试和中英文文档链接，构建 Linux x64 运行时；
   - 按所选类型升级版本，创建中英双语版本提交，再打包一次；
   - 检查干净解压启动、工具执行、Decky 加载、版本和 SHA-256；
   - 上传候选包，原子推送版本提交与对应标签；
   - 生成 Release 草稿，附 ZIP、校验文件和自动生成的发行说明。
4. 从 Actions 产物或 Release 草稿下载候选包，在 Deck 上验收。检查版本、实际任务、输入/语音、更新后数据保留；按 [设备测试](device-test.md) 记录范围。CI 不会替代实体手柄和实际语音体验。
5. 在 Releases 编辑草稿，补齐中英文用户说明与已知限制，确认后点击 **Publish release**。最后测试真实公开下载和插件升级。完整升级应从较旧安装版本验证；同版本设备只能检查“已是最新”。

不再需要手工应用 `version.patch`、提交版本文件、建标签或上传附件。打包发生在版本提交之后，包内源码编号与标签提交一致。

发布流程使用两个 job：build 与 draft。候选包和版本推送完成后，如果只生成草稿失败，使用 **Re-run failed jobs** 重跑 draft，复用同一个包；不要重新运行整条发行流程来修补草稿。已有公开 Release 不会被重写。

## 失败和并发

- 同一时间只执行一条发行流程；已有默认分支新提交导致快进推送失败时，版本提交和标签一起拒绝，不覆盖他人的工作。重新基于最新默认分支发起新运行。
- 构建检查失败不会推送版本或标签，也不会创建草稿。
- draft 重跑只补齐尚未公开的草稿附件；若版本已公开则退出，避免覆盖已发布包。
- Actions 产物保留 30 天；正式用户下载使用 Release 附件。
- 修改代码、提示词或运行资源后应重新生成新版本候选，不覆盖已有发布包。

## 可选：Linux x64 本地构建

```sh
npm ci --ignore-scripts
npm run typecheck
npm run test:frontend
npm run build
python3 scripts/prepare_runtime.py
npm test
npm run package -- --bump patch
python3 scripts/smoke_package.py
python3 scripts/decky_compat_report.py
python3 scripts/verify_release.py
```

本地普通打包会升级版本但不自动提交、推送或发布。`--commit-version` 用于 CI 的干净工作区，会先提交版本再打包；本地有未提交改动时会拒绝执行。每次打包仍遵守三段式版本升级。

## 用户更新和回退

Release 必须附 `deck-agent-X.Y.Z.zip` 和 `.zip.sha256`；Source code ZIP 或 Actions 外层 artifact ZIP 不能安装。更新检测优先正式版，尚无正式版时才选择最近 100 条记录中有匹配包的最高测试版；不会把正式版用户自动切到测试版。

插件下载、校验后调用 Decky 原生确认与本地包安装；失败时仍可选择本地 ZIP。安装请求已提交不代表成功，重开后核对版本。回退可安装旧包，但旧代码不保证兼容新数据，重要更新前备份设置和会话。

参考：[GitHub Release 操作](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)、[gh release create](https://cli.github.com/manual/gh_release_create)。
