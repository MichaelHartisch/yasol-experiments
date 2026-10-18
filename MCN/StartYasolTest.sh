#!/bin/bash
#./StartYasolTest.sh Main Poly 1800 Yasol/build/yasol "--isSimplyRestricted=1" 1 tree
#./StartYasolTest.sh Main DD 1800 Yasol/build/yasol "--isSimplyRestricted=1" 1 rndgraph

testname=$1
testtype=$2
timelimit=$3
solver=$4
options=("$5")
probability=$6
graph_type=$7
aux_file=$8
RANDOM=42
export TESTBENCH_DIR="$(pwd)"
mkdir -p Tests/$testname/Yasol_${testtype}/${graph_type}

#        echo "Solver path is: " $solver
#        echo "Which model: " $testtype
#        echo "timelimit for instances is: " $timelimit
#        echo "Additional solver options are: " $options
#        echo "ratio of considered instances is: " $probability
#	echo "Write starter filer for instances on graphs of type" $graph_type
#echo "auxfile is ${aux_file}"
for filename in $TESTBENCH_DIR/Instances/QIP_${testtype}/${graph_type}/*.qlp; do
    random=$RANDOM
    # Test instance with probability approximately p
    if awk -v r="$random" -v p="$probability" \
        'BEGIN { exit !(r < p * 32768) }'; then
        realname=${filename##*/}
        echo "$solver $filename --timeLimit=$timelimit "$options" > ${TESTBENCH_DIR}/Tests/$testname/Yasol_$testtype/${graph_type}/$realname.log 2>&1" >> ${aux_file}
    fi
done
