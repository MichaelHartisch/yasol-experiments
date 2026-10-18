testname=$1
testtype=$2
timelimit=$3
solver=$4
options=("$5")
probability=$6
aux_file=$7
RANDOM=42

export TESTBENCH_DIR="$(pwd)"

for folder in $TESTBENCH_DIR/Instances/*/QLP_${testtype}; do
#Bilevel/Instances/bcpins/QLP_FA/
    options_true=$options
    type_name=$(basename "$(dirname "$folder")")
    if [[ "$testtype" == "FA" ]]; then
        case "$type_name" in
            inter-fire|inter-assig|clique|plusbcpins)
                options_true=""
                ;;
        esac
    fi
#    echo $folder
#    echo $type_name
    LOG_DIR="${TESTBENCH_DIR}/Tests/$testname/Yasol_${testtype}/$type_name"
#    echo $LOG_DIR
    mkdir -p $LOG_DIR

    for filename in $folder/*.qlp; do
        random=$RANDOM
        # Test instance with probability approximately p
        if awk -v r="$random" -v p="$probability" \
            'BEGIN { exit !(r < p * 32768) }'; then
            realname=${filename##*/}
            echo "$solver $filename --timeLimit=$timelimit "$options_true" > ${LOG_DIR}/$realname.log 2>&1" >> $aux_file
        fi
    done
done
