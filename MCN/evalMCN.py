import ast
import os
import csv
import sys
from pathlib import Path


def parse_log(log_file,limit):
    instance_name = log_file.name.removesuffix(".log")

    # Default values: timelimit reached / no solution
    solved = 0
    solution_time = limit
    solution_value = ""

    with open(log_file, "r") as f:
        lines = f.readlines()

    # Find the last non-empty line
    last_line = next(
        (line.strip() for line in reversed(lines) if line.strip()),
        ""
    )

    # Check whether solver returned a result
    if last_line.startswith("("):
        try:
            # Parse Python tuple
            result = ast.literal_eval(last_line)

            # Original return structure:
            # Z, Y_opt, X_opt, an_opt, opt, status, stats
            Z, Y_opt, X_opt, an_opt, opt, status, stats = result

            # Extract relevant information
            solution_value = opt
            solution_time = float(stats["totTm"])
            solved = 1

        except (ValueError, SyntaxError, TypeError,
                KeyError, IndexError) as e:
            print(f"Warning: Could not parse {log_file}: {e}",
                  file=sys.stderr)

    return [instance_name, solved, solution_time, solution_value]

if len(sys.argv) != 4:
    raise ValueError('Usage: evalMCN.py testname graph_type')

testname = sys.argv[1]
graph_type = sys.argv[2]
timelimit = sys.argv[3]

folder = Path("Tests/"+testname)

if not folder.is_dir():
    parser.error(f"Folder does not exist: {folder}")

path = Path("Tests/"+testname+"/MCN/"+graph_type)
path_eval = "Tests/"+testname+"/eval/"
print("Checking MCN results in",path)

f = open(path_eval+"MCN_"+graph_type+".csv", 'w')
writer = csv.writer(f, delimiter = ";")
header = ['InstanceName', 'Solved', 'SolutionTime', 'SolutionValue']
writer.writerow(header)
FullData = list()
for file in path.iterdir():
    if not file.is_file():
        continue
    result = parse_log(file,timelimit)
    SolutionFound=0
    #print(result)
    FullData.append([file.stem, result[1], result[2], result[3]])

def first(elem):
    return elem[0]
FullData.sort(key=first)
for line in FullData:
    writer.writerow(line)
