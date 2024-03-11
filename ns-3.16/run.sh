#!/bin/bash
export NS_LOG='QbbNetDevice=level_all|prefix_func|prefix_time:GENERIC_SIMULATION=level_all|prefix_func|prefix_time:BEgressQueue=level_all|prefix_func|prefix_time'
export LD_LIBRARY_PATH='/home/projects/ns-allinone-3.16/ns-3.16/build'
export CXXFLAGS='-std=c++11'
./waf
echo '------Running------'
/home/projects/ns-allinone-3.16/ns-3.16/build/scratch/dcqcn > ../../dcqcn-output/log.out 2>&1
echo 'Finished.'
