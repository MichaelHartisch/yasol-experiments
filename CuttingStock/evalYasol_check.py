import os
import csv
import sys
import math
from pathlib import Path
import argparse
parser = argparse.ArgumentParser()

if len(sys.argv) != 3:
    raise ValueError('Usage: evalYasol_check.py folder/containing/logs timelimit')

#folder = sys.argv[1]
folder = Path(sys.argv[1])
folder_path= sys.argv[1]
timelimit=sys.argv[2]

if not folder.is_dir():
    parser.error(f"Folder does not exist: {folder}")

f = open(folder_path+"/evalSingle-stage.csv", 'w')
fT = open(folder_path+"/evalTwo-stage.csv", 'w')
writerSingle = csv.writer(f, delimiter = ";")
writerTwo = csv.writer(fT, delimiter = ";")

header = ['InstanceName', 'Solved', 'SolutionTime', 'SolutionValue']
writerSingle.writerow(header)
writerTwo.writerow(header)
FullData = list()
FullDataTwo = list()

for file in folder.iterdir():
    if not file.is_file() or not file.name.endswith("log"):
        continue
    text = file.read_text()
    #print(file.stem)
    solved = "Solution Status: OPTIMAL" in text
    unsat = "Solution Status: UNSAT" in text
    #print(solved or unsat)
    time = timelimit
    objective = -1
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("TIME:") and (solved or unsat):
            value = line.split(":", 1)[1].strip()
            #print(value)
            time = float(value)
        elif line.startswith("RESULT:"):
            value = line.split(":")[1].strip()
            objective = float(value)
    if unsat:
       objective=math.inf
    #print([Path(file.stem).stem, int(solved or unsat), time, objective])
    if file.name.endswith("RO_check.qlp.log"):
        FullDataTwo.append([Path(file.stem).stem.removesuffix("_RO_check"), int(solved or unsat), time, objective])
    else:
        FullData.append([Path(file.stem).stem.removesuffix("_check"), int(solved or unsat), time, objective])
def first(elem):
    return elem[0]
FullData.sort(key=first)
#print(FullData)
for line in FullData:
    writerSingle.writerow(line)
for line in FullDataTwo:
    writerTwo.writerow(line)
