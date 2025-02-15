#!/usr/bin/python3

"""
Follow a supplied temperature program,
logging process and reference temps all the way
"""

from __future__ import print_function

file_log = "/Applications/spectackler/2021217_t-cal.tsv"

import sys
import traceback
import time
import numpy as np
import pandas as pd
import neslabrte

class QTIProbe:
    "Class for QTI 6001 USB temperature probe"
    def __init__(self, port, baud=9600, timeout=1):
        """
        Open serial interface, return fault status.
        The serial handle becomes a public instance object.
        """
        import serial
        self.__ser__ = serial.Serial(port=port, baudrate=baud, timeout=timeout)
        self.__ser__.flush()
        # initialize
        self.__ser__.write(b'0')
        self.__ser__.flush()
        
    def temp_get(self):
        "Return current temperature."
        self.__ser__.write(b'2')
        self.__ser__.flush()
        return float(self.__ser__.readline().decode().strip())
        
if not sys.stdin.isatty():
    # if a state table is passed on sys.stdin, read it
    print("reading states from sys.stdin", file=sys.stderr)
    states = pd.read_csv(sys.stdin, sep='\t')
else:
    print("ERR: you need to pass the state table on sys.stdin!", file=sys.stderr)
    exit(1)

# open output file
with open(file_log, 'a+', buffering=1) as hand_log:

    # write header
    header = sorted(["clock", "watch", "temp_int", "temp_ext", "temp_ref"] + list(states.head()))
    hand_log.write('\t'.join(header) + '\n')
    
    # init water bath
    bath = neslabrte.NeslabController(port="/dev/cu.usbserial-FT4IVKAO1")
    nist = QTIProbe(port="/dev/cu.usbmodem141201") # using an Arduino today
        
    ## run experiment
    
    # start experiment timer (i.e. stopwatch)
    time_start = time.time()
    
    # start circulator
    #while not bath.on(): bath.on(1) # persistence problems
    bath.on(1)
    
    # switch to internal probe
    #while bath.probe_ext(): bath.probe_ext(1)
    
    # iterate over test states
    for state_num in range(states.shape[0]):
    
        # make dicts for this state, the last, and the next
        state_curr = states.iloc[state_num+0].to_dict()
        
        time_state = time.time()
        
        # set bath temperature persistently
        while not bath.temp_set(state_curr["temp_set"]): pass
        print("temp set to {} deg C".format(state_curr["temp_set"]), file=sys.stderr)
        
        # log data for the prescribed period
        while time.time() - time_state < state_curr["time"]:
            while True: # persistent polling
                try:
                    data = {
                        "clock": time.strftime("%Y%m%d %H%M%S"), 
                        "watch": time.time() - time_start, 
                        "temp_int": bath.temp_get_int(),
                        "temp_ext": bath.temp_get_ext(),
                        "temp_ref": nist.temp_get() # has 1 s latency but who cares
                    }
                    break
                except: pass
            data.update(state_curr) # add the command vars to the log
            hand_log.write('\t'.join([str(data[key]) for key in sorted(data.keys())]) + '\n')
            print("waiting {}/{} s".format(round(time.time()-time_state), data["time"]), file=sys.stderr, end='\r')
        
        print('', file=sys.stderr)
        
    # shut down hardware
    bath.on(0)