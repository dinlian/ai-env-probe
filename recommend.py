#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Env Probe - 版本推荐模块

Copyright (c) 2026 dinlian
Licensed under the MIT License. See LICENSE file for details.

本模块根据硬件信息推荐 PyTorch 安装方案，并生成显存适配建议。
"""

from common import vtuple, normalize_cuda_major, cuda_tag_to_major


NVIDIA_MODELS = [
    (["rtx 5090", "rtx 5080", "rtx 5070", "rtx 5060", "rtx 5050", "b100", "b200"], "Blackwell"),
    (["rtx 4090", "rtx 4080", "rtx 4070", "rtx 4060", "l40", "l4", "rtx 6000 ada"], "Ada"),
    (["rtx 3090", "rtx 3080", "rtx 3070", "rtx 3060", "rtx 3050",
      "a100", "a800", "a40", "a30", "a10", "rtx a"], "Ampere"),
    (["rtx 2080", "rtx 2070", "rtx 2060", "t4"], "Turing"),
    (["gtx 1660", "gtx 1650"], "Turing-lite"),
    (["h100", "h200", "h800", "h20"], "Hopper"),
    (["v100", "v100s"], "Volta"),
    (["gtx 1060 ti"], "Pascal"),
    (["gtx 1080", "gtx 1070", "gtx 1060", "p100", "p40"], "Pascal"),
]

AMD_MODELS = [
    (["rx 9070", "rx 9060"], "RDNA4", "ROCm 7.2+"),
    (["rx 7900", "rx 7800", "rx 7700", "rx 7600"], "RDNA3", "ROCm 7.1+"),
    (["rx 6950", "rx 6900", "rx 6800"], "RDNA2", "ROCm 6.x/7.x（HSA_OVERRIDE=10.3.0）"),
    (["rx 6750", "rx 6700"], "RDNA2", "ROCm 6.x/7.x（HSA_OVERRIDE=10.3.0，失败可试 10.3.1）"),
    (["rx 6650", "rx 6600", "rx 6500", "rx 6400"], "RDNA2", "ROCm 6.x/7.x（HSA_OVERRIDE=10.3.2）"),
    (["rx 5700", "rx 5600", "rx 5500"], "RDNA1", "ROCm 支持极差，不推荐"),
    (["radeon vii", "rx vega", "vega 56", "vega 64"], "Vega", "ROCm 支持差，不推荐"),
]


def _arch_preference(arch, drv_major):
    if arch == "Blackwell":
        if drv_major >= 580:
            return "cu130", "驱动 ≥580，优先 cu130（FP4/FP8 硬件加速）", "ok"
        if drv_major >= 570:
            return "cu128", "RTX 50 的 sm_120 从 CUDA 12.8 开始支持", "warn"
        return None, "RTX 50 (sm_120) 需要 cu128+，驱动低于 570 无法运行", "err"

    if arch in ("Pascal", "Volta"):
        if drv_major >= 560:
            return "cu124", "Pascal/Volta 最高安全线为 cu124；cu126+ 已移除 sm_61/sm_70 内核", "warn"
        if drv_major >= 525:
            return "cu121", "驱动较旧，使用 cu121（仍包含 Pascal/Volta 内核）", "warn"
        return None, "驱动低于 525，Pascal/Volta 在 CUDA 12.x 下需要 ≥525", "err"

    if arch == "Hopper":
        if drv_major >= 580:
            return "cu130", "驱动 ≥580，可用 cu130", "ok"
        if drv_major >= 560:
            return "cu126", "驱动不满足 cu130（需 ≥580），使用 cu126", "warn"
        return None, "驱动低于 560，建议升级后再安装", "err"

    if drv_major >= 580:
        return "cu130", "驱动 ≥580，可选用 cu130", "ok"
    if drv_major >= 560:
        return "cu126", "驱动不满足 cu130（需 ≥580），使用 cu126", "warn"
    return None, "驱动低于 560，建议升级到 ≥560 再安装 cu126", "err"


def recommend_cuda(arch, drv_major, smi_cuda_major=None):
    """返回 (cuda_tag, note, severity)；考虑驱动 smi_cuda 上限"""
    pref = _arch_preference(arch, drv_major)
    if pref[0] is None:
        return pref

    tag, note, severity = pref

    if smi_cuda_major is not None:
        try:
            smi_major = int(smi_cuda_major)
            tag_major = cuda_tag_to_major(tag)
            if tag_major is not None and tag_major > smi_major:
                if arch == "Blackwell":
                    return None, f"RTX 50 需要 CUDA 12.8+，驱动只支持 {smi_major}.x", "err"
                if arch in ("Pascal", "Volta") and smi_major < 12:
                    return None, f"Pascal/Volta 至少需要 CUDA 12.x，驱动只支持 {smi_major}.x", "err"
                if smi_major == 12:
                    return "cu126", f"{note}；但驱动最高支持 CUDA 12.x，降级到 cu126", "warn"
                if smi_major == 11:
                    return "cu118", f"{note}；但驱动最高支持 CUDA 11.x，降级到 cu118", "warn"
                return None, f"驱动最高只支持 CUDA {smi_major}.x，无法运行 {tag}", "err"
        except (ValueError, TypeError):
            pass

    return tag, note, severity


def build_pip_cmd(target_python, cuda_tag):
    """生成带目标解释器路径的 pip 命令"""
    if target_python and " " in target_python:
        py = f'"{target_python}"'
    else:
        py = target_python or "python"
    return (f"{py} -m pip install torch torchvision torchaudio "
            f"--index-url https://download.pytorch.org/whl/{cuda_tag}")


def recommend(hardware, target_python=None):
    """根据硬件推荐后端和安装方案"""
    os_name = hardware["os"]

    if hardware["nvidia"]:
        g = pick_primary(hardware["nvidia"])
        name_lower = g["name"].lower()
        arch = "Unknown"
        for kws, a in NVIDIA_MODELS:
            if any(k in name_lower for k in kws):
                arch = a
                break
        drv = g.get("driver") or "0"
        drv_major = vtuple(drv)[0] if vtuple(drv) else 0
        smi_cuda_major = normalize_cuda_major(g.get("smi_cuda"))

        cuda_tag, note, severity = recommend_cuda(arch, drv_major, smi_cuda_major)
        if cuda_tag is None:
            return {"backend": "NVIDIA CUDA", "arch": arch, "pip_cmd": None,
                    "note": note, "severity": "err"}
        return {"backend": "NVIDIA CUDA", "arch": arch,
                "pip_cmd": build_pip_cmd(target_python, cuda_tag),
                "cuda_tag": cuda_tag, "note": note, "severity": severity}

    if os_name == "Darwin" and hardware["mac_gpu"]:
        mac = hardware["mac_gpu"]
        py = target_python or "python"
        if mac["type"] == "apple_silicon":
            return {"backend": "Apple MPS", "arch": mac["name"],
                    "pip_cmd": f"{py} -m pip install torch torchvision torchaudio",
                    "note": "Apple Silicon，MPS 自动启用", "severity": "ok"}
        if mac["type"] == "amd":
            return {"backend": "Apple MPS (实验性)", "arch": mac["name"],
                    "pip_cmd": f"{py} -m pip install torch torchvision torchaudio",
                    "note": "Intel Mac + AMD 独显，MPS 支持为实验性，黑苹果风险更高",
                    "severity": "warn"}
        return {"backend": "CPU", "arch": "macOS 无可用 GPU",
                "pip_cmd": f"{py} -m pip install torch torchvision torchaudio "
                           "--index-url https://download.pytorch.org/whl/cpu",
                "note": "MPS 不可用，以 CPU 模式运行", "severity": "warn"}

    if hardware["amd"]:
        g = pick_primary(hardware["amd"])
        name_lower = g["name"].lower()
        arch, hint = "Unknown", "按官方最新稳定版"
        for kws, a, h in AMD_MODELS:
            if any(k in name_lower for k in kws):
                arch, hint = a, h
                break
        if arch in ("RDNA1", "Vega"):
            return {"backend": "AMD (unsupported)", "arch": arch,
                    "pip_cmd": None, "note": f"{arch} ROCm 支持极差", "severity": "err"}
        if os_name == "Windows":
            return {"backend": "AMD Windows (limited)", "arch": arch,
                    "pip_cmd": None,
                    "note": "Windows AMD 支持有限，建议 Linux + ROCm", "severity": "warn"}
        py = target_python or "python"
        return {"backend": "AMD ROCm", "arch": arch,
                "pip_cmd": f"{py} -m pip install torch torchvision torchaudio "
                           "--index-url https://download.pytorch.org/whl/rocm7.2",
                "note": hint, "severity": "ok"}

    if hardware["intel"]["type"] == "arc":
        py = target_python or "python"
        return {"backend": "Intel XPU", "arch": "Arc",
                "pip_cmd": f"{py} -m pip install torch torchvision torchaudio "
                           "--index-url https://download.pytorch.org/whl/xpu",
                "note": "需先安装 Intel GPU 驱动和 oneAPI Base Toolkit", "severity": "ok"}
    if hardware["intel"]["type"] == "igpu":
        return {"backend": "Intel iGPU (XPU 可选)", "arch": "Iris Xe/UHD",
                "pip_cmd": None,
                "note": "建议优先 CPU；XPU 实际加速有限，可能与部分工作流不兼容",
                "severity": "warn"}

    py = target_python or "python"
    return {"backend": "CPU", "arch": "N/A",
            "pip_cmd": f"{py} -m pip install torch torchvision torchaudio "
                       "--index-url https://download.pytorch.org/whl/cpu",
            "note": "可运行但速度极慢", "severity": "warn"}


def pick_primary(gpus):
    if not gpus:
        return None
    return sorted(gpus, key=lambda g: g.get("vram_gb") or 0, reverse=True)[0]


# ---------- 显存建议 ----------

def _add_image_advice(vram, res):
    if vram < 6:
        res["image"].append("SD1.5 / Pony (FP16) 低分辨率可行；SDXL 基本不可用")
    elif vram < 8:
        res["image"].append("SD1.5 舒适；SDXL 需低显存优化；FLUX 需 GGUF Q4")
    elif vram < 12:
        res["image"].append("SDXL 可行；FLUX.1-dev 需 FP8 或 GGUF Q4-Q5；SD3.5 Medium 可行")
    elif vram < 16:
        res["image"].append("SDXL 舒适；FLUX.1-dev FP8 / GGUF Q5-Q8 可行；SD3.5 Medium 舒适")
        res["image"].append("SD3.5 Large FP8 可行；FLUX.1-dev 原版 FP16 仍不够（约 22GB）")
    elif vram < 24:
        res["image"].append("FLUX.1-dev FP16 接近可行；SD3.5 Large、Flux.2 量化可行")
    else:
        res["image"].append("FLUX.1-dev FP16、SD3.5 Large、Flux.2、Qwen Image 均可流畅运行")


def _add_video_advice(vram, res):
    if vram < 8:
        res["video"].append("LTX-Video 2B (FP8/GGUF) 主要可行；Wan 1.3B 量化可尝试")
    elif vram < 12:
        res["video"].append("AnimateDiff (SD1.5)、SVD、CogVideoX-2B INT8 可行")
        res["video"].append("Wan 1.3B、LTX-Video 2B FP8 舒适")
    elif vram < 16:
        res["video"].append("CogVideoX-2B/5B INT8、LTX-2 / LTX-2.3 GGUF Q4-Q8 可行")
        res["video"].append("AnimateDiff (SD1.5)、SVD、Wan 1.3B 舒适")
        res["video"].append("Wan 14B 原版、HunyuanVideo 原版 ❌，需 GGUF Q4/Q5 才可尝试")
        res["video"].append("HunyuanVideo 1.5 (8.3B) FP8 约 14GB，12GB 需更激进 offload")
    elif vram < 24:
        res["video"].append("HunyuanVideo 1.5 FP8、Wan 2.2 5B、LTX-2 蒸馏 FP8 可行")
        res["video"].append("Wan 14B Q5_K_S 进入平衡区间；AnimateDiff SDXL 舒适")
    else:
        res["video"].append("Wan 14B FP8/Q8、HunyuanVideo 原版 GGUF、LTX-2 蒸馏版均可较舒适运行")


def _add_llm_advice(vram, res):
    if vram < 8:
        res["llm"].append("7B 需 AWQ/GPTQ 4bit 量化（约 4-5GB）；FP16 不可行")
        res["llm"].append("13B 及以上 FP16 均不可行")
    elif vram < 12:
        res["llm"].append("7B FP16 (约 14GB) 不可行；7B AWQ 4bit 可行")
        res["llm"].append("13B AWQ 4bit 约 8GB，可行")
    elif vram < 16:
        res["llm"].append("7B FP16 勉强（14GB，接近上限）；7B AWQ 舒适")
        res["llm"].append("13B AWQ 可行；13B FP16 不可行")
    elif vram < 24:
        res["llm"].append("7B FP16、13B AWQ、34B AWQ 可行")
        res["llm"].append("13B FP16 接近（约 26GB，需 offload）")
    elif vram < 48:
        res["llm"].append("13B FP16、34B AWQ、70B AWQ 部分可行")
        res["llm"].append("70B FP16 需多卡")
    else:
        res["llm"].append("70B FP16、70B AWQ、多数量化模型均可流畅运行")


def vram_advice(vram, profile_id="generic"):
    res = {"image": [], "video": [], "llm": [], "tips": []}
    if vram is None:
        return res

    if profile_id == "comfyui":
        _add_image_advice(vram, res)
        _add_video_advice(vram, res)
    elif profile_id in ("a1111", "diffusers"):
        _add_image_advice(vram, res)
    elif profile_id == "vllm":
        _add_llm_advice(vram, res)
    else:
        _add_image_advice(vram, res)

    if vram < 16:
        res["tips"].append("启用 --lowvram / --medvram（如支持）可显著降低峰值显存")
        res["tips"].append("安装 xformers 或启用 PyTorch SDPA 可降低注意力层显存")
        res["tips"].append("量化模型（GGUF/AWQ/GPTQ）需对应的加载器")
    return res