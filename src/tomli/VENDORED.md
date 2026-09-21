# Vendored: tomli 2.4.1

Frozen MIT-licensed backport of stdlib `tomllib` (Python < 3.11). Vendored so
`bin/setup` needs no pip install / no global package on 3.9/3.10 and works on
PEP 668 managed Pythons. Imported by `src/manifest.py` only as a fallback when
`tomllib` is absent.

- Upstream: https://github.com/hukkin/tomli
- Version: 2.4.1
- License: MIT (see `LICENSE`)
- Frozen: tomli is a stable backport; no upstream changes expected.
- Do not edit these files; re-vendor from upstream to update.
