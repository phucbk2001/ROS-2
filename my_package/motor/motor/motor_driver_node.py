#!/usr/bin/python3

import subprocess
import time
from click import prompt
import serial
import re
import json


import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
from geometry_msgs.msg import Twist


# =========== Configurable parameters =============
# Serial parameters
SKIP_SERIAL_LINES = 12
LIDAR_USB_NAME = "FTDI USB Serial Device"
MCU_USB_NAME = "cp210x"
BAUD_RATE = 115200
RECEIVING_FREQUENCY = 2000

# Node parameters
PUBLISH_FREQUENCY = 100

# =================================================

# Non-configure parameters
# Node parameters
receiving_timer = time.time()
publish_timer = time.time()
RECEIVING_PERIOD = 1
""" The timer will be started and every ``PUBLISH_PERIOD`` number of seconds the provided\
    callback function will be called. For no delay, set it equal ZERO. """
PUBLISH_PERIOD = 0

# Serial parameters
MCUSerialObject = None
foundMCU = False
foundLidar = False
serialData = ""
dictionaryData = {}

# JSON parameters
KEY = "pwm_pulse"
STORE_POS_1 = 0
STORE_POS_2 = 0
POS_1 = 0
POS_2 = 0


def checkConditions():
    global RECEIVING_PERIOD, PUBLISH_PERIOD
    if RECEIVING_FREQUENCY <= 0:
        raise Exception("RECEIVING_FREQUENCY must be an positive integer!")
    RECEIVING_PERIOD = 1 / RECEIVING_FREQUENCY

    if PUBLISH_FREQUENCY <= 0:
        raise Exception("PUBLISH_FREQUENCY must be an positive integer!")
    PUBLISH_PERIOD = 1 / PUBLISH_FREQUENCY


class Motor(object):
    def __init__(
        self, diameter, pulse_per_round_of_encoder, pwm_frequency, sample_time
    ):
        # Check conditions of Motor parameters
        self.checkConditions(
            diameter, pulse_per_round_of_encoder, pwm_frequency, sample_time
        )

        # Initialize private parameters

        # Initialize Kalman Filter

        # Initialize PID controller

    def checkConditions(
        self, diameter, pulse_per_round_of_encoder, pwm_frequency, sample_time
    ):
        self.checkDiamater(diameter)
        self.checkPulsePerRoundOfEncoder(pulse_per_round_of_encoder)
        self.checkPwmFrequency(pwm_frequency)
        self.checkSampleTime(sample_time)

    def checkDiamater(self, diameter):
        if float(diameter) and diameter > 0:
            self.__diameter = diameter
        else:
            raise Exception("Invalid value of diameter!")

    def checkPulsePerRoundOfEncoder(self, pulse_per_round_of_encoder):
        if float(pulse_per_round_of_encoder) and pulse_per_round_of_encoder > 0:
            self.__pulse_per_round_of_encoder = pulse_per_round_of_encoder
        else:
            raise Exception("Invalid value of pulse_per_round_of_encoder!")

    def checkPwmFrequency(self, pwm_frequency):
        if float(pwm_frequency) and pwm_frequency > 0:
            self.__pwm_frequency = pwm_frequency
        else:
            raise Exception("Invalid value of pwm_frequency!")

    def checkSampleTime(self, sample_time):
        if float(sample_time) and sample_time > 0:
            self.__sample_time = sample_time
        else:
            raise Exception("Invalid value of sample_time!")

    # Calculate RPM of motor
    def calculateRPM():
        

class MotorDriverNode(Node):
    def __init__(self):
        super().__init__("motor_driver")
        self.__need_publish = True
        self.left_ticks_pub = self.create_publisher(Int32, "left_ticks", 1)
        self.right_ticks_pub = self.create_publisher(Int32, "right_ticks", 1)
        self.timer = self.create_timer(0, self.publisherCallback)

        self.controller_sub = self.create_subscription(
            Twist, "cmd_vel", self.subscriberCallback, 1
        )
        self.controller_sub  # prevent unused variable warning

    def setNeedPublish(self):
        self.__need_publish = True

    def resetNeedPublish(self):
        self.__need_publish = False

    def publisherCallback(self):
        if self.__need_publish:
            left_ticks = Int32()
            right_ticks = Int32()
            left_ticks.data = POS_1
            right_ticks.data = POS_2
            self.left_ticks_pub.publish(left_ticks)
            self.right_ticks_pub.publish(right_ticks)
            # self.get_logger().info('Publishing: "%s"' % msg.data)

    def subscriberCallback(self, msg):
        driveMotors(msg)


def driveMotors(msg):
    # Kalman Filter
    # PID
    # controlMotors()

    data = {"pwm_pulse": [msg.linear.x * 1023 / 0.6, msg.linear.x * 1023 / 0.6]}
    data = json.dumps(data)
    MCUSerialObject.write(formSerialData(data))


def getMCUSerial():
    global foundMCU, foundLidar
    MCUSerial = None
    output = subprocess.getstatusoutput("dmesg | grep ttyUSB")
    stringDevices = list(output[1].split("\n"))
    stringDevices.reverse()

    for device in stringDevices:
        if device.find(MCU_USB_NAME) > 0 and not foundMCU:
            if device.find("disconnected") > 0:
                raise Exception("MCU is disconnected!")
            else:
                # print("MCU in serial: " + device.split()[-1])
                foundMCU = True
                MCUSerial = device.split()[-1]
                break

        # elif (device.find(LIDAR_USB_NAME) > 0 and not foundLidar):
        #     if (device.find("disconnected") > 0):
        #         raise Exception("Lidar is disconnected!")
        #     else:
        #         # print("Lidar in serial: " + device.split()[-1])
        #         foundLidar = True
        #         continue

    return MCUSerial


def initializeSerial():
    global MCUSerialObject
    MCUSerial = getMCUSerial()
    if MCUSerial:
        MCUSerialObject = serial.Serial(
            port="/dev/" + MCUSerial,
            baudrate=BAUD_RATE,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1,
            write_timeout=1,
        )

    skipLines = SKIP_SERIAL_LINES
    MCUSerialObject.setDTR(False)
    time.sleep(0.1)
    MCUSerialObject.reset_input_buffer()
    MCUSerialObject.setDTR(True)

    while skipLines:
        # Skip some lines of serial when MCU is reseted
        MCUSerialObject.readline()
        skipLines = skipLines - 1

    time.sleep(0.1)


def readSerialData():
    global serialData, dictionaryData
    rawData = MCUSerialObject.readline()
    # print(rawData)
    serialData = rawData.decode("windows-1252")  # decode s
    serialData = serialData.rstrip()  # cut "\r\n" at last of string
    filteredSerialData = re.sub(
        "[^A-Za-z0-9\s[]{}]", "", serialData
    )  # filter regular characters
    # print(filteredSerialData)
    try:
        dictionaryData = json.loads(filteredSerialData)
    except:
        return


def updateStorePosFromSerial():
    global STORE_POS_1, STORE_POS_2
    # MCUSerialObject.write(formSerialData("{pwm_pulse:[1023,1023]}"))
    readSerialData()
    # print("left tick: " + str(dictionaryData["left_tick"]))
    # print("right tick: " + str(dictionaryData["right_tick"]))
    STORE_POS_1 = dictionaryData["left_tick"]
    STORE_POS_2 = dictionaryData["right_tick"]


def updatePosFromStorePos():
    global POS_1, POS_2
    POS_1 = STORE_POS_1
    POS_2 = STORE_POS_2


def manuallyWrite():
    # A command is appended with "#" to mark as finish
    command = prompt("Command") + "#"
    command = bytes(command, "utf-8")
    MCUSerialObject.write(command)


def formSerialData(stringData):
    stringData += "#"
    data = bytes(stringData, "utf-8")
    return data


def setup():
    checkConditions()
    initializeSerial()


def loop(args=None):
    global receiving_timer, publish_timer, POS_1, POS_2
    rclpy.init(args=args)
    motor_driver_node = MotorDriverNode()

    try:
        while True:
            # manuallyWrite()
            if time.time() - receiving_timer >= RECEIVING_PERIOD:
                updateStorePosFromSerial()
                receiving_timer = time.time()

            if time.time() - publish_timer >= PUBLISH_PERIOD:
                updatePosFromStorePos()
                motor_driver_node.setNeedPublish()
                rclpy.spin_once(motor_driver_node)
                motor_driver_node.resetNeedPublish()
                publish_timer = time.time()

            rclpy.spin_once(motor_driver_node)

    except KeyboardInterrupt:
        MCUSerialObject.write(formSerialData("{pwm_pulse:[0,0]}"))
        MCUSerialObject.close()


def main():
    setup()
    loop()


if __name__ == "__main__":
    main()
