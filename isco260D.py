#!/usr/bin/python3

"""
isco260D.py

driver module for controlling [Teledyne] ISCO 260D syringe pump(s)
v0.5 (c) JRW 2019 - jwinnikoff@mbari.org

GNU PUBLIC LICENSE DISCLAIMER:
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import serial
import threading
from time import sleep

def dasnet_checksum(cmd):
    "Calculate 2-digit hex checksum for a DASNET command."
    #print([ord(char) for char in list(cmd)])
    tot = sum([ord(char) for char in list(cmd)])
    return format(256 - tot%256, '02x').upper()

def str2dasnet(msg, source='', dest=''):
    "Convert serial command to DASNET frame."
    cmd = "{}R{}{}{}".format(dest, source, format(len(msg), '02x'), msg).upper()
    frame = "{}{}\r".format(cmd, dasnet_checksum(cmd))
    return frame.encode()
    
def dasnet2str(frame):
    "Convert incoming DASNET message to a Python string, or None if checkbytes invalid."
    # parse the frame
    # as of 20200619, ack, dest are thrown away
    frame = frame.decode().rstrip()
    ack = frame[0]
    dest = frame[1]
    len_msg = eval("0x{}".format(frame[2:4]))
    msg = frame[4:-2]
    checksum = frame[-2:]
    # check message integrity
    if (len_msg == len(msg)) and (checksum == dasnet_checksum(frame[:-2])):
        return msg
    else:
        return None

class ISCOController:
    def __init__(self, port, baud=9600, timeout=1, source=1, dest=1):
        """
        Open serial interface, set remote status and baudrate.
        The serial handle becomes a public instance object.
        """
        self.__ser__ = serial.Serial(port=port, baudrate=baud, timeout=timeout)
        self.lock = threading.RLock()
        self.__source__ = source
        self.__dest__ = dest
        self.remote()
        
    def disconnect(self):
        "Close serial interface."
        with self.lock:
            self.__ser__.close()
        
    def rcvd_ok(self):
        "Readline and if OK code comes in, return True; else, False."
        with self.lock:
            return self.__ser__.read_until(b'\r') == b'R 8E\r'
        
    def read_vals(self):
        "Readline and extract values from DASNET frame."
        with self.lock:
            # split individual messages
            msg = dasnet2str(self.__ser__.read_until(b'\r'))
            try: msg_list = msg.split(',')
            # if nothing comes in
            except: return None
            msg_pairs = [msg.split('=') for msg in msg_list]
            # strip whitespace
            msg_pairs = [[i.strip() for i in pair] for pair in msg_pairs]
            msg_dict = dict(msg_pairs)
            # try to convert values to floats
            for key, val in msg_dict.items():
                try:
                    msg_dict[key] = float(val)
                except ValueError:
                    pass
            return msg_dict
        
    #TEMP?
    def flush(self):
        with self.lock:
            self.__ser__.flush()
            return self.__ser__.read_until(b'\r')
        
    # action commands
    ## acknowledged over serial with b'R 8E\r'
        
    def remote(self):
        with self.lock:
            self.__ser__.write(str2dasnet("REMOTE", self.__source__, self.__dest__))
            return self.__ser__.read_until(b'\r')
        
    def local(self):
        with self.lock:
            self.__ser__.write(str2dasnet("LOCAL", self.__source__, self.__dest__))
            return self.__ser__.read_until(b'\r')
            
    def disconnect(self):
        with self.lock:
            self.local()
            self.__ser__.close()
        
    def run(self):
        with self.lock:
            self.__ser__.write(str2dasnet("RUN", self.__source__, self.__dest__))
            return self.rcvd_ok()
        
    def stop(self):
        with self.lock:
            self.__ser__.write(str2dasnet("STOPALL", self.__source__, self.__dest__))
            return self.rcvd_ok()
        
    def clear(self):
        with self.lock:
            self.__ser__.write(str2dasnet("CLEAR", self.__source__, self.__dest__))
            return self.rcvd_ok()
        
    def digital(self, pins=[], bits=[]):
        "Get/set digital outputs"
        with self.lock:
            # robust to set single or multiple pins
            if type(pins) != list: pins = [pins]
            if type(bits) != list: bits = [bits]
            self.__ser__.write(str2dasnet("DIGITAL", self.__source__, self.__dest__))
            status = [True if x == 'L' else False for x in self.read_vals()["DIGITAL"]]
            if bits == []:
                if len(pins) == 1:
                    return status[pins[0]]
                else:
                    return [status[p] for p in pins]
            else:
                for pin, bit in zip(pins, bits):
                    status[pin] = bit
                sendcode = ''.join(['L' if x else 'H' for x in status])
                self.__ser__.write(str2dasnet("DIGITAL={}".format(sendcode), self.__source__, self.__dest__))
                return self.rcvd_ok()
    
    # Mode setters don't yet work 20200619
    def mode(self, mode, pump='A'):
        "Set operating mode"
        shortcuts = {
            "const_press"   :    'P',
            "const_flow"    :    'F',
            "refill"        :    'R',
            "press_grad"    :    'PG',
            "flow_grad"     :    'F1',
        }
        if mode in (list(shortcuts.values()) + list(shortcuts.keys())):
            self.__ser__.write(str2dasnet("INDEPENDENT".format(pump, mode)))
            print(self.__ser__.read_until(b'\r'))
            self.__ser__.write(str2dasnet("INDEPENDENTCD".format(pump, mode)))
            print(self.__ser__.read_until(b'\r'))
            try:
                mode = shortcuts[mode]
            except KeyError:
                pass
        self.__ser__.write(str2dasnet("MODE {} {}".format(pump, mode)))
        return self.__ser__.read_until(b'\r')
        
    def mode_const_press(self, pump='A'):
        with self.lock:
            if pump == 'A': pump = '' # an idiosyncrasy in the protocol
            self.__ser__.write(str2dasnet("CONST PRESS{}".format(pump)))
            return self.__ser__.read_until(b'\r')
            
    def mode_const_flow(self, pump='A'):
        with self.lock:
            if pump == 'A': pump = '' # an idiosyncrasy in the protocol
            self.__ser__.write(str2dasnet("CONST FLOW{}".format(pump)))
            return self.__ser__.read_until(b'\r')
            
    def mode_prgm_grad(self, pump='A'):
        with self.lock:
            if pump == 'A': pump = '' # an idiosyncrasy in the protocol
            self.__ser__.write(str2dasnet("PRGM_GRAD{}".format(pump)))
            return self.__ser__.read_until(b'\r')
        
    def zero(self, pump='A'):
        "Zero the pressure sensor."
        with self.lock:
            self.__ser__.write(str2dasnet("ZERO{}".format(pump), self.__source__, self.__dest__))
            return self.__ser__.read_until(b'\r')
        
    # register setters/getters
    ## these are for static values that are changeable only by user command
    ## i.e. not dynamic measured values
    
    def maxflow(self, flowrate=None, pump='A', setpt=True, limit=True):
        """
        Set/get max flowrates for constant pressure (limit) or flow (setpt) mode.
        Sets and gets in tandem by default, use boolean flags to do one or the other.
        """
        with self.lock:
            ret = {}
            if flowrate is None:
                if setpt:
                    self.__ser__.write(str2dasnet("MAXFLOW{}".format(pump), self.__source__, self.__dest__))
                    ret["setpt"] = dasnet2str(self.__ser__.read_until(b'\r'))
                if limit:
                    if pump == 'A': pump = ''
                    self.__ser__.write(str2dasnet("LIMITS{}".format(pump), self.__source__, self.__dest__))
                    ret["limit"] = dasnet2str(self.__ser__.read_until(b'\r'))
            else:
                if setpt:
                    self.__ser__.write(str2dasnet("MAXFLOW{}={}".format(pump, flowrate), self.__source__, self.__dest__))
                    ret["setpt"] = self.rcvd_ok()
                if limit:
                    self.__ser__.write(str2dasnet("MFLOW{}={}".format(pump, flowrate), self.__source__, self.__dest__))
                    ret["limit"] = self.rcvd_ok()
            return ret
            
    def minflow(self, flowrate=None, pump='A'):
        "Setter if flowrate is specified; otherwise return max flow."
        with self.lock:
            if flowrate is None:
                self.__ser__.write(str2dasnet("MINFLOW{}".format(pump), self.__source__, self.__dest__))
                return self.read_vals().values()[0]
            else:
                self.__ser__.write(str2dasnet("MINFLOW{}={}".format(pump, flowrate), self.__source__, self.__dest__))
                return self.rcvd_ok()
            
    def maxpress(self, pressure=None, pump='A'):
        "Setter if flowrate is specified; otherwise return max flow."
        with self.lock:
            if pressure is None:
                self.__ser__.write(str2dasnet("MAXPRESS{}".format(pump), self.__source__, self.__dest__))
                return self.read_vals().values()[0]
            else:
                self.__ser__.write(str2dasnet("MAXPRESS{}={}".format(pump, pressure), self.__source__, self.__dest__))
                return self.rcvd_ok()
            
    def minpress(self, pressure=None, pump='A'):
        "Setter if flowrate is specified; otherwise return max flow."
        with self.lock:
            if pressure is None:
                self.__ser__.write(str2dasnet("MINPRESS{}".format(pump), self.__source__, self.__dest__))
                return self.read_vals().values()[0]
            else:
                self.__ser__.write(str2dasnet("MINPRESS{}={}".format(pump, pressure), self.__source__, self.__dest__))
                return self.rcvd_ok()
            
    def press_set(self, pressure=None, pump='A'):
        """
        Set constant pressure setpoint if specified, else return existing setpoint.
        """
        with self.lock:
            if pressure is None:
                # return the current setpoint
                self.__ser__.write(str2dasnet("SETPRESS{}".format(pump), self.__source__, self.__dest__))
                return self.read_vals()["PRESS{}".format(pump)]
            else:
                # change the setpoint
                if pump == 'A': pump = '' # an idiosyncrasy in the protocol
                self.__ser__.write(str2dasnet("PRESS{}={}".format(pump, pressure), self.__source__, self.__dest__))
                return self.rcvd_ok()
            
    def integral_enable(self, pump='A'):
        "Enable integral pressure control."
        with self.lock:
            self.__ser__.write(str2dasnet("IPUMP{}=1".format(pump), self.__source__, self.__dest__))
            return self.__ser__.read_until(b'\r')
        
    def integral_disable(self, pump='A'):
        "Disable integral pressure control."
        with self.lock:
            self.__ser__.write(str2dasnet("IPUMP{}=0".format(pump), self.__source__, self.__dest__))
            return self.__ser__.read_until(b'\r')
        
    def units(self, unit="PSI"):
        "Set pressure unit for all pumps."
        with self.lock:
            # case-insensitive
            self.__ser__.write(str2dasnet("UNITSA={}".format(unit.upper()), self.__source__, self.__dest__))
            return self.read_vals()["UNITSA"]
    
    ## gradient programming
    
        
    # data requests
    ## for data measured in real time
        
    def gg(self):
        with self.lock:
            self.__ser__.write(str2dasnet("G&", self.__source__, self.__dest__))
            return self.__ser__.read_until(b'\r')
            
    def identify(self):
        with self.lock:
            self.__ser__.write(str2dasnet("IDENTIFY", self.__source__, self.__dest__))
            return self.__ser__.read_until(b'\r')
        
    def status(self, pump='A'):
        "Get operational status and problems."
        with self.lock:
            self.__ser__.write(str2dasnet("STATUS{}".format(pump), self.__source__, self.__dest__))
            return self.read_vals()
        
    def press_get(self, pump='A'):
        "Get actual pressure of pump."
        with self.lock:
            self.__ser__.write(str2dasnet("PRESS{}".format(pump), self.__source__, self.__dest__))
            # what should the default value be? The previous value?
            return self.read_vals().get("PRESS{}".format(pump))
        
    def flow_get(self, pump='A'):
        "Get actual flowrate of pump."
        with self.lock:
            self.__ser__.write(str2dasnet("FLOW{}".format(pump), self.__source__, self.__dest__))
            return self.read_vals()["FLOW{}".format(pump)]
        
    def vol_get(self, pump='A'):
        "Get volume remaining in cylinder."
        with self.lock:
            self.__ser__.write(str2dasnet("VOL{}".format(pump), self.__source__, self.__dest__))
            try:
                return self.read_vals()["VOL{}".format(pump)]
            except:
                #e.g. if the pump is busy
                return False
        
    # higher-level routines
    ## employ methods above
    
    def pause(self, pump='A'):
        "Stop pump without changing constant pressure setpoint."
        with self.lock:
            setpt_press = self.press_set(pump=pump)
            return all((self.clear(), self.press_set(pressure=setpt_press, pump=pump)))
    
    def tune_maxflow(self, pump='A'):
        """
        Measure the maximum flowrate that can be maintained without
        building residual pressure in the pump cylinder.
        """
        
        return 0
        
    #TEMPORARY
    def const_press_alarm(self, press_set, max_leak_rate):
        "Bring pump to constant pressure, then alarm and stop if flowrate exceeds threshold."
        
        if self.press_set(pressure=press_set):
            self.run()
            press_curr = self.press_get()
            while press_curr < press_set:
                press_curr = self.press_get()
                print(press_curr)
            sleep(10)
            flow_curr = self.flow_get()
            while flow_curr <= max_leak_rate:
                flow_curr = self.flow_get()
                print(flow_curr)
            self.clear()
            return("LEAK!")
        else:
            return(1)
        