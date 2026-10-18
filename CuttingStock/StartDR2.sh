#!/bin/bash
#./StartDR2.sh 1800 1 1
timelimit=$1
p=$2
history=$3

export TESTBENCH_DIR="$(pwd)"
export LOG_DIR=Tests/DR_${p}_${history}
mkdir -p $LOG_DIR

pfile="ParallelRunsDR_${p}_${history}.txt"
for filename in ${TESTBENCH_DIR}/instances/data/*.raw; do
     realname=${filename##*/}
     realname=${realname::-4}
     echo "./build/RunDecisionRule $filename $p $history $LOG_DIR/${realname} $timelimit > $LOG_DIR/${realname}_DR_${p}_${history}.log 2>&1 && rm $LOG_DIR/${realname}*.lp"  >> $pfile
done
