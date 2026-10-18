#!/bin/bash
#./StartEQuIPSTest.sh Main Poly 1800 $HOME/EQuIPS/build/EQuIPS 
testname=$1
testtype=$2
timelimit=$3
solver=$4
probability=$5
graph_type=$6
aux_file=$7
RANDOM=42
export TESTBENCH_DIR="$(pwd)"

mkdir -p ${TESTBENCH_DIR}/Tests/$testname/EQuIPS_${testtype}/${graph_type}

for filename in $TESTBENCH_DIR/Instances/QIP_${testtype}/${graph_type}/*.qlp; do
    random=$RANDOM
    # Test instance with probability approximately p
    if awk -v r="$random" -v p="$probability" \
        'BEGIN { exit !(r < p * 32768) }'; then
        realname=${filename##*/}
        echo "$solver $filename $timelimit > ${TESTBENCH_DIR}/Tests/$testname/EQuIPS_$testtype/${graph_type}/$realname.log 2>&1" >> $aux_file
    fi
done
