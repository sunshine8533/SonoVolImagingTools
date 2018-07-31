import ctypes


if ctypes.sizeof(ctypes.c_voidp) == 8:
    cCyAPI = ctypes.CDLL('x64/CyAPI_C.dll')
else:
    cCyAPI = ctypes.CDLL('x86/CyAPI_C.dll')
cCyAPI.getUSBDeviceNTStatus.restype = ctypes.c_ulong
cCyAPI.getUSBDeviceUSBDStatus.restype = ctypes.c_ulong
cCyAPI.getUSBEndpointNTStatus.restype = ctypes.c_ulong
cCyAPI.getUSBEndpointUSBDStatus.restype = ctypes.c_ulong
cCyAPI.getUSBEndpointTimeout.restype = ctypes.c_ulong
cCyAPI.getUSBEndpointPacketSize.restype = ctypes.c_ushort


FX3_FIRMWARE_DOWNLOAD_MEDIA_TYPE_RAM = 1
FX3_FIRMWARE_DOWNLOAD_MEDIA_TYPE_I2CE2PROM = 2
FX3_FIRMWARE_DOWNLOAD_MEDIA_TYPE_SPIFLASH = 3

FX3_FIRMWARE_DOWNLOAD_ERROR_CODE_SUCCESS = 0


class USBDevice:

    def __init__(self):
        self.cCyAPI = cCyAPI
        self._cUSBDevice = cCyAPI.newUSBDevice()

    def __del__(self):
        if cCyAPI is not None:  # TODO: Ensure that cCyAPI doesn't get cleaned up before this
            cCyAPI.deleteUSBDevice(self._cUSBDevice)

    def open(self, index):
        return bool(cCyAPI.openUSBDevice(self._cUSBDevice, index))

    def reset(self):
        return bool(cCyAPI.resetUSBDevice(self._cUSBDevice))

    def close(self):
        cCyAPI.closeUSBDevice(self._cUSBDevice)

    @property
    def isOpen(self):
        return bool(cCyAPI.isUSBDeviceOpen(self._cUSBDevice))

    @property
    def ntStatus(self):
        return cCyAPI.getUSBDeviceNTStatus(self._cUSBDevice)

    @property
    def usbdStatus(self):
        return cCyAPI.getUSBDeviceUSBDStatus(self._cUSBDevice)

    def getEndpoint(self, index):
        return USBEndpoint(cCyAPI.getUSBDeviceEndpoint(
            self._cUSBDevice, index))

    @property
    def bulkInEndpoint(self):
        return USBEndpoint(cCyAPI.getUSBDeviceBulkInEndpoint(
            self._cUSBDevice))

    @property
    def bulkOutEndpoint(self):
        return USBEndpoint(cCyAPI.getUSBDeviceBulkOutEndpoint(
            self._cUSBDevice))

    @property
    def controlEndpoint(self):
        return USBEndpoint(cCyAPI.getUSBDeviceControlEndpoint(
            self._cUSBDevice))

    @property
    def interruptInEndpoint(self):
        return USBEndpoint(cCyAPI.getUSBDeviceInterruptInEndpoint(
            self._cUSBDevice))

    @property
    def interruptOutEndpoint(self):
        return USBEndpoint(cCyAPI.getUSBDeviceInterruptOutEndpoint(
            self._cUSBDevice))

    @property
    def isocInEndpoint(self):
        return USBEndpoint(cCyAPI.getUSBDeviceisocInEndpoint(
            self._cUSBDevice))

    @property
    def isocOutEndpoint(self):
        return USBEndpoint(cCyAPI.getUSBDeviceIsocOutEndpoint(
            self._cUSBDevice))


class FX3Device(USBDevice):

    def __init__(self):
        self._cUSBDevice = cCyAPI.newFX3Device()

    @property
    def isBootloaderRunning(self):
        return bool(cCyAPI.isFX3DeviceBootloaderRunning(
            self._cUSBDevice))

    def downloadFirmware(self, filename, mediaType):
        return cCyAPI.downloadFirmwareToFX3Device(
            self._cUSBDevice, filename, mediaType)


class USBEndpoint:

    def __init__(self, cUSBEndpoint):
        self._cUSBEndpoint = cUSBEndpoint

    @property
    def ntStatus(self):
        return cCyAPI.getUSBEndpointNTStatus(self._cUSBEndpoint)

    @property
    def usbdStatus(self):
        return cCyAPI.getUSBEndpointUSBDStatus(self._cUSBEndpoint)

    @property
    def timeout(self):
        return cCyAPI.getUSBEndpointTimeout(self._cUSBEndpoint)

    @timeout.setter
    def timeout(self, value):
        cCyAPI.setUSBEndpointTimeout(self._cUSBEndpoint, value)

    @property
    def packetSize(self):
        return cCyAPI.getUSBEndpointPacketSize(self._cUSBEndpoint)

    def xferData(self, array):
        return bool(cCyAPI.xferDataToUSBEndpoint(
            self._cUSBEndpoint, array.ctypes.data, array.nbytes))

    def reset(self):
        return bool(cCyAPI.resetUSBEndpoint(self._cUSBEndpoint))
