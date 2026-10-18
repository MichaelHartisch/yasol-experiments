import os
import csv
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise ValueError('Usage: evalEQuIPS.py testname timelimit')

testname = sys.argv[1]
timelimit = sys.argv[2]

folder = Path("Tests/"+testname)

if not folder.is_dir():
    parser.error(f"Folder does not exist: {folder}")

path = Path("Tests/"+testname+"/EQuIPS/")
path_eval = "Tests/"+testname+"/eval/"

print("Checking EQUIPS results in",path)

for item in path.iterdir():
    if not item.is_dir():
        continue
    #print(item.name)
    f = open(path_eval+"EQuIPS_"+item.name+".csv", 'w')

    writer = csv.writer(f, delimiter = ";")
    header = ['InstanceName', 'Solved', 'SolutionTime', 'SolutionValue']
    writer.writerow(header)

    FullData = list()
    for file in item.iterdir():
        if not file.is_file():
            continue
        text = file.read_text()
#   print(file.stem)
#   print(text)
        solved = "Status: OPTIMAL" in text
#   print(solved)
        time = timelimit
        objective = -1

        for line in text.splitlines():
            line = line.strip()
            if line.startswith("Time:"):
                value = line.split(":", 1)[1].strip()
            #print(value)
                if value != "Limit":
                    time = float(value.replace("seconds", "").strip())
            elif line.startswith("Objective:"):
                value = line.split(":", 1)[1].strip()
                objective = float(value)
    #print([Path(file.stem).stem, int(solved), time, objective])
        FullData.append([Path(file.stem).stem, int(solved), time, objective])
    def first(elem):
        return elem[0]
    FullData.sort(key=first)
    #print(FullData)
    for line in FullData:
        writer.writerow(line)
