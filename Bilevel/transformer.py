#!/usr/bin/env python3
"""Transform one QLP file, writing to an explicitly specified destination."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Sequence

HEADERS = [
    "MINIMIZE", "MAXIMIZE", "SUBJECT TO", "UNCERTAINTY SUBJECT TO",
    "BOUNDS", "BINARIES", "EXISTS", "ALL", "ORDER", "END",
]
HEADER_SET = set(HEADERS)


def normalized_header(line: str) -> str | None:
    stripped = line.strip().upper()
    return stripped if stripped in HEADER_SET else None


def split_into_sections(lines: Sequence[str]) -> Dict[str, List[str]]:
    sections: Dict[str, List[str]] = {}
    current: str | None = None
    for line in lines:
        header = normalized_header(line)
        if header is not None:
            if header in sections:
                raise ValueError(f"Duplicate section header: {header}")
            sections[header] = []
            current = header
        else:
            if current is None:
                if line.strip():
                    raise ValueError("Found content before first QLP section header")
                continue
            sections[current].append(line)

    required = [
        "SUBJECT TO", "UNCERTAINTY SUBJECT TO", "BOUNDS", "BINARIES",
        "EXISTS", "ALL", "ORDER", "END",
    ]
    missing = [section for section in required if section not in sections]
    if missing:
        raise ValueError(f"Missing required section(s): {', '.join(missing)}")
    if "MINIMIZE" not in sections and "MAXIMIZE" not in sections:
        raise ValueError("Missing objective sense: expected MINIMIZE or MAXIMIZE")
    return sections


def cleaned_entries(lines: Sequence[str]) -> List[str]:
    return [line.strip() for line in lines if line.strip()]


def with_dummy_first(entries: Sequence[str]) -> List[str]:
    return ["dummy"] + [entry for entry in entries if entry != "dummy"]


def transform_text(text: str) -> str:
    lines = text.splitlines(keepends=True)
    sections = split_into_sections(lines)

    objective_section = "MINIMIZE" if "MINIMIZE" in sections else "MAXIMIZE"
    objective_lines = sections[objective_section]
    old_subject = sections["SUBJECT TO"]
    old_uncertainty = sections["UNCERTAINTY SUBJECT TO"]
    old_bounds = cleaned_entries(sections["BOUNDS"])
    old_binaries = cleaned_entries(sections["BINARIES"])
    old_exists = cleaned_entries(sections["EXISTS"])
    old_all = cleaned_entries(sections["ALL"])
    old_order = cleaned_entries(sections["ORDER"])

    # Define the swapped variable groups before applying the original fallbacks.
    new_exists_vars = [var for var in old_all if var.startswith(("a_", "x_"))]
    new_all_vars = [var for var in old_exists if var.startswith("y_")]
    if not new_exists_vars:
        new_exists_vars = old_all
    if not new_all_vars:
        new_all_vars = old_exists

    out: List[str] = []
    out.append("MAXIMIZE\n")
    out.extend(objective_lines)
    out.append("SUBJECT TO\n")
    out.extend(old_uncertainty)
    out.append("UNCERTAINTY SUBJECT TO\n")
    out.extend(old_subject)
    out.append("BOUNDS\n")
    for entry in with_dummy_first(old_bounds):
        out.append("0 <= dummy <= 1\n" if entry == "dummy" else f"{entry}\n")
    out.append("BINARIES\n")
    for entry in with_dummy_first(old_binaries):
        out.append(f"{entry}\n")
    out.append("EXISTS\n")
    for entry in with_dummy_first(new_exists_vars):
        out.append(f"{entry}\n")
    out.append("ALL\n")
    for entry in new_all_vars:
        out.append(f"{entry}\n")
    out.append("ORDER\n")
    for entry in with_dummy_first(old_order):
        out.append(f"{entry}\n")
    out.append("END\n")
    return "".join(out)


def transform_file(source: Path, destination: Path, overwrite: bool = False) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Input file does not exist: {source}")
    if source.resolve() == destination.resolve():
        raise ValueError("Input and output paths must be different")
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {destination}. Use --overwrite to replace it.")
    transformed = transform_text(source.read_text(encoding="utf-8"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(transformed, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Transform one QLP instance into a specified destination file.")
    parser.add_argument("source", type=Path, help="Path to original .qlp instance")
    parser.add_argument("destination", type=Path, help="Path to transformed .qlp file")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing destination file")
    args = parser.parse_args()
    transform_file(args.source.expanduser(), args.destination.expanduser(), args.overwrite)
#    print(f"Created: {args.destination}")


if __name__ == "__main__":
    main()
