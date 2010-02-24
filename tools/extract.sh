#!/bin/bash
inputfile=$1;
CONTEXTS=("PSI" "PST" "PLY" "PWA" "PSU" "PCY" "HHO" "HTA" "HTM" "SKE");
for context in ${CONTEXTS[@]}
do
 echo "Processing ${context}...";
 outputfile=${context};
 cat ${inputfile} | grep ${context} > $outputfile
 filesize=$(stat -c%s "${outputfile}");
 if [ ${filesize} == 0 ]; then
   rm -f ${outputfile};
 else 
  sed '1,100d' ${outputfile} > temp; sed -n -e :a -e '1,100!{P;N;D;};N;ba' temp > $outputfile;rm temp;
 fi
done
