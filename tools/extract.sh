#!/bin/bash
inputfile=$1;
CONTEXTS=("PSI" "PST" "PLY" "PWA" "PSU" "PCY" "HHO" "HTA" "HTM" "SKE");
for context in ${CONTEXTS[@]}
do
 echo "Processing ${context}...";
 outputfile=${inputfile}_${context}.log;
 cat ${inputfile} | grep ${context} > $outputfile
 filesize=$(stat -c%s "${outputfile}");
 if [ ${filesize} == 0 ]; then
   rm -f ${outputfile};
 fi
done
