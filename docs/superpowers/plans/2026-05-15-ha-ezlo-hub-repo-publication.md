# ha-ezlo-hub Repository Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing local integration and test suite into a fully publication-ready GitHub repository at `github.com/jamincollins/ha-ezlo-hub`.

**Architecture:** All changes are additive — new config/community files and targeted edits to three existing files. No production logic changes. Ruff violations (7 unused imports in tests) are fixed in Task 3 before any CI workflow is added.

**Tech Stack:** Python 3.11–3.13, pytest, pytest-asyncio, ruff, GitHub Actions (`actions/checkout@v4`, `actions/setup-python@v5`, `hacs/action@main`)

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `.gitignore` | Exclude APK, creds, hub_state.json, ha-config/ |
| Modify | `custom_components/ezlo/manifest.json` | Real GitHub URLs + codeowners |
| Modify | `hacs.json` | Add `homeassistant` minimum version |
| Modify | `requirements_test.txt` | Add `ruff>=0.4` |
| Modify | `tests/conftest.py` | Remove unused `AsyncMock` import |
| Modify | `tests/test_hub.py` | Remove unused `asyncio`, `Any` imports |
| Modify | `tests/test_sensor.py` | Remove unused `pytest`, `AsyncMock`, `patch` imports |
| Modify | `README.md` | Add CI/HACS/license badges after title |
| Create | `pyproject.toml` | pytest + ruff configuration |
| Create | `.github/workflows/ci.yml` | Test matrix on Python 3.11/3.12/3.13 |
| Create | `.github/workflows/hacs-validate.yml` | HACS + hassfest validation |
| Create | `.github/CODEOWNERS` | Auto-assign @jamincollins on every PR |
| Create | `.github/PULL_REQUEST_TEMPLATE.md` | PR checklist |
| Create | `.github/ISSUE_TEMPLATE/bug_report.yml` | Structured bug reports |
| Create | `.github/ISSUE_TEMPLATE/feature_request.yml` | Structured device requests |
| Create | `LICENSE` | MIT, 2026, Jamin Collins |
| Create | `CHANGELOG.md` | Keep-a-Changelog, v0.1.0 entry |
| Create | `CONTRIBUTING.md` | Dev setup, test/lint commands, PR guide |
| Create | `SECURITY.md` | Vulnerability reporting policy |
| Create | `scripts/get_hub_token.py` | Diagnostic utility; creds via env vars |

---

## Task 1: Update .gitignore

**Files:** Modify `.gitignore`

- [ ] **Step 1: Replace .gitignore with the complete version**

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
.eggs/
dist/
build/

# Test artefacts
.pytest_cache/
.coverage
htmlcov/

# IDE
.vscode/
.idea/

# Local development files — never commit these
creds
hub_state.json
ha-config/
com.vera.android_7.108.1.36.xapk
get_hub_token.py
/tmp/
*_identity.json
*_jwt.json
*_auth_state.pkl
```

Write that content to `.gitignore`.

- [ ] **Step 2: Verify sensitive files would not be staged**

Run:
```bash
git status --short
```

Expected: `creds`, `hub_state.json`, `ha-config/`, and `com.vera.android_7.108.1.36.xapk` do NOT appear in the output.

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: update .gitignore to exclude credentials and local artifacts"
```

---

## Task 2: Update metadata files

**Files:** Modify `custom_components/ezlo/manifest.json`, `hacs.json`, `requirements_test.txt`

- [ ] **Step 1: Update manifest.json**

Replace the contents of `custom_components/ezlo/manifest.json` with:

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

- [ ] **Step 2: Verify manifest.json is valid JSON**

Run:
```bash
python3 -c "import json; json.load(open('custom_components/ezlo/manifest.json')); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Update hacs.json**

Replace the contents of `hacs.json` with:

```json
{
  "name": "Ezlo Hub",
  "render_readme": true,
  "homeassistant": "2023.6.0"
}
```

- [ ] **Step 4: Verify hacs.json is valid JSON**

Run:
```bash
python3 -c "import json; json.load(open('hacs.json')); print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Update requirements_test.txt**

Replace the contents of `requirements_test.txt` with:

```
pytest>=7.4
pytest-asyncio>=0.23
aioresponses>=0.7
ruff>=0.4
```

- [ ] **Step 6: Commit**

```bash
git add custom_components/ezlo/manifest.json hacs.json requirements_test.txt
git commit -m "chore: update manifest URLs, HACS minimum HA version, add ruff to test deps"
```

---

## Task 3: Create pyproject.toml and fix ruff violations

**Files:** Create `pyproject.toml`, modify `tests/conftest.py`, `tests/test_hub.py`, `tests/test_sensor.py`

- [ ] **Step 1: Create pyproject.toml**

Create `pyproject.toml` with:

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

- [ ] **Step 2: Verify existing tests still pass**

Run:
```bash
python -m pytest tests/ -q
```

Expected: `65 passed`

- [ ] **Step 3: Check ruff violations on existing code**

Run:
```bash
ruff check custom_components/ tests/
```

Expected output (7 violations, all unused imports):
```
tests/conftest.py:12:27: F401 [*] `unittest.mock.AsyncMock` imported but unused
tests/conftest.py:94:8:  F401 [*] `voluptuous` imported but unused
tests/test_hub.py:4:8:   F401 [*] `asyncio` imported but unused
tests/test_hub.py:7:20:  F401 [*] `typing.Any` imported but unused
tests/test_sensor.py:6:8:   F401 [*] `pytest` imported but unused
tests/test_sensor.py:105:31: F401 [*] `unittest.mock.AsyncMock` imported but unused
tests/test_sensor.py:105:42: F401 [*] `unittest.mock.patch` imported but unused
```

- [ ] **Step 4: Fix tests/conftest.py — remove AsyncMock and voluptuous**

In `tests/conftest.py` line 12, change:
```python
from unittest.mock import AsyncMock, MagicMock
```
to:
```python
from unittest.mock import MagicMock
```

In `tests/conftest.py` line 94, remove the entire line:
```python
import voluptuous  # noqa: E402 — real package
```

- [ ] **Step 5: Fix tests/test_hub.py — remove asyncio and Any**

In `tests/test_hub.py`, remove lines 4 and 7:
```python
import asyncio          # remove this line
import base64
import json
from typing import Any  # remove this line
from unittest.mock import AsyncMock, MagicMock, patch
```

After the fix the import block should be:
```python
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch
```

- [ ] **Step 6: Fix tests/test_sensor.py — remove pytest, AsyncMock, patch**

In `tests/test_sensor.py`, remove the top-level `import pytest` at line 6:
```python
import pytest  # remove this line
```

Inside the `test_unsupported_device_types_are_logged` function body, change:
```python
from unittest.mock import AsyncMock, patch, MagicMock
```
to:
```python
from unittest.mock import MagicMock
```

- [ ] **Step 7: Verify ruff passes**

Run:
```bash
ruff check custom_components/ tests/
```

Expected: no output, exit code 0.

- [ ] **Step 8: Verify all 65 tests still pass**

Run:
```bash
python -m pytest tests/ -q
```

Expected: `65 passed`

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml tests/conftest.py tests/test_hub.py tests/test_sensor.py
git commit -m "chore: add pyproject.toml (pytest+ruff config) and fix 7 unused-import violations"
```

---

## Task 4: Create CI workflow

**Files:** Create `.github/workflows/ci.yml`

- [ ] **Step 1: Create the workflows directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Create .github/workflows/ci.yml**

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  test:
    name: "Test (Python ${{ matrix.python-version }})"
    runs-on: ubuntu-latest
    strategy:
      fail-fast: true
      matrix:
        python-version: ["3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: "pip"

      - name: Install dependencies
        run: pip install -r requirements_test.txt

      - name: Lint with ruff
        run: ruff check custom_components/ tests/

      - name: Run tests
        run: pytest tests/ -v
```

- [ ] **Step 3: Validate YAML syntax**

Run:
```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add test matrix workflow (Python 3.11/3.12/3.13, ruff + pytest)"
```

---

## Task 5: Create HACS validation workflow

**Files:** Create `.github/workflows/hacs-validate.yml`

- [ ] **Step 1: Create .github/workflows/hacs-validate.yml**

```yaml
name: HACS Validation

on:
  push:
  pull_request:
  schedule:
    - cron: "0 0 * * *"

jobs:
  validate:
    name: Validate with HACS action
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: HACS validation
        uses: hacs/action@main
        with:
          category: integration
```

- [ ] **Step 2: Validate YAML syntax**

Run:
```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/hacs-validate.yml')); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/hacs-validate.yml
git commit -m "ci: add nightly HACS/hassfest validation workflow"
```

---

## Task 6: Create LICENSE and CHANGELOG

**Files:** Create `LICENSE`, `CHANGELOG.md`

- [ ] **Step 1: Create LICENSE**

Create `LICENSE` with:

```
MIT License

Copyright (c) 2026 Jamin Collins

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Create CHANGELOG.md**

Create `CHANGELOG.md` with:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-15

### Added

- Local WebSocket connection to Ezlo Plus hub on port 17000 using `AES256-SHA256` TLS cipher
- Vera/Ezlo cloud authentication chain to obtain local hub access token
- `switch` platform: `switch.inwall` devices (e.g. in-wall fan switches)
- `lock` platform: `doorlock` devices with lock/unlock control
- `sensor` platform: battery percentage and battery maintenance state for door locks
- `cover` platform: `shutter.garage` devices (e.g. Z-Wave garage door openers)
- Automatic WebSocket reconnection after hub reboot or network interruption
- `INFO`-level logging for any device type not yet supported, with `DEBUG`-level
  item detail to assist in adding support for new devices
- 65-test suite runnable without a live hub or Home Assistant installation

[Unreleased]: https://github.com/jamincollins/ha-ezlo-hub/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/jamincollins/ha-ezlo-hub/releases/tag/v0.1.0
```

- [ ] **Step 3: Commit**

```bash
git add LICENSE CHANGELOG.md
git commit -m "docs: add MIT license and initial CHANGELOG"
```

---

## Task 7: Create CONTRIBUTING.md and SECURITY.md

**Files:** Create `CONTRIBUTING.md`, `SECURITY.md`

- [ ] **Step 1: Create CONTRIBUTING.md**

```markdown
# Contributing to ha-ezlo-hub

Thank you for your interest in contributing!

## Development setup

```bash
git clone https://github.com/jamincollins/ha-ezlo-hub.git
cd ha-ezlo-hub
pip install -r requirements_test.txt
```

## Running tests

```bash
pytest tests/ -v
```

All 65 tests run without a live hub or Home Assistant installation — the test
suite mocks both WebSocket connections and the Vera/Ezlo cloud API.

## Linting

```bash
ruff check custom_components/ tests/
```

Fix auto-fixable violations with `ruff check --fix`.

## Adding a new device type

1. Check the logs for an `INFO` line like:
   ```
   Unsupported Ezlo device type 'binary_sensor.motion' (name='…', id=…)
   ```
2. Enable `DEBUG` logging (`logger: logs: custom_components.ezlo: debug`) to see
   all items the device exposes.
3. Add the type constant to `custom_components/ezlo/const.py` and add it to
   `SUPPORTED_DEVICE_TYPES`.
4. Create `custom_components/ezlo/<platform>.py` following the pattern in
   `switch.py`.
5. Add the platform to `PLATFORMS` in `const.py`.
6. Write tests in `tests/test_<platform>.py` **before** writing the entity code
   — see `tests/test_switch.py` as a reference.
7. See the full guide in `README.md` → "Adding Support for New Device Types".

## Commit messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | When to use |
|--------|-------------|
| `feat:` | New device type or capability |
| `fix:` | Bug fix |
| `docs:` | README, CHANGELOG, docstrings |
| `test:` | Test additions or corrections |
| `chore:` | Config, deps, tooling |
| `refactor:` | Code change with no behaviour change |

## Pull request checklist

- [ ] Tests added or updated
- [ ] `ruff check custom_components/ tests/` exits 0
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] New device type documented in README if applicable
- [ ] DEBUG log output included in the PR if adding a new device type
```

- [ ] **Step 2: Create SECURITY.md**

```markdown
# Security Policy

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Email `jamin.collins@gmail.com` with:

- A description of the vulnerability
- Steps to reproduce
- Potential impact

You will receive a response within 72 hours. Please allow reasonable time for a
fix before any public disclosure.

## Scope

This integration stores a **local access token** (not your cloud password) in
Home Assistant's encrypted config storage. The token is specific to your hub and
can be revoked by removing and re-adding the integration.

No credentials or tokens are ever committed to this repository.
```

- [ ] **Step 3: Commit**

```bash
git add CONTRIBUTING.md SECURITY.md
git commit -m "docs: add CONTRIBUTING and SECURITY guides"
```

---

## Task 8: Create GitHub templates and CODEOWNERS

**Files:** Create `.github/CODEOWNERS`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/bug_report.yml`, `.github/ISSUE_TEMPLATE/feature_request.yml`

- [ ] **Step 1: Create .github/CODEOWNERS**

```
* @jamincollins
```

- [ ] **Step 2: Create .github/PULL_REQUEST_TEMPLATE.md**

```markdown
## Summary

<!-- Describe what this PR changes and why. -->

## Checklist

- [ ] Tests added or updated (`pytest tests/ -v` passes)
- [ ] `ruff check custom_components/ tests/` exits 0
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] New device type documented in README if applicable
- [ ] If adding a new device type: DEBUG log output included showing item names and valueTypes
```

- [ ] **Step 3: Create the ISSUE_TEMPLATE directory**

```bash
mkdir -p .github/ISSUE_TEMPLATE
```

- [ ] **Step 4: Create .github/ISSUE_TEMPLATE/bug_report.yml**

```yaml
name: Bug Report
description: Something is not working correctly
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: |
        Before filing a bug, enable DEBUG logging and reproduce the issue:
        ```yaml
        logger:
          logs:
            custom_components.ezlo: debug
        ```
  - type: input
    id: ha_version
    attributes:
      label: Home Assistant version
      placeholder: "e.g. 2024.5.3"
    validations:
      required: true
  - type: input
    id: integration_version
    attributes:
      label: Integration version
      placeholder: "e.g. 0.1.0 (shown in Settings → Devices & Services)"
    validations:
      required: true
  - type: input
    id: hub_firmware
    attributes:
      label: Hub firmware
      placeholder: "e.g. 2.0.90.3265.5 (shown in hub.info.get or HA device page)"
    validations:
      required: true
  - type: textarea
    id: description
    attributes:
      label: Describe the bug
      placeholder: What happened? What did you expect?
    validations:
      required: true
  - type: textarea
    id: steps
    attributes:
      label: Steps to reproduce
      placeholder: |
        1. ...
        2. ...
    validations:
      required: true
  - type: textarea
    id: logs
    attributes:
      label: Relevant log output
      description: Paste the full log snippet (INFO level minimum, DEBUG preferred).
      render: text
    validations:
      required: true
```

- [ ] **Step 5: Create .github/ISSUE_TEMPLATE/feature_request.yml**

```yaml
name: New Device Type Request
description: Request support for an Ezlo device type not yet handled
labels: ["enhancement"]
body:
  - type: markdown
    attributes:
      value: |
        To add a new device type we need the Ezlo device type string and the
        items it exposes. Enable DEBUG logging and look for log lines starting with
        `Unsupported Ezlo device type` and `→ item`.
  - type: input
    id: device_type
    attributes:
      label: Ezlo device type string
      placeholder: "e.g. binary_sensor.motion (from the INFO log line)"
    validations:
      required: true
  - type: textarea
    id: items
    attributes:
      label: Items exposed by the device
      description: |
        Paste the DEBUG log lines showing item names, valueTypes, and current values.
        Example:
          → item 'motion': valueType=bool, value=False
          → item 'battery': valueType=int, value=92
      render: text
    validations:
      required: true
  - type: input
    id: ha_platform
    attributes:
      label: Desired Home Assistant platform
      placeholder: "e.g. binary_sensor, climate, light"
    validations:
      required: false
  - type: input
    id: api_docs
    attributes:
      label: Link to Ezlo API docs (if available)
      placeholder: "https://api.ezlo.com/..."
    validations:
      required: false
  - type: textarea
    id: context
    attributes:
      label: Additional context
      placeholder: Device make/model, Z-Wave command class, anything else useful.
    validations:
      required: false
```

- [ ] **Step 6: Validate both YAML templates**

Run:
```bash
python3 -c "
import yaml
for f in ['.github/ISSUE_TEMPLATE/bug_report.yml', '.github/ISSUE_TEMPLATE/feature_request.yml']:
    yaml.safe_load(open(f))
    print(f'OK: {f}')
"
```

Expected:
```
OK: .github/ISSUE_TEMPLATE/bug_report.yml
OK: .github/ISSUE_TEMPLATE/feature_request.yml
```

- [ ] **Step 7: Commit**

```bash
git add .github/
git commit -m "chore: add CODEOWNERS, PR template, and issue templates"
```

---

## Task 9: Create scripts/get_hub_token.py

**Files:** Create `scripts/get_hub_token.py`

- [ ] **Step 1: Create the scripts directory**

```bash
mkdir -p scripts
```

- [ ] **Step 2: Create scripts/get_hub_token.py**

```python
#!/usr/bin/env python3
"""
Diagnostic utility: fetch the local hub access token from the Vera/Ezlo cloud.

Usage:
    export VERA_USER="your_vera_username"
    export VERA_PASS="your_vera_password"
    python3 scripts/get_hub_token.py

Optional: filter to a specific hub serial
    python3 scripts/get_hub_token.py 90030191

Output: user UUID and local token for each matched hub, ready to paste into
hub.offline.login.ui for manual testing.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import sys

import aiohttp

VERA_AUTH_URL = "https://vera-us-oem-autha11.mios.com/autha/auth/username/{}"
VERA_SHA1_SALT = "oZ7QE6LcLJp6fiWzdqZc"
JWT_EXCHANGE_URL = "https://cloud.ezlo.com/mca-router/token/exchange/legacy-to-cloud"
ACCESS_KEYS_URL = "https://api-cloud.ezlo.com/v1/request"


async def main(filter_serial: str | None = None) -> None:
    username = os.environ.get("VERA_USER")
    password = os.environ.get("VERA_PASS")

    if not username or not password:
        print("Error: VERA_USER and VERA_PASS environment variables must be set.", file=sys.stderr)
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        # Step 1: MIOS auth
        sha1_pass = hashlib.sha1(
            f"{username.lower()}{password}{VERA_SHA1_SALT}".encode()
        ).hexdigest()

        async with session.get(
            VERA_AUTH_URL.format(username),
            params={"SHA1Password": sha1_pass, "PK_Oem": "1", "TokenVersion": "2"},
        ) as resp:
            if resp.status != 200:
                print(f"Cloud auth failed: HTTP {resp.status}", file=sys.stderr)
                sys.exit(1)
            auth_data = await resp.json(content_type=None)

        identity = auth_data["Identity"]
        identity_sig = auth_data["IdentitySignature"]

        padded = identity + "=" * (-len(identity) % 4)
        pk_user = str(json.loads(base64.b64decode(padded))["PK_User"])

        # Step 2: JWT exchange
        async with session.get(
            JWT_EXCHANGE_URL,
            params={"pk_user": pk_user},
            headers={"MMSAuth": identity, "MMSAuthSig": identity_sig},
        ) as resp:
            jwt_token = (await resp.json(content_type=None))["token"]

        # Step 3: Access keys
        async with session.post(
            ACCESS_KEYS_URL,
            json={"call": "access_keys_sync", "params": {"version": -1}},
            headers={"Authorization": f"Bearer {jwt_token}"},
        ) as resp:
            keys_resp = await resp.json(content_type=None)

    if keys_resp.get("status") != 1:
        print(f"access_keys_sync failed: {keys_resp.get('data')}", file=sys.stderr)
        sys.exit(1)

    keys = keys_resp["data"]["keys"]
    printed = 0

    for key_data in keys.values():
        meta = key_data.get("meta", {})
        target = meta.get("target", {})
        entity = meta.get("entity", {})
        data = key_data.get("data", {})

        if (
            target.get("type") == "controller"
            and entity.get("type") == "user"
            and data.get("type") == "string"
        ):
            serial = target.get("uuid", "unknown")
            hub_id = meta.get("entity", {}).get("id", "")

            if filter_serial and hub_id != filter_serial:
                continue

            print(f"Hub UUID  : {serial}")
            print(f"Hub serial: {hub_id}")
            print(f"User UUID : {entity['uuid']}")
            print(f"Token     : {data['string']}")
            print()
            printed += 1

    if printed == 0:
        serial_note = f" matching serial {filter_serial!r}" if filter_serial else ""
        print(f"No hubs found{serial_note}.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    filter_serial = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(main(filter_serial))
```

- [ ] **Step 3: Verify ruff passes on the new script**

Run:
```bash
ruff check scripts/get_hub_token.py
```

Expected: no output, exit code 0.

- [ ] **Step 4: Verify the script fails cleanly without env vars set**

Run:
```bash
VERA_USER="" VERA_PASS="" python3 scripts/get_hub_token.py 2>&1; echo "Exit: $?"
```

Expected:
```
Error: VERA_USER and VERA_PASS environment variables must be set.
Exit: 1
```

- [ ] **Step 5: Commit**

```bash
git add scripts/get_hub_token.py
git commit -m "feat: add scripts/get_hub_token.py diagnostic utility (credentials via env vars)"
```

---

## Task 10: Update README with badges

**Files:** Modify `README.md`

- [ ] **Step 1: Add three badge lines after the title**

The current `README.md` starts with:
```markdown
# Ezlo Hub — Home Assistant Integration

A custom Home Assistant integration...
```

Change it to:
```markdown
# Ezlo Hub — Home Assistant Integration

[![CI](https://github.com/jamincollins/ha-ezlo-hub/actions/workflows/ci.yml/badge.svg)](https://github.com/jamincollins/ha-ezlo-hub/actions/workflows/ci.yml)
[![HACS Validation](https://github.com/jamincollins/ha-ezlo-hub/actions/workflows/hacs-validate.yml/badge.svg)](https://github.com/jamincollins/ha-ezlo-hub/actions/workflows/hacs-validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A custom Home Assistant integration...
```

- [ ] **Step 2: Verify the badge lines are correct Markdown**

Run:
```bash
python3 -c "
import re, sys
txt = open('README.md').read()
badges = re.findall(r'\[!\[.*?\]\(.*?\)\]\(.*?\)', txt)
assert len(badges) == 3, f'Expected 3 badges, found {len(badges)}'
print(f'OK: {len(badges)} badges found')
for b in badges:
    print(f'  {b[:80]}')
"
```

Expected:
```
OK: 3 badges found
  [![CI](https://github.com/jamincollins/ha-ezlo-hub/actions/workflows/ci.yml/ba...
  [![HACS Validation](https://github.com/jamincollins/ha-ezlo-hub/actions/workfl...
  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add CI, HACS validation, and license badges to README"
```

---

## Task 11: Verify and create initial publication commit

**Files:** All remaining untracked files

- [ ] **Step 1: Check what remains untracked**

Run:
```bash
git status --short
```

Review the output. The following should appear as untracked (`??`):
- `custom_components/` (integration source)
- `tests/` (test suite)
- `requirements_test.txt`
- `pyproject.toml`

The following must NOT appear:
- `creds`
- `hub_state.json`
- `ha-config/`
- `com.vera.android_7.108.1.36.xapk`
- `get_hub_token.py` (root-level)

If any sensitive file appears, stop and verify `.gitignore` from Task 1.

- [ ] **Step 2: Run the full test suite one final time**

Run:
```bash
python -m pytest tests/ -q
```

Expected: `65 passed`

- [ ] **Step 3: Run ruff one final time across all code**

Run:
```bash
ruff check custom_components/ tests/ scripts/
```

Expected: no output, exit code 0.

- [ ] **Step 4: Stage all remaining files**

```bash
git add custom_components/ tests/ requirements_test.txt pyproject.toml docs/
```

- [ ] **Step 5: Confirm nothing sensitive is staged**

Run:
```bash
git diff --cached --name-only | sort
```

Verify `creds`, `hub_state.json`, `ha-config/`, `com.vera.android_7.108.1.36.xapk`, and `get_hub_token.py` (root) are absent from the output.

- [ ] **Step 6: Create the initial release commit**

```bash
git commit -m "feat: initial release v0.1.0 — Ezlo Hub integration for Home Assistant

Supports:
- switch.inwall (in-wall switches)
- doorlock (Z-Wave door locks with battery sensors)
- shutter.garage (garage door openers)

Local WebSocket connection on port 17000 (AES256-SHA256 TLS).
Vera/Ezlo cloud auth chain fetches local token; all subsequent
communication is hub-local.

65 tests passing. HACS and hassfest compatible."
```

- [ ] **Step 7: Verify git log**

Run:
```bash
git log --oneline
```

Expected — 9 commits total, most recent first:
```
<hash> feat: initial release v0.1.0 — Ezlo Hub integration for Home Assistant
<hash> docs: add CI, HACS validation, and license badges to README
<hash> feat: add scripts/get_hub_token.py diagnostic utility (credentials via env vars)
<hash> chore: add CODEOWNERS, PR template, and issue templates
<hash> docs: add CONTRIBUTING and SECURITY guides
<hash> docs: add MIT license and initial CHANGELOG
<hash> ci: add nightly HACS/hassfest validation workflow
<hash> ci: add test matrix workflow (Python 3.11/3.12/3.13, ruff + pytest)
<hash> chore: add pyproject.toml (pytest+ruff config) and fix 7 unused-import violations
<hash> chore: update manifest URLs, HACS minimum HA version, add ruff to test deps
<hash> chore: update .gitignore to exclude credentials and local artifacts
<hash> docs: add repository design spec
```

- [ ] **Step 8: Show push instructions**

The repository is now ready to push. Run:
```bash
# Create the repo on GitHub first (https://github.com/new), then:
git remote add origin https://github.com/jamincollins/ha-ezlo-hub.git
git push -u origin main
```

After the push, the CI and HACS validation workflows will run automatically.

---

## Success criteria (from spec §9)

- [ ] `pytest tests/ -v` → 65/65 green
- [ ] `ruff check custom_components/ tests/ scripts/` → exit 0
- [ ] `hacs/action` validator → passes (verified after push)
- [ ] `git ls-files | grep -E 'creds|hub_state|\.xapk'` → no output
- [ ] README badges render on GitHub
- [ ] Both issue templates appear in the GitHub "New Issue" UI
