#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Env Probe - 解决方案生成器

Copyright (c) 2026 dinlian
Licensed under the MIT License. See LICENSE file for details.

根据检测结果生成分阶段、可执行、带验证和回滚的修复方案。
"""


def _py(target_python):
    if not target_python:
        return "python"
    if " " in target_python:
        return f'"{target_python}"'
    return target_python


def _pip(target_python):
    return f"{_py(target_python)} -m pip"


def _torch_url(backend, cuda_tag):
    if backend.startswith("NVIDIA") and cuda_tag:
        return f"https://download.pytorch.org/whl/{cuda_tag}"
    if backend.startswith("AMD"):
        return "https://download.pytorch.org/whl/rocm7.2"
    if backend == "Intel XPU":
        return "https://download.pytorch.org/whl/xpu"
    if backend.startswith("Apple"):
        return None  # PyPI 默认
    return "https://download.pytorch.org/whl/cpu"


def _torch_install_cmd(pip, backend, cuda_tag):
    url = _torch_url(backend, cuda_tag)
    if url:
        return f"{pip} install torch torchvision torchaudio --index-url {url}"
    return f"{pip} install torch torchvision torchaudio"


def _torch_download_cmd(pip, backend, cuda_tag):
    url = _torch_url(backend, cuda_tag)
    if url:
        return (f"{pip} download torch torchvision torchaudio "
                f"--index-url {url} -d ./pytorch_wheels")
    return f"{pip} download torch torchvision torchaudio -d ./pytorch_wheels"


def _detect_issues(recommended, probe, hardware):
    """把检测结果归一化为问题列表"""
    issues = []
    backend = recommended.get("backend", "CPU")
    torch = probe.get("torch", {})
    env_issues = probe.get("env_issues", [])
    deps = probe.get("deps", {})
    arch = probe.get("arch_supported", {})
    matrix = probe.get("matrix_test", {})

    if not torch.get("installed"):
        issues.append({"type": "torch_missing", "severity": "critical"})
    elif torch.get("error"):
        issues.append({"type": "torch_broken", "severity": "critical",
                       "detail": torch["error"]})

    if backend == "NVIDIA CUDA" and probe.get("cuda_available") is False:
        issues.append({"type": "cuda_unavailable", "severity": "critical"})

    if arch.get("in_list") is False:
        issues.append({"type": "arch_unsupported", "severity": "high",
                       "sm": arch.get("sm")})

    if matrix.get("passed") is False:
        issues.append({"type": "matrix_failed", "severity": "high",
                       "error": matrix.get("error")})

    for i in env_issues:
        if "Python 解释器与 torch 编译版本不一致" in i:
            issues.append({"type": "python_mismatch", "severity": "high",
                           "detail": i})
            break

    if deps.get("core_missing"):
        issues.append({"type": "deps_missing", "severity": "medium",
                       "missing": deps["core_missing"]})

    if deps.get("core_outdated"):
        issues.append({"type": "deps_outdated", "severity": "low",
                       "outdated": deps["core_outdated"]})

    return issues


def _max_severity(issues):
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    if not issues:
        return "none"
    return max(issues, key=lambda x: order.get(x["severity"], 0))["severity"]


def _step_snapshot(pip):
    return {
        "title": "记录当前环境快照",
        "purpose": "修复失败时能回滚到修复前的状态",
        "commands": [f"{pip} freeze > before_fix.txt"],
        "verify": "确认 before_fix.txt 已生成",
        "fallback": None,
    }


def _step_driver(hardware, pip, recommended):
    gpus = hardware.get("nvidia") or []
    drv = gpus[0].get("driver", "未知") if gpus else "未知"
    smi = gpus[0].get("smi_cuda", "未知") if gpus else "未知"
    cuda_tag = recommended.get("cuda_tag")
    required_major = cuda_tag[2:4] if cuda_tag and len(cuda_tag) >= 4 else "推荐值"

    fallback = None
    if cuda_tag and cuda_tag not in ("cu126", "cu118"):
        fallback = {
            "reason": "如果无法升级驱动（公司电脑、旧系统、稳定版驱动），降级到 cu126",
            "commands": [
                f"{pip} uninstall torch torchvision torchaudio -y",
                f"{pip} install torch torchvision torchaudio "
                f"--index-url https://download.pytorch.org/whl/cu126",
            ],
        }

    return {
        "title": "升级 NVIDIA 驱动",
        "purpose": f"当前驱动 {drv}（smi CUDA {smi}）不满足 {cuda_tag or '推荐版本'} 的要求",
        "commands": [
            "# 1. 访问 NVIDIA 驱动下载页",
            "#    https://www.nvidia.com/Download/index.aspx",
            "# 2. 选择对应显卡型号，下载 580.x 或更新版本",
            "# 3. 安装后重启系统",
            "nvidia-smi",
        ],
        "verify": f"nvidia-smi 输出中 CUDA Version 应 ≥ {required_major}.0",
        "fallback": fallback,
    }


def _step_install_torch(pip, target_python, recommended):
    backend = recommended.get("backend", "")
    cuda_tag = recommended.get("cuda_tag")
    online = _torch_install_cmd(pip, backend, cuda_tag)
    download = _torch_download_cmd(pip, backend, cuda_tag)
    offline = f"{pip} install --no-index --find-links=./pytorch_wheels torch torchvision torchaudio"

    return {
        "title": "安装 PyTorch",
        "purpose": f"为 {backend} 后端安装匹配的 torch",
        "commands": [
            "# 在线安装（网络正常时）",
            online,
            "",
            "# 离线安装（网络受限时）",
            "# 1. 在可联网机器上下载 wheel",
            download,
            "# 2. 把 pytorch_wheels/ 拷贝到目标机器",
            "# 3. 在目标机器上安装",
            offline,
        ],
        "verify": f'{_py(target_python)} -c "import torch; print(torch.__version__, torch.cuda.is_available())"',
        "fallback": None,
    }


def _step_reinstall_torch(pip, target_python, recommended):
    backend = recommended.get("backend", "")
    cuda_tag = recommended.get("cuda_tag")
    install = _torch_install_cmd(pip, backend, cuda_tag)

    return {
        "title": "重装 PyTorch（架构不匹配或实测失败）",
        "purpose": "当前 torch 的编译架构与 GPU 不匹配，或矩阵实测失败",
        "commands": [
            "# 1. 卸载当前版本",
            f"{pip} uninstall torch torchvision torchaudio -y",
            "",
            "# 2. 清理 pip 缓存（可选）",
            f"{pip} cache purge",
            "",
            "# 3. 安装推荐版本",
            install,
        ],
        "verify": f'{_py(target_python)} -c "import torch; print(torch.cuda.get_arch_list())"',
        "fallback": None,
    }


def _step_python_mismatch(pip, target_python, recommended, base_dir):
    backend = recommended.get("backend", "")
    cuda_tag = recommended.get("cuda_tag")
    reinstall = _torch_install_cmd(pip, backend, cuda_tag)

    return {
        "title": "处理 Python 解释器与 torch 编译版本不一致",
        "purpose": "当前解释器版本与 torch wheel 的 cpXXX 标签不匹配",
        "commands": [
            "# 方案 A（推荐）: 换用与 torch 匹配的 Python 解释器",
            "#   1. 查看已安装 torch wheel 的 cpXXX 标签",
            "#   2. 用匹配版本的 Python 重新运行本工具",
            f"#      <匹配的python> launcher.py --base-dir {base_dir or '.'}",
            "",
            "# 方案 B: 用当前解释器重装匹配的 torch",
            f"{pip} uninstall torch torchvision torchaudio -y",
            reinstall,
        ],
        "verify": f'{_py(target_python)} -c "import sys, torch; print(sys.version_info[:2], torch.__version__)"',
        "fallback": None,
    }


def _step_fix_deps(pip, target_python, base_dir, missing):
    sample = missing[:3]
    verify_cmd = f'{_py(target_python)} -c "import ' + ", ".join(sample) + '"'

    return {
        "title": f"补齐 {len(missing)} 个必需依赖",
        "purpose": "缺失: " + ", ".join(missing[:5]) + (" ..." if len(missing) > 5 else ""),
        "commands": [
            "# 方案 A（推荐）: 安装目标应用的完整依赖",
            f"cd {base_dir or '.'}",
            f"{pip} install -r requirements.txt",
            "",
            "# 方案 B: 逐个安装缺失包（方案 A 失败时）",
            f"{pip} install {' '.join(missing)}",
        ],
        "verify": verify_cmd,
        "fallback": None,
    }


def _step_upgrade_deps(pip, outdated):
    specs = [f"{o['name']}>={o['required']}" for o in outdated]
    names = "|".join(o["name"] for o in outdated)

    return {
        "title": f"升级 {len(outdated)} 个版本过低的依赖",
        "purpose": "部分依赖版本低于 profile 要求",
        "commands": [
            f"{pip} install --upgrade {' '.join(specs)}",
        ],
        "verify": f'{pip} list | grep -E "{names}"',
        "fallback": None,
    }


def _step_final_verify(target_python, profile_id, base_dir):
    return {
        "title": "最终验证",
        "purpose": "确认所有问题已解决",
        "commands": [
            f"{_py(target_python)} launcher.py --profile {profile_id} --base-dir {base_dir or '.'}",
        ],
        "verify": "所有检查项显示 ✅，汇总处无“需要处理”",
        "fallback": None,
    }


def build_solution_plan(recommended, probe, hardware, target_python, base_dir):
    """生成修复计划"""
    issues = _detect_issues(recommended, probe, hardware)
    severity = _max_severity(issues)

    if severity == "none":
        return {"severity": "none", "steps": [], "rollback": []}

    pip = _pip(target_python)
    profile_id = probe.get("profile", {}).get("id", "generic")
    steps = []
    rollback = []

    # 阶段 0: 快照（仅在需要修改环境时）
    if severity in ("critical", "high"):
        steps.append(_step_snapshot(pip))
        rollback.append({
            "reason": "回滚到修复前快照",
            "commands": [f"{pip} install -r before_fix.txt"],
        })

    # 阶段 1: 驱动（最高优先级，因为影响所有后续判断）
    if any(i["type"] == "cuda_unavailable" for i in issues):
        steps.append(_step_driver(hardware, pip, recommended))

    # 阶段 2: torch 安装/重装
    if any(i["type"] in ("torch_missing", "torch_broken") for i in issues):
        steps.append(_step_install_torch(pip, target_python, recommended))
    elif any(i["type"] in ("arch_unsupported", "matrix_failed") for i in issues):
        steps.append(_step_reinstall_torch(pip, target_python, recommended))

    # 阶段 3: Python 版本
    if any(i["type"] == "python_mismatch" for i in issues):
        steps.append(_step_python_mismatch(pip, target_python, recommended, base_dir))

    # 阶段 4: 依赖缺失
    if any(i["type"] == "deps_missing" for i in issues):
        missing = next(i["missing"] for i in issues if i["type"] == "deps_missing")
        steps.append(_step_fix_deps(pip, target_python, base_dir, missing))

    # 阶段 5: 依赖版本
    if any(i["type"] == "deps_outdated" for i in issues):
        outdated = next(i["outdated"] for i in issues if i["type"] == "deps_outdated")
        steps.append(_step_upgrade_deps(pip, outdated))

    # 阶段 6: 最终验证
    steps.append(_step_final_verify(target_python, profile_id, base_dir))

    return {"severity": severity, "steps": steps, "rollback": rollback}


def render_solution_plan(plan):
    """渲染为人类可读文本；无问题时返回空字符串"""
    if plan["severity"] == "none":
        return ""

    sev_label = {
        "critical": "🔴 严重（GPU 加速不可用，必须先修复）",
        "high": "🟠 高（环境可导入但无法正常运行）",
        "medium": "🟡 中（核心功能可用，部分依赖缺失）",
        "low": "🟢 低（可用，但依赖版本低于推荐值）",
    }.get(plan["severity"], plan["severity"])

    lines = []
    lines.append("")
    lines.append("=" * 62)
    lines.append("  修复方案")
    lines.append("=" * 62)
    lines.append("")
    lines.append(f"  严重度: {sev_label}")
    lines.append("")
    lines.append("  按顺序执行以下阶段，每个阶段验证通过后再进入下一阶段。")

    total = len(plan["steps"])
    for i, step in enumerate(plan["steps"], 1):
        lines.append("")
        lines.append(f"  【阶段 {i}/{total}】{step['title']}")
        lines.append(f"  目的: {step['purpose']}")
        lines.append("  执行:")
        for cmd in step["commands"]:
            if cmd.startswith("#") or cmd == "":
                lines.append(f"    {cmd}")
            else:
                lines.append(f"    {cmd}")
        if step.get("verify"):
            lines.append(f"  验证: {step['verify']}")
        if step.get("fallback"):
            lines.append(f"  💡 备选: {step['fallback']['reason']}")
            for cmd in step["fallback"]["commands"]:
                lines.append(f"    {cmd}")

    if plan["rollback"]:
        lines.append("")
        lines.append("  ⚠️ 回滚方案（修复后应用无法启动时执行）:")
        for r in plan["rollback"]:
            lines.append(f"    • {r['reason']}")
            for cmd in r["commands"]:
                lines.append(f"      {cmd}")

    lines.append("")
    return "\n".join(lines)