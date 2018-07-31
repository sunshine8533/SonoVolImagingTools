'''Ix Module User Interface
Jeff Leadbetter 2014
Copyright Daxsonics Ultrasound
'''

import multiprocessing
import numpy
import scipy.interpolate
import scipy.signal
import cv2

from guiqwt.plot import ImageDialog
from guiqwt.plot import CurveDialog
from guiqwt.builder import make  # Alias for guiqwt.builder.PlotItemBuilder()

from PyCyAPI import *
from IxModuleMCU import *

FIXED_SIZE = False
MULTIPROCESS = False
P_ARRAY = True

USB3 = True
DATA_FORMAT = 'Chris_rev' #['1_4', 'Chris_rev', '3/4']
AUTO_TRIGGER = False
WIRED_ZYNQ = True
IIR_FILTER = False

usbDevice = FX3Device()

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
            print 'Failed to download firmware'
    
    else:
        print 'No FX3 device found!'

def usbRead(dataSize):
    if usbDevice.isOpen or usbDevice.open(0):
        if usbDevice.isBootloaderRunning:
            print 'Program FX3 first'
            return None
#            if AUTO_TRIGGER:
#                firmwarePath = 'FX3Firmware/DualSlaveFifoSync.img'
#            else:
#                firmwarePath = 'FX3Firmware/SF_streamIN.img'
#            firmwareDownloadStatus = usbDevice.downloadFirmware(
#                firmwarePath,
#                FX3_FIRMWARE_DOWNLOAD_MEDIA_TYPE_RAM)
#            usbDevice.close()
#            if firmwareDownloadStatus ==\
#                    FX3_FIRMWARE_DOWNLOAD_ERROR_CODE_SUCCESS:
#                print 'Downloaded firmware'
#                return None
#            else:
#                print 'Failed to download firmware'
        else:
            if AUTO_TRIGGER:
                if not WIRED_ZYNQ:
                    usbEndpoint = usbDevice.getEndpoint(4)
                else:
                    usbEndpoint = usbDevice.bulkInEndpoint
            else:
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


# Multiprocessing data capture
def mpCapture(stopEvent, q, sampleCount):
        expectedByteCount = sampleCount * 4
        while not stopEvent.is_set():
            if USB3:
                rawData = usbRead(expectedByteCount)
                if rawData is None:
                    # Try once more. Maybe the firmware was just loaded.
                    rawData = usbRead(expectedByteCount)
            else:
                xilly = open('\\\\.\\xillybus_read_32', 'rb')
                rawData = xilly.read(expectedByteCount)
                xilly.close()
            if rawData is None:
                q.put(None)
                break
            actualByteCount = len(rawData)
            if actualByteCount < expectedByteCount:
                continue
            data = numpy.array(struct.unpack('%dI' % (sampleCount,), rawData), dtype='uint32')
            q.put(data)
        q.close()
        q.cancel_join_thread()


# Single-processing data capture
def spAcquire(sampleCount):
        expectedByteCount = sampleCount * 4
        if USB3:
            rawData = usbRead(expectedByteCount)
            if rawData is None:
                # Try once more. Maybe the firmware was just loaded.
                rawData = usbRead(expectedByteCount)
        else:
            xilly = open('\\\\.\\xillybus_read_32', 'rb')
            rawData = xilly.read(expectedByteCount)
            xilly.close()
        if rawData is None:
            return None
        data = numpy.array(struct.unpack('%dI' % (sampleCount,), rawData), dtype='uint32')
        return data


class BModeWindow(QWidget):
    def __init__(self, dataObject, parent=None):
        '''Class contains GUI tools and layout for B-mode imaging

        dataObject:  Inherits QObject. Is responsible for interfacing with
                     data acquisition hardware, data storage and memory assignment,
                     broadcasting data to main GUI, and providing physical parameters
                     related to plotting. During scanning or replay plots are updated
                     when the 'newBData' signal is received from the dataObject.
        '''
        super(BModeWindow, self).__init__(parent)

        ########
        # Timing
        ########
        self.currClock = time.clock()
        self.prevClock = self.currClock

        #####################
        # B-mode data members
        #####################

        self.dataObject = dataObject

        # Scanner Micro Controller
        # Assigned after init() using setMCU() method
        self.MCU = None

        # Image Control Widget
        # Optional widget to set dynamic range, filters, mapping, etc.
        self.imageControlWidget = None

        ###################
        # GUI widgets setup
        ###################

        # Set 'Run' and 'Stop' buttons
        self.runButton = QPushButton('Scan')
        self.stopButton = QPushButton('Stop')

        # Label to report frame rate
        self.lineRate = 0.0
        self.lineRateLabel = QLabel()

        # B-mode image display uses guiqwt.plot.ImageDialog()
        self.plotDialog = ImageDialog(edit=False, toolbar=False,
                                      options=dict(show_contrast=False,
                                                   aspect_ratio=1.00,
                                                   xlabel='Position (mm)',
                                                   ylabel='Depth (mm)',
                                                   ysection_pos='left'))

        # Remove the default plot grid apply black background without gridlines
        blankGrid = make.grid(background='#000000',
                              major_enabled=(False, False),
                              minor_enabled=(False, False),
                              major_style=None,
                              minor_style=None)
        plot = self.plotDialog.get_plot()
        plot.del_all_items(except_grid=False)
        plot.add_item(blankGrid)

        # Create a local image data array and a guiqwt.image.ImageItem
        imgyPx, imgxPx = self.dataObject.bData.shape

        self.currentImageData = numpy.zeros([imgxPx, imgyPx])
        imgWidth = self.dataObject.getBWidth()
        imgDepth = self.dataObject.getBDepth()
        self.currentImage = make.image(self.currentImageData,
                                       xdata=imgWidth,
                                       ydata=imgDepth,
                                       colormap='gist_gray')

        # Set the dynamic range
        self.BSignalRange = dataObject.getBRange()
        imgRange = dataObject.getBRange()
        self.currentImage.set_lut_range(imgRange)
        # Set the plot size and add the image
        dx = abs(imgWidth[1] - imgWidth[0])
        dy = abs(imgDepth[1] - imgDepth[0])
        plot = self.plotDialog.get_plot()
        if FIXED_SIZE:
            nativeSize = QSize(640 * dx / dy, 580)
            plot.setMaximumSize(nativeSize)
            plot.setMinimumSize(nativeSize)
        plot.add_item(self.currentImage)

        # B-mode data averaging
        maxAveragesExp = 3
        self.maxAverages = 2**maxAveragesExp
        self.averageList = [2**x for x in range(0,maxAveragesExp+1)]
        averageText = ['%d Frames' % i for i in self.averageList]
        self.averageComboBox = QComboBox()
        self.averageComboBox.addItems(averageText)

        # Flip image left to right
        self.flipLRButton = QPushButton('Flip L/R')
        self.flipLRButton.setCheckable(True)

        # Time gain
        self.gainWidget = TimeGainWidget(dataLength=dataObject.RFRecordLength)

        # Replay
        self.replayWidget = ReplayWidget(self.dataObject)

        ############
        # GUI layout
        ############

        grid = QGridLayout()
        row = 0

        runStopStack = QVBoxLayout()
        runStopStack.addWidget(self.runButton)
        runStopStack.addWidget(self.stopButton)
        runStopInterface = QHBoxLayout()
        runStopInterface.addLayout(runStopStack)
        runStopInterface.addStretch()
        grid.addLayout(runStopInterface, row, 0)
        row += 1

        lineRateLayout = QHBoxLayout()
        lineRateLayout.addWidget(QLabel('Line Rate (lps): '))
        lineRateLayout.addWidget(self.lineRateLabel)
        lineRateLayout.addStretch()
        grid.addLayout(lineRateLayout, row, 0)
        row += 1

        line = QFrame(self)
        line.setLineWidth(1)
        line.setFrameStyle(QFrame.HLine)
        grid.addWidget(line)
        row += 1
        #grid.addWidget(QLabel('Averaging :'), row, 0)
        #row += 1
        #grid.addWidget(self.averageComboBox, row, 0)
        #self.averageComboBox.setSizePolicy(QSizePolicy(QSizePolicy.Preferred))
        #row += 1

        plotLayout = QGridLayout()
        plotLayout.addWidget(self.plotDialog, 0, 0)
        plotLayout.addWidget(self.gainWidget, 0, 1)
        plotLayout.addWidget(self.flipLRButton, 1, 1)
        plotLayout.addWidget(self.replayWidget, 1, 0)

        plotVSpacer = QVBoxLayout()
        plotVSpacer.addStretch()
        plotVSpacer.addLayout(plotLayout)
        plotVSpacer.addStretch()
        plotHSpacer = QHBoxLayout()
        plotHSpacer.addStretch()
        plotHSpacer.addLayout(plotVSpacer)
        plotHSpacer.addStretch()
        grid.addLayout(plotHSpacer, row, 0)
        row += 1

        self.setLayout(grid)

        ###################
        # Signals and slots
        ###################
        self.connect(self.runButton,   SIGNAL('clicked()'), self.runBScan)
        self.connect(self.stopButton,  SIGNAL('clicked()'), self.stopBScan)
        self.connect(self.averageComboBox, SIGNAL('currentIndexChanged(int)'), self.setBAverage)
        self.connect(self.flipLRButton, SIGNAL('clicked()'), self.flipLeftRight)
        self.connect(self.gainWidget, SIGNAL('newBConfig'), self.newBConfig)
        self.connect(self.dataObject, SIGNAL('newBData'), self.replot)
        self.connect(self.dataObject, SIGNAL('failBData'), self.failBScan)
               
    def runBScan(self):
        '''Method calls program loop to acquire B-mode images'''

        # Calculate display frame rate
        self.prevClock = time.clock()

        # Start data collection
        self.dataObject.stopBVideo()
        self.dataObject.setBMode()
        self.dataObject.collect()

    def stopBScan(self):
        '''Stop B-mode image acquisition'''
        self.dataObject.scanning = False
        self.dataObject.setBVideoIndexAndUpdateGUI(0)

    def failBScan(self):
        '''Stop B-mode image acquisition due to an error'''
        self.stopBScan()
        # TODO

    def setBMaxPlotRange(self, sliderIndex):
        sliderIndex = max(1, sliderIndex)
        self.BSignalRange[1] = sliderIndex
        a, b = self.BSignalRange
        self.currentImage.set_lut_range([a, b])
        self.plotDialog.plot_widget.contrast.set_range(a, b)
        plot = self.plotDialog.get_plot()
        plot.set_active_item(self.currentImage)
        plot.replot()

    def setBMinPlotRange(self, sliderIndex):
        sliderIndex = min(59, sliderIndex)
        self.BSignalRange[0] = sliderIndex
        a, b = self.BSignalRange
        self.currentImage.set_lut_range([a, b])
        self.plotDialog.plot_widget.contrast.set_range(a, b)
        plot = self.plotDialog.get_plot()
        plot.set_active_item(self.currentImage)
        plot.replot()
        
    def setBAverage(self, index):
        # Parse out the number of frames to average from the combo box text
        temp = int(str(self.averageComboBox.currentText()).split()[0])
        self.dataObject.setBAverage(temp)

    def newBConfig(self):
        self.dataObject.newBConfig()

    def flipLeftRight(self):
        '''Flip the image from left to right'''
        flip = self.flipLRButton.isChecked()
        plot = self.plotDialog.get_plot()
        plot.set_axis_direction('bottom', flip)
        plot.set_active_item(self.currentImage)
        plot.replot()

    def replot(self, srcData):
        '''Update all B-mode images and related data display'''
        
        # Apply processing from the image control widget
        if self.imageControlWidget is not None:
            self.currentImageData[:] = self.imageControlWidget.processBImage(srcData, self.gainWidget.gain)
        else:
            self.currentImageData[:] = srcData[:]
                
        # Apply the adjusted levels to the display data
        # Leave the data source (dataObject) unaltered
        self.currentImage.set_data(self.currentImageData)        
        self.currentImage.set_lut_range(self.BSignalRange)
        plot = self.plotDialog.get_plot()
        plot.replot()
        
        # Report the display rate
        self.currClock = time.clock()
        self.lineRate = 1.0 / (self.currClock - self.prevClock)
        self.lineRateLabel.setText('{:.1f}'.format(self.lineRate))
        self.prevClock = self.currClock

    def setMCU(self, MCU):
        '''Assign a local reference to the scanner MCU'''
        self.MCU = MCU

    def setImageControlWidget(self, imgWidget):
        self.imageControlWidget = imgWidget
        self.connect(self.imageControlWidget.BNoiseFloorSlider, SIGNAL('valueChanged(int)'), self.setBMinPlotRange)
        self.connect(self.imageControlWidget.BSignalRangeSlider, SIGNAL('valueChanged(int)'), self.setBMaxPlotRange)
        self.connect(self.imageControlWidget, SIGNAL('newBConfig'), self.newBConfig)

        # Replace the initial display image
        # Output from the imageControlWidget may be a different due to image mapping

        # Remove old image item
        plot = self.plotDialog.get_plot()
        plot.del_all_items(except_grid=True)
        
        # Create and add new image item
        imgyPx, imgxPx = imgWidget.imgShape
        srcData = self.dataObject.bData
        self.currentImageData = self.imageControlWidget.processBImage(srcData)
        imgWidth = imgWidget.xDim
        imgDepth = imgWidget.yDim
        self.currentImage = make.image(self.currentImageData,
                                       xdata=imgWidth,
                                       ydata=imgDepth,
                                       colormap='gist_gray')

        imgRange = imgWidget.imgRange
        self.currentImage.set_lut_range(imgRange)
        plot.add_item(self.currentImage)
        
    def setAppearance(self):
        '''The GuiQWT objects don't repaint when their parents palette
        is updated. Apply palette here with any modifications wanted.
        '''

        windowPalette = self.palette()

        # Set the axis values to general foreground color
        # These are defined by QPallet.Text, which makes them init
        # differently from the general foreground (WindowText) color.
        plotPalette = self.plotDialog.palette()
        plotPalette.setColor(QPalette.Text, windowPalette.color(QPalette.WindowText))
        plotPalette.setColor(QPalette.WindowText, windowPalette.color(QPalette.WindowText))
        self.plotDialog.setPalette(plotPalette)
        self.plotDialog.palette()
        # Need to set the axis labels manually...
        plot = self.plotDialog.get_plot()
        plot.set_axis_color('bottom', windowPalette.color(QPalette.WindowText))
        plot.set_axis_color('left', windowPalette.color(QPalette.WindowText))


class TimeGainWidget(QWidget):
    def __init__(self, sliderCount=5, dataLength=6080, maxGain=20, parent=None):
        '''Widget to produce a display of sliders for setting the
        post-processing time gain cure in B-mode images.

        Input  - sliderCount, number of sliders to use. Each slider gives a log
                              scale gain value
               - dataLength, number of data points in the RF record of each A Line
               - maxGain, maximum gain, in dB

        Output - self.gain, this is a linear scale gain factor
                            for each point in RF A line
        '''

        super(TimeGainWidget, self).__init__(parent)

        # Store array lengths
        self.dataLength = dataLength
        self.sliderCount = sliderCount
        # Initially set unity gain
        self.gain = numpy.ones([500, 1])
        self.maxGain = maxGain

        # Create a list of slider widgets
        self.sliderList = []
        for i in range(sliderCount):
            self.sliderList.append(QSlider(Qt.Horizontal))
            self.sliderList[i].setMinimum(0)
            self.sliderList[i].setMaximum(2 * maxGain)
            self.sliderList[i].setValue(maxGain)

        ###############
        # Widget layout
        ###############

        vLayout = QVBoxLayout()

        for i in range(sliderCount):
            vLayout.addWidget(self.sliderList[i])
            self.connect(self.sliderList[i], SIGNAL('valueChanged(int)'), self.setGain)
            if i < sliderCount - 1:
                vLayout.addStretch()

        # An extra stretch helps line these up to the bottom of the plot
        vLayout.addStretch()
        self.setLayout(vLayout)

    def setGain(self, value=None):
        coarseGain = []
        for i in range(self.sliderCount):
            dbValue = self.sliderList[i].value() - self.maxGain
            kValue = 10 ** (float(dbValue) / 20.)
            coarseGain.append(kValue)

        coarseList = numpy.array(range(self.sliderCount), dtype=numpy.float)
        fineList = numpy.zeros([500, 1])
        fineList[:, 0] = range(500)
        fineList *= float(self.sliderCount - 1) / float(500 - 1)

        self.gain[:] = numpy.interp(fineList, coarseList, coarseGain)

        self.emit(SIGNAL('newBConfig'))


class ReplayWidget(QWidget):
    def __init__(self, dataObject, parent=None):
        '''Widget to replay a sequence of BImages as a video stream.

        dataObject: Contains buffers and processed data.
        '''
        super(ReplayWidget, self).__init__(parent)

        self.dataObject = dataObject

        self.playButton = QPushButton('Replay')
        self.stopButton = QPushButton('Stop')
        self.renderButton = QPushButton('Render')

        self.frameSlider = QSlider(Qt.Horizontal)
        self.frameSlider.setMinimum(0)
        self.frameSlider.setMaximum(self.dataObject.bVideoLength - 1)
        self.frameSlider.setValue(0)

        ###############
        # Widget layout
        ###############

        hLayout = QHBoxLayout()
        vLayout = QVBoxLayout()

        vLayout.addWidget(self.frameSlider)

        hLayout.addWidget(self.playButton)
        hLayout.addWidget(self.stopButton)
        hLayout.addWidget(self.renderButton)
        hLayout.addStretch()

        vLayout.addLayout(hLayout)

        self.setLayout(vLayout)

        #########
        # Signals
        #########

        self.connect(self.playButton, SIGNAL('clicked()'), self.dataObject.startBVideo)
        self.connect(self.stopButton, SIGNAL('clicked()'), self.dataObject.stopBVideo)
        self.connect(self.renderButton, SIGNAL('clicked()'), self.renderVideo)
        # Re-plotting is handled by parent widget, this just needs to move the slider
        self.connect(self.dataObject, SIGNAL('newBVideo'), self.updateSliderIndex)
        self.connect(self.frameSlider, SIGNAL('sliderMoved(int)'), self.updateVideoFrame)

    def updateSliderIndex(self, index):
        self.frameSlider.setValue(index)

    def updateVideoFrame(self, value):
        if not self.dataObject.alive:
            self.dataObject.bVideoIndex = value
            self.dataObject.bData = self.dataObject.bVideo[self.dataObject.bVideoIndex, :, :]
            self.dataObject.emit(SIGNAL('newBData'), self.dataObject.bData)

    def renderVideo(self):
        self.dataObject.stopBVideo()
        filename = QFileDialog.getSaveFileName(self, 'Save File', filter='*.avi')
        if filename != '':
            length, height, width = self.dataObject.bVideo.shape
            video = cv2.VideoWriter(str(filename), -1, int(self.dataObject.frameRate), (width, height), False)
            maxVal = self.dataObject.bRange[1]
            tempFrame = numpy.empty([height, width], numpy.uint16)
            for i in range(length):
                tempFrame[:, :] = self.dataObject.bVideo[i, :, :] * (65535 / maxVal)
                video.write(tempFrame)
            video.release()


class IxModuleData(QObject):

    def __init__(self, parent=None):
        super(IxModuleData, self).__init__(parent)

        self.scanning = False
        self.emitB = False
        self.emitM = False
        self.emitRF = False
        self.alive = False

        ############################
        # Set up acquisition buffers
        ############################
        bufferCnt = 6
        sampleCnt = 4096
        self.bufferCnt = bufferCnt
        self.sampleCnt = sampleCnt
        self.bufIndex = 0
        self.bufPerAcq = 1
        self.buffers = numpy.empty([self.bufferCnt, self.sampleCnt], dtype=numpy.uint32, order='C')
        self.data = self.buffers[0]
        
        if DATA_FORMAT == '1_4' or DATA_FORMAT == 'Chris_rev':  # 1/4
            self.zoneBuffers = numpy.zeros([4, 1000])
        elif DATA_FORMAT == '3/4':  # 3/4
            self.zoneBuffers = numpy.zeros([4, 500])
        
        # Universal parameters
        self.zRange = [10.0, 20.0]
                                                
        self.bPx = 500
        self.bLines = 500
        self.frameRate = 10.
        self.bVideoLength = int(10. * self.frameRate)
        self.bVideo = numpy.zeros([self.bVideoLength, self.bPx, self.bLines], dtype=numpy.double)
        self.bVideoIndex = 0
        self.bData = self.bVideo[self.bVideoIndex, :, :]
        self.bVideoTimer = QTimer()
        self.bVideoTimer.setInterval(int(1000. / self.frameRate))
        self.connect(self.bVideoTimer, SIGNAL('timeout()'), self.emitBVideoFrame)

        # B-mode physical parameters
        self.bDepth = self.zRange
        self.bWidth = [0.0, 25.0]
        self.bFocus = 15
        self.bRange = [0, 120]

        # B-mode frame averaging
        self.average = 1
        
        # RF data output
        self.RFRecordLength = 500
        # RF data contain Z values, i samples, q samples, and demodulated envelope data
        self.RFData = numpy.zeros([self.RFRecordLength,5], dtype=numpy.double)
        self.RFData[:, 0] = numpy.linspace(self.zRange[0], self.zRange[1], self.RFRecordLength)
        self.RFRange = [-1000., 1000.]

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

    def getBWidth(self):
        return self.bWidth
    
    def getBDepth(self):
        return self.bDepth
        
    def getBRange(self):
        '''Report the maximum B-mode signal range (dB scale)'''
        return self.bRange

    def setBMode(self):
        self.emitB = True
        self.emitM = False
        self.emitRF = False

    def setMMode(self):
        self.emitB = False
        self.emitM = True
        self.emitRF = False

    def setRF(self):
        self.emitB  = False
        self.emitM  = False
        self.emitRF = True

    def setMCU(self, MCU):
        self.MCU = MCU

    def setMotors(self, motor):
        self.motor = motor

    def setAverage(self, n):
        self.average = n
        self.emit(SIGNAL('newAverage'), n)

    def collect(self, single=False):
        if MULTIPROCESS:
            #print 'Collecting MP'
            self._collectMPArray()
        else:
            #print 'Collecting SP'
            self._collectSPArray(_single=single)

    def setBVideoIndexAndUpdateGUI(self, value):
        self.bVideoIndex = value
        self.bData = self.bVideo[self.bVideoIndex, :, :]
        self.emit(SIGNAL('newBData'), self.bData)
        self.emit(SIGNAL('newBVideo'), self.bVideoIndex)

    def startBVideo(self):
        self.scanning = False
        self.setBVideoIndexAndUpdateGUI(0)
        self.bVideoTimer.start()

    def stopBVideo(self):
        self.bVideoTimer.stop()
        self.scanning = False
        self.setBVideoIndexAndUpdateGUI(0)
        
    def emitBVideoFrame(self):
        self.setBVideoIndexAndUpdateGUI((self.bVideoIndex + 1) % self.bVideoLength)
        
    def processBArrayData(self):
        self.processData()
        self.bData[:, self.bLineIndex] = self.logEnv[:]

    def processRFArrayData(self):

        self.processData()
        self.RFData[:, 1] = self.iData[:]
        self.RFData[:, 2] = self.qData[:]
        self.RFData[:, 3] = self.eData[:]
            
    def processData(self):
        
        k = 2000. / 4095.

        noiseFloor = 1.0
        
        data = self.buffers[self.bufIndex]
        self.data = data

        if DATA_FORMAT == '1_4':  # 1/4
            self.zoneBuffers[0, :] = data[0:1000]
            self.zoneBuffers[1, :] = data[1000:2000]
            self.zoneBuffers[2, :] = data[2000:3000]
            self.zoneBuffers[3, :] = data[3000:4000]
        elif DATA_FORMAT == 'Chris_rev':
            offset = 1
            self.zoneBuffers[0, :] = data[offset:offset+1000]
            self.zoneBuffers[1, :] = data[offset+1024:offset+2024]
            self.zoneBuffers[2, :] = data[offset+2048:offset+3048]
            self.zoneBuffers[3, :] = data[offset+3072:offset+4072]
        else:  # 3/4
            self.zoneBuffers[0, :] = data[0:500]
            self.zoneBuffers[1, :] = data[1000:1500]
            self.zoneBuffers[2, :] = data[2000:2500]
            self.zoneBuffers[3, :] = data[3000:3500]

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
        if DATA_FORMAT == '1_4' or DATA_FORMAT == 'Chris_rev':  # 1/4
            iqData[0:2*112] = zone1[0:2*112]
            iqData[2*112:2*200] = zone2[2*112:2*200]
            iqData[2*200:2*312] = zone3[2*200:2*312]
            iData = iqData[::2]
            qData = iqData[1::2]
        else:  # 3/4
            iqData[0:112] = zone1[0:112]
            iqData[112:200] = zone2[112:200]
            iqData[200:312] = zone3[200:312]
            iData = iqData[:]
            qData = numpy.roll(iqData[0:500], -1)

        if IIR_FILTER:
            iData[:] = scipy.signal.lfilter(self.iirB, self.iirA, iData)
            qData[:] = scipy.signal.lfilter(self.iirB, self.iirA, qData)

        self.iData = iData
        self.qData = qData
        self.iqData = iqData

        env = numpy.sqrt(iData**2 + qData**2)
        env[env < noiseFloor] = noiseFloor
        self.logEnv = 20. * numpy.log10(env / noiseFloor)
        
        '''
        Equal weight blending
        env = numpy.zeros(500)
        for n in range(4):
                
            if n == 0:            
                iData = numpy.array(zone1[::2])
                qData = numpy.array(zone1[1::2])
            if n == 1:            
                iData = numpy.array(zone2[::2])
                qData = numpy.array(zone2[1::2])
            if n == 2:            
                iData = numpy.array(zone3[::2])
                qData = numpy.array(zone3[1::2])
            if n == 3:            
                iData = numpy.array(zone4[::2])
                qData = numpy.array(zone4[1::2])
                
            iData[:] = scipy.signal.lfilter(self.iirB, self.iirA, iData)
            qData[:] = scipy.signal.lfilter(self.iirB, self.iirA, qData)
               
            env += numpy.sqrt(iData**2+qData**2)
            
        env /= 4.
        env[env<noiseFloor] = noiseFloor
        logEnv = 20.*numpy.log10(env/noiseFloor)
        '''

        # Display the envelope
        #self.eData = logEnv  # Log scale
        self.eData = env  # Linear scale

    # Multi-process
    def _collectMPArray(self):

        self.bLineIndex = 0
        self.bufIndex = 0
        bufIndex = self.bufIndex

        que = multiprocessing.Queue()
        stopEvent = multiprocessing.Event()
        p = multiprocessing.Process(target=mpCapture, args=(stopEvent, que, self.sampleCnt))
        p.start()

        self.scanning = True
        while self.scanning:
            self.buffers[bufIndex, :] = 0.

            acqCnt = 0

            if self.MCU is None:
                for i in range(self.average):
                    data = que.get()
                    if data is None:
                        if self.emitB:
                            self.emit(SIGNAL('failBData'))
                        if self.emitRF:
                            self.emit(SIGNAL('failRFData'))
                        break
                    self.buffers[bufIndex, :] += data
                    acqCnt += 1
            else:
                for i in range(self.average):
                    try:
                        trigRet = self.MCU.manualTrigger()
                    except:
                        break
                    if trigRet == 1:
                        data = que.get()
                        if data is None:
                            if self.emitB:
                                self.emit(SIGNAL('failBData'))
                            if self.emitRF:
                                self.emit(SIGNAL('failRFData'))
                            break
                        self.buffers[bufIndex, :] += data
                    else:
                        print 'Trigger Fault'
            
            if acqCnt < 1:
                break
            self.buffers[bufIndex, :] /= acqCnt

            # Emit signal to re-plot in main GUI, provide data as argument
            if self.emitB:
                
                self.processBArrayData()

                self.emit(SIGNAL('newBData'), self.bData)
                self.bLineIndex += 1

            if self.emitRF:
                self.processRFArrayData()

                self.emit(SIGNAL('newRFData'), self.RFData)

            # Increment buffer index
            bufIndex = (bufIndex + 1) % self.bufferCnt
            self.bufIndex = bufIndex

            # In B-mode, check whether enough lines have been collected
            if self.emitB:
                if self.bLineIndex >= self.bData.shape[1]:
                    self.bLineIndex = 0
                    self.emitBVideoFrame()
                    if self.bVideoIndex == 0:
                        # We have recorded a full video and cycled back to the start
                        self.scanning = False

            # Check for user input
            QApplication.processEvents()
        
        stopEvent.set()
        p.join()

    # Single-process
    def _collectSPArray(self, _single=False):

        self.bLineIndex = 0
        self.bufIndex = 0
        bufIndex = self.bufIndex

        self.scanning = True
        while self.scanning:
            self.buffers[bufIndex, :] = 0

            acqCnt = 0

            if self.MCU is None:
                for i in range(self.average):
                    while True:
                        self.count +=1
                        data = spAcquire(self.sampleCnt)
#                        if data[999] != data[1000] and data[1000] == data[1001]:
#                            self.success += 1                            
                        break
#                        self.fail += 1
   
                    if data is None:
                        if self.emitB:
                            self.emit(SIGNAL('failBData'))
                        if self.emitRF:
                            self.emit(SIGNAL('failRFData'))
                        break
                    self.buffers[bufIndex, :] += data
                    acqCnt += 1
            else:
                for i in range(self.average):
                    try:
                        trigRet = self.MCU.manualTrigger()
                    except:
                        break
                    if trigRet == 1:
                        data = spAcquire(self.sampleCnt)
                        if data is None:
                            if self.emitB:
                                self.emit(SIGNAL('failBData'))
                            if self.emitRF:
                                self.emit(SIGNAL('failRFData'))
                            break
                        self.buffers[bufIndex, :] += data
                        acqCnt += 1
                    else:
                        print 'Trigger Fault'
            
            if acqCnt < 1:
                break
            self.buffers[bufIndex, :] /= acqCnt

            # Emit signal to re-plot in main GUI, provide data as argument
            if self.emitB:
                
                self.processBArrayData()

                self.emit(SIGNAL('newBData'), self.bData)
                self.bLineIndex += 1

            if self.emitRF:
                self.processRFArrayData()
                
                self.emit(SIGNAL('newRFData'), self.RFData)

            # Increment buffer index
            bufIndex = (bufIndex + 1) % self.bufferCnt
            self.bufIndex = bufIndex

            # In B-mode, check whether enough lines have been collected
            if self.emitB:
                if self.bLineIndex >= self.bData.shape[1]:
                    self.bLineIndex = 0
                    self.emitBVideoFrame()
                    if self.bVideoIndex == 0:
                        # We have recorded a full video and cycled back to the start
                        self.scanning = False
                    
            # Check for user input
            QApplication.processEvents()
            if _single == True:
                self.scanning = False
                self.bufIndex = 0
    
    def newBConfig(self):
        if not self.alive:
            # Refresh the plot to show the effect of the new configuration
            self.emit(SIGNAL('newBData'), self.bData)


class ImageControlWidget(QWidget):
    def __init__(self, parent=None):
        '''
        Widget to adjust grayscale mapping
        
        Required Arguments

        dataobject:   Contains buffers and processed data.
        '''
        super(ImageControlWidget, self).__init__(parent)

        # Output image parameters
        self.imgShape = [500, 500]
        self.xDim = [-10.0, 10.0]
        self.yDim = [0.0, 10.0]
        self.imgRange = [0, 80]

        self.BImage = numpy.zeros(self.imgShape)
        self.LUT = numpy.linspace(0, 80, 256)

        # Dynamic range and compression curve
        self.BNoiseFloorSlider = QSlider(Qt.Horizontal)
        self.BNoiseFloorSlider.setMinimum(1)
        self.BNoiseFloorSlider.setMaximum(80)
        self.BNoiseFloorSlider.setValue(00)

        self.BSignalRangeSlider = QSlider(Qt.Horizontal)
        self.BSignalRangeSlider.setMinimum(1)
        self.BSignalRangeSlider.setMaximum(80)
        self.BSignalRangeSlider.setValue(70)

        self.sCompressionCheckBox = QCheckBox('Compression')

        self.sigmaSlider = QSlider(Qt.Horizontal)
        self.sigmaSlider.setMinimum(1)
        self.sigmaSlider.setMaximum(20)
        self.sigmaSlider.setValue(13)

        self.centerSlider = QSlider(Qt.Horizontal)
        self.centerSlider.setMinimum(1)
        self.centerSlider.setMaximum(80)
        self.centerSlider.setValue(38)

        self.setLUT()

        # Speckle reduction (bilinear filter)
        self.filterCheckBox = QCheckBox('Speckle Reduction')
        
        self.filterSigmaColorSlider = QSlider(Qt.Horizontal)
        self.filterSigmaColorSlider.setMinimum(0)
        self.filterSigmaColorSlider.setMaximum(20)
        self.filterSigmaColorSlider.setValue(5)

        self.filterSigmaSpaceSlider = QSlider(Qt.Horizontal)
        self.filterSigmaSpaceSlider.setMinimum(0)
        self.filterSigmaSpaceSlider.setMaximum(90)
        self.filterSigmaSpaceSlider.setValue(50)

        # Layout
        vLayout = QVBoxLayout()
        vLayout.addWidget(QLabel('Noise (dB):'))
        vLayout.addWidget(self.BNoiseFloorSlider)
        vLayout.addWidget(QLabel('Maximum (dB):'))
        vLayout.addWidget(self.BSignalRangeSlider)
        line = QFrame(self)
        line.setLineWidth(1)
        line.setFrameStyle(QFrame.HLine)
        vLayout.addWidget(line)
        vLayout.addWidget(self.sCompressionCheckBox)
        vLayout.addWidget(QLabel('Sigma (dB):'))
        vLayout.addWidget(self.sigmaSlider)
        vLayout.addWidget(QLabel('Center (dB):'))
        vLayout.addWidget(self.centerSlider)
        line = QFrame(self)
        line.setLineWidth(1)
        line.setFrameStyle(QFrame.HLine)
        vLayout.addWidget(line)
        vLayout.addWidget(self.filterCheckBox)
        vLayout.addWidget(QLabel('Sigma Color'))
        vLayout.addWidget(self.filterSigmaColorSlider)
        vLayout.addWidget(QLabel('Sigma Space'))
        vLayout.addWidget(self.filterSigmaSpaceSlider)
        vLayout.addStretch()
        
        self.setLayout(vLayout)

        # Signals and slots
        self.connect(self.sigmaSlider, SIGNAL('valueChanged(int)'), self.setLUT)
        self.connect(self.centerSlider, SIGNAL('valueChanged(int)'), self.setLUT)
        self.connect(self.sCompressionCheckBox, SIGNAL('stateChanged(int)'), self.setLUT)
        self.connect(self.filterSigmaColorSlider, SIGNAL('valueChanged(int)'), self.newSpeckleReduction)
        self.connect(self.filterSigmaSpaceSlider, SIGNAL('valueChanged(int)'), self.newSpeckleReduction)
        self.connect(self.filterCheckBox, SIGNAL('stateChanged(int)'), self.newSpeckleReduction)

    def setLUT(self, value=None):

        minVal = self.BNoiseFloorSlider.value()
        maxVal = self.BSignalRangeSlider.value()
        sigma = self.sigmaSlider.value()
        center = self.centerSlider.value()

        if self.sCompressionCheckBox.isChecked():
            start = minVal
            stop = maxVal
            width = 10.
            adjust = -sigma

            x = numpy.array([start, center, stop])
            y = numpy.array([start, center + adjust, stop])

            n = int((stop - start) / width)
            xi = numpy.linspace(start, stop, n)
            fi = scipy.interpolate.interp1d(x, y, kind='linear')

            yi = fi(xi)

            fii = scipy.interpolate.UnivariateSpline(xi, yi)
            numpy.linspace(minVal, maxVal, 256)
            xii = numpy.linspace(start, stop, 256)
            self.LUT = fii(xii)

        else:
            self.LUT = numpy.linspace(0, 80, 256)

        self.emit(SIGNAL('newBConfig'))

    def newSpeckleReduction(self, value=None):
        self.emit(SIGNAL('newBConfig'))

    def processBImage(self, srcData, timeGain=None):
    
        if timeGain is not None:
            srcData += 20 * numpy.log10(timeGain)
            srcData[srcData > 90.] = 90.
            srcData[srcData < 0.] = 0.
            
        # Apply bilinear filter
        if self.filterCheckBox.isChecked():
            '''Parameters:
            src Source 8-bit or floating-point, 1-channel or 3-channel image.
            dst  Destination image of the same size and type as src .
            d  Diameter of each pixel neighborhood that is used during filtering. If it is non-positive, it is computed from sigmaSpace .
            sigmaColor  Filter sigma in the color space. A larger value of the parameter means that farther colors within the pixel neighborhood (see sigmaSpace ) will be mixed together, resulting in larger areas of semi-equal color.
            sigmaSpace  Filter sigma in the coordinate space. A larger value of the parameter means that farther pixels will influence each other as long as their colors are close enough (see sigmaColor ). When d>0 , it specifies the neighborhood size regardless of sigmaSpace . Otherwise, d is proportional to sigmaSpace .
            '''
            sigmaColor = self.filterSigmaColorSlider.value() / 5.
            sigmaSpace = self.filterSigmaSpaceSlider.value() / 5.
            srcDataF = cv2.bilateralFilter(numpy.array(srcData, dtype=numpy.float32),
                                           0, sigmaColor, sigmaSpace)

        else:
            srcDataF = srcData

        # Apply the sector scan map
        self.BImage[:] = srcDataF[:]
        # Apply the current image level compression from the look up table (LUT)
        self.BImage[:] = numpy.take(self.LUT,
                                    numpy.array(self.BImage*255/80, dtype=numpy.uint8))

        if timeGain is not None:
            srcData -= 20 * numpy.log10(timeGain)
            srcData[srcData < 0.] = 0.
        
        return self.BImage


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        '''Main window for IxModuleDVT ultrasound imaging application'''
        super(MainWindow, self).__init__(parent)

        self.setWindowTitle('IxModule UI')

        # Set central widget - Main Scan window
        self.mainWindow = MainScanWindow()
        self.setCentralWidget(self.mainWindow)

        ##############
        # Dock widgets
        ##############

        # MCU widget
        if AUTO_TRIGGER:
            self.mcuWidget = None
        else:
            self.mcuWidget = MCUWidget()
            self.mcuWidget.setAutoFillBackground(True)

            mcuDockWidget = QDockWidget('MCU', self)
            mcuDockWidget.setObjectName('mcuDockWidget')
            mcuDockWidget.setAllowedAreas(Qt.LeftDockWidgetArea)
            mcuDockWidget.setWidget(self.mcuWidget)
            self.addDockWidget(Qt.LeftDockWidgetArea, mcuDockWidget)

            # Provide reference to the MCU in widgets that require it
            self.mainWindow.dataObject.setMCU(self.mcuWidget)

        # Image Control Widget
        self.imageControlWidget = ImageControlWidget()
        self.imageControlWidget.setAutoFillBackground(True)

        imageControlDockWidget = QDockWidget('Image Settings', self)
        imageControlDockWidget.setObjectName('contrastDockWidget')
        imageControlDockWidget.setAllowedAreas(Qt.LeftDockWidgetArea)
        imageControlDockWidget.setWidget(self.imageControlWidget)
        self.addDockWidget(Qt.LeftDockWidgetArea, imageControlDockWidget)

        # Provide reference to the image adjust panel
        self.mainWindow.BModeTab.setImageControlWidget(self.imageControlWidget)

    def closeEvent(self, event):
        '''Clean up child widgets before exit

        1) Close the active COM port
        2) Stop scanning
        '''
        if self.mcuWidget is not None:
            self.mcuWidget.closePort()
        self.mainWindow.dataObject.scanning = False
        event.accept()
        QMainWindow.closeEvent(self, event)


class MainScanWindow(QWidget):
    def __init__(self, parent=None):
        super(MainScanWindow, self).__init__(parent)

        # All imaging modes access the same data object
        # This is owned by the MainScanWindow widget and
        # referenced by the individual image mode widgets
        self.dataObject = IxModuleData()

        # GUI appearance
        bModePalette = QPalette()
        bModePalette.setColor(QPalette.Window, Qt.black)
        bModePalette.setColor(QPalette.WindowText, Qt.white)

        # Each imaging mode widget is given a tab in the central widget
        self.imageModeTabs = QTabWidget()
        tab = 0

        # B-mode imaging
        self.BModeTab = BModeWindow(self.dataObject)
        self.BModeTab.setAutoFillBackground(True)
        self.BModeTab.setPalette(bModePalette)
        self.BModeTab.setAppearance()
        self.imageModeTabs.insertTab(tab,self.BModeTab, 'B-mode')
        tab += 1

        # RF scan lines
        self.RFTab = RFWindow(self.dataObject)
        self.RFTab.setAutoFillBackground(True)
        self.imageModeTabs.insertTab(tab, self.RFTab, 'RF Data')
        tab += 1

        # End imaging mode list

        # Set the GUI layout
        grid = QGridLayout()
        grid.addWidget(self.imageModeTabs, 0, 0)
        self.setLayout(grid)


class RFWindow(QWidget):

    def __init__(self, dataObject, parent=None):
        '''Class contains GUI tools and layout for RF data display

        dataObject:  Inherits QObject. Is responsible for interfacing with
                     data acquisition hardware, data storage and memory assignment,
                     broadcasting data to main GUI, and providing physical parameters
                     related to plotting. During scanning or replay plots are updated
                     when a 'newRFData' signal is received from the dataObject.
        '''
        super(RFWindow, self).__init__(parent)

        ########
        # Timing
        ########
        self.currClock = time.clock()
        self.prevClock = self.currClock

        ######################
        # RF mode data members
        ######################
        self.dataObject = dataObject
        self.dataObject.setRF()

        ###################
        # GUI widgets setup
        ###################

        # Set 'Run' and 'Stop' buttons in horizontal layout
        self.runButton = QPushButton('Scan')
        self.stopButton = QPushButton('Stop')

        # Label to report frame rate
        self.lineRate = 0.0
        self.lineRateLabel = QLabel()

        lineRateLayout = QHBoxLayout()
        lineRateLayout.addWidget(QLabel('Line Rate (lps): '))
        lineRateLayout.addWidget(self.lineRateLabel)
        lineRateLayout.addStretch()

        # Label to report signal rms
        self.vrms = 0.0
        self.vrmsLabel = QLabel()

        vrmsLayout = QHBoxLayout()
        vrmsLayout.addWidget(QLabel('Signal (mVrms): '))
        vrmsLayout.addWidget(self.vrmsLabel)
        vrmsLayout.addStretch()

        # RF data averaging
        maxAveragesExp = 3
        self.maxAverages = 2**maxAveragesExp
        self.averageList = [2**x for x in range(0, maxAveragesExp + 1)]
        averageText = ['%d Records' % i for i in self.averageList]
        self.averageComboBox = QComboBox()
        self.averageComboBox.addItems(averageText)

        # Time domain plot using a guiqwt.plot.CurveDialog
        self.plotDialog = SimpleCurveDialog(edit=True, toolbar=True,
                                            options=dict(xlabel='Depth (m)', ylabel='I&Q Signal (mV)'))

        plot = self.plotDialog.get_plot()
        axisId = plot.get_axis_id('bottom')
        plot.set_axis_limits(axisId, dataObject.zRange[0], dataObject.zRange[1])
        axisId = plot.get_axis_id('left')
        plot.set_axis_limits(axisId, dataObject.RFRange[0], dataObject.RFRange[1])

        self.colorEnum = [Qt.darkBlue, Qt.darkRed, Qt.darkGreen, Qt.darkMagenta, Qt.blue, Qt.red, Qt.green, Qt.magenta]

        self.RFCurve = []
        
        for i in range(3):
            xRF = self.dataObject.RFData[:, 0]
            yRF = self.dataObject.RFData[:, i + 1]
            if i == 0:
                rfTitle = 'iData'
            elif i == 1:
                rfTitle = 'qData'
            else:
                rfTitle = 'eData'
            self.RFCurve.append(make.curve(xRF, yRF, title=rfTitle,
                                           color=self.colorEnum[i], linestyle='SolidLine', linewidth=1,
                                           marker=None, markersize=5, markerfacecolor='red',
                                           markeredgecolor='black', shade=None, 
                                           curvestyle=None, baseline=None,
                                           xaxis='bottom', yaxis='left'))
            plot.add_item(self.RFCurve[i])
        xIQ = numpy.zeros(self.dataObject.RFData.shape[0] * 2)

        deltaX = self.dataObject.RFData[1, 0] - self.dataObject.RFData[0, 0]
        xIQ[0::2] = self.dataObject.RFData[:, 0]
        xIQ[1::2] = self.dataObject.RFData[:, 0] + deltaX / 2

        # Frequency domain plot using a guiqwt.plot.CurveDialog
        self.rawDataDialog = SimpleCurveDialog(edit=True, toolbar=True,
                                               options=dict(xlabel='Depth (mm)', ylabel='Raw Data'))

        plot = self.rawDataDialog.get_plot()
        axisId = plot.get_axis_id('bottom')
        plot.set_axis_limits(axisId, 0, dataObject.sampleCnt)
        
        xRawData = self.dataObject.RFData[:, 0]
        yRawData = self.dataObject.RFData[:, 3]
        self.rawDataCurve = make.curve(xRawData, yRawData, color=self.colorEnum[0], linestyle='SolidLine', linewidth=1,
                                       marker=None, markersize=5, markerfacecolor='red',
                                       markeredgecolor='black', shade=None, 
                                       curvestyle=None, baseline=None,
                                       xaxis='bottom', yaxis='left')
        plot.add_item(self.rawDataCurve)

        ############
        # GUI layout
        ############

        grid = QGridLayout()
        row = 0

        runStopStack = QVBoxLayout()
        runStopStack.addWidget(self.runButton)
        runStopStack.addWidget(self.stopButton)
        runStopInterface = QHBoxLayout()
        runStopInterface.addLayout(runStopStack)
        runStopInterface.addStretch()
        grid.addLayout(runStopInterface, row, 0)
        row += 1

        grid.addLayout(lineRateLayout, row, 0)
        row += 1

        grid.addLayout(vrmsLayout, row, 0)
        row += 1

        line = QFrame(self)
        line.setLineWidth(1)
        line.setFrameStyle(QFrame.HLine)
        grid.addWidget(line)
        row += 1
        grid.addWidget(QLabel('Averaging :'), row, 0)
        row += 1
        grid.addWidget(self.averageComboBox, row, 0)
        self.averageComboBox.setSizePolicy(QSizePolicy(QSizePolicy.Preferred))
        row += 1

        grid.addWidget(self.plotDialog, row, 0)
        row += 1

        grid.addWidget(self.rawDataDialog, row, 0)
        row += 1
        self.setLayout(grid)

        ###################
        # Signals and slots
        ###################

        self.connect(self.runButton,  SIGNAL('clicked()'), self.runRFScan)
        self.connect(self.stopButton, SIGNAL('clicked()'), self.stopRFScan)
        self.connect(self.averageComboBox, SIGNAL('currentIndexChanged(int)'), self.setAverage)
        self.connect(self.dataObject, SIGNAL('newRFData'), self.replot)
        self.connect(self.dataObject, SIGNAL('failRFData'), self.failRFScan)

    def runRFScan(self):
        ''' Start the thread containing the data acquisition loop'''

        # Calculate display frame rate
        self.prevClock = time.clock()

        # Start data collection
        self.dataObject.setRF()
        self.dataObject.collect()

    def stopRFScan(self):
        self.dataObject.scanning = False

    def failRFScan(self):
        self.stopRFScan()
        # TODO

    def setAverage(self):
        temp = int(str(self.averageComboBox.currentText()).split()[0])
        self.dataObject.setAverage(temp)

    def replot(self, rfData):

        for i in range(3):
            self.RFCurve[i].set_data(rfData[:, 0], rfData[:, i + 1])

        plot = self.plotDialog.get_plot()
        plot.replot()

        self.currClock = time.clock()
        self.lineRate = 1.0 / (self.currClock - self.prevClock)
        self.lineRateLabel.setText('{:.1f}'.format(self.lineRate))
        self.prevClock = self.currClock

        # Compute signal RMS
        vrms = numpy.std(rfData[:, 1])
        self.vrmsLabel.setText('{:.2f}'.format(vrms))

        xEnv = rfData[:, 0]
        yEnv = rfData[:, 3]
        # Hack to show raw buffer data in lower display
        xEnv = numpy.array(range(self.dataObject.data.size))
        yEnv = self.dataObject.data
        self.rawDataCurve.set_data(xEnv, yEnv)
        plot = self.rawDataDialog.get_plot()
        plot.replot()

    def setMCU(self, MCU):
        self.MCU = MCU


class SimpleCurveDialog(CurveDialog):
    '''Method override to remove 'OK' & 'Cancel' buttons
    from the GUIQWT CurveDialog class
    '''
    def install_button_layout(self):
        pass


if __name__ == '__main__':
    init_FX3(usbDevice)
    app = QApplication(sys.argv)
    form = MainWindow()
    form.setWindowState(Qt.WindowMaximized)
    form.show()
    app.exec_()
