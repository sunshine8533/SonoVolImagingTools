# -*- coding: utf-8 -*-
release_version = ''

'''
Created on Thu Sep 29 14:35:48 2016

@author: Yaoyao Zhang
''' 

from DataProcess import *
from TestPreload import *
from FunctionGenerator import *
from DataObject import *
from IxModuleHybridMCU import HybridMCU
import numpy as np
import os
import sys

def collect_static_gain(sn, mcu):
    '''Ramps the MinGain and records the output signal at a fixed frequency.    
    CFG file loaded from <SN>_<Testname>.ini. If no such a file exists, <Testname>.ini will be copied to result path.
    '''

    testname    = 'STATIC_GAIN'
    operation   = 'Collect'
    print '*'*60+'\n'+ operation + ' ' + testname
    print 'SN: ' + sn
    
    #Setup and initialize path and cfg file
    cwd                 = os.getcwd()
    global_cfg          = config(cwd +'\\'+ 'GlobalSetting.ini')
    section             = 'GlobalSetting'
    data_savepath       = global_cfg.get_str(section, 'Data_SavePath')
    fg_addr             = global_cfg.get_str(section,'fg_addr')             
    
    datapath            = data_savepath + sn + '\\'
    datafile            = datapath + sn + '_' + testname + '.h5'    
    cfgfile_original    = cwd + '\\' + testname + '.ini'  
    cfgfile             = datapath + sn + '_' + testname + '.ini'

    res = init_datapath_cfg(datapath, cfgfile, cfgfile_original)
    if res[0]:
        cfg = res[1]
    else:
        print res[1]
        return False
        
    #Check if h5 file exists, prompt user if about to overwrite an existing file
    if os.path.isfile(datafile):
        if yesnobox('WARNING','h5 file already exists. Overwrite and continue?'):
           print('Overwriting results for %s\n' %(sn))# if user is OK with uncommited local changes, continue as normal
        else:
           return False#abort script if user does not want to proceed with uncommited local changes
        
    #Compare Gitinfo of current version info with saved one in cfg file. User alerted if mismatch detected.
    res = verify_version_info(cfg, operation, release_version)
    print res[1]
    if not res[0]:
        return False

    #Load Settings
    section         = 'CollectSetting'         
    channels        = cfg.get_list(section,'channels')
    MinGain_step    = cfg.get_int(section,'MinGain_step')        
    HiLo            = cfg.get_list(section,'HiLo')
    nsamples        = cfg.get_int(section,'nsamples')
    offset          = cfg.get_int(section,'offset')
    nrawsamples     = cfg.get_int(section,'nrawsamples')
    save_raw        = cfg.get_bool(section, 'save_raw')
    averaging       = cfg.get_int(section,'averaging')

    section         = 'GENSetting'
    freq            = cfg.get_float(section,'freq')
    delay           = cfg.get_float(section,'delay')        
    ncycles         = cfg.get_int(section,'ncycles')
    waveform        = cfg.get_str(section,'waveform')
    trigger_source  = cfg.get_str(section,'trigger_source')
    trigger_level   = cfg.get_float(section,'trigger_level')
    
    #Initialize devices
    try:
        dataObject = DataObj()
        dataObject.setMCU(mcu)   
    except Exception, e:
        print e.message
        return False 

    res = fGen(fg_addr)
    if res[0]:
        fg = res[1]
    else:
        print res[1]     
        return False
        
    #amp setpoints
    amp_setpoints   = []
    options         = cfg.get_items(section)
    for key in options.keys():
        if key[:6] == 'amp_sp':
            amp_setpoints.append(options[key])

    section         = 'MCUSetting'
    MCU_Pulse       = cfg.get_str(section,'MCU_Pulse')
    PPulse          = cfg.get_int(section,'PPulse')        
    NPulse          = cfg.get_int(section,'NPulse')    
    MCU_TgcSlope    = cfg.get_str(section,'MCU_TgcSlope')
    TgcSlope        = cfg.get_int(section,'TgcSlope')
    MCU_MinGain     = cfg.get_str(section,'MCU_MinGain')    
    MCU_HiLo        = cfg.get_str(section,'MCU_HiLo')
    
    #Intialize important arrays and virables  
    nchannels   = len(channels)
    nHiLos      = len(HiLo) 
    if MinGain_step > 0:
        MinGains    = np.arange(0, 256, MinGain_step)
    elif MinGain_step < 0:
        MinGains    = np.arange(255, -1, MinGain_step)[::-1]
    nMinGains   = MinGains.shape[0]

    amps        = np.zeros([nMinGains,nHiLos])
    for hilo_index, hilo in enumerate(HiLo):
        for sp in amp_setpoints:
            if sp[0] == hilo:
                amps[np.logical_and(MinGains >= sp[1], MinGains <= sp[2]), hilo_index] = sp[3]    
    eData       = np.zeros([nsamples,nchannels,nMinGains,nHiLos])
    rawData     = np.zeros([nrawsamples,nchannels,nMinGains,nHiLos])
    
    #Setup acquisition
    dataObject.setAverage(averaging)

    #Setup Function Generator    
    fg.en_Output(1,0)
    fg.set_Waveform(1,waveform)
    fg.en_Burst(1,1)
    fg.set_Trigger_Source(1,trigger_source)
    fg.set_Trigger_Level(1,trigger_level)
    fg.set_Frequency(1, freq)
    fg.set_Burst_Ncycles(1, ncycles)
    fg.set_Tdelay(1, delay)

    #Setup MCU
    mcu.setPPulse(PPulse, MCU_Pulse)
    mcu.setNPulse(NPulse, MCU_Pulse)
    mcu.setTgcSlope(TgcSlope, MCU_TgcSlope)  
    for i in range(5):   
        dataObject.collect(single = True, reset = False)
    if not res:
        print 'FX3 data trasfer failed' 
        return False
            
    #Confimation to start test
    msgbox(testname, 'Start %s\n- Turn off ''SCOPE''\n- Turn on ''GEN''\n- Turn off all 8 switches of SW1\n- Ensure "VSampling" KTX bitfile is uploaded\nClick OK to continue'%(operation + ' ' + testname))

    #Run test    
    fg.en_Output(1,1)           
    for channel_index, channel in enumerate(channels):
        print '\nCollecting on CH%d' %(channel)
        msgbox(testname, 'Switch channel selector to CH%s and click ok' % (channel))
        for hilo_index, hilo in enumerate(HiLo):
            mcu.setHiLo(hilo, MCU_HiLo)
            for mingain_index, mingain in enumerate(MinGains):
                print '.',
                mcu.setMinGain(mingain, MCU_MinGain)
                fg.set_Voltage(1, -amps[mingain_index, hilo_index]*10/2, amps[mingain_index, hilo_index]*10/2) #compensation for 20dB attenuator
                dataObject.collect(single = True, reset = True)
                rawData[:, channel_index, mingain_index, hilo_index] = dataObject.buffers[0, :]   
                dataObject.processData(offset)
                eData[:, channel_index, mingain_index, hilo_index] = dataObject.eData
    fg.en_Output(1,0)

    #Save to binary file
    print '\nSaving to file...'
    if save_raw:
        var_list = 'var_list,amps,MinGains,eData,rawData'.split(',')
        dumpdata(var_list, (var_list,amps,MinGains,eData,rawData),datafile)
    else:        
        var_list = 'var_list,amps,MinGains,eData'.split(',')
        dumpdata(var_list, (var_list,amps,MinGains,eData),datafile)
    
    #Finish test  
    fg.close_device()
    print operation + ' ' + testname + ' Finished\n'+'*'*60
    msgbox(testname, '%s finished' % (testname))   
    return True
   
if __name__ == '__main__':
    argvs = sys.argv    
    if len(argvs) == 1:
        sn = SN_Entry()
    else:
        sn = argvs[1]
    mcu = HybridMCU()
    if mcu.arduino_connected:
        try:
            collect_static_gain(sn, mcu)   
            mcu.close()
        except:
            mcu.close()
            raise
    else:
        msgbox('WARNING', 'Arduino connection failed.')
 


