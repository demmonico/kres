#!/usr/bin/env bash
#-----------------------------------------------------------#
# This is a script aimed in help to analyze time series logs from kres tool to calculate statistics over time
# Check README.md for usage examples
#
# FORMAT: ./kres-stat.sh [ARGS|FLAGS]
#
# @author: https://github.com/demmonico
# @package: https://github.com/demmonico/kres
#
#-----------------------------------------------------------#

_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
LOG_DIR="${1:-"${_DIR}/logs"}"
LOG_FILENAME_MASK="${2:-"*.log"}"
TMP_RAW_DATA_FILE="${LOG_DIR}/kres-log-raw-data.tmp"
TMP_SORTED_DATA_FILE="${LOG_DIR}/kres-log-sorted-data.tmp"

function min() {
  cat ${TMP_SORTED_DATA_FILE} | awk 'BEGIN{a=1000000}{if ($1<0+a) a=$1} END{print a}'
}
function avg() {
  cat ${TMP_SORTED_DATA_FILE} | awk '{ sum += $1; n++ } END { if (n > 0) print sum / n; }'
}
function stdev() {
  cat ${TMP_SORTED_DATA_FILE} | awk '{sum+=$1; sumsq+=$1*$1}END{print sqrt(sumsq/NR - (sum/NR)**2)}'
}
function max() {
  cat ${TMP_SORTED_DATA_FILE} | awk 'BEGIN{a=-1000000}{if ($1>0+a) a=$1} END{print a}'
}
function p50() {
  cat ${TMP_SORTED_DATA_FILE} | awk ' { a[i++]=$1; } END { x=int((i+1)/2); if (x < (i+1)/2) print (a[x-1]+a[x])/2; else print a[x-1]; }'
}
function p95() {
  cat ${TMP_SORTED_DATA_FILE} | awk '{all[NR] = $0} END{print all[int(NR*0.95 - 0.5)]}'
}



for file in "${LOG_DIR}"/${LOG_FILENAME_MASK}; do
  date
  echo "$file"
  echo "Data samples $( cat $file | wc -l )"

  echo "Metric / min / avg / stdev / max / p50 / p95"
  for source in CPU_U/A,2,1 CPU_R/A,2,2 CPU_RU/U,3,1 RAM_U/A,4,1 RAM_R/A,4,2 RAM_RU/U,5,1; do
    params=($(echo $source | tr ',' ' '));
    title=${params[0]};
    res=${params[1]};
    col=${params[2]};

    cat $file | cut -d "|" -f $res | cut -d ":" -f 2 | cut -d "/" -f $col | cut -d "%" -f 1 | awk '{$1=$1};1' > ${TMP_RAW_DATA_FILE}
    cat ${TMP_RAW_DATA_FILE} | sort -n > ${TMP_SORTED_DATA_FILE}

    echo "$title $(min) $(avg) $(stdev) $(max) $(p50) $(p95)"

    rm ${TMP_RAW_DATA_FILE} ${TMP_SORTED_DATA_FILE}
  done

  echo ''
done
