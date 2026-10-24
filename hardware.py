#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Env Probe - 硬件探测模块

Copyright (c) 2026 dinlian
Licensed under the MIT License. See LICENSE file for details.

本模块只做硬件探测，不做版本推荐或环境检测。
所有函数返回纯数据结构，不产生副作用（除了一次性 subprocess 调用）。
"""

import re
import json
import subprocess


def _run(cmd, timeout=15):
    try:
        return subprocess.check_output(
            cmd, stderr=subprocess.DEVNULL, text=True, timeout=timeout
        ).strip()
    except Exception:
        return None


def detect_nvidia():
    """返回 NVIDIA GPU 列表；优先 pynvml，回退 nvidia-smi"""
    gpus = []
    try:
        import pynvml
        pynvml.nvmlInit()
        drv = pynvml.nvmlSystemGetDriverVersion()
        if isinstance(drv, bytes):
            drv = drv.decode()
        for i in range(pynvml.nvmlDeviceGetCount()):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(h)
            if isinstance(name, bytes):
                name = name.decode()
            mem = pynvml.nvmlDeviceGetMemoryInfo(h).total / (1024 ** 3)
            gpus.append({"name": name, "vram_gb": round(mem, 1),
                         "driver": drv, "smi_cuda": None})
        pynvml.nvmlShutdown()
    except Exception:
        pass

    if not gpus:
        q = _run(["nvidia-smi",
                  "--query-gpu=name,memory.total,driver_version",
                  "--format=csv,noheader,nounits"])
        if q:
            for line in q.splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    try:
                        vram = round(float(parts[1]) / 1024, 1)
                    except ValueError:
                        vram = None
                    gpus.append({"name": parts[0], "vram_gb": vram,
                                 "driver": parts[2], "smi_cuda": None})
            full = _run(["nvidia-smi"])
            if full:
                m = re.search(r"CUDA Version:\s*(\d+\.\d+)", full)
                for g in gpus:
                    g["smi_cuda"] = m.group(1) if m else None
    return gpus


def detect_amd(os_name):
    """返回 AMD GPU 列表"""
    gpus = []
    rocm = _run(["rocm-smi", "--showproductname"])
    if rocm:
        for line in rocm.splitlines():
            if "GPU" in line and ("RX" in line or "Radeon" in line):
                m = re.search(r"(RX\s*\d{4}\s*\w*)", line)
                if m:
                    gpus.append({"name": m.group(1), "driver": "ROCm", "vram_gb": None})
    if not gpus and os_name == "Linux":
        lspci = _run(["lspci"])
        if lspci:
            for line in lspci.splitlines():
                if "VGA" in line and "AMD" in line:
                    m = re.search(r"(Radeon\s+RX\s*\d{4}\s*\w*)", line)
                    if m:
                        gpus.append({"name": m.group(1), "driver": None, "vram_gb": None})
    if gpus:
        mem = _run(["rocm-smi", "--showmeminfo", "vram"])
        if mem:
            m = re.search(r"VRAM Total Memory \(B\):\s*(\d+)", mem)
            if m:
                gpus[0]["vram_gb"] = round(int(m.group(1)) / (1024 ** 3), 1)
    return gpus


def detect_macos_gpu():
    """返回 macOS GPU 信息；type 为 apple_silicon / amd / intel_igpu / cpu"""
    mac = {"type": "cpu", "name": "无可用 GPU", "vram_gb": None}
    out = _run(["system_profiler", "SPDisplaysDataType", "-json"])
    if out:
        try:
            data = json.loads(out)
            for item in data.get("SPDisplaysDataType", []):
                chip = (item.get("sppci_model") or item.get("_name")
                        or item.get("Chipset Model") or "")
                c = chip.strip().lower()
                vram = item.get("spdisplays_vram") or item.get("spdisplays_vram_shared")
                vram_gb = None
                if vram:
                    mm = re.search(r"(\d+)", str(vram))
                    if mm:
                        vram_gb = round(int(mm.group(1)) / 1024, 1)
                if c.startswith("apple m"):
                    return {"type": "apple_silicon", "name": chip.strip(), "vram_gb": None}
                if "amd" in c or "radeon" in c:
                    mac = {"type": "amd", "name": chip.strip(), "vram_gb": vram_gb}
                    break
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    if mac["type"] == "cpu":
        out = _run(["system_profiler", "SPDisplaysDataType"])
        if out:
            chips = re.findall(r"Chipset Model:\s*(.+)", out)
            for chip in chips:
                c = chip.strip().lower()
                if c.startswith("apple m"):
                    return {"type": "apple_silicon", "name": chip.strip(), "vram_gb": None}
                if "amd" in c or "radeon" in c:
                    return {"type": "amd", "name": chip.strip(), "vram_gb": None}
            if chips:
                mac = {"type": "intel_igpu", "name": chips[0].strip(), "vram_gb": None}
    return mac


def detect_intel(os_name):
    """返回 Intel GPU 信息；type 为 arc / igpu / None"""
    if os_name == "Linux":
        out = _run(["lspci"])
        if out:
            for line in out.splitlines():
                if "VGA" in line and "Intel" in line:
                    if re.search(r"Arc\s*[AB]\d", line, re.I):
                        return {"type": "arc", "name": line.split(":")[-1].strip()}
                    return {"type": "igpu", "name": line.split(":")[-1].strip()}
    elif os_name == "Windows":
        # 优先 PowerShell；wmic 已弃用，仅作回退
        out = _run(["powershell", "-Command",
                    "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"],
                   timeout=20)
        if not out:
            out = _run(["wmic", "path", "win32_VideoController", "get", "Name"])
        if out:
            for line in out.splitlines():
                if "Intel" in line:
                    if re.search(r"Arc", line, re.I):
                        return {"type": "arc", "name": line.strip()}
                    return {"type": "igpu", "name": line.strip()}
    return {"type": None, "name": None}


def detect_all(os_name):
    """一次性探测所有硬件"""
    return {
        "os": os_name,
        "nvidia": detect_nvidia(),
        "amd": detect_amd(os_name) if os_name != "Darwin" else [],
        "mac_gpu": detect_macos_gpu() if os_name == "Darwin" else None,
        "intel": detect_intel(os_name),
    }


def pick_primary(gpus):
    """按显存最大值选主卡"""
    if not gpus:
        return None
    return sorted(gpus, key=lambda g: g.get("vram_gb") or 0, reverse=True)[0]


def primary_vram(hardware):
    """返回主卡显存（GB），无 GPU 时返回 None"""
    if hardware["nvidia"]:
        return pick_primary(hardware["nvidia"])["vram_gb"]
    if hardware["amd"]:
        return pick_primary(hardware["amd"]).get("vram_gb")
    if hardware["mac_gpu"] and hardware["mac_gpu"].get("vram_gb"):
        return hardware["mac_gpu"]["vram_gb"]
    return None