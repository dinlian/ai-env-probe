# Third-Party Notices

AI Env Probe 采用 [MIT License](LICENSE) 发布，Copyright (c) 2026 dinlian。

本工具在运行时会与以下第三方软件交互，但**不包含、不链接、不修改、不重新分发**它们的源代码或二进制文件。

## PyTorch / torchvision / torchaudio

- License: BSD 3-Clause
- Copyright: Facebook, Inc. and other contributors
- 本工具仅通过目标 Python 解释器读取用户环境中已安装的版本信息，不捆绑或再分发 PyTorch 的任何文件。
- 源码分发模式不包含 PyTorch 的任何文件。

## nvidia-ml-py (pynvml)

- License: BSD 3-Clause
- Copyright (c) 2011-2023, NVIDIA Corporation. All rights reserved.
- 本工具优先尝试导入 `pynvml` 以读取 GPU 信息；若未安装，回退到系统命令 `nvidia-smi`。
- 源码分发模式不包含 `pynvml` 的任何文件。
- 若以 PyInstaller 二进制形式分发并捆绑了 `pynvml`，则必须在分发材料中保留上述版权声明和 BSD 许可证全文。

## ComfyUI / Stable Diffusion WebUI / vLLM / HuggingFace Diffusers

- 本工具通过子进程与上述应用的目标 Python 解释器交互，**不包含、不链接、不修改、不重新分发**它们的源代码。
- 上述名称仅用于描述性说明检测对象，不表示任何隶属关系或官方背书。
- 本工具不构成对 GPL 或其他开源许可证项目的衍生作品。

## 打包版说明

如果以 PyInstaller `--onedir` 或 `--onefile` 形式分发打包版，分发材料中**实际捆绑**的第三方组件可能包括：

- **Python 解释器**：PSF License，由 PyInstaller 自动捆绑
- **PyInstaller bootloader**：GPL-2.0 with bootloader exception，允许闭源分发
- **`pynvml`**（如果打包环境安装了该包）：BSD 3-Clause，见上文

`probe.py`、`profiles/`、`common.py`、`hardware.py`、`recommend.py`、`solution.py` 均以独立文件形式随打包目录分发，运行时通过子进程调用，不构成对目标应用的衍生作品。

## 商标声明

“ComfyUI” 是 Comfy Org 的商标，“Stable Diffusion” 是 Stability AI 的商标，“PyTorch” 是 Linux Foundation 的商标。本工具中出现上述名称仅用于描述性说明检测对象，不表示任何隶属关系或官方背书。