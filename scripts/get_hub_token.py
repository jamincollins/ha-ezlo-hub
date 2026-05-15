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
