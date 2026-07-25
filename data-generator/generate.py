#!/usr/bin/env python
"""Generate the NovaSpace Group synthetic finance dataset.

    python data-generator/generate.py

Writes one CSV per table to ``data-generator/output/`` (git-ignored, fully
regenerable), the SAC extracts to ``data-generator/output/sac/``, and a small
committed slice of each table to ``data-generator/samples/``.

All data is synthetic. No real or client data is used, referenced or
approximated. The seed is fixed, so every number this repository quotes anywhere
is reproducible by running this script.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from novaspace import config, writer  # noqa: E402
from novaspace.build import build_dataset  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=HERE / "output",
        help="where the full CSVs go (default: data-generator/output)",
    )
    parser.add_argument(
        "--samples-dir", type=Path, default=HERE / "samples",
        help="where the small committed slices go (default: data-generator/samples)",
    )
    parser.add_argument(
        "--sac-dir", type=Path, default=HERE.parent / "sac" / "extracts",
        help=(
            "where the SAC extracts go (default: sac/extracts). These are "
            "committed: they are small, and they are exactly what gets uploaded "
            "to the import-only SAC tenant, so the repository holds the same "
            "bytes the story was built on."
        ),
    )
    parser.add_argument(
        "--seed", type=int, default=config.SEED,
        help=f"RNG seed (default: {config.SEED}). Changing this changes every number.",
    )
    parser.add_argument(
        "--scale", type=float, default=1.0,
        help="volume multiplier. 1.0 is the published dataset; lower is for quick checks.",
    )
    parser.add_argument(
        "--sample-rows", type=int, default=200,
        help="rows per committed sample file (default: 200)",
    )
    parser.add_argument(
        "--no-samples", action="store_true", help="skip writing the sample slices",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    print(f"NovaSpace synthetic dataset - seed {args.seed}, scale {args.scale}")
    print("All data is synthetic. No real or client data is involved.\n")

    started = time.perf_counter()
    dataset = build_dataset(seed=args.seed, scale=args.scale)
    build_seconds = time.perf_counter() - started

    print(f"{'table':<22} {'rows':>12}")
    print("-" * 36)
    total_rows = 0
    for name, frame in dataset.tables.items():
        rows = writer.write_csv(frame, args.output_dir / f"{name}.csv")
        total_rows += rows
        print(f"{name:<22} {rows:>12,}")

    print("-" * 36)
    print(f"{'TOTAL':<22} {total_rows:>12,}\n")

    print(f"SAC extracts -> {args.sac_dir}")
    print("(import-only tenant, so these are the source of truth there)")
    for name, frame in dataset.sac_tables().items():
        path = args.sac_dir / f"{name}.csv"
        rows = writer.write_csv(frame, path)
        size_mb = path.stat().st_size / 1e6
        print(f"  {name:<22} {rows:>10,} rows  {size_mb:6.1f} MB")

    if not args.no_samples:
        for name, frame in dataset.tables.items():
            writer.write_sample(
                frame, args.samples_dir / f"{name}.csv", args.sample_rows
            )
        print(f"\nSamples written to {args.samples_dir} ({args.sample_rows} rows each)")

    elapsed = time.perf_counter() - started
    print(f"\nBuilt in {build_seconds:.1f}s, written in {elapsed - build_seconds:.1f}s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
