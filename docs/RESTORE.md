# Optional Python/ML profile

The pinned profile targets Android ARM64 and CPython 3.14.x. It is optional
and is not installed by the default manager.

Verify the environment:

```bash
uname -m
python --version
python -m pip --version
df -h "$HOME"
```

Verify the committed source and binary artifacts:

```bash
sha256sum -c manifests/artifact-sha256.txt
```

Install the profile only when it is needed:

```bash
bash scripts/install-ml-stack.sh
```

The installer simulates the APT transaction first and asks before applying
it. It refuses a plan that would remove packages. PyTorch, NumPy, SciPy,
Pillow and related Termux packages are managed separately by Termux/DPKG.

Core validation:

```bash
python scripts/verify-ml-stack.py
```

Optional network/model validation downloads a small public test model:

```bash
python scripts/verify-ml-stack.py --network --model-repo optimum-intel-internal-testing/tiny-random-bert
```
