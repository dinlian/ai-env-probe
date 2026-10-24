# AI Env Probe

> A universal AI inference environment checker for **ComfyUI**, **Stable Diffusion WebUI**, **HuggingFace Diffusers**, and **vLLM**. Detects GPU / driver / PyTorch compatibility, recommends the correct CUDA build, and generates step-by-step fix plans.
>
> No Python installation required if you download the packaged release.

---

通用 AI 推理环境检测工具。一次运行，输出硬件信息、PyTorch 版本推荐、加速可用性和依赖缺失诊断，并在出现问题时给出分阶段、可验证、可回滚的修复方案。

## 📥 我应该下载哪个？

| 你的情况 | 下载这个 | 需要懂 Python 吗？ |
|---|---|---|
| **纯小白：电脑上也没 Python，只想测测显卡能不能跑 AI** | `ai-env-probe-1.0.0-windows.zip` / `ai-env-probe-1.0.0-linux.zip`（打包版） | **完全不需要** |
| **已装 ComfyUI：想检测当前环境为什么报错或跑得慢** | 源码包，双击 `run_check.bat` | 需要（ComfyUI 自带，不用另装） |
| **不确定自己属于哪种情况** | **下载打包版**，解压双击就能用，两种场景都兼容 | **完全不需要** |

**打包版使用指南**：下载解压后，双击可执行文件（Windows 为 `ai-env-probe.exe`，Linux 为 `./ai-env-probe`）。如果工具放在 ComfyUI 根目录（与 `main.py` 同级），它会自动做完整环境检测；如果不在，它会做硬件预检并告诉你下一步怎么做。

## ✨ 支持的应用

| Profile | 检测对象 | 自动识别条件 |
|---|---|---|
| `comfyui` | ComfyUI (第三方检测) | `main.py` + `custom_nodes/` |
| `a1111` | Stable Diffusion WebUI (第三方检测) | `webui.py` 或 `launch.py` |
| `diffusers` | HuggingFace Diffusers (第三方检测) | `requirements.txt` 含 `diffusers` |
| `vllm` | vLLM (第三方检测) | `vllm/` 目录 + `setup.py` |
| `generic` | 任意 PyTorch 项目 | 以上均未命中 |

---

## ❓ 常见问题与避坑指南 (FAQ)

由于本工具是个人开源的免费软件，没有购买商业数字签名，所以不同系统可能会触发安全拦截。**请放心，本工具不联网、不上传数据、绝对安全**。以下是各系统的解除拦截指南：

### 🛑 Windows 用户看这里

**1. 提示“Windows 已保护你的电脑” (SmartScreen)**
这是因为没有数字签名。点击弹窗上的 **“更多信息”**，然后点击右下角出现的 **“仍要运行”** 即可。

**2. 提示“智能应用控制已阻止可能不安全的应用” (Smart App Control)**
这是 Windows 11 极其严格的拦截（见弹窗“无法验证发布者”）。因为这个功能一旦关闭，**未来可能需要重装系统才能重新开启**，所以请在你信任本工具的前提下操作：
- 点击屏幕右下角的盾牌图标，打开 **Windows 安全中心**。
- 点击左侧的 **“应用和浏览器控制”**。
- 点击 **“智能应用控制设置”**。
- 将状态从“强制”切换为 **“关闭”**，然后重新双击运行工具。

### 🍎 macOS 用户看这里

**1. 提示“无法打开，因为无法验证开发者” (Gatekeeper)**
- **方法 A**：在 `run_check.command` 或下载的可执行文件上 **右键点击**，选择 **“打开”**，然后在弹窗中再次点击“打开”。
- **方法 B**：打开终端，输入 `xattr -d com.apple.quarantine 你的文件名` 来解除隔离。

**2. 终端提示“Permission denied” (权限不足)**
Mac/Linux 默认下载的脚本没有执行权限。请在终端里运行一次 `chmod +x run_check.command` 即可。

### 🐧 Linux 用户看这里

**1. 双击没反应 / 提示权限不足**
请打开终端，进入解压后的目录，执行 `chmod +x ai-env-probe`，然后输入 `./ai-env-probe` 运行。

**2. 我该如何让工具检测我的 ComfyUI？**
请确保工具的可执行文件（或 `.bat` 脚本）与 ComfyUI 的 `main.py` 在**同一个文件夹**内，工具会自动找到旁边的 `python_embeded` 或 `venv` 环境进行检测。

---

## 💻 命令行参数（进阶）

```bash
# 在目标应用目录下运行
python launcher.py --base-dir /path/to/target --profile auto

# 指定解释器和 profile
python launcher.py --python /path/to/python --profile comfyui

# CI 场景输出 JSON
python launcher.py --json > report.json

# 列出所有可用 profile
python launcher.py --list-profiles