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
