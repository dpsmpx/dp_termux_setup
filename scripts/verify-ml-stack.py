#!/usr/bin/env python3
"""Verify the pinned Termux ARM64 ML stack. Network/model tests are opt-in."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import math
import os
import struct
import tempfile
import wave
from pathlib import Path


EXPECTED = {
    "torch": "2.15.0",
    "torchvision": "0.29.2",
    "torchaudio": "2.11.1",
    "torchcodec": "0.17.0",
    "numpy": "2.5.4",
    "scipy": "1.18.1",
    "pillow": "13.0.0",
    "tokenizers": "0.23.3",
    "hf-xet": "1.8.0",
    "huggingface-hub": "2.4.0",
    "safetensors": "0.8.0",
    "transformers": "5.22.2",
    "requests": "2.34.2",
    "regex": "2026.11.7",
}


def check_versions() -> None:
    print("=== DISTRIBUTION VERSIONS ===")
    mismatches = []
    for name, expected in EXPECTED.items():
        actual = metadata.version(name)
        status = "PASS" if actual == expected else "MISMATCH"
        print(f"{name}: {actual} (recorded {expected}) [{status}]")
        if actual != expected:
            mismatches.append(f"{name}: expected {expected}, found {actual}")
    if mismatches:
        raise RuntimeError("Pinned environment version mismatch: " + "; ".join(mismatches))


def check_core(np, torch) -> None:
    print("\n=== NUMPY / PYTORCH ===")
    values = np.arange(6, dtype=np.float32)
    tensor = torch.from_numpy(values)
    assert torch.equal(tensor, torch.arange(6, dtype=torch.float32))
    print("NumPy to PyTorch: PASS")

    print("\n=== SCIPY ===")
    from scipy.linalg import det

    assert float(det(np.eye(3, dtype=np.float32))) == 1.0
    print("SciPy determinant: PASS")

    print("\n=== PILLOW ===")
    from PIL import Image

    image = Image.new("RGB", (8, 8), (30, 60, 90))
    assert image.size == (8, 8)
    print("Pillow image creation: PASS")

    print("\n=== TOKENIZERS ===")
    from tokenizers import Tokenizer, models, pre_tokenizers

    tokenizer = Tokenizer(
        models.WordLevel(
            {"[UNK]": 0, "Termux": 1, "ML": 2},
            unk_token="[UNK]",
        )
    )
    tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
    assert tokenizer.encode("Termux ML").tokens == ["Termux", "ML"]
    print("Tokenizers native extension: PASS")

    print("\n=== SAFETENSORS ROUNDTRIP ===")
    from safetensors.torch import load_file, save_file

    sample = {
        "weights": torch.arange(12, dtype=torch.float32).reshape(3, 4),
        "bias": torch.tensor([0.25, -0.5], dtype=torch.float32),
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "roundtrip.safetensors"
        save_file(sample, str(path))
        restored = load_file(str(path), device="cpu")
        assert sample.keys() == restored.keys()
        for key in sample:
            assert torch.equal(sample[key], restored[key]), key
    print("Safetensors save/load: PASS")

    print("\n=== TORCHVISION NMS ===")
    from torchvision.ops import nms

    boxes = torch.tensor([[0.0, 0.0, 10.0, 10.0], [1.0, 1.0, 9.0, 9.0]])
    scores = torch.tensor([0.9, 0.8])
    assert nms(boxes, scores, 0.5).tolist() == [0]
    print("TorchVision native NMS: PASS")

    print("\n=== TORCHAUDIO RESAMPLING ===")
    import torchaudio

    signal = torch.sin(torch.linspace(0, 100, 16000)).unsqueeze(0)
    resampled = torchaudio.functional.resample(signal, 16000, 8000)
    assert tuple(resampled.shape) == (1, 8000)
    print("TorchAudio resample: PASS")

    print("\n=== TORCHCODEC WAV DECODE ===")
    from torchcodec.decoders import AudioDecoder

    with tempfile.TemporaryDirectory() as tmp:
        wav_path = Path(tmp) / "tone.wav"
        frames = [
            int(12000 * math.sin(2 * math.pi * 440 * i / 16000))
            for i in range(1600)
        ]
        with wave.open(str(wav_path), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(16000)
            stream.writeframes(struct.pack("<" + "h" * len(frames), *frames))
        decoded = AudioDecoder(str(wav_path)).get_all_samples()
        assert decoded.sample_rate == 16000
        assert decoded.data.numel() > 0
    print("TorchCodec decode: PASS")


def check_network_and_model(torch, repo: str) -> None:
    print("\n=== REQUESTS / HUB NETWORK ===")
    import requests

    response = requests.get(
        "https://huggingface.co/api/models/google-bert/bert-base-uncased",
        timeout=30,
    )
    response.raise_for_status()
    assert response.json().get("id") == "google-bert/bert-base-uncased"
    print("Requests HTTPS + Hugging Face API: PASS")

    print("\n=== TRANSFORMERS MODEL LOAD / INFERENCE ===")
    from transformers import AutoModelForMaskedLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(repo)
    model = AutoModelForMaskedLM.from_pretrained(
        repo,
        use_safetensors=True,
    ).eval()

    inputs = tokenizer(
        "Termux Android ARM64 machine learning",
        return_tensors="pt",
    )
    with torch.inference_mode():
        output = model(**inputs)

    assert torch.isfinite(output.logits).all()
    print("Model:", repo)
    print("Class:", type(model).__name__)
    print("Logits shape:", tuple(output.logits.shape))
    print("Transformers inference: PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--network",
        action="store_true",
        help="Perform live Requests/Hugging Face API and model tests.",
    )
    parser.add_argument(
        "--model-repo",
        default="optimum-intel-internal-testing/tiny-random-bert",
        help="Small public model used with --network.",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=1,
        help="Set BLAS/OpenMP and PyTorch intra/inter-op threads for this process.",
    )
    args = parser.parse_args()

    if args.threads < 1:
        parser.error("--threads must be >= 1")

    # Set native thread-pool limits before importing NumPy/PyTorch so their
    # OpenBLAS/OpenMP runtimes can read the values during initialization.
    for variable in (
        "OPENBLAS_NUM_THREADS",
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ[variable] = str(args.threads)

    import numpy as np
    import torch

    print("Python ML stack verification")
    print("PyTorch default threads:", torch.get_num_threads())
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(args.threads)
    print("PyTorch test threads:", torch.get_num_threads())
    print("PyTorch inter-op test threads:", torch.get_num_interop_threads())
    print("BLAS/OpenMP environment thread limit:", args.threads)

    check_versions()
    check_core(np, torch)

    if args.network:
        check_network_and_model(torch, args.model_repo)

    print("\nALL REQUESTED CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
