#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Env Probe - 检测器（probe）

Copyright (c) 2026 dinlian
Licensed under the MIT License. See LICENSE file for details.

由 launcher.py 以子进程方式调用，在目标应用的解释器中独立运行。
不链接、不复制、不重新分发目标应用的任何代码。
stdout 必须是纯 JSON，禁止打印任何其他内容。
"""

import os
import re
import sys
import json
import argparse
import importlib
from importlib import metadata as importlib_metadata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (
    TOOL_NAME, VERSION, COPYRIGHT, LICENSE,
    vtuple, normalize_cuda_major, auto_detect_profile_id, get_resource_dir,
)


def pkg_version(name):
    try:
        return importlib_metadata.version(name)
    except importlib_metadata.PackageNotFoundError:
        return None
    except Exception:
        return None


def load_profile(profile_name, base_dir):
    profiles_dir = os.path.join(get_resource_dir(), "profiles")
    if not os.path.isdir(profiles_dir):
        return {"name": "Generic", "id": "generic", "core": {}, "extra": {}}

    if profile_name == "auto":
        profile_name = auto_detect_profile_id(base_dir)

    path = os.path.join(profiles_dir, f"{profile_name}.json")
    if not os.path.isfile(path):
        return {"name": "Generic", "id": "generic", "core": {}, "extra": {}}

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data["id"] = profile_name
        data.setdefault("name", profile_name)
        return data
    except Exception:
        return {"name": "Generic", "id": "generic", "core": {}, "extra": {}}


def check_requirements(req_dict):
    missing = []
    outdated = []
    versions = {}
    for name, cfg in req_dict.items():
        ver = pkg_version(name)
        if ver is None:
            missing.append(name)
            versions[name] = None
        else:
            versions[name] = ver
            min_ver = cfg.get("min") if isinstance(cfg, dict) else None
            if min_ver:
                need = vtuple(min_ver)
                cur = vtuple(ver)
                if cur[:len(need)] < need:
                    outdated.append({"name": name, "current": ver, "required": min_ver})
    return {"missing": missing, "outdated": outdated, "versions": versions}


def matrix_test():
    """CUDA 环境下做矩阵乘法实测；非 CUDA 返回 passed=True（跳过）"""
    try:
        import torch
        if not torch.cuda.is_available():
            return {"passed": True, "error": None, "skipped": True}
        x = torch.randn(256, 256, device="cuda")
        _ = x @ x
        torch.cuda.synchronize()
        return {"passed": True, "error": None, "skipped": False}
    except Exception as e:
        return {"passed": False, "error": str(e), "skipped": False}


def check_arch_supported():
    try:
        import torch
        if not torch.cuda.is_available():
            return {"sm": None, "in_list": None}
        cap = torch.cuda.get_device_capability(0)
        sm = f"sm_{cap[0]}{cap[1]}"
        arch_list = torch.cuda.get_arch_list() if hasattr(torch.cuda, "get_arch_list") else []
        return {"sm": sm, "in_list": (sm in arch_list) if arch_list else None}
    except Exception:
        return {"sm": None, "in_list": None}


TORCH_MATRIX = {
    (2, 14): ("3.10", "3.14", "0.29", "2.11"),
    (2, 13): ("3.10", "3.14", "0.28", "2.11"),
    (2, 12): ("3.10", "3.13", "0.27", "2.11"),
    (2, 11): ("3.10", "3.13", "0.26", "2.11"),
    (2, 10): ("3.9",  "3.13", "0.25", "2.10"),
    (2, 9):  ("3.9",  "3.13", "0.24", "2.9"),
    (2, 8):  ("3.9",  "3.13", "0.23", "2.8"),
    (2, 7):  ("3.9",  "3.13", "0.22", "2.7"),
    (2, 6):  ("3.8",  "3.13", "0.21", "2.6"),
    (2, 5):  ("3.8",  "3.12", "0.20", "2.5"),
    (2, 4):  ("3.8",  "3.12", "0.19", "2.4"),
    (2, 3):  ("3.8",  "3.12", "0.18", "2.3"),
    (2, 2):  ("3.8",  "3.11", "0.17", "2.2"),
    (2, 1):  ("3.8",  "3.11", "0.16", "2.1"),
    (2, 0):  ("3.8",  "3.11", "0.15", "2.0"),
}


def main():
    parser = argparse.ArgumentParser(description=f"{TOOL_NAME} - probe")
    parser.add_argument("--profile", default="auto")
    parser.add_argument("--base-dir", default=os.getcwd())
    args = parser.parse_args()

    profile = load_profile(args.profile, args.base_dir)

    result = {
        "meta": {
            "tool": TOOL_NAME,
            "version": VERSION,
            "copyright": COPYRIGHT,
            "license": LICENSE,
        },
        "profile": {
            "id": profile.get("id", "generic"),
            "name": profile.get("name", "Generic"),
        },
        "python": {
            "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "major": sys.version_info.major,
            "minor": sys.version_info.minor,
            "executable": sys.executable,
        },
        "torch": {"installed": False},
        "torchvision": {"installed": False},
        "torchaudio": {"installed": False},
        "matrix_test": {"passed": None, "error": None, "skipped": False},
        "arch_supported": {"sm": None, "in_list": None},
        "cudnn": {"available": None, "version": None},
        "cuda_available": None,
        "xpu_available": None,
        "mps_available": None,
        "deps": {"core_missing": [], "extra_missing": [],
                 "core_outdated": [], "extra_outdated": [], "versions": {}},
        "env_issues": [],
    }

    issues = set()

    try:
        import torch
        result["torch"] = {
            "installed": True,
            "version": torch.__version__,
            "cuda": torch.version.cuda,
            "hip": getattr(torch.version, "hip", None),
            "cpython": getattr(torch.version, "cpython", None),
            "error": None,
        }
        try:
            result["cuda_available"] = torch.cuda.is_available()
            if result["cuda_available"]:
                result["torch"]["device_name"] = torch.cuda.get_device_name(0)
        except Exception:
            result["cuda_available"] = False
        try:
            result["xpu_available"] = hasattr(torch, "xpu") and torch.xpu.is_available()
        except Exception:
            result["xpu_available"] = False
        try:
            result["mps_available"] = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
        except Exception:
            result["mps_available"] = False
        try:
            if hasattr(torch.backends, "cudnn"):
                result["cudnn"]["available"] = torch.backends.cudnn.is_available()
                if result["cudnn"]["available"]:
                    result["cudnn"]["version"] = torch.backends.cudnn.version()
        except Exception:
            pass
    except ModuleNotFoundError as e:
        if e.name == "torch":
            result["torch"]["error"] = "torch 未安装"
            issues.add("torch 未安装")
        else:
            result["torch"]["installed"] = True
            result["torch"]["error"] = f"缺少依赖模块: {e.name}"
            issues.add(f"torch 缺依赖: {e.name}")
    except OSError as e:
        result["torch"]["error"] = f"动态库加载失败: {e}"
        issues.add("torch 动态库加载失败（通常是 CUDA 运行时库路径问题）")
    except Exception as e:
        result["torch"]["error"] = str(e)
        issues.add(f"torch 导入失败: {e}")

    for pkg in ["torchvision", "torchaudio"]:
        try:
            mod = importlib.import_module(pkg)
            ver = getattr(mod, "__version__", "unknown")
            pkg_cuda = getattr(getattr(mod, "version", None), "cuda", None)
            result[pkg] = {"installed": True, "version": ver, "cuda": pkg_cuda, "error": None}
        except ModuleNotFoundError as e:
            if e.name == pkg:
                result[pkg] = {"installed": False, "error": f"{pkg} 未安装"}
            else:
                result[pkg] = {"installed": True, "error": f"缺少依赖模块: {e.name}"}
                issues.add(f"{pkg} 缺依赖: {e.name}")
        except Exception as e:
            result[pkg] = {"installed": False, "error": str(e)}
            issues.add(f"{pkg} 导入失败: {e}")

    if result["torch"].get("installed"):
        torch_ver_str = result["torch"].get("version", "")
        torch_base = vtuple(torch_ver_str.split("+")[0])[:2]
        if torch_base in TORCH_MATRIX:
            _, _, exp_tv, exp_ta = TORCH_MATRIX[torch_base]
            if result["torchvision"].get("installed"):
                tv_ver = result["torchvision"].get("version", "")
                if vtuple(tv_ver.split("+")[0])[:2] < vtuple(exp_tv):
                    issues.add(f"torchvision 版本过低 (期望 ≥{exp_tv}, 当前 {tv_ver})")
            if result["torchaudio"].get("installed"):
                ta_ver = result["torchaudio"].get("version", "")
                if vtuple(ta_ver.split("+")[0])[:2] < vtuple(exp_ta):
                    issues.add(f"torchaudio 版本过低 (期望 ≥{exp_ta}, 当前 {ta_ver})")

    torch_cuda = result["torch"].get("cuda")
    if torch_cuda:
        t_major = normalize_cuda_major(torch_cuda)
        for pkg in ["torchvision", "torchaudio"]:
            pkg_cuda = result[pkg].get("cuda")
            if pkg_cuda:
                p_major = normalize_cuda_major(pkg_cuda)
                if p_major != t_major:
                    issues.add(f"{pkg} CUDA 主版本不一致 (torch={torch_cuda}, {pkg}={pkg_cuda})")

    torch_py = result["torch"].get("cpython")
    if torch_py:
        cur_short = f"{sys.version_info.major}{sys.version_info.minor}"
        torch_short = re.sub(r"[^\d]", "", str(torch_py))[:2]
        if cur_short != torch_short:
            issues.add(
                f"Python 解释器与 torch 编译版本不一致 (当前 cp{cur_short}, torch cp{torch_short})")

    if result["torch"].get("installed") and result.get("cuda_available"):
        result["matrix_test"] = matrix_test()
        if result["matrix_test"].get("passed") is False:
            issues.add(f"矩阵乘法实测失败: {result['matrix_test']['error']}")
        result["arch_supported"] = check_arch_supported()
        if result["arch_supported"].get("in_list") is False:
            issues.add(
                f"GPU 架构 {result['arch_supported']['sm']} 不在当前 torch 编译列表中")

    if result["torch"].get("installed"):
        core = check_requirements(profile.get("core", {}))
        extra = check_requirements(profile.get("extra", {}))
        result["deps"]["core_missing"] = core["missing"]
        result["deps"]["extra_missing"] = extra["missing"]
        result["deps"]["core_outdated"] = core["outdated"]
        result["deps"]["extra_outdated"] = extra["outdated"]
        result["deps"]["versions"] = {**core["versions"], **extra["versions"]}
        if core["missing"]:
            issues.add(f"缺少必需依赖: {', '.join(core['missing'])}")
        for item in core["outdated"]:
            issues.add(
                f"{item['name']} 版本偏低 (要求 ≥{item['required']}, 当前 {item['current']})")

    result["env_issues"] = sorted(issues)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()