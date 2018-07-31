'''Ix Module User Interface
Jeff Leadbetter 2014
Copyright Daxsonics Ultrasound

Split from IxModuleUI.py April 2017.
'''

import numpy
import scipy.interpolate
import scipy.signal
import struct
from PyCyAPI import *

FIXED_SIZE = False
MULTIPROCESS = False
P_ARRAY = True

USB3 = True
AUTO_TRIGGER = False #Changed for X3-1 standalone testing.
WIRED_ZYNQ = True
IIR_FILTER = False

def init_FX3(usbDevice):
    if usbDevice.isOpen or usbDevice.open(0):
        #firmwarePath = 'FX3Firmware/DualSlaveFifoSync.img'
        #firmwarePath = 'FX3Firmware/SF_streamIN.img'
        firmwarePath = 'FX3Firmware/SlaveFifoSync_Chris_edits.img'
        firmwareDownloadStatus = usbDevice.downloadFirmware(
            firmwarePath,
            FX3_FIRMWARE_DOWNLOAD_MEDIA_TYPE_RAM)
        usbDevice.close()
        if firmwareDownloadStatus ==\
                FX3_FIRMWARE_DOWNLOAD_ERROR_CODE_SUCCESS:
            print 'Downloaded firmware'
    
        else:
            pass
    
    else:
        print 'No FX3 device found!'

def usbRead(usbDevice, dataSize):
    if usbDevice.isOpen or usbDevice.open(0):
        if usbDevice.isBootloaderRunning:
            print 'Program FX3 first'
            return None
        else:
            if AUTO_TRIGGER:
                if not WIRED_ZYNQ:
                    usbEndpoint = usbDevice.getEndpoint(4)
                else:
                    usbEndpoint = usbDevice.bulkInEndpoint
            else:
                #usbEndpoint = usbDevice.getEndpoint(1)
                usbEndpoint = usbDevice.bulkInEndpoint
            if usbEndpoint:
                usbEndpoint.timeout = 1000  # Milliseconds
                arraySize = dataSize
#                packetSize = 4096 *4 # usbEndpoint.packetSize
#                arraySize = packetSize
#                while arraySize < dataSize:
#                    arraySize += packetSize
                array = numpy.zeros(arraySize, numpy.uint8)
                isXferDataSuccess = usbEndpoint.xferData(array)
                if isXferDataSuccess:
                    return array[:dataSize]
                else:
                    print 'Failed to transfer data: ntStatus=0x%.8x, usbdStatus=0x%.8x' %\
                        (usbEndpoint.ntStatus, usbEndpoint.usbdStatus)
                    #usbEndpoint.reset()
                    return None
            else:
                print 'Failed to find BULK IN endpoint'
                return None
    else:
        print 'Failed to open USB device'
        return None


# Single-processing data capture
def spAcquire(usbDevice, sampleCount):
    
        expectedByteCount = sampleCount * 4
        if USB3:
            rawData = usbRead(usbDevice, expectedByteCount)
            if rawData is None:
                # Try once more. Maybe the firmware was just loaded.
                rawData = usbRead(usbDevice, expectedByteCount)
                if rawData is None:                   
                    return None
        else:
            xilly = open('\\\\.\\xillybus_read_32', 'rb')
            rawData = xilly.read(expectedByteCount)
            xilly.close()
        if rawData is None:
            return None
        data = numpy.array(struct.unpack('%dI' % (sampleCount,), rawData), dtype='uint32')
        return data
    
class DataObj(object):

    def __init__(self, channel_data=False):

        self.usbDevice = FX3Device()
        init_FX3(self.usbDevice)
    
        self.scanning = False
        
        self._channel_data = channel_data
        if not self._channel_data:
            self.setBuffers(1024*4) #Defaults to 4096 for 4FZ, call dataObject.setBuffers(8192) for all channel data        
            self.zoneBuffers = numpy.zeros([4, 1000])
        else:
            self.setBuffers(1024*8)
            self.channelData = numpy.zeros([8, 1000])
        
        # data averaging
        self.average = 1

        # Placeholder for MCU
        self.MCU = None

        # Data filter
        co = 1500.
        z = 10.0E-03
        nz = 500.
        dz = z/nz
        dt = 2. * dz / co
        fs = 1. / dt
        fn = 0.5*fs
        cl = 10.0E+06
        #ch = 17.0E+06
        self.iirB, self.iirA = scipy.signal.iirfilter(N=12,
                                                      Wn=cl/fn,
                                                      btype='highpass',
                                                      ftype='bessel')
                                                      
        self.success = 0
        self.fail = 0
        self.count = 0

    def setBuffers(self,sampleCount=4096):
        # Set up acquisition buffers
        bufferCnt = 6
        self.bufferCnt = bufferCnt
        self.sampleCnt = sampleCount
        self.bufIndex = 0
        self.bufPerAcq = 1
        self.buffers = numpy.empty([self.bufferCnt, self.sampleCnt], dtype=numpy.uint32, order='C')
        self.data = self.buffers[0]

    def setMCU(self, MCU):
        self.MCU = MCU

    def setAverage(self, n):
        self.average = n

    def processChannelData(self, offset = 1, nsamples = 1000, chsamples = 1024):
        if not self._channel_data:
            print 'DataObject is not initiated for channel data'
            return
            
        k = 2. /4095.
        data = self.buffers[self.bufIndex]
        self.data = data
        
        for channel in range(8):
            Data = numpy.array(data[chsamples*channel+offset : chsamples*channel+offset+nsamples], dtype=numpy.float64)
            Data *= k
            Data = Data - Data[100:].mean()
            self.channelData[channel, :] = Data  
        
    def processData(self, offset = 1):       
        if self._channel_data:
            print 'DataObject is initiated only for channel data'
            return
            
        k = 2. / 4095.
        
        data = self.buffers[self.bufIndex]
        self.data = data

        self.zoneBuffers[0, :] = data[offset:offset+1000]
        self.zoneBuffers[1, :] = data[offset+1024:offset+2024]
        self.zoneBuffers[2, :] = data[offset+2048:offset+3048]
        self.zoneBuffers[3, :] = data[offset+3072:offset+4072]

        zone1 = self.zoneBuffers[0, :]
        zone2 = self.zoneBuffers[1, :]
        zone3 = self.zoneBuffers[2, :]
        zone4 = self.zoneBuffers[3, :]

        zone1 *= k
        zone2 *= k
        zone3 *= k
        zone4 *= k

        zone1 = zone1 - zone1[100:].mean()
        zone2 = zone2 - zone2[100:].mean()
        zone3 = zone3 - zone3[100:].mean()
        zone4 = zone4 - zone4[100:].mean()

        iqData = numpy.array(zone4)
        iqData[0:2*112] = zone1[0:2*112]
        iqData[2*112:2*200] = zone2[2*112:2*200]
        iqData[2*200:2*312] = zone3[2*200:2*312]
        iData = iqData[::2]
        qData = iqData[1::2]

        if IIR_FILTER:
            iData[:] = scipy.signal.lfilter(self.iirB, self.iirA, iData)
            qData[:] = scipy.signal.lfilter(self.iirB, self.iirA, qData)

        self.iData = iData
        self.qData = qData
        self.iqData = iqData

        env = numpy.sqrt(iData**2 + qData**2)
        self.eData = env  # Linear scale
        
    def resetFx3(self, usbDevice):
        try:
            status = usbDevice.reset()
            return status
        except:
            return False

                
    def collect(self, single=False, reset=True):
        res = self._collectSPArray(_single=single,_reset=reset)
        return res
        
    # Single-process
    def _collectSPArray(self, _single=False, _reset=True):

        self.bLineIndex = 0
        self.bufIndex = 0
        bufIndex = self.bufIndex

        self.scanning = True
        while self.scanning:
            self.buffers[bufIndex, :] = 0

            acqCnt = 0

            if self.MCU is None:
                for i in range(self.average):
                    self.count +=1
                    data = spAcquire(self.usbDevice, self.sampleCnt)                           
                    break   
                    if data is None:
                        return False
                    self.buffers[bufIndex, :] += data
                    acqCnt += 1
            else:
                for i in range(self.average):
                    if _reset:
                        res = self.resetFx3(self.usbDevice)
                        if not res:
                            print 'Reset FX3 fault'
                    
                    try:
                        trigRet = self.MCU.manualTrigger()
                    except:
                        print 'Trigger raised exception :`('
                        break
                    if trigRet == 1:
                        data = spAcquire(self.usbDevice, self.sampleCnt)
                        if data is None:
                            return False
                        self.buffers[bufIndex, :] += data
                        acqCnt += 1
                    else:
                        print 'Trigger fault'
                        return False
            
            if acqCnt < 1:
                break
            self.buffers[bufIndex, :] /= acqCnt

            # Increment buffer index
            bufIndex = (bufIndex + 1) % self.bufferCnt
            self.bufIndex = bufIndex
                   
            # Check for user input
#            QApplication.processEvents()
            if _single == True:
                self.scanning = False
                self.bufIndex = 0
        return True
        
    def newBConfig(self):
        if not self.alive:
            # Refresh the plot to show the effect of the new configuration
#            self.emit(SIGNAL('newBData'), self.bData)
            print('newBConfig called')

if __name__ == '__main__':
    print ('not intended for use as standalone module')
    from IxModuleHybridMCU import *
    mcu = HybridMCU()
    dataObject = DataObj()
    dataObject.setMCU(mcu)
    #not intended to be called as main
    