import serial
import math


class RadarTarget:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.speed = 0
        self.distance_res = 0
        self.distance = 0
        self.angle = 0

    def calculate(self):
        self.distance = math.sqrt(self.x**2 + self.y**2)
        self.angle = math.degrees(math.atan2(self.y, self.x))

    def __str__(self):
        return (f"Distance: {self.distance/10:.2f} cm | "
                f"Angle: {self.angle:.2f}° | "
                f"X: {self.x} mm | Y: {self.y} mm | "
                f"Speed: {self.speed} cm/s")


class RD03DRadar:

    MULTI_TARGET_CMD = bytes([
        0xFD, 0xFC, 0xFB, 0xFA,
        0x02, 0x00,
        0x90, 0x00,
        0x04, 0x03, 0x02, 0x01
    ])

    def __init__(self, port="/dev/serial0", baudrate=256000):
        self.ser = serial.Serial(port, baudrate, timeout=1)
        self.buffer = bytearray()

        self.targets = [
            RadarTarget(),
            RadarTarget(),
            RadarTarget()
        ]

        print("RD-03D Radar Initialized")

        # activate multi target mode
        self.ser.write(self.MULTI_TARGET_CMD)

    def read_data(self):
        while self.ser.in_waiting:
            byte = self.ser.read(1)
            self.buffer.extend(byte)

            if len(self.buffer) >= 2:
                if self.buffer[-1] == 0xCC and self.buffer[-2] == 0x55:
                    self.process_frame()
                    self.buffer.clear()

    def process_frame(self):

        if len(self.buffer) < 32:
            return

        data = self.buffer

        self.parse_target(0, data, 4)
        self.parse_target(1, data, 12)
        self.parse_target(2, data, 20)

        for i, t in enumerate(self.targets):
            print(f"Target {i+1}: {t}")

        print("------")

    def parse_target(self, index, data, offset):

        x = (data[offset] | (data[offset+1] << 8)) - 0x200
        y = (data[offset+2] | (data[offset+3] << 8)) - 0x8000
        speed = (data[offset+4] | (data[offset+5] << 8)) - 0x10
        dist_res = (data[offset+6] | (data[offset+7] << 8))

        target = self.targets[index]
        target.x = x
        target.y = y
        target.speed = speed
        target.distance_res = dist_res

        target.calculate()


def main():

    radar = RD03DRadar()

    while True:
        radar.read_data()


if __name__ == "__main__":
    main()