本文件记录 AI Env Probe 的所有重要变更。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2026-10-24

首个稳定版本。经多轮迭代后定稿，覆盖主流 NVIDIA / AMD / Intel / Apple / CPU
硬件，支持 ComfyUI、Stable Diffusion WebUI、HuggingFace Diffusers、vLLM
等应用的环境检测，并在问题场景下给出分阶段、可验证、可回滚的修复方案。

### Added

#### 核心架构
- **启动器 / 检测器分离**：`launcher.py` 负责硬件探测与调度，`probe.py`
  通过子进程在目标解释器中独立执行检测，不共享地址空间，避免启动器自身
  Python 环境污染检测结果。
- **启动器模式标记**：`AI_ENV_PROBE_LAUNCHER=1` 时 `find_python` 跳过
  `sys.executable` 候选，避免便携 Python 或打包 exe 被误当成检测目标。
  打包模式下由 `main()` 自动设置该变量。
- **多 profile 支持**：`profiles/*.json` 定义各应用的依赖清单，新增应用
  只需加 JSON 文件，无需改 Python 代码。
  - 内置 profile：`comfyui`、`a1111`、`diffusers`、`vllm`、`generic`
  - `--profile auto` 根据目录特征自动识别
  - `--list-profiles` 列出所有可用配置
- **模块拆分**：
  - `common.py`：常量、版本、版权、目录识别、路径工具
  - `hardware.py`：硬件探测（NVIDIA / AMD / Intel / macOS 三分支）
  - `recommend.py`：版本推荐、显存适配建议
  - `launcher.py`：编排层（参数解析、解释器定位、probe 调度、输出渲染）
  - `probe.py`：目标环境检测器
  - `solution.py`：修复方案生成器

#### 硬件覆盖
- **NVIDIA**：Pascal (GTX 10) → Volta (V100) → Turing (RTX 20) →
  Ampere (RTX 30) → Ada (RTX 40) → Hopper (H100) → Blackwell (RTX 50)，
  含专业卡（A100/A800/H100/H200/T4/L4/L40/RTX A 系列）
- **AMD**：Vega → RDNA1 → RDNA2 (RX 6000) → RDNA3 (RX 7000) → RDNA4 (RX 9000)
- **Intel**：Arc 独显（A/B 系列）与 Iris Xe / UHD 核显分流处理
- **Apple**：macOS 三分支检测
  - Apple Silicon (M1–M4)：MPS 后端
  - Intel Mac + AMD 独显（含黑苹果）：MPS 实验性支持，明确警告
  - Intel Mac 核显 / 纯 CPU：CPU 模式
- **CPU**：无 GPU 或 GPU 不可用时的兜底分支

#### 版本推荐逻辑
- **架构 + 驱动联合决策**：不再按架构写死 CUDA 版本，而是结合驱动版本
  决定可用 tag。
- **Pascal/Volta 推荐上限锁定 cu124**：cu126+ 的 wheel 已移除 `sm_61` /
  `sm_70` 内核，强行安装会报 `no kernel image is available`。
- **Blackwell 需 cu128+**：RTX 50 的 `sm_120` 从 CUDA 12.8 开始支持，
  驱动低于 570 明确报错。
- **驱动 `smi_cuda` 上限校验**：驱动只支持 CUDA 12.x 时，不会推荐 cu130，
  自动降级到 cu126 或 cu118。
- **CUDA 主版本归一化**：统一处理 `"13.0"`、`13000`、`"12.8"` 等不同格式，
  避免 `13000 ≠ 13.0` 的误报。

#### 检测能力
- **矩阵乘法实测**：`torch.cuda.is_available()` 为 True 不代表能跑 kernel，
  实测 256×256 矩阵乘法确认加速真正可用。非 CUDA 后端返回 `skipped=True`，
  不阻断 MPS / XPU / CPU 用户。
- **架构匹配检查**：比对 `torch.cuda.get_device_capability()` 与
  `torch.cuda.get_arch_list()`，提前发现架构不被支持的问题。
- **Python 解释器一致性**：比对当前解释器版本与 `torch.version.cpython`
  的 `cpXXX` 标签，避免 Python 3.12 用户装了 cp313 wheel。
- **CUDA 主版本一致性**：torch、torchvision、torchaudio 三方 CUDA 主版本
  必须一致。
- **cuDNN 可用性**：卷积类模型性能的关键指标。
- **依赖检查**：按 profile 的 `core` / `extra` 分类，`core` 缺失影响启动，
  `extra` 缺失仅提示不影响。

#### 修复方案
- **分阶段修复计划**：按严重度（critical / high / medium / low）和依赖关系
  排序，用户按阶段执行、每步验证、失败有备选。
- **覆盖的问题类型**：
  - torch 未装 / 导入失败 → 在线/离线双路径安装
  - 架构不匹配 / 矩阵失败 → 卸载 + 清缓存 + 装正确版本
  - 驱动过低 → 下载 URL + 重启 + 验证；无法升级时降级 cu126
  - Python 版本不匹配 → 换解释器 / 重装 wheel 两条路线
  - 依赖缺失 → 先 `-r requirements.txt`，失败再逐个装
  - 依赖版本低 → `--upgrade` + 版本约束
- **回滚支持**：修复前 `pip freeze` 快照，出问题一条命令回滚。

#### 显存建议
- **按 profile 区分建议内容**：
  - `comfyui`：图片 + 视频模型分档
  - `a1111` / `diffusers`：图片模型分档
  - `vllm`：LLM 显存分档（7B/13B/34B/70B × FP16/AWQ/GPTQ）
  - `generic`：图片模型分档
- **覆盖最新模型**：SD1.5、SDXL、SD3.5 Medium/Large、FLUX.1-dev、
  Flux.2、Qwen Image、LTX-Video 2B、Wan 1.3B/14B、HunyuanVideo 1.5、
  CogVideoX、AnimateDiff、SVD 等。

#### 小白用户友好设计
- **快速结论**：输出最前面增加一段“一眼结论”，告诉用户显卡型号、能否运行、
  推荐版本。
- **硬件预检模式**：找不到目标应用解释器时不再报错退出，自动降级为硬件
  预检，输出硬件信息、推荐版本、显存建议和下一步指引。
- **启动脚本分情况引导**：`run_check.bat` / `.command` / `.sh` 找不到 Python
  时，不再输出技术术语清单，而是按“情况 A / B / C”引导用户，并给出打包版
  下载链接，避免小白用户卡在“我到底属于哪种情况”上。
- **一键打包脚本**：`build.bat`（Windows）/ `build.sh`（macOS/Linux）一键
  生成 `--onedir` 打包版，用户双击即用、无需安装 Python。

#### 输出与集成
- **`--json` 模式**：输出完整结构化数据，适合 CI 直接消费；失败时也输出
  统一结构（带 `error` 字段）。
- **`--quiet` 模式**：抑制所有人类可读输出（banner、section 标题、详细
  诊断）；出错时仍输出错误信息。适合需要静默运行的脚本场景。
- **进度提示**：`run_probe` 执行前提示“正在调用 probe.py...”，避免用户
  以为卡死（最长等待 180s）。
- **显存建议语义化**：矩阵实测输出“通过 / 失败 / 跳过（非 CUDA 后端）”，
  而非 `True/False`。
- **profile auto 识别依据**：输出“auto 识别结果，依据 base_dir 目录特征”，
  方便用户判断识别是否准确。

#### 三平台一键启动
- `run_check.bat`（Windows）：`chcp 65001` 解决中文乱码；`cd /d "%~dp0"`
  保证从任意位置双击都能定位；优先 `py -3` 避免 Microsoft Store 占位符。
- `run_check.command`（macOS）：`cd "$(dirname "$0")"`；`read -n 1` 停留；
  首次需 `chmod +x` 或右键 → 打开。
- `run_check.sh`（Linux）：同上。
- **解释器查找优先级**：`AI_ENV_PROBE_PYTHON` 环境变量 → `python_embeded/`
  → `python_embedded/` → `venv/` → `.venv/` → 常见 conda 环境
  （`comfyui` / `comfyui-py310~313` / `sd` / `stable-diffusion` / `base`）
  → 系统 `py -3` / `python` / `python3`。
- **找不到 Python 时的引导**：分“情况 A（工具位置不对）/ 情况 B（还没装
  ComfyUI）/ 情况 C（装了但找不到）”给出具体行动和打包版下载链接。

#### 构建与分发
- `build.bat` / `build.sh`：一键生成 PyInstaller `--onedir` 打包版。
- **分发形态建议**：源码 + 启动脚本（GPL 独立程序抗辩最强）或
  `--onedir` 打包（非技术用户友好），不推荐 `--onefile`。

#### 测试
- `tests/test_compat.py`：兼容性规则回归
  - Pascal/Volta 永不推荐 cu126+
  - Blackwell 需 cu128+
  - Ampere 驱动感知
  - `smi_cuda` 上限校验
  - CUDA 主版本归一化
  - `cuXXX` → 主版本转换
- `tests/test_profiles.py`：profile 完整性
  - 所有 profile 结构合法
  - 不含 `torch`/`torchvision`/`torchaudio`（已在 probe 单独检查）
  - 非 generic profile 名称含“第三方检测”限定词

### Changed

#### 行为变化
- **`find_python` 优先级调整**：
  1. `--python` 显式指定
  2. `base_dir` 下的专用解释器（`python_embeded` / `venv` / `.venv`）
  3. `sys.executable`（仅当非启动器模式、能 `import torch` **且**
     `base_dir` 像目标应用根目录）
  4. `cwd` 下的专用解释器
  5. 系统 `python3` / `python`

  旧版会无条件使用 `sys.executable`，导致在 conda base 环境运行时误判
  为 ComfyUI 目标环境。

- **`build_pip_cmd` 生成带路径的命令**：从 `python -m pip ...` 改为
  `{target_python} -m pip ...`，避免用户看到命令后装到错误环境。

- **`is_healthy` 简化**：静态项完全交给 `probe.env_issues`，`is_healthy`
  只判断动态测试（CUDA / XPU / MPS 可用性、矩阵实测）。避免双重判断
  在边界情况不一致。

- **AMD Windows 不再因 CUDA 不可用被判不健康**：CUDA 不可用是预期行为，
  只要 torch 能导入、core 依赖齐全即视为健康。

- **`matrix_test` 在非 CUDA 环境返回 `passed=True`（`skipped=True`）**：
  MPS / XPU / CPU 用户不应被矩阵测试阻断。

- **`env_issues` 去重**：`torchvision` 缺失不再同时出现在“导入失败”和
  “依赖缺失”两个位置。

- **profile 名称加限定词**：`ComfyUI` → `ComfyUI (第三方检测)`，
  降低商标混淆风险。

- **`--quiet` 抑制所有人类可读输出**：旧版只抑制 banner，section 标题仍打印，
  CI 场景仍嘈杂。新版在 `--quiet` 下 `render_*` 全部跳过，只保留最终
  错误信息。

- **启动脚本错误提示重写**：从技术术语清单改为“情况 A / B / C + 不确定
  就下打包版”三段式引导，面向小白用户。

### Fixed

- **Pascal/Volta 被推荐 cu126 的回归**：cu126+ 已移除 `sm_61`/`sm_70` 内核，
  推荐会误导用户安装无法运行的环境。
- **`13000 vs 13.0` 误报**：`torchvision.version.cuda` 返回整数 `13000`，
  `torch.version.cuda` 返回字符串 `"13.0"`，直接比较会误报主版本不一致。
- **健康环境被建议卸载重装**：旧版只要推荐版本与实际不同就提示重装，
  即使环境完全正常。
- **打包后找不到 profiles**：`load_profile` 未处理 `sys._MEIPASS`。
- **`find_python` 对 `base_dir` 与 `cwd` 优先级错误**：旧版先查 `cwd`，
  在从其它目录启动时可能找错解释器。
- **`torch` 不可用时仍执行依赖检查**：产生大量误导性“依赖缺失”报错。
- **Windows `wmic` 已弃用**：优先 `PowerShell Get-CimInstance`，
  `wmic` 仅作回退。
- **便携 Python / 打包 exe 被误判为目标环境**：新增
  `AI_ENV_PROBE_LAUNCHER=1` 标记，`find_python` 跳过 `sys.executable`。

### Security

- **不联网、不上传**：工具仅做本地只读检测，不向任何服务器发送数据。
- **不修改系统配置**：只读取版本、驱动、依赖信息，不写入任何配置。
- **不修改目标应用**：通过子进程调用 `probe.py`，不改动 ComfyUI、A1111、
  vLLM 等应用的任何文件。

### Compliance

- **`LICENSE`**：MIT 许可证，Copyright (c) 2026 dinlian。
- **`THIRD_PARTY_NOTICES.md`**：声明 PyTorch（BSD-3-Clause）、
  nvidia-ml-py（BSD-3-Clause）等第三方依赖的版权与许可，补齐二进制
  再分发的合规义务。
- **商标描述性使用**：README、BANNER、输出中明确“第三方独立脚本，
  与所检测应用无隶属关系或官方背书”；profile 名称带“(第三方检测)”
  限定词。
- **GPL 独立程序抗辩**：`launcher.py` 与 `probe.py` 保持两个独立文件，
  通过 `subprocess.run()` + JSON 管道交互，不链接、不复制、不重新分发
  目标应用代码。
- **分发建议**：推荐源码 + 启动脚本或 PyInstaller `--onedir`，
  不推荐 `--onefile`（会削弱独立程序抗辩）。

### Known Limitations

- **conda 用户双击启动脚本时不会自动激活环境**：双击 `.bat` / `.command`
  不会执行 `conda activate`，需要设置 `AI_ENV_PROBE_PYTHON` 指向目标
  解释器，或先激活环境再运行 `python launcher.py`。
- **macOS 桌面版 ComfyUI 运行时位置不固定**：可能需要手动 `--python`。
- **macOS 未签名二进制会被 Gatekeeper 拦截**：如果使用 PyInstaller 打包，
  用户需右键 → 打开，或执行 `xattr -d com.apple.quarantine`。
- **Windows 未签名 exe 会触发 SmartScreen**：如果打包分发，用户需
  “更多信息 → 仍要运行”。
- **驱动探测依赖 `nvidia-smi` 或 `pynvml`**：两者都不可用时，NVIDIA
  分支会失效，走 CPU 兜底。
- **`--onefile` 打包不推荐**：会削弱 GPL 独立程序抗辩，且若捆绑 `pynvml`
  需附 `THIRD_PARTY_NOTICES.md`。
- **profiles 依赖表为静态**：应用发布新版本时需手动更新
  `profiles/*.json` 中的最低版本要求。
- **启动脚本的打包版下载链接为占位符**：首次发布前需要把
  `https://github.com/dinlian/ai-env-probe/releases` 替换为实际仓库地址。

### Acknowledgements

- 感谢 PyTorch、ComfyUI、HuggingFace、vLLM 等开源社区提供的兼容性
  文档和版本矩阵。
- 感谢所有提交 issue 和 PR 的用户。

---

## 版本历史

| 版本 | 日期 | 说明 |
|---|---|---|
| 1.0.0 | 2026-10-24 | 首个稳定版本 |

---

## 未来计划（Roadmap）

以下为规划中的改进方向，不代表承诺：

- **profile 自动更新**：从各应用的官方 `requirements.txt` 自动拉取并
  更新 profile，减少手动维护。
- **更多 profile**：Ollama（非 Python，查二进制和模型目录）、
  LM Studio、Fooocus、SD.Next 等。
- **CI 集成模板**：提供 GitHub Actions / GitLab CI 的现成模板。
- **报告导出**：支持导出为 Markdown / HTML 报告，方便用户提交 issue 时
  附带环境信息。
- **硬件数据库在线更新**：`NVIDIA_MODELS` / `AMD_MODELS` 支持从远程
  更新，新显卡发布后无需等版本迭代。
- **GUI 版本**：为不熟悉命令行的用户提供简单的图形界面。