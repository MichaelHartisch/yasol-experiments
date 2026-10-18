#!/bin/bash
#./CreateROCheck.sh Main_RO
test=$1

mkdir Tests/$test/check
for filename in Tests/$test/instances/RO/*.qlp; do
#    echo "Found " $filename
    realname=${filename##*/}
#    echo "RealName: " $realname
    outname="Tests/${test}/check/${realname%%.*}_check.qlp"
#    echo $outname
    solname="${filename}.sol"
#    echo $solname
    instname=${filename/"_RO"/""}
    instname=${instname/"RO"/"QLP"}
#    echo $instname
    if [[ -f $solname ]];then
        python3 parser_writer_RO.py $solname $outname $instname
    fi
done
