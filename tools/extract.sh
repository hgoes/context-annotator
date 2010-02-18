#!/bin/bash
inputfile=$1;
CONTEXTS=("PSI" "PST" "PLY" "PWA" "PSU" "PCY" "HHO" "HTA" "HTM" "SKE");
for context in ${CONTEXTS[@]}
do
 echo "Processing ${context}...";
 cat ${inputfile} | grep ${context} > ${inputfile}_${context}.log;
done
