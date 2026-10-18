#!/bin/bash
#.\CreateMIPCheck.sh Main_RC
test=$1

mkdir -p Tests/$test/check
for filename in Tests/$test/instances/QLP/*.qlp; do
    #echo "Found " $filename
    realname=${filename##*/}
    #echo "RealName: " $realname
    outname="Tests/${test}/check/${realname%%.*}_check.qlp"
    #echo $outname
    python3 parser_writer_MIP.py Tests/$test $realname  $outname
done
