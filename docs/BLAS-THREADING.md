# BLAS and PyTorch thread diagnostic

## Reference observations (2026-11-07)

- Termux `libopenblas 0.3.34`
- NumPy reports OpenBLAS 0.3.34, `USE_OPENMP`, `MAX_THREADS=0`, `NO_AFFINITY=1`, ARMV8
- PyTorch reports the OpenMP parallel backend
- Default PyTorch intra-op threads: 6
- Default PyTorch inter-op threads: 6
- `nproc`: 6; PyTorch build reports hardware concurrency 8

A Transformers BERT inference completed and produced finite logits, but printed several messages of the form:

```
BLAS : Bad memory unallocation! : 50 0x...
```

A separate run used all of these per-process limits:

```bash
OPENBLAS_NUM_THREADS=1 \
OMP_NUM_THREADS=1 \
MKL_NUM_THREADS=1 \
NUMEXPR_NUM_THREADS=1 \
python your_inference.py
```

The Python process also called:

```python
import torch
torch.set_num_threads(1)
torch.set_num_interop_threads(1)
```

Ten consecutive inference iterations passed without the BLAS message.

## Interpretation

This is an empirical workaround, not a proven root-cause diagnosis. Because several environment variables and both PyTorch thread settings changed together, the test does not isolate whether OpenBLAS, OpenMP, interaction between thread pools, or another component emitted the warning.

Do not globally force single-thread operation for every workload. It may reduce throughput. Start with per-process limits for affected inference jobs, then benchmark and isolate variables one at a time before selecting a persistent setting.

The warning was not observed in the ten single-threaded iterations; the test does not prove that all concurrent workloads are safe.
