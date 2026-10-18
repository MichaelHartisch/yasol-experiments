#!/bin/bash
#./StartYasol_ROCheck.sh Main_RO 1800 /home/hartisch/Yasol_4.6.1_Udev_fixed/build/yasol
testname=$1
timelimit=$2
solver=$3
export FOLDER=check
export TESTBENCH_DIR="$(pwd)"
export LOG_DIR=Tests/$testname/$FOLDER
mkdir -p $LOG_DIR

pfile="ParallelRuns${FOLDER}_${testname}.txt"
for filename in ${LOG_DIR}/*.qlp; do
    realname=${filename##*/}
    echo "$solver $filename --timeLimit=$timelimit > ${TESTBENCH_DIR}/${LOG_DIR}/$realname.log 2>&1" >> $pfile
done
