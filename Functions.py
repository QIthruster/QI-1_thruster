#
# QI thruster based on Raspberry Pi 4B
#
# Serial port interface (SPI) with the digital potentiometer:
#   GPIO 7 - SPI CE1
#   GPIO 11 - SPI CLK
#   GPIO 10 - SPI MOSI
#
# The second SPI is reserved for ADC
#
# GPIO outputs:
#   GPIO 21 - enable 15 V OpAmp
#   GPIO 20 - red LED for ON/OFF of 15 V OpAmp
#   GPIO 16 - red LED for low battery
#   GPIO 19 - reserved or multiplexer CH1
#   GPIO 26 - reserved or multiplexer CH2
#
# ADC inputs:
#   In 9 - battery (1/3 potential divider and 5 V buffer)
#   In 8 - 15 V OpAmp output (1/3 potential divider and 5 V buffer)
#   In 7 - HV output (1/1000 potential divider and 5 V buffer)
#   In 6 - reserved or sensor input (5 V buffer)
#   In 5 - reserved or sensor input (5 V buffer)
#   In 4 - reserved or sensor input (without buffer)
#   In 3 - reserved or sensor input (without buffer)

import spidev
import time
import ADS1263
import RPi.GPIO as GPIO
import os

#GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Activating the digital potentiometer
spi = spidev.SpiDev()
spi.open(0, 1)
spi.max_speed_hz = 976000

# Activating ADC HAT
REF = 5.0  # Reference voltage for ADC HAT  
ADC = ADS1263.ADS1263()
ADC.ADS1263_init()

# Position of the digital potentiometer slider
def write_pot(input):
    msb = input >> 8
    lsb = input & 0xFF
    spi.xfer([msb, lsb])

# Reading the voltage at the ADC channels
def Read_ADC(Ch):
    ADC_Value = ADC.ADS1263_GetAll()
    try:
        control = ADC_Value[1]
    except:
        print('Error with reading ADC. The program will be terminated')
        GPIO_OFF()
        write_pot(0x00)
        OpAmp_ES('OFF')
        exit()

    Voltage = 0.0
    try:
        if(ADC_Value[Ch]>>31 ==1):
            Voltage = REF * 2 - ADC_Value[Ch] * REF / 0x80000000
        else:
            Voltage = ADC_Value[Ch] * REF / 0x7fffffff
    except:
        print('Error with reading ADC. The program will be terminated')
        GPIO_OFF()
        write_pot(0x00)
        OpAmp_ES('OFF')
        exit()

    return Voltage

#    try:
#        ADC_Value = ADC.ADS1263_GetAll()
#        if(ADC_Value[Ch]>>31 ==1):
#            Voltage = REF * 2 - ADC_Value[Ch] * REF / 0x80000000
#        else:
#            Voltage = ADC_Value[Ch] * REF / 0x7fffffff
#        return Voltage
#    except:
#        exit()
#    return Voltage

# 15 Vcc Op Amp ON/OFF with the red LED indication
def OpAmp_ES(output):
    opamp = 21  # controlling op am amp output
    LED = 20  # Red LED for op amp ON/OFF
    GPIO.setup(opamp, GPIO.OUT)
    GPIO.setup(LED, GPIO.OUT)
    if output == 'ON':
        GPIO.output(opamp, GPIO.HIGH)
        GPIO.output(LED, GPIO.HIGH)
    elif output == 'OFF':
        GPIO.output(opamp, GPIO.LOW)
        GPIO.output(LED, GPIO.LOW)

# All GPIO outputs OFF
def GPIO_OFF():
    LED16 = 16  # Red LED for low battery
    LED20 = 20  # Red LED for Op Amp
    GPIO19 = 19  # reserved (or current sensor range 1)
    GPIO26 = 26  # reserved (or current sensor range 2)
    GPIO.setup(LED16, GPIO.OUT)
    GPIO.setup(LED20, GPIO.OUT)
    GPIO.setup(GPIO19, GPIO.OUT)
    GPIO.setup(GPIO26, GPIO.OUT)
    GPIO.output(LED16, GPIO.LOW)
    GPIO.output(LED20, GPIO.LOW)
    GPIO.output(GPIO19, GPIO.LOW)
    GPIO.output(GPIO26, GPIO.LOW)

# Controlling the battery charge
def Battery():
    LED = 16  # Red LED for the battery
    GPIO.setup(LED, GPIO.OUT)
    V = Read_ADC(9) * 3.0
    print('Battery voltage = ', V, ' V')
    if 6.0 <= V <= 6.5:
        print('Warning: Battery is low!')
        GPIO.output(LED, GPIO.HIGH)
    elif V < 6.0:
        print('Warning: Raspberry Pi will be shutdown in 5 s because the battery is dangerously low (< 6 V)')
        time.sleep(5)
        GPIO_OFF()  # All GPIO outputs OFF
        write_pot(0x00)  # nulling the output of digital potentiometer
        OpAmp_ES('OFF')  # OpAmp if OFF
        os.system("shutdown now -h")

# Voltage one step up
def HV_up(Previous_NS, tau):

    hex_Previous_NS = int(hex(Previous_NS), 16)
    i = hex_Previous_NS
    HV_actual = Read_ADC(7)  # actual HV across the capacitor

    if i <= 0x101 and HV_actual <= 4.0:
        i = i + 0x01
        write_pot(i)
        OpAmp = Read_ADC(8) * 6.0  # output of Op Amp (Vcc = 15 V)
        time.sleep(tau)  # waiting for the capacitor charge
        HV_actual = Read_ADC(7)
    else:
        OpAmp = Read_ADC(8) * 6.0  # output of Op Amp (Vcc = 15 V)

    Battery()
    print('Op Amp output = ', OpAmp, ' V')
    print('Actual HV output = ', HV_actual, ' kV')

    NS_stop = i
            
    return NS_stop, OpAmp, HV_actual

# Voltage one step down
def HV_down(Previous_NS, tau):
    
    hex_Previous_NS = int(hex(Previous_NS), 16)
    i = hex_Previous_NS

    if 0x00 < i:
        i = i - 0x01
        write_pot(i)
        OpAmp = Read_ADC(8) * 6.0
        time.sleep(tau)  # waiting for the capacitor discharge
        HV_actual = Read_ADC(7)
    else:
        OpAmp = Read_ADC(8) * 6.0  # output of Op Amp (Vcc = 15 V)
        HV_actual = Read_ADC(7)  # actual HV across the QI capacitor

    Battery()
    print('Op Amp output = ', OpAmp, ' V')
    print('Actual HV output = ', HV_actual, ' kV')

    NS_stop = i
   
    return NS_stop, OpAmp, HV_actual

# Current sensor range
def CurrentSensorRange(range):
    range1 = 19
    range2 = 26
    GPIO.setup(range1, GPIO.OUT)
    GPIO.setup(range2, GPIO.OUT)
    GPIO.output(range1, GPIO.LOW)
    GPIO.output(range2, GPIO.LOW)
    if range == 1:
        GPIO.output(range1, GPIO.HIGH)
    elif range == 2:
        GPIO.output(range2, GPIO.HIGH)

# Current sensor CS-1
# Sensor resistance 15.6 k (+/- 0.1%, low voltage)
# Series resistance 1.5 MOhms (high voltage)
# This sensor was calibrated with ADC In 3 without a buffer. The calibration file was saved on Raspberry Pi.
def CurrentSensor(bias, Ch):
    x = (Read_ADC(Ch) - bias)
    y = -0.11372504497803 * x**8 + 1.4343168169319 * x**7 -7.3278668065487 * x**6 + \
        19.4325718360446 * x**5 - 28.448512253201 * x**4 + \
        22.3174566367283 * x**3 - 7.6319260686742 * x**2 + 1.1951000922818 * x
    #return x  # used during the sensor calibration
    return y
