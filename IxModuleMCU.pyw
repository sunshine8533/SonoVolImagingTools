import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import serial
import struct
import time


class MCUWidget(QWidget):
    def __init__(self, parent=None):
        super(MCUWidget, self).__init__(parent)

        self.setWindowTitle('MCU')

        self.MCU = MCU()

        # Port connection
        self.connectButton = QPushButton('Connect to:')
        self.portIdEdit = QLineEdit('Enter Port ID Here')
        self.MCU.autoConnect()
        if self.MCU.connected:
            self.portIdEdit.setText(self.MCU.name)

        # Manual trigger
        self.manualTriggerButton = QPushButton('Trigger')
       
        self.startScanButton = QPushButton('Scan')
        self.stopScanButton = QPushButton('Stop')

        # Toggle transfer state
        self.manualTransferButton = QPushButton('Transfer')

        # Pulse amplitude (+)
        self.pulsePAmpButton = QPushButton('+ Pulse Amplitude: ')
        self.pulsePAmpSpinBox = QDoubleSpinBox()
        self.pulsePAmpSpinBox.setRange(0, 255)
        self.pulsePAmpSpinBox.setDecimals(0)
        self.pulsePAmpSpinBox.setSingleStep(1)
        self.pulsePAmpSpinBox.setValue(255)

        # Pulse amplitude (-)
        self.pulseNAmpButton = QPushButton('- Pulse Amplitude: ')
        self.pulseNAmpSpinBox = QDoubleSpinBox()
        self.pulseNAmpSpinBox.setRange(0, 255)
        self.pulseNAmpSpinBox.setDecimals(0)
        self.pulseNAmpSpinBox.setSingleStep(1)
        self.pulseNAmpSpinBox.setValue(255)

        # Gain control
        self.hiloButton = QPushButton('HI/LO')
        self.hiloButton.setCheckable(True)

        # Minimum gain
        self.minGainButton = QPushButton('Minimum Gain: ')
        self.minGainSpinBox = QDoubleSpinBox()
        self.minGainSpinBox.setRange(0, 255)
        self.minGainSpinBox.setDecimals(0)
        self.minGainSpinBox.setSingleStep(1)
        self.minGainSpinBox.setValue(127)

        # TGC slope
        self.tgcSlopeButton = QPushButton('TGC Slope: ')
        self.tgcSlopeSpinBox = QDoubleSpinBox()
        self.tgcSlopeSpinBox.setRange(0, 255)
        self.tgcSlopeSpinBox.setDecimals(0)
        self.tgcSlopeSpinBox.setSingleStep(1)
        self.tgcSlopeSpinBox.setValue(127)

        ###############
        # Widget layout
        ###############

        grid = QGridLayout()
        row = 0

        grid.addWidget(self.connectButton, row, 0)
        grid.addWidget(self.portIdEdit, row, 1)
        row += 1

        logicLabel = QLabel('Logic Control')
        grid.addWidget(logicLabel, row, 0)
        row += 1

        grid.addWidget(self.manualTriggerButton, row, 0)
        row += 1

        grid.addWidget(self.manualTransferButton, row, 0)
        row += 1

        grid.addWidget(self.startScanButton, row, 0)
        row += 1

        grid.addWidget(self.stopScanButton, row, 0)
        row += 1

        pulseSectionLabel = QLabel('Pulser Control')
        grid.addWidget(pulseSectionLabel, row, 0)
        row += 1

        grid.addWidget(self.pulsePAmpButton, row, 0)
        grid.addWidget(self.pulsePAmpSpinBox, row, 1)
        row += 1

        grid.addWidget(self.pulseNAmpButton, row, 0)
        grid.addWidget(self.pulseNAmpSpinBox, row, 1)
        row += 1

        gainSectionLabel = QLabel('Gain Control')
        grid.addWidget(gainSectionLabel, row, 0)
        row += 1

        grid.addWidget(self.hiloButton, row, 0)
        row += 1

        grid.addWidget(self.minGainButton, row, 0)
        grid.addWidget(self.minGainSpinBox, row, 1)
        row += 1

        grid.addWidget(self.tgcSlopeButton, row, 0)
        grid.addWidget(self.tgcSlopeSpinBox, row, 1)
        row += 1

        vBox = QVBoxLayout()
        vBox.addLayout(grid)
        vBox.addStretch()

        self.setLayout(vBox)

        ###################
        # Signals and slots
        ###################

        self.connect(self.connectButton, SIGNAL('clicked()'), self.connectMCU)

        self.connect(self.manualTriggerButton, SIGNAL('clicked()'), self.manualTrigger)
        self.connect(self.manualTransferButton, SIGNAL('clicked()'), self.manualTransfer)

        self.connect(self.startScanButton, SIGNAL('clicked()'), self.startScan)
        self.connect(self.stopScanButton, SIGNAL('clicked()'), self.stopScan)
        
        self.connect(self.pulsePAmpButton, SIGNAL('clicked()'), self.setPPulse)
        self.connect(self.pulsePAmpSpinBox, SIGNAL('valueChanged(double)'), self.setPPulse)
        self.connect(self.pulseNAmpButton, SIGNAL('clicked()'), self.setNPulse)
        self.connect(self.pulseNAmpSpinBox, SIGNAL('valueChanged(double)'), self.setNPulse)
        
        self.connect(self.hiloButton, SIGNAL('clicked()'), self.setHiLo)
        self.connect(self.minGainButton, SIGNAL('clicked()'), self.setMinGain)
        self.connect(self.minGainSpinBox, SIGNAL('valueChanged(uint)'), self.setMinGain)
        self.connect(self.tgcSlopeButton, SIGNAL('clicked()'), self.setTgcSlope)
        self.connect(self.tgcSlopeSpinBox, SIGNAL('valueChanged(uint)'), self.setTgcSlope)

    def connectMCU(self):
        portIDtext = unicode(self.portIdEdit.text())
        self.MCU.connect(portIDtext)

    def closePort(self):
        self.MCU.close()

    def manualTrigger(self):
        val = self.MCU.manualTrigger()
        return val

    def manualTransfer(self):
        val = self.MCU.manualTransfer()
        return val

    def startScan(self):
        val = self.MCU.startScan()
        return val

    def stopScan(self):
        val = self.MCU.stopScan()
        return val

    def setPPulse(self):
        val = self.pulsePAmpSpinBox.value()
        code = self.MCU.setPPulse(val)
        print code

    def setNPulse(self):
        val = self.pulseNAmpSpinBox.value()
        code = self.MCU.setNPulse(val)
        print code

    def setHiLo(self):
        code = self.MCU.setHiLo(2)
        print code

    def setMinGain(self):
        val = self.minGainSpinBox.value()
        code = self.MCU.setMinGain(val)
        print code

    def setTgcSlope(self):
        val = self.tgcSlopeSpinBox.value()
        code = self.MCU.setTgcSlope(val)
        print code


class MCU(serial.Serial):
    '''Class definition for serial communication to Arduino
    w/ added functionality specific to the MCU

    Notes:
    1 - MCU is inherited form serial.Serial
    2 - Initialization does not open the serial connection
    3 - Do not directly call the inherited open() method, as
        the Arduino requires reboot time, the connect() method
        allows for this.
    '''

    opCode = {
        'TRIGGER_MANUAL':   0,
        'TRANSFER_TOGGLE':  1,
        'PPULSE':           3,
        'NPULSE':           4,
        'HILO':             5,
        'TGC_START':        7,
        'TGC_SLOPE':        8,
        'ECHO':             9,
        'START_SCAN':       10,
        'STOP_SCAN':        11,
    }

    fmtCode = {
        'ubyte':    'B',
        'ushort':   'H',
        'float':    'f',
    }

    def __init__(self):
        '''Initialize the serial class but do not open connection'''
        serial.Serial.__init__(self, port=None, baudrate=115200, timeout=1.0, writeTimeout=1.0)
        self.connected = False
    def listPorts(self):

        port_list = []
        # Quickly scan all possible COM port addresses
        import serial
        for i in range(256):
            try:
                sTest = serial.Serial('COM%s'%(i))
                port_list.append(sTest.portstr)
                sTest.close()
            except serial.SerialException:
                pass

        return port_list

    def connect(self, portID):
        '''Connect to the specified port and pause for Arduino reboot'''
        self.port = portID
        echo = 5
        ntrials = 3
        try:
            # Ensure the specified port is close to begin with
            self.close()
            self.open()
        except serial.SerialException:
            self.close()
            self.port = ''
            self.connected = False
            return False
            
        # Wait for device to reboot            
        time.sleep(2.0)          
        for trial in range(ntrials):
            self.reset_input_buffer()
            self.reset_output_buffer()
            # Test connection
            try:
                e = int(self.sendEcho(echo))                
                if e == echo:
                    self.connected = True
                    return True
            except:
                pass

        self.close()
        self.port = ''
        self.connected = False
        return False

    def autoConnect(self):
        if self.connected:
            return True
            
        port_list = self.listPorts()

        for port in port_list:
            if self.connect(port):
                break
            else:
                self.connected = False
                self.port = ''
        return self.connected
    
    def _read(self):
        for i in range(50):
            time.sleep(0.005)
            if self.inWaiting() >0:
                break
        t = -1
        #time.sleep(0.05)
        while self.inWaiting() >0:
            line = self.readline()
            t = line[:-2]
            if t.isdigit():
                t = int(t)
            else:
                time.sleep(0.1)
                #print line
        return t
        
    def _send(self, cmd, data, fmt):
        '''Private function used to send serial data'''

        try:
            cmdString = struct.pack(self.fmtCode['ubyte'], cmd)
            self.write(cmdString)
            if data != None:
                dataString = struct.pack(fmt, data)
                self.write(dataString)
            #time.sleep(0.05)
            return True

        except:
            return False

    def manualTrigger(self):
        k = 1
        '''Generate a single trigger event'''
        while self.inWaiting() > 0:
            self._read()
        while True:
            self.flushInput()    
            self._send(self.opCode['TRIGGER_MANUAL'], None, self.fmtCode['ushort'])
            r = self._read()
            if r == k:
                break
            else:
                #print 'Reply failed'
                time.sleep(0.1)
        return r

#    def startScan(self):
#        '''Start continuous scanning'''
#        while self.inWaiting() > 0:
#            self._read()
#        self.flushInput()
#        self._send(self.opCode['START_SCAN'], None, self.fmtCode['ushort'])
#        while self.inWaiting() <= 0:
#            pass
#        return int(self.readline())
#
#    def stopScan(self):
#        '''Stop Continuous scanning'''
#        while self.inWaiting() > 0:
#            self._read()
#        self.flushInput()
#        self._send(self.opCode['STOP_SCAN'], None, self.fmtCode['ushort'])
#        # TODO: JRL - bug - arduino won't reply over usb after stop code...
#        while self.inWaiting() <= 0:
#            pass
#        return int(self.readline())

    def setPPulse(self, k):
        r=-1
        if 0 <= k <= 255:
            setVal = int(k)
            while True:
                self._send(self.opCode['PPULSE'], setVal, self.fmtCode['ushort'])
                r = self._read()
                if r == k:
                    break
            return r
            #return int(self.readline())

    def setNPulse(self, k):
        r=-1
        if 0 <= k <= 255:
            setVal = int(k)
            while True:
                self._send(self.opCode['NPULSE'], setVal, self.fmtCode['ushort'])
                r = self._read()
                if r == k:
                    break
            #return int(self.readline())
            return r
            
    def setHiLo(self, k):
        '''Set the Hi/Lo post amp'''
        r=-1
        setVal = int(k)
        if setVal ==2:
            while True:
                self._send(self.opCode['HILO'], setVal, self.fmtCode['ushort'])
                r = self._read()
                if r != -1:
                    break
            return r
        else:
            while True:
                self._send(self.opCode['HILO'], setVal, self.fmtCode['ushort'])
                r = self._read()
                if r == k:
                    break
            return r

    def setMinGain(self, k):
        r=-1
        if 0 <= k <= 255:
            setVal = int(k)
            while True:
                self._send(self.opCode['TGC_START'], setVal, self.fmtCode['ushort'])
                r = self._read()
                if r == k:
                    break
            return r

    def setTgcSlope(self, k):
        r=-1
        if 0 <= k <= 255:
            setVal = int(k)
            while True:
                self._send(self.opCode['TGC_SLOPE'], setVal, self.fmtCode['ushort'])
                r = self._read()
                if r == k:
                    break
            return r

    def sendEcho(self, echoCode):
        self._send(self.opCode['ECHO'], echoCode, self.fmtCode['ushort'])
        return self.readline()


if __name__ == '__main__':
    app = QApplication(sys.argv)
#    form = MCUWidget()
#    form.show()
#    app.exec_()
