"""
Ground truth regression check: does the committed ground truth still hold?

context/ground_truth/ claims its figures are "derived from the generated data,
not hand-authored" and that regenerating with the pinned seed reproduces them
exactly. Nothing enforced that claim until this script.

The gap it closes is specific and nasty. The weekly parity check compares
generators/measures.py against the warehouse -- but both sides come from the
same shorelane version, so if a generator change perturbs the RNG they drift
*together* and parity still passes. It agrees with itself while every figure in
context/ground_truth/, every eval rubric, and every published number silently
becomes wrong.

This is the only check that pins the numbers to what was actually committed.

    python tests/check_ground_truth.py

Exits non-zero on any mismatch. Run it in CI on every PR.
"""
from __future__ import annotations

import pathlib
import re
import sys

from generators import orders
from generators.measures import five_revenues

REPO = pathlib.Path(__file__).resolve().parent.parent
GROUND_TRUTH = REPO / "context" / "ground_truth" / "revenue_q1_2024.md"

PERIOD = ("2024-01-01", "2024-03-31")  # fully elapsed; matches the ground truth doc
TOLERANCE = 0.005  # to the cent, same bar as parity/check_parity.py

# Table label in the markdown -> measure key from five_revenues().
ROW_LABELS = {
    "gmv": "gmv",
    "net revenue": "net_revenue",
    "recognized revenue": "recognized_revenue",
    "billed revenue": "billed_revenue",
    "collected cash": "collected_cash",
}


def parse_committed() -> dict[str, float]:
    """Pull the five figures out of the markdown table.

    Rows look like:  | GMV | 1,359,503.83 | Marketing / Exec |
    with the canonical row bolded: | **Recognized revenue** | **1,428,393.18** | ...
    """
    text = GROUND_TRUTH.read_text()
    found: dict[str, float] = {}

    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue

        label = cells[0].replace("*", "").strip().lower()
        key = ROW_LABELS.get(label)
        if key is None:
            continue

        amount = cells[1].replace("*", "").replace(",", "").replace("$", "").strip()
        if re.fullmatch(r"-?\d+(\.\d+)?", amount):
            found[key] = float(amount)

    missing = set(ROW_LABELS.values()) - set(found)
    if missing:
        raise SystemExit(
            f"Could not parse {sorted(missing)} from {GROUND_TRUTH.name}. "
            "Has the table format changed?"
        )
    return found


def main() -> int:
    committed = parse_committed()
    derived = five_revenues(orders.generate(), *PERIOD)

    try:
        source = GROUND_TRUTH.relative_to(REPO)
    except ValueError:  # pointed elsewhere, e.g. by a test
        source = GROUND_TRUTH
    print(f"Ground truth check, {PERIOD[0]} .. {PERIOD[1]}")
    print(f"  source: {source}\n")

    failed = False
    for key in ["gmv", "net_revenue", "recognized_revenue", "billed_revenue", "collected_cash"]:
        want, got = committed[key], derived[key]
        ok = abs(want - got) < TOLERANCE
        failed |= not ok
        status = "OK" if ok else f"MISMATCH (diff {got - want:+,.2f})"
        print(f"  {key:<20} committed={want:>15,.2f}  derived={got:>15,.2f}  {status}")

    if failed:
        print(
            "\nGround truth no longer matches the generators.\n"
            "Something perturbed the RNG. Per CLAUDE.md this is a BREAKING change:\n"
            "  1. confirm the change was intended\n"
            "  2. bump DATASET_VERSION in config.py\n"
            "  3. re-derive every file in context/ground_truth/ in the same commit\n"
            "Do NOT simply paste the new numbers in -- that hides whatever moved."
        )
        return 1

    # The planted trap is the reason the fixture exists; assert it explicitly so
    # a change that quietly defuses it cannot pass as green.
    if not derived["recognized_revenue"] > derived["gmv"]:
        print(
            f"\nThe signature trap is GONE: recognized_revenue "
            f"({derived['recognized_revenue']:,.2f}) is no longer > gmv "
            f"({derived['gmv']:,.2f}). The eval is meaningless without it."
        )
        return 1

    print("\nground truth holds; signature trap intact (recognized > gmv)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
