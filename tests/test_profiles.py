#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""profile 完整性测试"""

import os
import json


def test_all_profiles_valid():
    profiles_dir = os.path.join(os.path.dirname(__file__), "..", "profiles")
    assert os.path.isdir(profiles_dir), "profiles 目录不存在"
    expected = ["generic", "comfyui", "a1111", "diffusers", "vllm"]
    for name in expected:
        path = os.path.join(profiles_dir, f"{name}.json")
        assert os.path.isfile(path), f"缺少 profile: {name}.json"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert "name" in data, f"{name}.json 缺少 name"
        assert "core" in data, f"{name}.json 缺少 core"
        assert isinstance(data["core"], dict), f"{name}.json core 必须是对象"
        for pkg, cfg in data["core"].items():
            assert isinstance(cfg, dict), f"{name}.json 中 {pkg} 配置必须是对象"
            if "min" in cfg:
                assert isinstance(cfg["min"], str), f"{name}.json 中 {pkg}.min 必须是字符串"


def test_no_torch_in_profiles():
    profiles_dir = os.path.join(os.path.dirname(__file__), "..", "profiles")
    forbidden = {"torch", "torchvision", "torchaudio"}
    for fname in os.listdir(profiles_dir):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(profiles_dir, fname), encoding="utf-8") as f:
            data = json.load(f)
        for section in ("core", "extra"):
            overlap = forbidden & set(data.get(section, {}))
            assert not overlap, f"{fname} 的 {section} 中不应包含 {overlap}"


def test_profile_names_have_disclaimer():
    """非 generic profile 的名称应包含'第三方检测'限定词"""
    profiles_dir = os.path.join(os.path.dirname(__file__), "..", "profiles")
    for name in ["comfyui", "a1111", "diffusers", "vllm"]:
        path = os.path.join(profiles_dir, f"{name}.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert "第三方检测" in data["name"], \
            f"{name}.json 的 name 应包含'第三方检测'限定词，避免商标混淆"


if __name__ == "__main__":
    test_all_profiles_valid()
    test_no_torch_in_profiles()
    test_profile_names_have_disclaimer()
    print("✅ 所有 profile 测试通过")