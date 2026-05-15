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
