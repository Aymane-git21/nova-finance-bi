#!/usr/bin/env python
"""Write cap/.cdsrc-private.json from the generated HANA credentials.

    python cap/configure.py

CAP needs database credentials; ``hana/hxe.sh init`` generates them. Rather
than duplicating a password into a second file by hand - and inevitably
committing one of the two - this derives the CAP config from the single source
and writes it to a path .gitignore excludes.

``currentSchema`` is the important line: it points the connection at
NOVASPACE_API, so the CDS entities bind to the published interface views by
bare name and there is no schema qualification anywhere in the model to drift.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO / "hana"))

from load_data import read_credentials  # noqa: E402

API_SCHEMA = "NOVASPACE_API"
TARGET = HERE / ".cdsrc-private.json"


def main() -> int:
    settings = read_credentials()
    config = {
        "requires": {
            "db": {
                "kind": "hana",
                "credentials": {
                    "host": settings["host"],
                    "port": int(settings["port"]),
                    "user": settings["user"],
                    "password": settings["password"],
                    "currentSchema": API_SCHEMA,
                    "schema": API_SCHEMA,
                    "encrypt": False,
                    "sslValidateCertificate": False,
                },
            }
        }
    }
    TARGET.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    TARGET.chmod(0o600)
    print(f"wrote {TARGET} (mode 600, git-ignored)")
    print(f"  host   {settings['host']}:{settings['port']}")
    print(f"  user   {settings['user']}")
    print(f"  schema {API_SCHEMA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
