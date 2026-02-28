# How to Publish convoseed-agent to PyPI

## One-time setup

```bash
pip install build twine
```

## Build

```bash
cd convoseed_package/
python -m build
```

This creates:
```
dist/
  convoseed_agent-1.1.0.tar.gz      ← source distribution
  convoseed_agent-1.1.0-py3-none-any.whl  ← wheel
```

## Test on TestPyPI first (recommended)

```bash
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ convoseed-agent
```

## Publish to real PyPI

```bash
twine upload dist/*
```

You'll need a PyPI account. Create one at https://pypi.org/account/register/
Then create an API token at https://pypi.org/manage/account/token/

## Verify

```bash
pip install convoseed-agent
python -c "import convoseed_agent; print(convoseed_agent.__version__)"
# → 1.1.0
```

## After publishing — add to GitHub repo

Copy the convoseed_agent/ folder into your ConvoSeed repo:

```
ConvoSeed/
├── spec/CSP-1.md
├── src/
│   └── convoseed_agent/    ← add this folder
│       ├── __init__.py
│       ├── encoder.py
│       ├── wrapper.py
│       ├── registry.py
│       ├── cache.py
│       └── scheduler.py
├── pyproject.toml          ← add this
├── README.md               ← update this
└── ...
```

Commit message:
  feat: add convoseed-agent pip package (CSP-1 v1.1 reference implementation)
