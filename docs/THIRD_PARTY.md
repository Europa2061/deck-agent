# 第三方来源与许可证

[English](THIRD_PARTY.en.md)

- Pi 1.5.0：[earendil-works/pi](https://github.com/earendil-works/pi/tree/v1.5.0)，MIT。通过固定版本 npm 包分发，保留包内许可证和所有必要运行依赖，包括内部 TUI 库；产品不提供 TUI 入口。
- Node 22.23.1：[官方发行](https://nodejs.org/dist/v22.23.1/)，保留 `runtime/node/LICENSE`，其中包含 Node 自身及其依赖的许可证。
- sherpa-onnx 2.0.1：[官方发行](https://github.com/k2-fsa/sherpa-onnx/releases/tag/v2.0.1)，Apache-2.0；许可证保存在 `licenses/sherpa-onnx-LICENSE`。
- ONNX Runtime：由上述 sherpa-onnx 官方运行包包含，MIT；许可证保存在 `licenses/onnxruntime-LICENSE`。此前检查的动态库报告版本 1.28.2。
- SenseVoice Small INT8：来自 [sherpa-onnx 转换仓库](https://huggingface.co/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17)。[原模型卡](https://huggingface.co/FunAudioLLM/SenseVoiceSmall/raw/main/README.md) 指定 [FunASR 模型协议](https://github.com/modelscope/FunASR/blob/main/MODEL_LICENSE)（本次核查为 1.1），要求保留来源、作者和模型名，详见协议全文；不能套用 SenseVoice 代码的 MIT。转换仓库固定版本的 LICENSE 也指向 FunASR 许可说明。权重不随插件打包；新下载固定 commit，逐文件校验 SHA-256。原版归档仅保留用于校验既有安装的迁移。
- Whisper Small/Base INT8：来自 [Small](https://huggingface.co/csukuangfj/sherpa-onnx-whisper-small) 与 [Base](https://huggingface.co/csukuangfj/sherpa-onnx-whisper-base) 的 sherpa-onnx 转换仓库；[OpenAI 官方声明](https://github.com/openai/whisper#license) 明确原代码和权重采用 MIT，应保留版权和许可声明。转换仓库固定版本根目录未列出独立 LICENSE，未确认额外许可声明。权重不随插件打包，固定 commit，逐文件校验 SHA-256。
- Paraformer 中英粤 INT8：来自 [sherpa-onnx 转换仓库](https://huggingface.co/csukuangfj/sherpa-onnx-paraformer-trilingual-zh-cantonese-en)。[ModelScope 原模型官方 API](https://www.modelscope.cn/api/v1/models/dengcunqin/speech_seaco_paraformer_large_asr_nat-zh-cantonese-en-16k-common-vocab11666-pytorch) 的模型许可字段和[原始 README](https://www.modelscope.cn/api/v1/models/dengcunqin/speech_seaco_paraformer_large_asr_nat-zh-cantonese-en-16k-common-vocab11666-pytorch/repo?Revision=a63221070fd8baa970d841ceea59edfc1188a1ac&FilePath=README.md) 均明确声明 Apache License 2.0（2026-11-04 核查）。这是该具体原模型的许可声明；转换仓库未提供单独的 LICENSE 或额外许可声明。权重不随插件打包，固定 commit 并逐文件校验 SHA-256。
- 用户可选择 [hf-mirror](https://hf-mirror.com/) 作为 Hugging Face 下载镜像，仓库、版本和校验值保持一致。
- Decky API 1.1.3：[loader-api](https://github.com/SteamDeckHomebrew/loader-api)，BSD-3-Clause，构建时打包的许可证保存在 `licenses/decky-api-LICENSE`。Decky UI 由宿主提供，不把 Decky Loader 本体复制进安装包。

应用自有源码使用根目录 MIT 许可证。npm 运行依赖的许可证随各包保留；安装包不重新许可这些依赖。

- Markdown 显示：使用 [react-markdown](https://github.com/remarkjs/react-markdown) 10.1.0 和 [remark-gfm](https://github.com/remarkjs/remark-gfm) 4.0.1；MIT 及依赖许可证保留在 `licenses/markdown-dependencies-LICENSES.txt`。
