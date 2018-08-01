# -*- coding: utf-8 -*-

'''
Created on Wed Jul 31 14:35:48 2018

@author: Yaoyao Zhang
''' 

from DataProcess import *
from DataObject import *
from IxModuleHybridMCU import HybridMCU
import numpy as np
import os

class ImagingObject(object):
    
    def __init__(self, MCU, project = 'test', path = '.\\DataSave', bufferCnt = 20, averaging = 1):

        self.mcu = MCU
        self.lineIndex = 0
        self.set_dataObj()
        self.set_project(project)
        self.set_savepath(path)        
        self.set_averaging(averaging)       
        self.set_buffer(bufferCnt)
            

    def set_dataObj(self):
        try:
            self.dataObject = DataObj()
            self.dataObject.setMCU(self.mcu)   
        except Exception, e:
            print e.message
        return
        
    def set_averaging(self, averaging):        
        self.dataObject.setAverage(averaging)

    def set_buffer(self, bufferCnt, sampleCount=4096):
        # Set up acquisition buffers
        self.bufferCnt = bufferCnt
        self.sampleCnt = sampleCount
        self.bufIndex = 0
        self.bufPerAcq = 1
        self.buffer = np.empty([self.bufferCnt, self.sampleCnt], dtype=numpy.uint32, order='C')
        
    def set_project(self, project):
        self.project = project
        return
        
    def set_savepath(self, path):
        self.savepath = path + '\\' + self.project + '\\'
        try:
            os.makedirs(self.savepath)
        except:
            pass
        return

    def set_ppulse(self, k, device = 'arduino'):
        self.mcu.setPPulse(k, device)
        return
        
    def set_npulse(self, k, device = 'arduino'):
        self.mcu.setNPulse(k, device)
        return
        
    def set_mingain(self, k, device = 'arduino'):
        self.mcu.setMinGain(k, device)
        return
        
    def set_timegain(self, k, device = 'arduino'):
        self.mcu.setTgcScope(k, device)
        return

    def set_hilo(self, k, device = 'arduino'):
        self.mcu.setHiLo(k, device)
        return        
        
    def save_buffer(self, data):
        if self.bufIndex < self.bufferCnt:
            self.buffer[:, self.bufIndex] = np.array(data)
            self.bufIndex += 1
        elif self.bufIndex == self.bufferCnt:
            self.buffer = np.roll(self.buffer, -1, axis = 1)
            self.buffer[:, self.bufIndex] = np.array(data)
        else:
            print 'Buffer Index can not be larger than BufferCnt'
        return

    def collect_line(self, n = 1):
        e = 5
        for line in range(n):
            fname = self.savepath.str(self.lineIndex).zfill(e) + '.txt'
            line_data = np.array(self.collect())
            self.save_data(line_data, fname)
            self.lineIndex += 1
            if self.lineIndex >= 10**e: 
                self.lineIndex = 0
        return        
        
    def collect(self):
        self.dataObject.collect(single = True, reset = True)
        data = self.dataObject.buffers[0, :]   
        self.save_buffer(data)
        return data
        
    def save_data(self, data, fname):
        np.savetxt(fname, data)
        return        

mcu = HybridMCU()
img = ImagingObject(mcu)
