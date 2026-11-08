---
name: decky-plugins
description: 按用途寻找 Decky 商店外插件，下载并安装用户指定的 GitHub/本地插件，核对版本或排查安装失败。
---

插件发现使用 deck_plugins search，搜索范围由工具限定为 GitHub topic:decky-plugin（https://github.com/topics/decky-plugin）。根据用户需求换关键词，使用 inspect(repo) 和 read_source 阅读候选的 README、Releases、已知问题；不维护精选目录，也不把 Topic 当官方审核或“未上架商店”的证明。用户给出具体仓库/ZIP 时可以直接检查该来源，不必要求作者先添加 Topic。

推荐时说明用途、作者、来源、当前版本和已查到的兼容说明，识别模板、旧分支及归档项目。下载必须是实际发行的 Decky 插件包，不能用 Source code ZIP 替代。prepare(repo/url/archive,tag,sha256) 下载并检查包，返回 id 和清单；资产不唯一时先 inspect，再指定正确 url。

读清 name/version/flags/sourceChecksumVerified 后，用 install(ticket=id) 将请求交给前端。Deck Agent 会显示待安装入口并打开 Decky 原生确认，由用户确认安装；工具返回 queued 仅表示等待确认。前端不在场时请求保留，回到插件页面后可以继续。

从「继续安装」打开原生窗口后，待安装卡片会消失。待安装列表变空或 ticket 进入 prompted 都只表示已交接。安装结束后用 status 核对 observedInstalled，再确认 Decky 插件列表能加载该版本。取消或接口失败后可以对同一个 ticket 重新 install。Deck Agent 自身更新走「关于与更新」，避免在模型任务中重载自己。

更新可重新 inspect/prepare/install 选择对应版本，并保存来源。卸载、回退和特殊安装方式可先检查 Decky 当前支持的接口，结合原生工具规划；保留设置与数据，不把代码回退等同数据可回退。资料不足时明确缺少什么证据，模型仍可用其他现有工具继续查证。
