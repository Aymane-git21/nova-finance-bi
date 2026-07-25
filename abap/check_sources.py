#!/usr/bin/env python
"""Static consistency check over the ABAP sources.

    python abap/check_sources.py

These sources have never been activated - no ABAP system was reachable
(docs/adr/003-abap-evidence-strategy.md). That makes "it compiles" unavailable
as evidence, and unverifiable code in a portfolio is worth close to nothing.

So this checks what CAN be checked without a system:

  * every Z* object referenced by another source actually exists here
  * every file carries the NOT ACTIVATED marker, so nothing can be mistaken
    for activated code
  * every object's name matches its filename, the way abapGit requires
  * the AMDP's declared table function exists and its returns clause matches
    the columns the method actually selects
  * pseudonymous user columns never reach an interface or consumption view

It is a linter, not a compiler, and the README says so. What it rules out is
the embarrassing class of error: a view referencing something that was renamed,
or a file that quietly lost its label.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
MARKER = "NOT ACTIVATED"

# Columns that must never surface above the table layer.
PSEUDONYM_COLUMNS = ("posting_user_id", "manager_user_id", "completed_by_user_id")


class Findings:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.checks = 0

    def check(self, condition: bool, message: str) -> None:
        self.checks += 1
        if not condition:
            self.errors.append(message)


def object_name(path: Path) -> str:
    """abapGit filenames are <object>.<type>.<ext>, lower case."""
    return path.name.split(".")[0].lower()


def strip_comments(text: str) -> str:
    text = re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\"!.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*--.*$", "", text, flags=re.MULTILINE)
    return text


def main() -> int:
    if not SRC.is_dir():
        raise SystemExit(f"no source directory at {SRC}")

    sources = sorted(
        p for p in SRC.iterdir()
        if p.is_file() and p.suffix in (".asddls", ".abap", ".srvdsrv", ".xml")
    )
    if not sources:
        raise SystemExit(f"no ABAP sources found in {SRC}")

    defined = {object_name(p) for p in sources}
    findings = Findings()

    print(f"checking {len(sources)} sources in {SRC}\n")

    # -- markers and naming -------------------------------------------------
    for path in sources:
        if path.name == "package.devc.xml":
            continue
        text = path.read_text(encoding="utf-8")
        findings.check(
            MARKER in text,
            f"{path.name}: missing the '{MARKER}' marker",
        )

        body = strip_comments(text)
        declared = re.search(
            r"define\s+(?:table\s+function|view\s+entity|table|service)\s+([\w/]+)",
            body, re.IGNORECASE,
        ) or re.search(r"CLASS\s+([\w/]+)\s+DEFINITION", body, re.IGNORECASE)
        if declared:
            findings.check(
                declared.group(1).lower() == object_name(path),
                f"{path.name}: declares '{declared.group(1)}' but the filename "
                f"says '{object_name(path)}'",
            )

    # -- cross references ---------------------------------------------------
    reference_pattern = re.compile(r"\b(z[a-z0-9_]{2,})\b", re.IGNORECASE)
    for path in sources:
        if path.suffix == ".xml":
            continue
        body = strip_comments(path.read_text(encoding="utf-8"))
        own = object_name(path)
        for match in sorted(set(reference_pattern.findall(body))):
            name = match.lower()
            if name == own:
                continue
            findings.check(
                name in defined,
                f"{path.name}: references '{match}', which is not defined in src/",
            )

    # -- the AMDP and its table function ------------------------------------
    amdp = SRC / "zcl_amdp_runrate.clas.abap"
    table_function = SRC / "zi_programmerunrate.ddls.asddls"
    if amdp.exists() and table_function.exists():
        amdp_text = amdp.read_text(encoding="utf-8")
        tf_text = table_function.read_text(encoding="utf-8")

        findings.check(
            "FOR TABLE FUNCTION zi_programmerunrate" in amdp_text.lower()
            .replace("for table function zi_programmerunrate",
                     "FOR TABLE FUNCTION zi_programmerunrate"),
            "zcl_amdp_runrate: does not declare FOR TABLE FUNCTION zi_programmerunrate",
        )
        findings.check(
            "zcl_amdp_runrate=>get_run_rate" in tf_text.lower(),
            "zi_programmerunrate: does not delegate to zcl_amdp_runrate=>get_run_rate",
        )
        findings.check(
            "if_amdp_marker_hdb" in amdp_text.lower(),
            "zcl_amdp_runrate: missing the IF_AMDP_MARKER_HDB interface, without "
            "which BY DATABASE FUNCTION will not compile",
        )
        findings.check(
            "options read-only" in amdp_text.lower(),
            "zcl_amdp_runrate: an analytical AMDP should be OPTIONS READ-ONLY",
        )

        # The returns clause and the RETURN SELECT must agree, column for column.
        returns_block = re.search(r"returns\s*\{(.*?)\}", tf_text, re.DOTALL)
        return_select = re.search(
            r"RETURN\s+SELECT(.*?)(?:FROM\s)", amdp_text, re.DOTALL | re.IGNORECASE
        )
        if returns_block and return_select:
            declared_cols = [
                m.group(1).lower()
                for m in re.finditer(r"^\s*(\w+)\s*:", returns_block.group(1), re.MULTILINE)
            ]
            selected_cols = [
                m.group(1).lower()
                for m in re.finditer(r"\bAS\s+(\w+)\s*(?:,|$)", return_select.group(1),
                                     re.IGNORECASE | re.MULTILINE)
            ]
            missing = [c for c in declared_cols if c not in selected_cols]
            extra = [c for c in selected_cols if c not in declared_cols]
            findings.check(
                not missing,
                f"zcl_amdp_runrate: declared in the table function but never "
                f"selected: {missing}",
            )
            findings.check(
                not extra,
                f"zcl_amdp_runrate: selected but not declared in the table "
                f"function: {extra}",
            )

    # -- personal data ------------------------------------------------------
    for path in sources:
        if not path.name.startswith(("zi_", "zc_")):
            continue
        body = strip_comments(path.read_text(encoding="utf-8"))
        for column in PSEUDONYM_COLUMNS:
            findings.check(
                column not in body.lower(),
                f"{path.name}: exposes '{column}'. User-level attribution is an "
                "audit function and has no business in an analytical view - see "
                "docs/gdpr-and-data-protection.md",
            )

    # -- report -------------------------------------------------------------
    if findings.errors:
        print(f"{len(findings.errors)} problem(s) in {findings.checks} checks:\n")
        for error in findings.errors:
            print(f"  FAIL  {error}")
        print("\nThese sources cannot be compiled without an ABAP system, so this "
              "linter is the only check there is. Fix them.")
        return 1

    print(f"all {findings.checks} checks pass across {len(sources)} sources.")
    print("\nThis is a static consistency check, NOT a compiler. It proves the "
          "sources are internally coherent and correctly labelled.")
    print("It does not prove they activate. Nothing here claims they do.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
