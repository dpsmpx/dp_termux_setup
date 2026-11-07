# Binary artifacts

The five source/binary artifacts below are tracked in this repository.
Verify their SHA-256 values using `manifests/artifact-sha256.txt`.

| Repository path | Artifact type | SHA-256 |
|---|---|---|
| `artifacts/debs/python-tokenizers_0.23.3_aarch64.deb` | Termux ARM64 package | `2ff955dc2928a658c44cd972ee4f45e0009e69b98a92180b5ae29b3e1ba8c454` |
| `artifacts/debs/python-hf-xet_1.8.0_aarch64.deb` | Termux ARM64 package | `6dcd3b28bf10b2ff44ec4d24d81e397e8030c5e9675775371ce134c088be56b0` |
| `artifacts/sources/safetensors-0.8.0.tar.gz` | Verified PyPI source | `fabaf3e0f18a6618d9b36560682562157f77c2b71fcffc7b432be2baed9d753d` |
| `artifacts/wheels/safetensors-0.8.0-cp310-abi3-android_24_arm64_v8a.whl` | Android ARM64 wheel | `29263ee16e3d5c96304890a48aaf8579c3f16d0acba412f361a250047849dfe3` |
| `artifacts/wheels/regex-2026.11.7-cp314-cp314-android_24_arm64_v8a.whl` | Android ARM64 wheel | `ab44a913600a21284b965816992936336bb7cfb04a406b6d2f7b4a9186b1de2d` |

```bash
sha256sum -c manifests/artifact-sha256.txt
```

The Safetensors and regex wheels target Android API 24 / ARM64 and the
recorded Python 3.14 environment. Rebuild and inspect them for other Python
versions or Android ABIs.
