import os
import csv
import sys
from pathlib import Path

if len(sys.argv) != 4:
    raise ValueError('Usage: evalYasol.py testname test_type timelimit')

testname = sys.argv[1]
testtype = sys.argv[2]
timelimit = sys.argv[3]
folder = Path("Tests/"+testname)

if not folder.is_dir():
    parser.error(f"Folder does not exist: {folder}")

path_m = Path("Tests/"+testname+"/Yasol_"+testtype)
path_eval = "Tests/"+testname+"/eval/"

print("Checking Yasol results in ",path_m)
for item in path_m.iterdir():
    if not item.is_dir():
        continue
    #print(item.name)
    f = open(path_eval+"Yasol_"+testtype+"_"+item.name+".csv", 'w')

    writer = csv.writer(f, delimiter = ";")
    header = ['InstanceName', 'Solved', 'SolutionTime', 'SolutionValue']
    writer.writerow(header)

    FullData = list()
    for file in item.iterdir():
        if not file.is_file():
            continue
        text = file.read_text()
        #print(file.stem)
#            print(text)
        solved = "Solution Status: OPTIMAL" in text
        time = timelimit
        objective = -1
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("TIME:") and solved:
                value = line.split(":", 1)[1].strip()
               # print(value)
                time = float(value)

            elif line.startswith("RESULT:"):
                value = line.split(":")[1].strip()
                objective = float(value)
       # print([Path(file.stem).stem, int(solved), time, objective])
        FullData.append([Path(file.stem).stem.removesuffix("_new"), int(solved), time, objective])

    def first(elem):
        return elem[0]
    FullData.sort(key=first)
    #print(FullData)
    for line in FullData:
        writer.writerow(line)

  
