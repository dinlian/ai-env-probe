#!/bin/bash
# ============================================================
#  AI Env Probe - macOS/Linux 启动脚本
#  Copyright (c) 2026 dinlian
#  Licensed under the MIT License. See LICENSE file for details.
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

if [ -n "$AI_ENV_PROBE_PYTHON" ] && [ -x "$AI_ENV_PROBE_PYTHON" ]; then
    run_and_pause "$AI_ENV_PROBE_PYTHON" launcher.py --base-dir "$BASE_DIR"
fi

for py in "python/bin/python3" "python/bin/python"; do
    if [ -x "$py" ]; then
        export AI_ENV_PROBE_LAUNCHER=1
        run_and_pause "./$py" launcher.py --base-dir "$BASE_DIR"
    fi
done

for venv in venv .venv; do
    if [ -x "$venv/bin/python" ]; then
        run_and_pause "$venv/bin/python" launcher.py --base-dir "$BASE_DIR"
    fi
done

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

if command -v python3 >/dev/null 2>&1; then
    run_and_pause python3 launcher.py --base-dir "$BASE_DIR"
fi
if command -v python >/dev/null 2>&1; then
    run_and_pause python launcher.py --base-dir "$BASE_DIR"
fi

cat <<'EOF'

============================================================
  没有找到可用的 Python 环境
============================================================

你可能遇到了以下情况之一，请对照处理：

 【情况 A】你已经装了 ComfyUI，但工具没有放在 ComfyUI 目录里
    解决：把整个 ai-env-probe 文件夹复制到 ComfyUI 根目录
          （与 main.py 在同一个文件夹里），再运行启动脚本。

 【情况 B】你还没装 ComfyUI，只想看看这台电脑能不能跑 AI
    解决：下载"打包版"，不需要安装 Python，双击就能用：
          https://gitee.com/dinlian_1/ai-env-probe/releases
          选择对应系统的压缩包。

 【情况 C】你确认自己装了 Python，但工具就是找不到
    解决：在终端运行 which python3 和 which python，截图发给开发者。

============================================================
EOF
read -n 1 -s -r -p "按任意键关闭..."
echo
exit 1