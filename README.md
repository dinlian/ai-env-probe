# AI Env Probe

> A universal AI inference environment checker for **ComfyUI**, **Stable Diffusion WebUI**,
> **HuggingFace Diffusers**, and **vLLM**. Detects GPU / driver / PyTorch compatibility,
> recommends the correct CUDA build, and generates step-by-step fix plans.
>
> No Python installation required if you download the packaged release.
>
> 中文文档见下方。For full documentation in Chinese, see below.

---

通用 AI 推理环境检测工具。一次运行，输出硬件信息、PyTorch 版本推荐、加速可用性和依赖缺失诊断，并在出现问题时给出分阶段、可验证、可回滚的修复方案。

## 我应该下载哪个？

| 你的情况 | 下载这个 | 需要 Python |
|---|---|---|
| **已经装了 ComfyUI，想检测它的环境** | `ai-env-probe-1.0.0.zip`（源码包） | 需要（ComfyUI 自带） |
| **还没装 ComfyUI，只想看看电脑能不能跑 AI** | `ai-env-probe-1.0.0-windows.zip` / `macos.zip` / `linux.zip`（打包版） | **不需要** |
| **不确定自己属于哪种情况** | **下载打包版**，两种场景都能处理 | **不需要** |

打包版在 ComfyUI 目录下会做完整检测，不在 ComfyUI 目录下会做硬件预检并引导下一步。

## 支持的应用

| Profile | 检测对象 | 自动识别条件 |
|---|---|---|
| `comfyui` | ComfyUI (第三方检测) | `main.py` + `custom_nodes/` |
| `a1111` | Stable Diffusion WebUI (第三方检测) | `webui.py` 或 `launch.py` |
| `diffusers` | HuggingFace Diffusers (第三方检测) | `requirements.txt` 含 `diffusers` |
| `vllm` | vLLM (第三方检测) | `vllm/` 目录 + `setup.py`，或 `requirements.txt` 含 `vllm` |
| `generic` | 任意 PyTorch 项目 | 以上均未命中 |

## 快速开始

### 方式一：打包版（小白用户推荐）

1. 到 [Releases](../../releases) 页面下载对应系统的压缩包
2. 解压到任意目录
3. 双击可执行文件

**不需要安装 Python**。如果工具放在 ComfyUI 根目录（与 `main.py` 同级），会自动找到 ComfyUI 的解释器做完整检测；如果不在，会做硬件预检并提示下一步。

Windows 首次运行可能被 SmartScreen 拦截，点击「更多信息 → 仍要运行」。
macOS 首次运行需右键 → 打开，或执行 `xattr -d com.apple.quarantine <文件名>`。

### 方式二：源码 + 启动脚本（已有 ComfyUI 的用户）

把整个目录放到目标应用根目录，然后双击：

- Windows: `run_check.bat`
- macOS: `run_check.command`（首次右键 → 打开，或 `chmod +x`）
- Linux: `run_check.sh`

启动脚本会按优先级自动寻找解释器，不需要额外配置。

### 方式三：命令行

```bash
# 在目标应用目录下运行
python launcher.py --base-dir /path/to/target --profile auto

# 指定解释器和 profile
python launcher.py --python /path/to/python --profile comfyui

# CI 场景输出 JSON
python launcher.py --json > report.json

# 列出所有可用 profile
python3 launcher.py --list-profiles