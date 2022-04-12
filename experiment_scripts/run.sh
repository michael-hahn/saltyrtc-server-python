#!/bin/bash

# Run the SaltyRTC server container
python run.py -s
# Wait for two seconds
sleep 2
# Monitor server CPU and memory usage
# Get server PID
pid=$(ps aux | grep "/usr/local/bin/saltyrtc-server" | grep -v grep | awk '{print $2}')
# Get top results every 0.1 seconds and parse the results in the format: TIME,PID,VIRT,RES,%CPU,%MEM
top -b -n 300 -d 0.1 -p "${pid}" | awk -v OFS=',' '$1=="top" { time=$3 } $1+0>0 { print time,$1,$5,$6,$9,$10; fflush(); }' >> cpumem.log &

# Run the clients
python run.py -n 0 -m 32
