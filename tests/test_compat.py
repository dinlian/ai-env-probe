#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兼容性规则回归测试"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common import vtuple, normalize_cuda_major, cuda_tag_to_major, auto_detect_profile_id
from launcher import recommend_cuda


def test_pascal_never_cu126():
    for drv in [525, 560, 580, 600]:
        tag, _, _ = recommend_cuda("Pascal", drv)
        assert tag in ("cu124", "cu121", None), f"Pascal 驱动 {drv} 推荐了 {tag}"
    for drv in [525, 560, 580]:
        tag, _, _ = recommend_cuda("Volta", drv)
        assert tag in ("cu124", "cu121", None), f"Volta 驱动 {drv} 推荐了 {tag}"


def test_blackwell_requires_cu128_plus():
    assert recommend_cuda("Blackwell", 560)[0] is None
    assert recommend_cuda("Blackwell", 570)[0] == "cu128"
    assert recommend_cuda("Blackwell", 580)[0] == "cu130"


def test_ampere_driver_aware():
    assert recommend_cuda("Ampere", 580)[0] == "cu130"
    assert recommend_cuda("Ampere", 560)[0] == "cu126"
    assert recommend_cuda("Ampere", 500)[0] is None


def test_smi_cuda_upper_bound():
    tag, _, _ = recommend_cuda("Ampere", 580, smi_cuda_major="12")
    assert tag != "cu130", f"驱动只支持 CUDA 12.x，却推荐了 {tag}"


def test_cuda_major_normalize():
    assert normalize_cuda_major("13.0") == "13"
    assert normalize_cuda_major(13000) == "13"
    assert normalize_cuda_major("12.6") == "12"
    assert normalize_cuda_major(12060) == "12"
    assert normalize_cuda_major(None) is None


def test_cuda_tag_to_major():
    assert cuda_tag_to_major("cu130") == 13
    assert cuda_tag_to_major("cu128") == 12
    assert cuda_tag_to_major("cu126") == 12
    assert cuda_tag_to_major("cu124") == 12
    assert cuda_tag_to_major("cu121") == 12


if __name__ == "__main__":
    test_pascal_never_cu126()
    test_blackwell_requires_cu128_plus()
    test_ampere_driver_aware()
    test_smi_cuda_upper_bound()
    test_cuda_major_normalize()
    test_cuda_tag_to_major()
    print("✅ 所有兼容性规则测试通过")