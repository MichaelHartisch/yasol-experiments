import os
import csv
import math
import sys
import re

from pathlib import Path
from typing import Optional

NUM = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"

RE_DATA_FILE = re.compile(r"Alps0030I Data file:\s*(\S+)")
RE_WALL_TIME = re.compile(r"Alps0278I Search wall-clock time:\s*(%s)\s*seconds" % NUM)
RE_CPU_TIME = re.compile(r"Alps0274I Search CPU time:\s*(%s)\s*seconds" % NUM)
RE_BEST_QUALITY = re.compile(r"Alps0260I Best solution found had quality\s+(%s)" % NUM)
RE_COST = re.compile(r"^Cost\s*=\s*(%s)\s*$" % NUM, re.MULTILINE)
RE_REL_GAP = re.compile(r"Blis0058I Relative optimality gap is\s*(%s)\s*%%" % NUM)

# Progress-table line:
# Nodes Done   Upper Bound   Lower Bound      Gap   Time Nodes Left
#      82133          2270          2270    0.00%    330      16594
RE_PROGRESS = re.compile(
    r"^\s*(\d+)\s+(%s)\s+(%s)\s+(%s)%%?\s+(%s)\s+(\d+)\s*$" % (NUM, NUM, NUM, NUM),
    re.MULTILINE,
)
import math
from typing import Optional

def fmt(x: Optional[float]) -> str:
    """Format numeric values compactly for CSV."""
    if x is None:
        return ""

    try:
        x = float(x)
    except (ValueError, TypeError):
        return ""

    if math.isnan(x):
        return ""

    if not math.isfinite(x):
        return str(x)

    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))

    return f"{x:.10g}"


def first_float(regex: re.Pattern[str], text: str) -> Optional[float]:
    m = regex.search(text)
    return float(m.group(1)) if m else None

def parse_log(path: Path, timelimit: Optional[float]) -> dict[str, str]:
    text = path.read_text(errors="replace")

    if "Alps0208I Search completed" in text or "Optimal solution:" in text:
        status = "1"
    elif "Alps0230I Reached time limit" in text:
        status = "0"
    elif "infeasible" in text.lower():
        status = "1"
    elif timelimit is not None:
        # Fallback only: useful for truncated logs or logs without explicit final status.
        wall = first_float(RE_WALL_TIME, text)
        if wall is not None and wall >= 1.001 * timelimit:
            status = "0"
        else:
            status = "0"
    else:
        status = "0"

    wall_time = first_float(RE_WALL_TIME, text)
    if wall_time is None:
        wall_time = first_float(RE_CPU_TIME, text)
    if wall_time is None and timelimit is not None and status == "0":
        wall_time = timelimit

    # Solution: prefer Cost line in the final solution block, otherwise ALPS best-quality line.
    cost_matches = RE_COST.findall(text)
    solution = float(cost_matches[-1]) if cost_matches else first_float(RE_BEST_QUALITY, text)

    gap = first_float(RE_REL_GAP, text)

    progress_rows = RE_PROGRESS.findall(text)
    last_lb = None
    last_gap = None
    if progress_rows:
        # Groups: nodes, upper, lower, gap, time, nodes_left
        last_lb = float(progress_rows[-1][2])
        last_gap = float(progress_rows[-1][3])

    if gap is None:
        gap = last_gap

    # Bound: for optimal, bound = solution. For non-optimal, the printed final
    # relative gap can be newer than the last progress-table lower bound; when
    # available, reconstruct the bound from solution and gap using MibS/ALPS's
    # table convention: gap = (upper - lower) / |lower| * 100.
    bound = None
    if solution is not None and gap is not None:
        if abs(gap) < 1e-12:
            bound = solution
        elif last_lb is not None:
            # Use the last table bound as default; if the final Blis0058 gap differs
            # from the last printed table gap, reconstruct a more up-to-date bound.
            if last_gap is not None and abs(gap - last_gap) > 1e-6:
                bound = solution / (1.0 + gap / 100.0)
            else:
                bound = last_lb
        else:
            bound = solution / (1.0 + gap / 100.0)
    elif last_lb is not None:
        bound = last_lb

    return {
        "Status": status,
        "Time": fmt(wall_time),
        "Solution": fmt(solution),
        "Bound": fmt(bound),
        "Gap": fmt(gap),
    }

if len(sys.argv) != 3:
    raise ValueError('Usage: evalMibS.py testname timelimit')

testname = sys.argv[1]
timelimit = sys.argv[2]

folder = Path("Tests/"+testname)

if not folder.is_dir():
    parser.error(f"Folder does not exist: {folder}")

path = Path("Tests/"+testname+"/MibS/")
path_eval = "Tests/"+testname+"/eval/"

print("Checking MibS results in",path)

for item in path.iterdir():
    if not item.is_dir():
        continue
    #print(item.name)
    f = open(path_eval+"MibS_"+item.name+".csv", 'w')

    writer = csv.writer(f, delimiter = ";")
    header = ['InstanceName', 'Solved', 'SolutionTime', 'SolutionValue']
    writer.writerow(header)

    FullData = list()
    for file in item.iterdir():
        if not file.is_file():
            continue
        result=parse_log(file, timelimit)
        FullData.append([Path(file.stem).stem, result["Status"], result["Time"], result["Solution"]])
    def first(elem):
        return elem[0]
    FullData.sort(key=first)
    #print(FullData)
    for line in FullData:
        writer.writerow(line)
