@echo off
REM ============================================================
REM  AI Env Probe - Windows 启动脚本
REM  Copyright (c) 2026 dinlian
REM  Licensed under the MIT License. See LICENSE file for details.
REM ============================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if defined AI_ENV_PROBE_PYTHON if exist "%AI_ENV_PROBE_PYTHON%" (
    "%AI_ENV_PROBE_PYTHON%" launcher.py --base-dir "%~dp0"
    goto :end
)

if exist "python\python.exe" (
    set AI_ENV_PROBE_LAUNCHER=1
    "python\python.exe" launcher.py --base-dir "%~dp0"
    goto :end
)
if exist "python_embeded\python.exe" (
    "python_embeded\python.exe" launcher.py --base-dir "%~dp0"
    goto :end
)
if exist "python_embedded\python.exe" (
    "python_embedded\python.exe" launcher.py --base-dir "%~dp0"
    goto :end
)
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" launcher.py --base-dir "%~dp0"
    goto :end
)
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" launcher.py --base-dir "%~dp0"
    goto :end
)

for %%E in (comfyui comfyui-py313 comfyui-py312 comfyui-py311 comfyui-py310 sd stable-diffusion base) do (
    if exist "%USERPROFILE%\miniforge3\envs\%%E\python.exe" (
        "%USERPROFILE%\miniforge3\envs\%%E\python.exe" launcher.py --base-dir "%~dp0"
        goto :end
    )
    if exist "%USERPROFILE%\anaconda3\envs\%%E\python.exe" (
        "%USERPROFILE%\anaconda3\envs\%%E\python.exe" launcher.py --base-dir "%~dp0"
        goto :end
    )
    if exist "%USERPROFILE%\miniconda3\envs\%%E\python.exe" (
        "%USERPROFILE%\miniconda3\envs\%%E\python.exe" launcher.py --base-dir "%~dp0"
        goto :end
    )
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 launcher.py --base-dir "%~dp0"
    goto :end
)
where python >nul 2>nul
if %errorlevel%==0 (
    python launcher.py --base-dir "%~dp0"
    goto :end
)

echo.
echo ============================================================
echo   没有找到可用的 Python 环境
echo ============================================================
echo.
echo  你可能遇到了以下情况之一，请对照处理：
echo.
echo  【情况 A】你已经装了 ComfyUI，但工具没有放在 ComfyUI 目录里
echo     解决：把整个 ai-env-probe 文件夹复制到 ComfyUI 根目录
echo           （与 main.py 在同一个文件夹里），再双击 run_check.bat
echo.
echo  【情况 B】你还没装 ComfyUI，只想看看这台电脑能不能跑 AI
echo     解决：下载"打包版"，不需要安装 Python，双击就能用：
echo           https://gitee.com/dinlian_1/ai-env-probe/releases
echo           选择文件名里带 windows.zip 的那个，解压后双击 exe
echo.
echo  【情况 C】你确认自己装了 Python，但工具就是找不到
echo     解决：在命令行里运行以下两条命令，把输出截图发给开发者：
echo           where python
echo           where py
echo.
echo  【不确定自己属于哪种情况？】
echo     直接用情况 B 的打包版即可，它两种场景都能处理。
echo.
echo ============================================================
pause
exit /b 1

:end
echo.
pause