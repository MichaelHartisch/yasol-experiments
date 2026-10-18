#!/usr/bin/env bash
set -euo pipefail

# collect_dr_results.sh
#
# Usage:
#   ./collect_dr_results.sh LOG_FOLDER [OUTPUT_CSV]
#
# Example:
#   ./collect_dr_results.sh logs dr_results.csv
#
# Expected log-file names:
#   binPacking_T_B_I_seed_DR_h.log
#
# Output columns:
#   instance,T,B,I,h,status,time_sec,obj,scenarios,iterations,final_bound
#
# Convention:
#   - For STATUS=TIMELIMIT, obj is left empty because the printed OBJ is not a
#     certified decision-rule objective. The final_bound column is filled from
#     the last "BOUND_MAIN:" line.
#   - For old logs without BOUND_MAIN, the script falls back to parsing the last
#     CPLEX progress-table Best Bound.
#   - For non-TIMELIMIT statuses, obj is taken from the final "OBJ:" line and
#     final_bound is left empty.

if [[ $# -lt 1 || $# -gt 2 ]]; then
    echo "Usage: $0 LOG_FOLDER [OUTPUT_CSV]" >&2
    exit 1
fi

LOG_DIR="$1"
OUT_CSV="${2:-dr_results.csv}"

if [[ ! -d "$LOG_DIR" ]]; then
    echo "Error: LOG_FOLDER does not exist or is not a directory: $LOG_DIR" >&2
    exit 1
fi

extract_last_colon_value() {
    local key="$1"
    local file="$2"

    awk -v key="$key" '
        $0 ~ "^" key ":" {
            val = $0
            sub("^" key ":[[:space:]]*", "", val)
            gsub(/\r/, "", val)
        }
        END {
            if (val != "") print val
        }
    ' "$file"
}

extract_last_bound_main() {
    local file="$1"

    awk '
        /^BOUND_MAIN:[[:space:]]*/ {
            val = $0
            sub(/^BOUND_MAIN:[[:space:]]*/, "", val)
            gsub(/\r/, "", val)
        }
        END {
            if (val != "") print val
        }
    ' "$file"
}

# Fallback for older logs that do not contain BOUND_MAIN.
# This tries to read the last CPLEX "Best Bound" value from the CPLEX node table.
extract_timelimit_bound_from_cplex_table() {
    local file="$1"

    awk '
        function isnum(x) {
            return x ~ /^[-+]?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$/
        }

        function isint(x) {
            return x ~ /^[-+]?[0-9]+$/
        }

        /Node[[:space:]]+Left[[:space:]]+Objective/ && /Best[[:space:]]+Bound/ {
            in_table = 1
            next
        }

        /Root node processing/ ||
        /Total \(root\+branch&cut\)/ ||
        /CPLEX solution status/ ||
        /ObjValue of Main/ ||
        /^BOUND_MAIN:/ ||
        /^Solve 12a/ ||
        /^Solve 12bs/ ||
        /^ABORT:/ {
            in_table = 0
        }

        in_table {
            if ($0 !~ /%/) next

            line = $0
            gsub(/\*/, " ", line)
            gsub(/\+/, "", line)
            gsub(/%/, "", line)

            n = split(line, a, /[[:space:]]+/)

            delete nums
            nnum = 0

            for (i = 1; i <= n; ++i) {
                if (isnum(a[i])) {
                    nums[++nnum] = a[i]
                }
            }

            if (nnum >= 5) {
                # Regular CPLEX rows usually end with:
                #   BestInteger BestBound ItCnt Gap
                # after numeric extraction:
                #   ... BestInteger BestBound ItCnt Gap
                # so BestBound is nums[nnum-2].
                #
                # Incumbent-only rows may omit ItCnt and end with:
                #   BestInteger BestBound Gap
                # so BestBound is nums[nnum-1].
                if (nnum >= 6 && isint(nums[nnum-1])) {
                    candidate = nums[nnum-2]
                } else {
                    candidate = nums[nnum-1]
                }

                if (isnum(candidate)) {
                    last_bound = candidate
                }
            }
        }

        END {
            if (last_bound != "") print last_bound
        }
    ' "$file"
}

{
    echo "instance;T;B;I;h;status;time_sec;obj;scenarios;iterations;final_bound"

    shopt -s nullglob

    for file in "$LOG_DIR"/binPacking_*_DR_*.log; do
        base="$(basename "$file")"
        if [[ ! "$base" =~ ^binPacking_([0-9]+)_([0-9]+)_([0-9]+)_([0-9]+)_DR_([0-9]+)_([0-9]+)\.log$ ]]; then
            echo "Warning: skipping file with unexpected name: $base" >&2
            continue
        fi

        T="${BASH_REMATCH[1]}"
        B="${BASH_REMATCH[2]}"
        I="${BASH_REMATCH[3]}"
        seed="${BASH_REMATCH[4]}"
        p="${BASH_REMATCH[5]}"
        h="${BASH_REMATCH[6]}"
        instance="binPacking_${T}_${B}_${I}_${seed}"

        status="$(extract_last_colon_value "STATUS" "$file" || true)"
        time_sec="$(extract_last_colon_value "TIME" "$file" || true)"
        logged_obj="$(extract_last_colon_value "OBJ" "$file" || true)"
        scenarios="$(extract_last_colon_value "SCENARIOS" "$file" || true)"
        iterations="$(extract_last_colon_value "ITERATIONS" "$file" || true)"

        if [[ -z "$status" ]]; then
            status="TIMELIMIT"
        fi

        obj="$logged_obj"
        final_bound=""

        if [[ "$status" == "TIMELIMIT" ]]; then
            # The printed OBJ is the last master objective, not a certified DR value.
            obj=""

            # Preferred parser for new logs.
            final_bound="$(extract_last_bound_main "$file" || true)"

            # Backward-compatible fallback for old logs.
            if [[ -z "$final_bound" ]]; then
                final_bound="$(extract_timelimit_bound_from_cplex_table "$file" || true)"
            fi

            if [[ -z "$final_bound" ]]; then
                echo "Warning: no BOUND_MAIN or CPLEX best bound found for timed-out log: $base" >&2
            fi
        fi

        printf '%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s\n' \
            "$instance" "$T" "$B" "$I" "$h" "$status" "$time_sec" \
            "$obj" "$scenarios" "$iterations" "$final_bound"
    done
} > "$OUT_CSV"

echo "Wrote $OUT_CSV"
