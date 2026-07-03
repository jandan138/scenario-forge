# Development Checks

Install:

```bash
python -m pip install -e ".[dev]"
```

Run:

```bash
make check
```

The default check runs:

- unit and contract tests;
- Ruff linting;
- starter package scaffold/check smoke;
- `git diff --check`.

Heavy simulator checks are not part of the bootstrap lane. Future simulator checks should be
separate targets and marked so pure package validation remains fast.
