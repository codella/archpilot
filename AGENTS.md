# Repository Guidelines

## Project Structure & Module Organization

Archpilot is a Python 3.11+ terminal installation planner. `archpilot/cli.py` handles commands and authentication; `inventory.py` contains read-only hardware probes; `planner.py` validates preferences and creates draft plans; `agent.py` isolates Codex SDK interactions. Tests live in `tests/`. Release tooling and the bootstrap template live in `scripts/`; `.github/workflows/release.yml` publishes version-tagged releases. Generated wheels, installers and VM test ISOs belong in ignored `dist/`.

## Build, Test, and Development Commands

Run from the repository root:

```sh
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/archpilot demo
.venv/bin/python -m unittest discover -s tests -v
bash -n scripts/install.sh.in
.venv/bin/python scripts/build_release.py
```

The demo uses fixture hardware without API calls. `archpilot inventory` probes local hardware; `archpilot login` and `archpilot chat` enable authenticated conversation. Release builds create a wheel and checksum-pinned installer. Supply `--base-url` when preparing a hosted release. See `README.md` for VM testing and ISO creation.

## Coding Style & Naming Conventions

Use four-space indentation, `snake_case` functions and modules, and `PascalCase` classes. Match existing Python style and keep modules focused. No formatter or linter is configured. Keep subprocess arguments as explicit lists; never execute model-generated shell text. Bash scripts use strict mode and quote variable expansions.

## Testing Guidelines

Use standard-library `unittest`, files named `test_*.py`, and methods named `test_*`. No numeric coverage threshold is configured. Add meaningful tests for changed validation, disk exclusions, export behavior and bootstrap failure recovery. Mock system installation commands; tests must not modify disks or require credentials. Distinguish mocked tests from actual VM and authenticated SDK verification.

## Commit & Pull Request Guidelines

Git history is unavailable in this workspace, so no established commit convention can be verified. Use short imperative subjects, such as `Add local release bootstrap support`. PRs should explain behavior changes, link relevant issues, list verification performed, and identify untested integration paths. Include terminal output when CLI behavior changes. Release tags must match the version in `pyproject.toml`.

## Safety & Configuration

Preserve planning-only behavior: plans remain drafts and non-executable. Disk selection stays explicit and outside model responses. Never commit credentials, authentication caches, generated environments or exported hardware plans. Keep the SDK version pinned and regenerate installer checksums whenever release wheels change.
