# AI Env Probe - Windows 启动脚本 (PowerShell 版)
$Host.UI.RawUI.WindowTitle = "AI Env Probe - 环境检测"
chcp 65001 > $null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Set-Location -Path $PSScriptRoot

function Run-Command ($cmd) {
    Invoke-Expression $cmd
    exit
}

# 0. 用户手动指定
if ($env:AI_ENV_PROBE_PYTHON -and (Test-Path $env:AI_ENV_PROBE_PYTHON)) {
    Run-Command "& '$env:AI_ENV_PROBE_PYTHON' launcher.py --base-dir '$PSScriptRoot'"
}

# 1. 便携 Python
if (Test-Path "python\python.exe") {
    $env:AI_ENV_PROBE_LAUNCHER = "1"
    Run-Command "& '.\python\python.exe' launcher.py --base-dir '$PSScriptRoot'"
}

# 2. 目标应用自带解释器
if (Test-Path "python_embeded\python.exe") {
    Run-Command "& '.\python_embeded\python.exe' launcher.py --base-dir '$PSScriptRoot'"
}
if (Test-Path "python_embedded\python.exe") {
    Run-Command "& '.\python_embedded\python.exe' launcher.py --base-dir '$PSScriptRoot'"
}
if (Test-Path "venv\Scripts\python.exe") {
    Run-Command "& '.\venv\Scripts\python.exe' launcher.py --base-dir '$PSScriptRoot'"
}
if (Test-Path ".venv\Scripts\python.exe") {
    Run-Command "& '.\.venv\Scripts\python.exe' launcher.py --base-dir '$PSScriptRoot'"
}

# 3. 常见 conda 环境
$condaEnvs = @("comfyui", "comfyui-py313", "comfyui-py312", "comfyui-py311", "comfyui-py310", "sd", "stable-diffusion", "base")
$condaBases = @("$env:USERPROFILE\miniforge3", "$env:USERPROFILE\anaconda3", "$env:USERPROFILE\miniconda3")
foreach ($base in $condaBases) {
    foreach ($envName in $condaEnvs) {
        $pyPath = "$base\envs\$envName\python.exe"
        if ($envName -eq "base") { $pyPath = "$base\python.exe" }
        
        if (Test-Path $pyPath) {
            Run-Command "& '$pyPath' launcher.py --base-dir '$PSScriptRoot'"
        }
    }
}

# 4. 系统 Python (py 或 python)
if (Get-Command "py" -ErrorAction SilentlyContinue) {
    Run-Command "py -3 launcher.py --base-dir '$PSScriptRoot'"
}
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    Run-Command "python launcher.py --base-dir '$PSScriptRoot'"
}

# ========== 找不到 Python：分情况中文引导 ==========
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  ❌ 没有找到可用的 Python 环境" -ForegroundColor Red
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host " 你可能遇到了以下情况之一，请对照处理：" -ForegroundColor Yellow
Write-Host ""
Write-Host "  【情况 A】你已经装了 ComfyUI，但工具没有放在 ComfyUI 目录里"
Write-Host "     解决：把整个 ai-env-probe 文件夹复制到 ComfyUI 根目录"
Write-Host "           （与 main.py 在同一个文件夹里），再双击 run_check.bat" -ForegroundColor Green
Write-Host ""
Write-Host "  【情况 B】你还没装 ComfyUI，只想看看这台电脑能不能跑 AI"
Write-Host "     解决：下载“打包版”，不需要安装 Python，双击就能用：" -ForegroundColor Green
Write-Host "           https://gitee.com/dinlian_1/ai-env-probe/releases" -ForegroundColor Blue
Write-Host "           选择文件名里带 windows.zip 的那个，解压后双击 exe"
Write-Host ""
Write-Host "  【情况 C】你确认自己装了 Python，但工具就是找不到"
Write-Host "     解决：在命令行里运行 where python，看看有没有输出。" -ForegroundColor Green
Write-Host ""
Write-Host "  【不确定自己属于哪种情况？】"
Write-Host "     直接用情况 B 的打包版即可，它两种场景都能处理。" -ForegroundColor Green
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""