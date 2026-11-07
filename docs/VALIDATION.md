# Validation record

Tested on the reference Android 15 ARM64 Termux environment on 2026-11-07.

## Package and runtime checks

- `dpkg --audit`: no output / no reported package database errors.
- Tokenizers 0.23.3 and HF Xet 1.8.0 imported from Termux package locations.
- Hugging Face Hub 2.4.0 initialized; public model API request returned HTTP 200.
- Requests 2.34.2 returned HTTP 200 from the Hugging Face model API.
- Transformers 5.22.2 loaded a tiny BERT test configuration and tokenizer.

## Native / ML checks

- NumPy array to PyTorch tensor interoperability: PASS.
- SciPy determinant: PASS.
- Pillow image creation: PASS.
- Tokenizers word-level test: PASS.
- TorchVision NMS native operation: PASS.
- TorchAudio resampling 16 kHz to 8 kHz: PASS.
- TorchCodec WAV decode: PASS.
- Safetensors Rust extension import: PASS.
- Safetensors read: 100 tensors / 126,851 elements.
- Safetensors save/load roundtrip: all tensor values equal.
- Transformers inference: output shape (1, 41, 1124), all logits finite.
- Single-threaded Transformers inference: 10 iterations passed without the observed BLAS memory-unallocation warning.
- Xet-backed 520,212-byte checkpoint download: SHA-256 matched the published LFS ETag.

## Known limitations

- The Transformers test checkpoint is a tiny random fixture, not a production pretrained model.
- Its repository contains weights for multiple task heads; loading one head may report other keys as UNEXPECTED.
- The OpenBLAS / OpenMP warning root cause has not been isolated.
- `pip check` prints Android platform-support notices for several Termux-provided distributions (including NumPy, SciPy, PyTorch and Pillow). The functional tests above passed; the notices should not be confused with a dependency-resolution failure.
- This is one tested device/software profile, not a claim of universal compatibility across Termux builds.
