from bluepy.btle import Scanner, DefaultDelegate
import bluepy.btle as btle
import time
'''
sudo is needed for this functionality
'''


class ScanDelegate(DefaultDelegate):

    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            print("Discovered device", dev.addr)
        elif isNewData:
            print("Received new data from", dev.addr)

    @staticmethod
    def scanBluetoothDevices():
        scanner = Scanner().withDelegate(ScanDelegate())
        devices = scanner.scan(10.0)

        for dev in devices:
            print("Device %s (%s), RSSI=%d dB" %
                  (dev.addr, dev.addrType, dev.rssi))
            for (adtype, desc, value) in dev.getScanData():
                print("  %s = %s" % (desc, value))


'''
Device 88:25:83:f3:e9:f4 (public), RSSI=-53 dB
  Flags = 06
  Incomplete 16b Services = 0000ffe0-0000-1000-8000-00805f9b34fb
  Tx Power = 00
  Manufacturer = 484d882583f3e9f4
  16b Service Data = 00b000000000
  Complete Local Name = OTTO-BLE

'''


class BluetoothClient:

    def __init__(self, mac_address, UUID_service):
        self.mac_address = mac_address
        self.UUID_service = UUID_service

        # zl-rc04a
        self.peripheral = btle.Peripheral(mac_address)

        # GET SERVICES
        services = self.peripheral.getServices()
        for service in services:
            print(service)

        # NORMAL get to write to ...
        self.service = self.peripheral.getServiceByUUID(UUID_service)
        self.characteristic = self.service.getCharacteristics()[0]

    def disconnect(self):
        self.peripheral.disconnect()

    def sendCommand(self, commandStr):
        commandBytes = commandStr.encode('utf-8')
        self.characteristic.write(commandBytes)
        # self.characteristic.write(b'M 1 1000\r')


# ScanDelegate.scanBluetoothDevices()

'''
mac_address = "88:25:83:f3:e9:f4"
UUID_service = "0000ffe0-0000-1000-8000-00805f9b34fb"
bluetoothClient = BluetoothClient(mac_address, UUID_service)
bluetoothClient.sendCommand('M 1 1000\r')
time.sleep(5)
bluetoothClient.sendCommand('M 0 1000\r')
bluetoothClient.disconnect()
'''

'''
Command string
1.Stop: "S\r"
2.Buzzer: "T a b\r"   a is fre, b is duration
3.Movement: "M a b c\r" a is which movement, b is speed, c is moveSize (动作幅度)
  a
  'M 0' // stop
  'M 1' // up
  'M 2' // down
  'M 4' // right
  'M 3' // left
  'M 5' // updown
  'M 6' // moonwalkright
  'M 7' // moonwalkleft
  'M 8' // swing
  'M 9' // crossright
  'M 10' // crossleft
  'M 12' // flapfront
  'M 13' // flapback
  'M 14' // tiptoe
  'M 15' // bendright
  'M 16' // bendleft
  'M 17' // shakeright
  'M 18' // shakeleft
  'M 19' // jitter
  'M 20' // ascend

  b speed
  500 fast
  1000 medium
  1500 slow

  c moveSize ?

4.LED: "L a\r"
  L 000000001000010100100011000000000 == sad
  可能不好用
        { title: 'Happy', image: Images.humanoid.mouth.happy, cmd: 'L 0000000100001010010001100000000', stopAtEnd: false },
        { title: 'Super Happy', image: Images.humanoid.mouth.superhappy, cmd: 'L 0000000111111010010001100000000', stopAtEnd: false },
        { title: 'Love', image: Images.humanoid.mouth.love, cmd: 'L 0010010101101100001010010001100', stopAtEnd: false },
        { title: 'Sad', image: Images.humanoid.mouth.sad, cmd: 'L 0000000001100010010100001000000', stopAtEnd: false },
        { title: 'Fail', image: Images.humanoid.mouth.fail, cmd: 'L 0100001010010001100010010100001', stopAtEnd: false },
        { title: 'Confused', image: Images.humanoid.mouth.confused, cmd: 'L 0000000001000010101100010000000', stopAtEnd: false },
        { title: 'Fart', image: Images.humanoid.mouth.fart, cmd: 'L 0000000111111001001001001000110', stopAtEnd: false },
        { title: 'Fretful', image: Images.humanoid.mouth.fretful, cmd: 'L 0000000000000111111000000000000', stopAtEnd: false },
        { title: 'Angry', image: Images.humanoid.mouth.angry, cmd: 'L 0000000011110100001100001000000', stopAtEnd: false },
        { title: 'Sleeping', image: Images.humanoid.mouth.sleeping, cmd: 'L 0000000000000011000011000000000', stopAtEnd: false },
        { title: 'Magic', image: Images.humanoid.mouth.magic, cmd: 'L 0000000010010100001010010000000', stopAtEnd: false },
        { title: 'Victory', image: Images.humanoid.mouth.victory, cmd: 'L 0001100010010100001010010001100', stopAtEnd: false },
        { title: 'Wave', image: Images.humanoid.mouth.wave, cmd: 'L 0000000000011000100001000110000', stopAtEnd: false }

5. Gesture: "H a\r"
        { title: 'Happy', image: Images.gestures.happy, cmd: 'H 1', stopAtEnd: false },
        { title: 'Super Happy', image: Images.gestures.superhappy, cmd: 'H 2', stopAtEnd: false },
        { title: 'Love', image: Images.gestures.love, cmd: 'H 7', stopAtEnd: false },
        { title: 'Sad', image: Images.gestures.sad, cmd: 'H 3', stopAtEnd: false },
        { title: 'Fail', image: Images.gestures.fail, cmd: 'H 13', stopAtEnd: false },
        { title: 'Confused', image: Images.gestures.confused, cmd: 'H 6', stopAtEnd: false },
        { title: 'Fart', image: Images.gestures.fart, cmd: 'H 5', stopAtEnd: false },
        { title: 'Fretful', image: Images.gestures.fretful, cmd: 'H 9', stopAtEnd: false },
        { title: 'Angry', image: Images.gestures.angry, cmd: 'H 8', stopAtEnd: false },
        { title: 'Sleeping', image: Images.gestures.sleeping, cmd: 'H 4', stopAtEnd: false },
        { title: 'Magic', image: Images.gestures.magic, cmd: 'H 10', stopAtEnd: false },
        { title: 'Victory', image: Images.gestures.victory, cmd: 'H 12', stopAtEnd: false },
        { title: 'Wave', image: Images.gestures.wave, cmd: 'H 11', stopAtEnd: false }

6. Sing (Sound):
        { title: 'Sing 1', image: Images.sing.mode1, cmd: 'K 16', stopAtEnd: false },
        { title: 'Sing 2', image: Images.sing.mode2, cmd: 'K 17', stopAtEnd: false },
        { title: 'Sing 3', image: Images.sing.mode3, cmd: 'K 18', stopAtEnd: false },
        { title: 'OhOoh', image: Images.sing.ohooh, cmd: 'K 4', stopAtEnd: false },
        { title: 'Push', image: Images.sing.buttonPushed, cmd: 'K 19', stopAtEnd: false },
        { title: 'Kinda Happy', image: Images.sing.happyShort, cmd: 'K 10', stopAtEnd: false },
        { title: 'Happy', image: Images.sing.happy, cmd: 'K 8', stopAtEnd: false },
        { title: 'Super Happy', image: Images.sing.superHappy, cmd: 'K 9', stopAtEnd: false },
        { title: 'Sad', image: Images.sing.sad, cmd: 'K 11', stopAtEnd: false },
        { title: 'Sleeping', image: Images.sing.sleeping, cmd: 'K 7', stopAtEnd: false },
        { title: 'Surprise', image: Images.sing.surprise, cmd: 'K 3', stopAtEnd: false },
        { title: 'Disconnection', image: Images.sing.disconnection, cmd: 'K 2', stopAtEnd: false },
        { title: 'Confused', image: Images.sing.confused, cmd: 'K 12', stopAtEnd: false },
        { title: 'Fart', image: Images.sing.fart3, cmd: 'K 15', stopAtEnd: false },
        { title: 'Cuddly', image: Images.sing.cuddly, cmd: 'K 6', stopAtEnd: false }


  SCmd.addCommand("K", receiveSing);      //  sendAck & sendFinalAck
  SCmd.addCommand("C", receiveTrims);     //  sendAck & sendFinalAck
  SCmd.addCommand("G", receiveServo);     //  sendAck & sendFinalAck
  SCmd.addCommand("R", receiveName);      //  sendAck & sendFinalAck
  SCmd.addCommand("E", requestName);
  SCmd.addCommand("D", requestDistance);
  SCmd.addCommand("N", requestNoise);
  SCmd.addCommand("B", requestBattery);   // 3v7 lipo battery
  SCmd.addCommand("I", requestProgramId);
  SCmd.addCommand("J", requestMode);
  SCmd.addCommand("P", requestRGB);
  SCmd.addDefaultHandler(receiveStop);

'''