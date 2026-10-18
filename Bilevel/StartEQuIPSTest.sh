#!/bin/bash
#./StartEQuIPSTest.sh Main 1800 $HOME/EQuIPS_updated/build/EQuIPS 

testname=$1
timelimit=$2
solver=$3
probability=$4
aux_file=$5
RANDOM=42

export TESTBENCH_DIR="$(pwd)"

for folder in $TESTBENCH_DIR/Instances/*/QLP_LA; do
    type_name=$(basename "$(dirname "$folder")")
#    echo $folder
#    echo $type_name
    LOG_DIR="${TESTBENCH_DIR}/Tests/$testname/EQuIPS/$type_name"
    mkdir -p $LOG_DIR

    for filename in $folder/*.qlp; do
        random=$RANDOM
        # Test instance with probability approximately p
        if awk -v r="$random" -v p="$probability" \
            'BEGIN { exit !(r < p * 32768) }'; then
            realname=${filename##*/}
            echo "$solver $filename $timelimit > ${LOG_DIR}/$realname.log 2>&1" >> $aux_file
        fi
    done
done
