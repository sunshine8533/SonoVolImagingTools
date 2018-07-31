'''
Communication with iBMC on standalone mode imaging board through QSPI by calling qspigen.exe.
Author: Yaoyao Zhang
Edited for QSPI 1.7 by JD week of 2017.04.10

qspigen.exe
Version 1.5
Usage examples:
RDSR command example
qspigen -w 0xFB -wc 0x1C -rc 4 -v

READ command example - Read 32 bytes starting at address 0x0000
qspigen -w 0xFB -wc 0xDC 0x00 0x00 0x00 0x20 -rc 0x20 -v


WRITE command example - Write 4 bytes starting at address 0x0020
qspigen -w 0xFB -wc 0x5C 0x00 0x20 0x00 0x04 0x01 0x02 0x03 0x04 -v

List available FTDI devices.
qspigen -l


Options:
-h, -?   Display this help menu.
-l       List the available FTDI devices.
-d <dev num>
         Specify the FTDI device number. Only needed if multiple FTDI
         devices with description 'FT4222' are available. Use -l option
         to see the list of available devices.
-w <byte0> <byte1> ...
         Write the bytes given using the four data lines. The data is defined
         by byte0, byte1 and so on.
-wc <byte0> <byte1> ...
         Write the bytes given using the four data lines and include the bytes
         in the crc-32 calculation.  The data is defined by byte0, byte1 and
         so on.
-r <num bytes>
         Read the number of bytes specified using the four data lines.
-rc <num bytes>
         Read the number of bytes specified using the four data lines and
         calculate the crc-32. An additional 4 bytes will be read which are
         the crc bytes. The calculated crc will be checked against the crc
         read and an error notification will be displayed if they do not match.
-v
     Verbose option. Display complete transaction details.

Version 1.5

## Read/Write re-written for QSPIGEN 1.7 10.4.2017 by JD



read:
        qspigen -w 0xfb -wc 0xdc [addr_start_byte1] [addr_start_byte2] [nbytes_byte1] [nbytes_byte2] -rc [nbytes]
write:
        qspigen -w 0xfb -wc 0x5c [addr_start_byte1] [addr_start_byte2] [nbytes_byte1] [nbytes_byte2] [data_byte1] [data_byte2] ... [data_byten]
        '''
        

import subprocess
import re
import numpy as np #for module testing only
from TestPreload import *

def read_bytes(addr_start, nbytes, qspi):
    try:
        c, r = qspi.read_registers(addr_start, nbytes)
        byte = []
        res = r.replace('\n', '')
        res = re.search(r'Read:.*',res).group(0)
        res= res.split('\r')
        for line in res[1:]:
            line = line.replace(' ', '')[4:]
            for i in range(0, len(line),2):
                byte.append(line[i:i+2])
        return (True, byte, c, r)
    except:
        return (False, None, c, r)
      
def bytes2num(byte):
    b = ''
    for i in byte[::-1]: b += i
    num = int(b, 16)
    return num
  
class qspigen(object):
    def __init__(self, parent = None):
        self.dev_num = 0
        self.app = 'qspigen.exe' 
        assert_exist(self.app)
        self.option = {'help':'-h',
                       'listDevice':'-l',
                       'selectDevice':'-d',
                       'write':'-w',
                       'write_CRC':'-wc',
                       'read':'-r',
                       'read_CRC':'-rc',
                       'verbose':'-v'}
        self.command = {'RDSR':0x1c,    #Read Status Register
                        'WRCR':0x3c,    #Write Control Register
                        'READ':0xdc,    #Read Data Bytes
                        'WRITE':0x5c,   #Write Data Bytes
                        'UNLOCK':0xfb}  #Unlock Opcode

    def _num2byte(self, num):
        if num > 0xffff or num <0:
            print 'Address out of range!'
            return None
        h = '%04x' %(num)
        byte1, byte2 = int(h[:2],16), int(h[2:],16)
        return byte1, byte2
                        
    def _exec(self, *args):
        command = []
        command.append(self.app)
#        command.append(self.option['selectDevice'])
#        command.append(hex(0x00))
        for arg in args:
            command.append(arg)
        output = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()[0]        
        command_line = ' '.join(command)
        return command_line, output                   
                        
    def list_devices(self):
        cmd, ret = self._exec(self.option['listDevice'])
        return cmd, ret
        
    def help_menu(self):
        cmd, ret = self._exec(self.option['help'])
        return cmd, ret
        
    def read_registers(self, addr_start, nbytes):
        addr_start_byte1, addr_start_byte2 = self._num2byte(addr_start)
        nbytes_byte1, nbytes_byte2 = self._num2byte(nbytes)
        cmd, ret = self._exec(self.option['write'], hex(self.command['UNLOCK']), self.option['write_CRC'], hex(self.command['READ']), \
                   hex(addr_start_byte1), hex(addr_start_byte2), hex(nbytes_byte1), hex(nbytes_byte2), self.option['read'], hex(nbytes))
        return cmd, ret
    
    def write_registers(self, addr_start, nbytes, byte):
        addr_start_byte1, addr_start_byte2 = self._num2byte(addr_start)
        nbytes_byte1, nbytes_byte2 = self._num2byte(nbytes)
        exps = [self.option['write'], hex(self.command['UNLOCK']), self.option['write_CRC'], hex(self.command['WRITE']), \
              hex(addr_start_byte1), hex(addr_start_byte2), hex(nbytes_byte1), hex(nbytes_byte2)]
        for data_byte in byte:
            exps.append(hex(data_byte))
        exps.append(self.option['verbose'])
        cmd, ret = self._exec(*exps)
        return cmd, ret            
 

'''
Registers that need to be manipulated for manufacturing testing:
TGC == 0x0070 (high byte)
STATIC GAIN == 0x0070 (low byte)
HV == 0x0060 (single byte)
HILO == 0x0140 (10th byte, 0 = LO, 1 = HI)
HILO will be hard coded to put it in the 1st byte rather than implement all registers having target bytes to write to.
iBMC automatically propagates written values throughout the 16byte address space, but HILO register is not exclusively HILO
'''

#names
control_register = {0:'TGC',
                  1:'STATIC',
                  2:'HV',
                  3:'HILO'}    
#
control_register_addr = {0:112,
                1:112,
                2:96,
                3:320}                

#write this so that registerController can replace wholesale the mcu class used in scripts now.
class registerController(object):
    def __init__(self, ntrials = 10):
        self.qspi = qspigen()
        self.ntrials = ntrials
        self.HiLoByte = 1 #1st byte is 0x00 for LO, 0x10 for HI, also the number of bytes to be written IN DECIMAL (0x04).
      
    def setHiLo(self,value):  
        #change HILO register value        
        data=[256,256] 
        if (value == 1):
            value = 16
        for i in range(self.ntrials):
            self.qspi.write_registers(control_register_addr[3],4,[value,0,0,0])
            #retrieve the newly written register
            c,r =self.qspi.read_registers(control_register_addr[3],16)
            #verify the new value in register matches what was written
            data = self.convertReadData(r)     
            if data[0] == value:
                return True
        print 'setHiLo timeout in %d trials' %(self.ntrials)
        return False                    
                

    def setTgcSlope(self,value):        
        #change TGC only
        #retrieve STATIC Value then write the two bytes
        tgc=256     
        mingain = self.getMinGain()
        for i in range(self.ntrials):   
            self.qspi.write_registers(control_register_addr[0],2,[value,mingain])        
            tgc = self.getTgcSlope()
            if tgc == value:
                return True
        print 'setTgcSlope timeout in %d trials' %(self.ntrials)
        return False   
            
    def setMinGain(self,value): #MinGain = STATIC gain
        #Change STATIC only
        mingain=256
        tgc = self.getTgcSlope()
        for i in range(self.ntrials):   
            c, r = self.qspi.write_registers(control_register_addr[0],2,[tgc,value])              
            mingain = self.getMinGain()
            if (mingain == value):              
                return True
        print 'setMinGain timeout in %d trials' %(self.ntrials)
        return False  
    
    def setPPulse(self,value):
        #change HV+ amplitude
        ppulse=256     
        npulse = self.getNPulse()    
        for i in range(self.ntrials):       
            self.qspi.write_registers(control_register_addr[2],2,[value,npulse])        
            ppulse = self.getPPulse() 
            if (ppulse == value):  
                return True
        print 'setPPulse timeout in %d trials' %(self.ntrials)
        return False  
        
    def setNPulse(self,value):
        #change HV- amplitude
        npulse=256        
        ppulse = self.getPPulse()        
        for i in range(self.ntrials):        
            self.qspi.write_registers(control_register_addr[2],2,[ppulse,value])        
            npulse = self.getNPulse() 
            if (npulse == value):               
                return True
        print 'setPPulse timeout in %d trials' %(self.ntrials)
        return False  

    def getMinGain(self):  
        data=[256, 256]
        for i in range(self.ntrials):         
            c,r = self.qspi.read_registers(control_register_addr[1],16)             
            data = self.convertReadData(r)
            if (data[1]!=256):
                return data[1]
        print 'getMinGain timeout in %d trials' %(self.ntrials)
        return data[1]
    
    def getTgcSlope(self):       
        data=[256, 256]  
        for i in range(self.ntrials): 
            c,r = self.qspi.read_registers(control_register_addr[0],16)             
            data = self.convertReadData(r)
            if (data[0]!=256):
                return data[0]
        print 'getTgcSlope timeout in %d trials' %(self.ntrials)
        return data[0]
    
    def getPPulse(self):
        data=[256, 256]             
        for i in range(self.ntrials): 
            c,r = self.qspi.read_registers(control_register_addr[2],16)             
            data = self.convertReadData(r)
            if (data[0]!=256):
                return data[0]
        print 'getPPulse timeout in %d trials' %(self.ntrials)
        return data[0]
                
    def getNPulse(self):
        data=[256, 256]              
        for i in range(self.ntrials): 
            c,r = self.qspi.read_registers(control_register_addr[2],16)            
            data = self.convertReadData(r)
            if (data[1]!=256):
                return data[1]
        print 'getNPulse timeout in %d trials' %(self.ntrials)
        return data[0]
    
    #gets the returned hex byte array as a python list of integers [01, 02, 03, ... , n]            
    def convertReadData(self,r):       
        try:
            data = []
            dataIn = re.split(r'Read:',r.replace('\r','').replace(' ','')) #splits in to two-entry list    
            dataIn = re.split(r'\n',dataIn[1]) #each return line (0x0000 01 02 03 04 05 06 07 08) now its own entry
            dataIn = filter(None,dataIn) #removes the null entries
            charactersPerByte=2
            for dataLine in dataIn:
                byteStringArray = [dataLine[i*2-4:i*2-4+charactersPerByte] for i in range (4,len(dataLine))] # returns each of the 8 bytes in line in csv string list
                byteStringArray = filter(None,byteStringArray)
                for byte in byteStringArray:
                    data.append(int(byte,16)) #append integer value to data to be returned
                if len(byteStringArray) < 8:
                    return data         ## prevents null data from entering returned array
            return data
        except:
            data=[256,256,256,256,256,256,256,256,256,256,256,256,256,256,256,256] #this returned list indicates error to the calling getter functions.
            return data

        
'''
There are four Power monitors IN230. 
Register address: 
INA_13V_BASE_ADDR       0020:002F
INA_7V_BASE_ADDR        0030:003F
INA_3V6_BASE_ADDR       0040:004F
INA_1V5_BASE_ADDR       0050:005F
'''   
pwr_monitor_names = ['12p6V',
            '5p5V',
            '3p5V',
            '1p5V']
 
pwr_monitor_addr = [[0x20,0x2f],
            [0x30,0x3f],
            [0x40,0x4f],
            [0x50,0x5f]]
               
class INA(object):
    def __init__(self, name, addr, parent = None):
        self.qspi = qspigen()
        self.name = name
        self.address = np.arange(addr[0], addr[1]+1)
        self.nbytes = self.address.shape[0]

        self.shruntR = 0.01  #Shunt Resistor (Ohm)
        self.svbase = 2.5e-6 #Base of shunt voltage (V)
        self.shuntVoltage = 0
        self.bvbase = 1.25e-3 #Base of bus voltage (V)
        self.busVoltage = 0.
        self.cbase = 0.
        self.current = 0.
        self.power = 0.
        self.cal = 0.

    
    def refresh(self, ntrials = 10):  
        for i in range(ntrials):
            (flag, byte, c, r) = read_bytes(self.address[0], self.nbytes, self.qspi)
            if flag:
                self.busVoltage = bytes2num(byte[4:6])*self.bvbase
                self.shuntVoltage = bytes2num(byte[2:4])*self.svbase
                self.cal = bytes2num(byte[10:12])
                self.cbase = 5.12e-3/self.shruntR/self.cal
                self.current = bytes2num(byte[8:10])*self.cbase
                self.power = self.current*self.busVoltage
                return flag, c, r
            else:
                pass
        print 'No Valid Data Read in %s trials: %s' %(ntrials, r)
        return False, c, r


def init_pwr_monitors(INA_names, INA_addr):
    print 'Initiatializing Power Monitors'
    pwr_monitors = []
    for i, name in enumerate(INA_names):
        pwr_monitors.append(INA(name, INA_addr[i]))
    return pwr_monitors
        
'''
There are 8 temperature sensors T30TS. 
Register address: 
T30TS_TRI0_BASE_ADDR       00E0:00FF
    LNA_CH1                    00E0:00E7
    LNA_CH5-6                  00E8:00EF
    5V_REG                     00F0:00F7 
T30TS_TRI1_BASE_ADDR       0100:011F
    DIG_REG                    0100:0107
    KTX                        0108:010F
    USB3                       0110:0117
T30TS_AUX1_BASE_ADDR       0120:012F
    AUX1                       0120:0127
T30TS_AUX2_BASE_ADDR       0130:013F
    AUX2                       0130:0137
'''   
temp_adc_addr       = [0xe0, 0x10f]
temp_channel_names  = ['2p5V_AUX',
                       '1p8V_AUX',
                       '1p0V_DIG',
                       '2p1V_AFE',
                       'p48V_HV',
                       '5p0V_AFE',
                       'CH-6_AMP',
                       'CH-1_AMP']


class temp_adc(object):
    def __init__(self, addr, channel_names, parent = None):        
        print 'Initiatializing Temperature ADC'
        self.qspi = qspigen()
        self.address = np.arange(addr[0], addr[1]+1)
        self.nbytes = self.address.shape[0]
        self.Vref = 3.3
        self.lsb = self.Vref/4096
        self.channel_names = channel_names
        self.channels = self.init_channels(self.channel_names)
        self.nchannels = len(self.channels)
        self.channel_temps = np.zeros([3, self.nchannels])

    def init_channels(self, channel_names):
        channels = []
        for index, name in enumerate(channel_names):
            channels.append(temp_channel(name, index))
        return channels

    def _bytes2vol(self, byte):
        num = bytes2num(byte)
        v = num * self.lsb
        return v       
        
    def refresh(self, ntrials = 10):  
        for i in range(ntrials):
            (flag, byte, c, r) = read_bytes(self.address[0], self.nbytes, self.qspi)
            if flag:
                for i, ch in enumerate(self.channels):
                    v1 = self._bytes2vol(byte[2*i:2*(i+1)])
                    v2 = self._bytes2vol(byte[16+2*i:16+2*(i+1)])
                    v3 = self._bytes2vol(byte[32+2*i:32+2*(i+1)])
                    vols = [v1, v2, v3]
                    temps = ch.set_values(vols)
                    self.channel_temps[:,i] = np.array(temps)                    
                return flag, c, r
            else:
                pass
        print 'No Valid Data Read in %s trials: %s' %(ntrials, r)
        return flag, c, r

class temp_channel(object):
    def __init__(self, name, index):        
        self.name = name
        self.index = index
        self.v_in = 3.3
        self.r0 = 10e3
        self.t_nom = 25.
        self.r_nom = 10e3        
        self.b = 3434.
        self.temp = 0.
        self.temp_limit_max = 0.
        self.temp_limit_min = 0.
        
    def _vol2res(self, v):
        r = v*self.r0/(self.v_in-v)
        return r        
            
    def _res2temp(self, r):
        T0 = 273.15 + self.t_nom
        r0 = self.r_nom
        a = (np.log(r0)-np.log(r))/self.b
        T = 1./(1./T0-a)
        t = T - 273.15
        return t
        
    def set_values(self, vols):
        temps = []        
        for vol in vols:
            r = self._vol2res(vol)
            t = self._res2temp(r)
            temps.append(t)
        self.temp, self.temp_limit_max, self.temp_limit_min = temps
        return temps        

vol_adc_addr        = [0x110, 0x13f]
vol_channel_names   = ['1p2V_AUX',
                       '2p5V_DIG',
                       '1p8V_DIG',
                       '1p0V_DIG',
                       '12V_IMG',
                       '5p0V_IMG',
                       '1p8V_IMG_R',
                       '1p8V_IMG_L']
vol_channel_gains           = [1,
                       4.02/(1.+4.02),
                       1,
                       1,
                       2./(2.+10.),
                       4.32/(4.32+6.49),
                       1,
                       1]
                       
class vol_adc(object):
    def __init__(self, addr, channel_names, vol_channel_gains, parent = None):        
        print 'Initiatializing Voltage ADC'
        self.qspi = qspigen()
        self.address = np.arange(addr[0], addr[1]+1)
        self.nbytes = self.address.shape[0]
        self.Vref = 2.5
        self.lsb = self.Vref/4096
        self.channel_names = channel_names
        self.vol_channel_gains = vol_channel_gains
        self.nchannels = len(self.channel_names)
        self.channel_vols = np.zeros([3, self.nchannels])
        self.channel_vol_gains = vol_channel_gains

    def _bytes2vol(self, byte):
        num = bytes2num(byte)
        v = num * self.lsb
        return v       
        
    def refresh(self, ntrials = 10):  
        for i in range(ntrials):
            (flag, byte, c, r) = read_bytes(self.address[0], self.nbytes, self.qspi)
            if flag:
                for i in range(self.nchannels):
                    v1 = self._bytes2vol(byte[2*i:2*(i+1)])/self.channel_vol_gains[i]
                    v2 = self._bytes2vol(byte[16+2*i:16+2*(i+1)])/self.channel_vol_gains[i]
                    v3 = self._bytes2vol(byte[32+2*i:32+2*(i+1)])/self.channel_vol_gains[i]
                    vols = [v1, v2, v3]
                    self.channel_vols[:,i] = np.array(vols)                    
                return flag, c, r
            else:
                pass
        print 'No Valid Data Read in %s trials: %s' %(ntrials, r)
        return flag, c, r

'''
Test outcome writes to eeprom.
There is a requirement to write board information (Part Number, Revision, Serial Number) to a on-board EEPROM during Beta 2 manufacturing test.
There is also a requiement write some test information, such as test date and test outcome(s).  
 
Register address: 
PN_REV_ADDR             0200:020B
SN_ADDR                 0210:021F
TestDate_ADDR           0220:022F
TestOutcome_ADDR        0230:023F
'''   
 
pn_rev_addr             = [0x0200, 0x020B]
sn_addr                 = [0x020C, 0x021B]
TestDate_addr           = [0x0220, 0x0221]
TestOutcome_addr        = [0x0222, 0x0223]

class MFG_eeprom(object):
    def __init__(self, pn_rev_addr, sn_addr, TestDate_addr,  TestOutcome_addr, parent = None): 
        self.qspi = qspigen()
        self.pn_rev_addr = pn_rev_addr
        self.sn_addr = sn_addr
        self.TestDate_addr = TestDate_addr
        self.TestOutcome_addr = TestOutcome_addr
    
    def write_PN_REV(self, pn, rev):
        '''PN and REV must be string type'''
        nbytes = self.pn_rev_addr[1]-self.pn_rev_addr[0]+1        
        byte = [0] *nbytes  
        
        if len(pn) != nbytes-5:
            print 'Wrong PN string length'
            return

        if len(rev) == 1:
            rev += ' '
        elif len(rev) ==2:
            pass
        else:
            print 'Wrong REV string length'
            return
            
        head = '000'      
        string = head + pn + rev
        for i, value in enumerate(string):
            byte[i] = ord(value)
                       
        self.qspi.write_registers(self.pn_rev_addr[0], nbytes, byte)
        
    def write_SN(self, sn):        
        nbytes = self.sn_addr[1]-self.sn_addr[0]+1
        byte = [0] *nbytes

        if len(sn) != nbytes-3:
            print 'Wrong SN string length'
            return

        head = '000'
        string = head + sn            
        for i, value in enumerate(string):
            byte[i] = ord(value)
        self.qspi.write_registers(self.sn_addr[0], nbytes, byte) 
    
    def write_TestDate(self, week, year):        
        nbytes = self.TestDate_addr[1]-self.TestDate_addr[0]+1
        byte = [0] *nbytes
        byte[0] = int(week)
        byte[1] = int(year)
        self.qspi.write_registers(self.TestDate_addr[0], nbytes, byte) 
            
    def write_TestOutcome(self, outcome_bits):
        nbytes = self.TestOutcome_addr[1]-self.TestOutcome_addr[0]+1
        byte = [255]*nbytes
        if len(outcome_bits) == 16:
            byte[0] = int(outcome_bits[8:],2)
            byte[1] = int(outcome_bits[:8],2)
        else:
            print 'Wrong Outcome bits length'
            return
        self.qspi.write_registers(self.TestOutcome_addr[0], nbytes, byte)
            
    def read_PN_REV(self):
        (flag, byte, c, r) = read_bytes(self.pn_rev_addr[0], 16, self.qspi)
        if flag:
            byte_raw = byte[:12]
            string = ''            
            for b in byte_raw:
                string += chr(int(b, 16))
            head = string [:3]
            pn = string[3:10]
            rev = string[10:12]       
            if rev[1] == ' ':
                rev = rev[:-1]
        return head, pn, rev
                
    def read_SN(self):
        (flag, byte, c, r) = read_bytes(self.sn_addr[0], 16, self.qspi)
        if flag:
            string = ''
            for b in byte:
                string += chr(int(b, 16))
            head = string[:3]            
            sn = string[3:16]
            return head, sn
            
    def read_TestDate(self):
        (flag, byte, c, r) = read_bytes(self.TestDate_addr[0], 16, self.qspi)
        if flag:
            TestDate_byte = byte[0:2]
            week = int(TestDate_byte[0], 16)
            year = int(TestDate_byte[1], 16)
        return week, year

    def read_TestOutcome(self):
        (flag, byte, c, r) = read_bytes(self.TestOutcome_addr[0], 16, self.qspi)
        if flag:
            TestOutcome_byte = byte[0:2]
            outcome_bits = '{0:08b}'.format(int(TestOutcome_byte[1], 16))+'{0:08b}'.format(int(TestOutcome_byte[0], 16))
        return outcome_bits
        
if __name__ == '__main__':
    q = qspigen()
    reg = registerController()
    pwr_monitors = init_pwr_monitors(pwr_monitor_names, pwr_monitor_addr)
    for m in pwr_monitors:
        print m.refresh()
    temp_adc = temp_adc(temp_adc_addr, temp_channel_names)
    print temp_adc.refresh()
    vol_adc = vol_adc(vol_adc_addr, vol_channel_names, vol_channel_gains)
    print temp_adc.refresh()
    eeprom = MFG_eeprom(pn_rev_addr, sn_addr, TestDate_addr, TestOutcome_addr)
     