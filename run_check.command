#!/bin/bash
# ============================================================
#  AI Env Probe - macOS 启动脚本
#  Copyright (c) 2026 dinlian
#  Licensed under the MIT License. See LICENSE file for details.
#  本脚本仅做本地环境检测，不联网、不上传数据、不修改系统配置。
#  AI_ENV_PROBE_PYTHON 应指向目标应用实际使用的解释器，
#  而不是任意系统 Python，否则检测结果可能失真。
# ============================================================
cd "$(dirname "$0")" || exit 1
BASE_DIR="$(pwd)"

run_and_pause() {
    "$@"
    local code=$?
    echo
    read -n 1 -s -r -p "按任意键关闭..."
    echo
    exit $code
}

# 0. 用户手动指定目标解释器
if [ -n "$AI_ENV_PROBE_PYTHON" ] && [ -x "$AI_ENV_PROBE_PYTHON" ]; then
    run_and_pause "$AI_ENV_PROBE_PYTHON" launcher.py --base-dir "$BASE_DIR"
fi

# 1. 便携 Python（只用于跑启动器，不参与检测目标）
for py in "python/bin/python3" "python/bin/python"; do
    if [ -x "$py" ]; then
        export AI_ENV_PROBE_LAUNCHER=1
        run_and_pause "./$py" launcher.py --base-dir "$BASE_DIR"
    fi
done

# 2. 目标应用自带解释器
for venv in venv .venv; do
    if [ -x "$venv/bin/python" ]; then
        run_and_pause "$venv/bin/python" launcher.py --base-dir "$BASE_DIR"
    fi
done

# 3. 常见 conda 环境
for env in comfyui comfyui-py313 comfyui-py312 comfyui-py311 comfyui-py310 sd stable-diffusion base; do
    for base in "$HOME/miniforge3" "$HOME/anaconda3" "$HOME/miniconda3" "$HOME/mambaforge"; do
        py="$base/envs/$env/bin/python"
        if [ -x "$py" ]; then
            run_and_pause "$py" launcher.py --base-dir "$BASE_DIR"
        fi
        py="$base/bin/python"
        if [ "$env" = "base" ] && [ -x "$py" ]; then
            run_and_pause "$py" launcher.py --base-dir "$BASE_DIR"
        fi
    done
done

# 4. 系统 Python
if command -v python3 >/dev/null 2>&1; then
    run_and_pause python3 launcher.py --base-dir "$BASE_DIR"
fi
if command -v python >/dev/null 2>&1; then
    run_and_pause python launcher.py --base-dir "$BASE_DIR"
fi

# ---------- 未找到 Python：分情况引导用户 ----------
cat <<'EOF'

============================================================
  没有找到可用的 Python 环境
============================================================

你可能遇到了以下情况之一，请对照处理：

 【情况 A】你已经装了 ComfyUI，但工具没有放在 ComfyUI 目录里

    解决：把整个 ai-env-probe 文件夹复制到 ComfyUI 根目录
          （与 main.py 在同一个文件夹里），再双击 run_check.command

 【情况 B】你还没装 ComfyUI，只想看看这台电脑能不能跑 AI

    解决：下载"打包版"，不需要安装 Python，双击就能用：
          https://github.com/dinlian/ai-env-probe/releases
          选择文件名里带 macos.zip 的那个，解压后双击可执行文件
          （首次运行需右键 → 打开，绕过 macOS 安全拦截）

 【情况 C】你确认自己装了 Python，但工具就是找不到

    解决：打开"终端"应用，运行以下两条命令，把输出截图发给开发者：
          which python3
          which python

 【不确定自己属于哪种情况？】

    直接用情况 B 的打包版即可，它两种场景都能处理。

============================================================
EOF
read -n 1 -s -r -p "按任意键关闭..."
echo
exit 1