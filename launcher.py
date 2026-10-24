#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Env Probe - 启动器

Copyright (c) 2026 dinlian
Licensed under the MIT License. See LICENSE file for details.

本工具仅做本地环境检测，不修改系统配置，不联网上传数据。
通过子进程调用 probe.py，在目标应用的解释器中独立执行检测逻辑，
不链接、不复制、不重新分发目标应用的任何代码。

流程：探测硬件 → 推荐版本 → 定位目标解释器 → 调用 probe.py → 诊断输出 → 生成修复方案
"""

import os
import sys
import json
import argparse
import platform
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (
    TOOL_NAME, VERSION, COPYRIGHT, LICENSE, BANNER,
    auto_detect_profile_id, get_resource_dir, _looks_like_target_app,
)
from hardware import detect_all, pick_primary, primary_vram
from recommend import recommend, vram_advice
from solution import build_solution_plan, render_solution_plan


# ============================================================
# 输出工具
# ============================================================

def section(title):
    print(f"\n{'=' * 62}\n  {title}\n{'=' * 62}")


def ok(msg): print(f"  ✅ {msg}")
def warn(msg): print(f"  ⚠️  {msg}")
def err(msg): print(f"  ❌ {msg}")
def info(msg): print(f"     {msg}")
def rec(msg): print(f"  💡 推荐: {msg}")
def fix(msg): print(f"  🔧 修复: {msg}")


# ============================================================
# 定位目标解释器
# ============================================================

def find_python(base_dir=None, explicit_python=None):
    """优先级：
    1. --python 显式指定
    2. base_dir 下的专用解释器（python_embeded / venv / .venv）
    3. sys.executable（仅源码模式、非启动器模式、能 import torch 且 base_dir 像目标应用）
    4. cwd 下的专用解释器
    5. 系统 python3 / python

    AI_ENV_PROBE_LAUNCHER=1 时跳过第 3 步，避免便携 Python / 打包启动器
    被误当成目标环境。打包模式下由 main() 自动设置该变量。
    """
    if explicit_python and os.path.isfile(explicit_python):
        return explicit_python

    launcher_mode = os.environ.get("AI_ENV_PROBE_LAUNCHER") == "1"

    def _search(d):
        if not d:
            return None
        for c in [
            os.path.join(d, "python_embeded", "python.exe"),
            os.path.join(d, "python_embeded", "python"),
            os.path.join(d, "python_embedded", "python.exe"),
            os.path.join(d, "python_embedded", "python"),
            os.path.join(d, "venv", "Scripts", "python.exe"),
            os.path.join(d, "venv", "bin", "python"),
            os.path.join(d, ".venv", "Scripts", "python.exe"),
            os.path.join(d, ".venv", "bin", "python"),
        ]:
            if os.path.isfile(c):
                return c
        return None

    # 2. base_dir 下的专用解释器
    found = _search(base_dir)
    if found:
        return found

    # 3. sys.executable（仅源码模式、非启动器模式、且 base_dir 像目标应用）
    if not getattr(sys, "frozen", False) and not launcher_mode:
        if _looks_like_target_app(base_dir):
            try:
                import torch  # noqa: F401
                return sys.executable
            except Exception:
                pass

    # 4. cwd 下的专用解释器
    cwd = os.getcwd()
    if cwd != base_dir:
        found = _search(cwd)
        if found:
            return found

    # 5. 系统 python
    for cmd in ["python3", "python"]:
        try:
            subprocess.check_output([cmd, "--version"], stderr=subprocess.DEVNULL)
            return cmd
        except Exception:
            continue
    return None


def run_probe(target_python, profile, base_dir, quiet=False):
    probe = os.path.join(get_resource_dir(), "probe.py")
    if not os.path.isfile(probe):
        err(f"找不到 probe.py: {probe}")
        return None

    if not quiet:
        info("正在调用 probe.py 检测目标环境（最长等待 180s）...")

    try:
        result = subprocess.run(
            [target_python, probe, "--profile", profile, "--base-dir", base_dir or os.getcwd()],
            capture_output=True, text=True, timeout=180
        )
    except subprocess.TimeoutExpired:
        err("probe.py 执行超时（>180s）")
        return None
    except Exception as e:
        err(f"调用 probe.py 失败: {e}")
        return None

    if result.returncode != 0:
        err(f"probe.py 退出码 {result.returncode}")
        if result.stderr:
            info(f"stderr: {result.stderr[:500]}")
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        err(f"probe.py 输出非 JSON: {e}")
        info(f"stdout 前 300 字符: {result.stdout[:300]}")
        return None


# ============================================================
# 健康判断（env_issues 负责静态项，本函数补充动态项）
# ============================================================

def is_healthy(backend, probe):
    if probe.get("env_issues"):
        return False

    if backend in ("NVIDIA CUDA", "AMD ROCm"):
        if not probe.get("cuda_available"):
            return False
        if probe.get("matrix_test", {}).get("passed") is False:
            return False
    elif backend == "Intel XPU":
        if not probe.get("xpu_available"):
            return False
    elif backend.startswith("Apple MPS"):
        if not probe.get("mps_available"):
            return False
    # CPU 分支、AMD Windows 分支：env_issues 为空即视为健康
    return True


# ============================================================
# 列出 profiles
# ============================================================

def list_profiles():
    profiles_dir = os.path.join(get_resource_dir(), "profiles")
    if not os.path.isdir(profiles_dir):
        print(f"profiles 目录不存在: {profiles_dir}")
        return 1
    print(f"\n可用检测配置（{profiles_dir}）:\n")
    for f in sorted(os.listdir(profiles_dir)):
        if f.endswith(".json"):
            path = os.path.join(profiles_dir, f)
            try:
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
                name = data.get("name", f[:-5])
                pid = f[:-5]
                print(f"  {pid:<12}  {name}")
            except Exception:
                print(f"  {f[:-5]:<12}  （解析失败）")
    print()
    return 0


# ============================================================
# 人类可读输出
# ============================================================

def render_hardware(hardware, quiet=False):
    if quiet:
        return
    section("1. 系统与硬件探测")
    info(f"操作系统: {platform.platform()}")
    info(f"CPU 架构: {platform.machine()}")
    info(f"启动器 Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    if getattr(sys, "frozen", False):
        info("运行模式: 打包（启动器与目标环境隔离）")

    if hardware["nvidia"]:
        primary = pick_primary(hardware["nvidia"])
        info(f"NVIDIA GPU: {len(hardware['nvidia'])} 块")
        for i, g in enumerate(hardware["nvidia"]):
            mark = " ← 主卡" if g is primary else ""
            info(f"  [{i}] {g['name']} | 显存 {g['vram_gb']} GB | 驱动 {g['driver']} | "
                 f"smi CUDA {g['smi_cuda'] or '未知'}{mark}")
    elif hardware["mac_gpu"]:
        m = hardware["mac_gpu"]
        info(f"macOS GPU: 类型 {m['type']} | 芯片 {m['name']}"
             + (f" | 显存 {m['vram_gb']} GB" if m.get("vram_gb") else ""))
    elif hardware["amd"]:
        primary = pick_primary(hardware["amd"])
        for i, g in enumerate(hardware["amd"]):
            mark = " ← 主卡" if g is primary else ""
            info(f"  [{i}] AMD {g['name']} | 显存 {g['vram_gb'] or '未知'} GB | "
                 f"{g['driver'] or '未知'}{mark}")
    elif hardware["intel"]["type"] == "arc":
        info(f"Intel Arc: {hardware['intel']['name']}")
    elif hardware["intel"]["type"] == "igpu":
        info(f"Intel 核显: {hardware['intel']['name']}")
    else:
        warn("未检测到独立 GPU，走 CPU 分支")


def render_recommend(recommended, quiet=False):
    if quiet:
        return
    section("2. 基于硬件的版本推荐")
    rec(f"后端: {recommended['backend']} | 架构: {recommended['arch']}")
    rec(f"说明: {recommended['note']}")


def render_probe(probe, profile_meta, quiet=False):
    if quiet:
        return
    section("4. 目标环境检测（probe）")
    print("     [说明] 以下应用名称仅用于描述检测对象，不表示官方关联或背书。")
    info(f"检测配置: {profile_meta.get('name', 'Unknown')} (id={profile_meta.get('id', '?')})")
    info(f"目标解释器 Python: {probe['python']['version']}")
    info(f"目标解释器路径: {probe['python']['executable']}")

    t = probe.get("torch", {})
    if t.get("installed"):
        info(f"torch: {t.get('version')} | CUDA: {t.get('cuda') or 'None'}"
             + (f" | ROCm: {t.get('hip')}" if t.get("hip") else "")
             + (f" | 错误: {t['error']}" if t.get("error") else ""))
    else:
        err(f"torch 未安装或不可用: {t.get('error')}")

    tv = probe.get("torchvision", {})
    ta = probe.get("torchaudio", {})
    if tv.get("installed"):
        info(f"torchvision: {tv.get('version')}")
    if ta.get("installed"):
        info(f"torchaudio: {ta.get('version')}")

    if probe.get("cuda_available") is not None:
        info(f"torch.cuda.is_available(): {probe.get('cuda_available')}")
    if probe.get("arch_supported", {}).get("sm"):
        info(f"GPU 架构: {probe['arch_supported']['sm']} | "
             f"在 torch 编译列表中: {probe['arch_supported']['in_list']}")
    if probe.get("matrix_test", {}).get("passed") is not None:
        mt = probe["matrix_test"]
        if mt.get("skipped"):
            info("矩阵乘法实测: 跳过（非 CUDA 后端）")
        else:
            info(f"矩阵乘法实测: {'通过' if mt.get('passed') else '失败'}")
    if probe.get("cudnn", {}).get("available") is not None:
        info(f"cuDNN: {probe['cudnn']['available']}"
             + (f" (v{probe['cudnn']['version']})" if probe["cudnn"].get("version") else ""))
    if probe.get("xpu_available") is not None:
        info(f"torch.xpu.is_available(): {probe.get('xpu_available')}")
    if probe.get("mps_available") is not None:
        info(f"torch.backends.mps.is_available(): {probe.get('mps_available')}")

    deps = probe.get("deps", {})
    profile_name = profile_meta.get("name", "目标应用")
    print(f"\n  {profile_name} 依赖检查:")
    if deps.get("core_missing"):
        err(f"缺少必需依赖: {', '.join(deps['core_missing'])}")
    else:
        ok("必需依赖齐全")
    if deps.get("core_outdated"):
        for o in deps["core_outdated"]:
            warn(f"{o['name']} 版本偏低 (要求 ≥{o['required']}, 当前 {o['current']})")
    if deps.get("extra_missing"):
        info(f"非必需依赖缺失: {', '.join(deps['extra_missing'])}（不影响启动）")


def render_vram(adv, vram, quiet=False):
    if quiet or not vram:
        return
    section("5. 显存适配性")
    info(f"主卡显存: {vram} GB")
    if adv["image"]:
        print("     🖼️  图片生成:")
        for line in adv["image"]:
            print(f"       • {line}")
    if adv["video"]:
        print("     🎬 视频生成:")
        for line in adv["video"]:
            print(f"       • {line}")
    if adv["llm"]:
        print("     🧠 大语言模型:")
        for line in adv["llm"]:
            print(f"       • {line}")
    if adv["tips"]:
        print("     💡 通用技巧:")
        for line in adv["tips"]:
            print(f"       • {line}")


def render_summary(recommended, probe, healthy, plan, vram, quiet=False):
    if quiet:
        return
    section("检测完成")
    print(f"\n  硬件后端: {recommended['backend']}")
    print(f"  推荐说明: {recommended.get('note', '')}")

    if healthy:
        print()
        ok("当前环境已可正常导入、矩阵实测通过、加速可用")
        print("     已安装版本与推荐版本可能不同，但只要兼容且能跑，就不需要重装。")
        if vram and vram < 16:
            print("       • 显存紧张时优先使用 --lowvram / --medvram")
            print("       • 安装 xformers 或启用 PyTorch SDPA 可降低注意力层显存")
            print("       • 量化模型需对应的加载器（GGUF / AWQ / GPTQ）")
        else:
            print("       • 保持驱动更新，定期备份环境即可")
    else:
        print()
        err("当前环境存在问题，需要处理：")
        issues = probe.get("env_issues", [])
        if issues:
            for i in issues:
                print(f"       • {i}")
        else:
            print("       • 环境未通过健康检查，但未捕获到具体问题项")

        rendered = render_solution_plan(plan)
        if rendered:
            print(rendered)


# ============================================================
# 主流程
# ============================================================

def main():
    # 打包模式下强制标记启动器身份，避免 sys.executable 被当成目标环境
    if getattr(sys, "frozen", False):
        os.environ["AI_ENV_PROBE_LAUNCHER"] = "1"

    parser = argparse.ArgumentParser(
        description=f"{TOOL_NAME} - 通用 AI 推理环境检测")
    parser.add_argument("--python", help="指定目标 Python 解释器路径")
    parser.add_argument("--base-dir", help="目标应用根目录（用于 auto 识别 profile）")
    parser.add_argument("--profile", default="auto",
                        help="检测配置: auto / comfyui / a1111 / diffusers / vllm / generic")
    parser.add_argument("--quiet", action="store_true", help="不显示版权 banner 和人类可读输出")
    parser.add_argument("--json", action="store_true", help="输出 JSON（抑制人类可读输出）")
    parser.add_argument("--list-profiles", action="store_true", help="列出所有可用 profile")
    args = parser.parse_args()

    if args.list_profiles:
        return list_profiles()

    if not args.json and not args.quiet:
        print(BANNER, end="")

    os_name = platform.system()
    base_dir = args.base_dir or os.getcwd()
    quiet = args.json or args.quiet

    # ---------- 1. 硬件探测 ----------
    hardware = detect_all(os_name)
    render_hardware(hardware, quiet)

    # ---------- 2. 定位解释器 + 版本推荐 ----------
    target_python = find_python(base_dir, args.python)
    if not target_python:
        if args.json:
            print(json.dumps({
                "tool": TOOL_NAME, "version": VERSION,
                "error": "未找到可用的 Python 解释器",
            }, ensure_ascii=False))
        else:
            section("2. 定位目标解释器")
            err("未找到可用的 Python 解释器")
            fix("请用 --python 指定目标解释器")
        return 1

    recommended = recommend(hardware, target_python)
    render_recommend(recommended, quiet)

    if not quiet:
        section("3. 定位目标解释器")
        info(f"目标解释器: {target_python}")
        if os.environ.get("AI_ENV_PROBE_LAUNCHER") == "1":
            info("启动器模式: 已启用（跳过 sys.executable 候选，避免误判）")
        if args.profile == "auto":
            detected_id = auto_detect_profile_id(base_dir)
            info(f"检测配置: {detected_id}（auto 识别结果，依据 base_dir 目录特征）")
        else:
            info(f"检测配置: {args.profile}")

    # ---------- 3. 调用 probe ----------
    probe = run_probe(target_python, args.profile, base_dir, quiet)
    if probe is None:
        if args.json:
            print(json.dumps({
                "tool": TOOL_NAME, "version": VERSION,
                "error": "probe 执行失败",
            }, ensure_ascii=False))
        return 1

    profile_meta = probe.get("profile", {})
    profile_id = profile_meta.get("id", "generic")
    render_probe(probe, profile_meta, quiet)

    # ---------- 4. 显存建议 ----------
    vram = primary_vram(hardware)
    adv = vram_advice(vram, profile_id)
    render_vram(adv, vram, quiet)

    # ---------- 5. 健康判断 + 修复方案 ----------
    healthy = is_healthy(recommended["backend"], probe)
    plan = build_solution_plan(recommended, probe, hardware, target_python, base_dir)

    # ---------- 6. 汇总 ----------
    if args.json:
        final = {
            "tool": TOOL_NAME,
            "version": VERSION,
            "copyright": COPYRIGHT,
            "hardware": {
                "os": os_name,
                "nvidia": hardware["nvidia"],
                "amd": hardware["amd"],
                "mac_gpu": hardware["mac_gpu"],
                "intel": hardware["intel"],
                "vram_gb": vram,
            },
            "recommended": recommended,
            "target_python": target_python,
            "launcher_mode": os.environ.get("AI_ENV_PROBE_LAUNCHER") == "1",
            "profile": profile_meta,
            "probe": probe,
            "healthy": healthy,
            "vram_advice": adv,
            "solution": plan,
        }
        print(json.dumps(final, ensure_ascii=False, indent=2))
        return 0

    render_summary(recommended, probe, healthy, plan, vram, quiet)

    if not args.quiet:
        print()
        print("-" * 62)
        print(f"  {COPYRIGHT}  |  {LICENSE} License  |  v{VERSION}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())