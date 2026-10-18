#!/usr/bin/env bash

# Path to converter executable
CONVERTER=$1

# Recursively find all .mps files
find . -type f -name "*.mps" | while read -r mpsfile; do

    # Remove .mps extension
    base="${mpsfile%.mps}"

    auxfile="${base}.aux"
    qlpfile="${base}.qlp"

    # Check whether matching .aux file exists
    if [[ -f "$auxfile" ]]; then
        echo "Converting:"
        echo "  MPS : $mpsfile"
        echo "  AUX : $auxfile"
        echo "  QLP : $qlpfile"

        "$CONVERTER" "$mpsfile" "$auxfile" "../QLP_FA/$qlpfile"

        if [[ $? -eq 0 ]]; then
            echo "  -> Success"
        else
            echo "  -> Failed"
        fi

        echo
    else
        echo "Skipping $mpsfile (missing $auxfile)"
        echo
    fi

done
