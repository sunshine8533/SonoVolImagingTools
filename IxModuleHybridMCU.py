# -*- coding: utf-8 -*-
'''

Jasper Dupuis 20170419

Wrap splash_qspigen and IxModuleMCU in to one class to allow external triggering while using
the qspigen toolset.

Scripts accessing iBMC monitors should still import splash_qspigen directly, as registerController
does not have access to the classes with those methods.

'''

from IxModuleMCU import MCU
from qspigen import registerController
import time

class HybridMCU():
    def __init__(self,autoConnect = True):
        self.mcu = MCU()
        self.arduino_connected = False
        if autoConnect:
            self.connect_arduino()
        self.reg = registerController()  #Not required as of 2060616
        
    def connect_arduino(self):
        self.arduino_connected = self.mcu.autoConnect()
        return self.arduino_connected
        
    def manualTrigger(self,identifier = 'arduino'):
        if identifier == 'arduino':
            r = self.mcu.manualTrigger()
        return r
        
    def setPPulse(self, k, identifier = 'arduino'):
        if identifier == 'qspi': 
            self.reg.setPPulse(k)
        elif identifier == 'arduino':
            self.mcu.setPPulse(k)
        else:
            print 'Wrong identifier given'
        return

    def setNPulse(self, k, identifier = 'arduino'):
        if identifier == 'qspi': 
            self.reg.setNPulse(k)
        elif identifier == 'arduino':
            self.mcu.setNPulse(k)
        else:
            print 'Wrong identifier given'
        return
        
    def setHiLo(self, k, identifier = 'arduino'):
        if identifier == 'qspi': 
            self.reg.setHiLo(k)
        elif identifier == 'arduino':
            self.mcu.setHiLo(k)
        else:
            print 'Wrong identifier given'
        return
        
    def setMinGain(self, k, identifier = 'arduino'):
        if identifier == 'qspi':
            self.reg.setMinGain(k)
        elif identifier == 'arduino':
            self.mcu.setMinGain(k)
        else:
            print 'Wrong identifier given'     
        return

    def setTgcSlope(self, k, identifier = 'arduino'):
        if identifier == 'qspi':
            self.reg.setTgcSlope(k)
        elif identifier == 'arduino':
            self.mcu.setTgcSlope(k)
        else:
            print 'Wrong identifier given'   
        return
        
    def close(self):
        self.mcu.close()
        
    def open(self):
        self.mcu.open()
        time.sleep(2.0)
