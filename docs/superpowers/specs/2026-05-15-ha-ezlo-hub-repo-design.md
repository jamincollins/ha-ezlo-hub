# ha-ezlo-hub: GitHub Repository Design

**Date:** 2026-05-15  
**Repo:** `https://github.com/jamincollins/ha-ezlo-hub`  
**Scope:** Turn the existing local integration + test suite into a publication-ready GitHub repository following HACS and Home Assistant community standards.  
**Approach chosen:** Option B — Full project with standard GitHub conventions (no release automation).

---

## 1. Repository Structure

```
ha-ezlo-hub/
├── custom_components/
│   └── ezlo/
│       ├── __init__.py
│       ├── config_flow.py
│       ├── const.py
│       ├── cover.py
│       ├── hub.py
│       ├── lock.py
│       ├── manifest.json        ← updated URLs and codeowners
│       ├── sensor.py
│       ├── strings.json
│       └── switch.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_cover.py
│   ├── test_hub.py
│   ├── test_lock.py
│   ├── test_sensor.py
│   └── test_switch.py
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   └── hacs-validate.yml
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml
│   │   └── feature_request.yml
│   ├── CODEOWNERS
│   └── PULL_REQUEST_TEMPLATE.md
├── scripts/
│   └── get_hub_token.py         ← diagnostic utility, credentials via env vars
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-05-15-ha-ezlo-hub-repo-design.md
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
├── hacs.json
├── LICENSE
├── pyproject.toml
├── README.md                    ← updated with CI/HACS/license badges
├── requirements_test.txt
└── SECURITY.md
```

### Files excluded from the repository (via .gitignore)

| File / Directory | Reason |
|---|---|
| `com.vera.android_7.108.1.36.xapk` | Reverse-engineering artifact; not part of integration |
| `creds` | Contains live cloud credentials |
| `hub_state.json` | Local device state snapshot |
| `ha-config/` | Local Docker HA installation |
| `get_hub_token.py` (root) | Replaced by `scripts/get_hub_token.py` |
| `__pycache__/`, `*.pyc` | Python bytecode |
| `.pytest_cache/`, `.coverage` | Test artefacts |

---

## 2. File Changes

### `custom_components/ezlo/manifest.json`

Three fields updated:

```json
{
  "domain": "ezlo",
  "name": "Ezlo Hub",
  "codeowners": ["@jamincollins"],
  "config_flow": true,
  "documentation": "https://github.com/jamincollins/ha-ezlo-hub",
  "issue_tracker": "https://github.com/jamincollins/ha-ezlo-hub/issues",
  "iot_class": "local_push",
  "requirements": [],
  "version": "0.1.0"
}
```

### `hacs.json`

Add minimum HA version:

```json
{
  "name": "Ezlo Hub",
  "render_readme": true,
  "homeassistant": "2023.6.0"
}
```

### `requirements_test.txt`

Add `ruff`:

```
pytest>=7.4
pytest-asyncio>=0.23
aioresponses>=0.7
ruff>=0.4
```

### `README.md`

Add three badges immediately after the `# Ezlo Hub` title:

```markdown
[![CI](https://github.com/jamincollins/ha-ezlo-hub/actions/workflows/ci.yml/badge.svg)](https://github.com/jamincollins/ha-ezlo-hub/actions/workflows/ci.yml)
[![HACS Validation](https://github.com/jamincollins/ha-ezlo-hub/actions/workflows/hacs-validate.yml/badge.svg)](https://github.com/jamincollins/ha-ezlo-hub/actions/workflows/hacs-validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
```

---

## 3. CI Workflows

### `.github/workflows/ci.yml`

Trigger: push to any branch, pull_request.

Steps:
1. `actions/checkout@v4`
2. `actions/setup-python@v5` — matrix: `["3.11", "3.12", "3.13"]`
3. `pip install -r requirements_test.txt`
4. `ruff check custom_components/ tests/`
5. `pytest tests/ -v`

Fail-fast: yes. A lint failure or a single test failure blocks the PR.

### `.github/workflows/hacs-validate.yml`

Trigger: push, pull_request, and nightly cron (`0 0 * * *`).

Steps:
1. `actions/checkout@v4`
2. `hacs/action@main` with `category: integration`

The nightly run catches HACS rule changes breaking the integration before any user reports it.

---

## 4. Developer Tooling

### `pyproject.toml`

```toml
[tool.pytest.ini_options]
asyncio_mode = "strict"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
ignore = ["E501"]
```

`ruff` covers pycodestyle, pyflakes, and import sorting in a single tool.  
`mypy` is explicitly excluded — type hints are present for readability, not enforcement.

---

## 5. GitHub Community Files

### `LICENSE`
MIT licence. Copyright 2026 Jamin Collins.

### `CHANGELOG.md`
Keep-a-Changelog format. Initial entry:

```
## [0.1.0] - 2026-05-15
### Added
- Local WebSocket connection to Ezlo Plus hub (port 17000, AES256-SHA256)
- Vera/Ezlo cloud authentication to obtain local access token
- switch platform: switch.inwall devices
- lock platform: doorlock devices with battery sensors
- cover platform: shutter.garage devices
- sensor platform: battery % and battery maintenance state
- Automatic reconnection on hub reboot or network drop
- INFO logging for unsupported device types
```

### `CONTRIBUTING.md`
Sections:
- Development environment setup (clone, `pip install -r requirements_test.txt`)
- Running tests (`pytest tests/ -v`) and linting (`ruff check`)
- Adding a new device type (cross-reference to README section)
- Commit message convention: conventional commits (`feat:`, `fix:`, `docs:`, `test:`)
- PR checklist (mirrors the PR template)

### `SECURITY.md`
- Report vulnerabilities by email; do not open a public issue
- Placeholder: `security@<your-domain>` — owner must substitute a real address
- Note: cloud credentials are never stored in the repository

### `.github/PULL_REQUEST_TEMPLATE.md`
Checklist:
- [ ] Tests added or updated
- [ ] `ruff check` passes locally
- [ ] CHANGELOG.md updated under `[Unreleased]`
- [ ] New device type documented in README if applicable
- [ ] DEBUG log output included if adding a new device type

### `.github/ISSUE_TEMPLATE/bug_report.yml`
Required fields: HA version, integration version, hub firmware, full log snippet
(at least INFO level, DEBUG preferred), steps to reproduce, expected vs actual behaviour.

### `.github/ISSUE_TEMPLATE/feature_request.yml`
Required fields: device type string from the unsupported-device log line, item
names and valueTypes from DEBUG log output, link to Ezlo API docs if available,
description of desired HA entity type.

### `.github/CODEOWNERS`
```
* @jamincollins
```

---

## 6. `scripts/get_hub_token.py`

A cleaned-up version of the root-level utility used during development. Changes from the original:

- Credentials read from `VERA_USER` and `VERA_PASS` environment variables (not hardcoded)
- Usage comment at the top explaining what the script does and how to run it
- Output shows the `user` UUID and `token` needed for manual hub setup
- No credentials or device-specific data left in the file

---

## 7. Initial Git Commit

Single commit titled:

```
feat: initial release v0.1.0 — Ezlo Hub integration for Home Assistant
```

Commit includes all files listed in the repository structure above.  
The `.gitignore` ensures credentials, APK, local HA config, and hub state are never staged.

---

## 8. Out of Scope

The following are explicitly excluded from this effort:

- **Release automation** (semantic-release, auto-CHANGELOG on merge) — premature before any users or release cadence exist
- **`mypy` type checking** — type hints are present but enforcement adds noise at this stage
- **Coverage reporting** (Codecov, Coveralls) — useful later, not needed for initial publication
- **GitHub Pages / docs site** — README is sufficient for v0.1.0
- **Dependabot** for Python dependencies — requirements_test.txt is minimal and stable
- **Dependabot** for GitHub Actions — worth adding after initial publication settles

---

## 9. Success Criteria

The repository is publication-ready when:

1. `pytest tests/ -v` passes with 65/65 tests green
2. `ruff check custom_components/ tests/` exits 0
3. `hacs/action` validator passes
4. No credentials, APK, or local state files are tracked by git
5. `README.md` renders correctly on GitHub (badges, tables, code blocks)
6. Both issue templates are functional on GitHub
