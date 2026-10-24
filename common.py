#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Env Probe - 共用模块

Copyright (c) 2026 dinlian
Licensed under the MIT License. See LICENSE file for details.
"""

import os
import re

TOOL_NAME = "AI Env Probe"
VERSION = "1.0.0"
COPYRIGHT = "Copyright (c) 2026 dinlian"
LICENSE = "MIT"

BANNER = f"""
{TOOL_NAME}  v{VERSION}
{COPYRIGHT}  |  {LICENSE} License
本工具不联网、不上传数据、不修改系统配置
本工具为第三方独立脚本，与所检测应用无隶属关系或官方背书
{"-" * 62}
"""


def vtuple(s):
    if not s:
        return ()
    return tuple(int(x) for x in re.findall(r"\d+", str(s))[:3])


def normalize_cuda_major(v):
    if v is None:
        return None
    if isinstance(v, int):
        return str(v // 1000)
    s = str(v).strip()
    if not s:
        return None
    if "." in s:
        return s.split(".")[0]
    try:
        return str(int(s) // 1000)
    except ValueError:
        return s


def cuda_tag_to_major(tag):
    """cu130 -> 13, cu128 -> 12, cu126 -> 12, cu124 -> 12, cu121 -> 12"""
    if not tag or not tag.startswith("cu"):
        return None
    s = tag.replace("cu", "")
    if len(s) >= 3:
        return int(s[:2])
    return int(s)


def auto_detect_profile_id(base_dir):
    """根据目录特征自动识别应用类型"""
    if not base_dir or not os.path.isdir(base_dir):
        return "generic"

    if os.path.isfile(os.path.join(base_dir, "main.py")) and \
       os.path.isdir(os.path.join(base_dir, "custom_nodes")):
        return "comfyui"

    if os.path.isfile(os.path.join(base_dir, "webui.py")) or \
       os.path.isfile(os.path.join(base_dir, "launch.py")):
        return "a1111"

    if os.path.isdir(os.path.join(base_dir, "vllm")) and \
       os.path.isfile(os.path.join(base_dir, "setup.py")):
        return "vllm"

    req = os.path.join(base_dir, "requirements.txt")
    if os.path.isfile(req):
        try:
            with open(req, encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
            if "vllm" in content:
                return "vllm"
            if "diffusers" in content:
                return "diffusers"
            if "comfyui" in content:
                return "comfyui"
            if "gradio" in content and "stable-diffusion" in content:
                return "a1111"
        except Exception:
            pass

    return "generic"


def get_resource_dir():
    """获取资源目录（打包时从 _MEIPASS，源码时从脚本目录）"""
    import sys
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

def _looks_like_target_app(d):
    """判断目录是否像 AI 应用根目录（用于 find_python 的决策）"""
    if not d or not os.path.isdir(d):
        return False
    # ComfyUI
    if os.path.isfile(os.path.join(d, "main.py")) and \
       os.path.isdir(os.path.join(d, "custom_nodes")):
        return True
    # A1111 / Forge
    if os.path.isfile(os.path.join(d, "webui.py")) or \
       os.path.isfile(os.path.join(d, "launch.py")):
        return True
    # vLLM 源码
    if os.path.isdir(os.path.join(d, "vllm")) and \
       os.path.isfile(os.path.join(d, "setup.py")):
        return True
    # 通用 Python 项目
    if os.path.isfile(os.path.join(d, "requirements.txt")):
        return True
    return False