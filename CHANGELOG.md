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