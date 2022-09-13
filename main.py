from Functions import *
import numpy as np
import time
from pynput import keyboard
from datetime import datetime

# Measurement parameters (program inputs)
R_series = 1.5  # resistance in series with the QI capacitor in MOhms
R_shunt = 25.0  # shunting resistor across the QI capacitor in MOhms
C = 0.01  # estimated QI capacitance in uF (micro Farads)
factor_up = 5.0  # (factor_up * tau_up) is the waiting time for the capacitor full charge
factor_down = 5.0  # (factor_down * tau_down) is the waiting time for the capacitor full discharge
current_range = 1  # operational range of the current sensor; range 1 - GPIO 19, range 2 - GPIO 26
Ch = 3  # Your channel (ADC In 3 - In 6) for the current sensor. In 5 and 6 are internally buffered.
# The current sensor function CurrentSensor(bias, Ch) is in Functions.py

# ****************************< Do not change anything below >*********************************************************
# Rescaling the measurement parameters
R_series = R_series * 1.0e+6  # MOhms to Ohms
R_shunt = R_shunt * 1.0e+6  # MOhms to Ohms
C = C * 1.0e-6  # uF to F

# Initial configuration of the device
GPIO_OFF()
write_pot(0x00)  # nulling the output of digital potentiometer
OpAmp_ES('OFF')  # OpAmp is OFF

# Capacitor charging and discharging characteristic times
tau_up = R_series * C  # charging characteristic time in seconds
tau_down = (R_series + R_shunt) * C  # discharging characteristic time in seconds
initial_discharge = factor_down * tau_down
print('')
print('Wait for the initial safety discharge of capacitor... ', initial_discharge, ' s')
time.sleep(initial_discharge)
print('')

# Starting measurements
print('Wait, we are calibrating the current sensor...')
print('')
# Calibration of the current sensor
CurrentSensorRange(current_range)
bias = 0.0
for i in range(10):
    bias = bias + Read_ADC(Ch)
bias = bias / 10.0
print('Bias voltage measured at the current sensor output = ', bias, ' V')
print('')

print('To stop the program, push the "Esc" button')
print('To increase or decrease the voltage by one step push the "Shift" or "Ctrl" button respectively')
print('After each push, wait for the indication!')
print('You will also be prompted to manually enter the thrust value from the electronic scale')
print('')

Message = 'Enter the file name (without extension) in which you want to save the measurement data (or "q" to quit): '
key = 1
name = 'Failed_attempt'
try:
    name = str(input(Message))
    if name == 'q' or name == 'Q':
        GPIO_OFF()
        write_pot(0x00)
        OpAmp_ES('OFF')
        key = 0
        print('')
except:
    print('')
    print('The program was terminated due to an invalid file name. Please try again')
    GPIO_OFF()
    write_pot(0x00)
    OpAmp_ES('OFF')
    exit()

if key == 0:
    exit()
else:
    # Ready for measurements
    OpAmp_ES('ON')  # OpAmp is ON
    Previous_NS = 0
    HV_start = 0.0

# Data and time stamp for the file name extension
dateTimeObj = datetime.now()
timestampStr = dateTimeObj.strftime("%d-%b-%Y %H:%M")

folder = '/home/UoPi/Desktop/QI tests'  # The folder where all experiments are saved
full_name = folder + '/' + name + '.txt'  # Full path to the file
with open(full_name, 'w+') as file:
    l1 = '# QI thruster based on Raspberry Pi 4B\n'
    l2 = '# File name: ' + name + '.txt\n'
    l3 = '# Date and time: ' + timestampStr + '\n'
    l4 = '# Columns: ' + 'OpAmp output (V), HV output (kV), current (uA), thrust (your units)\n'
    l5 = '# Note: Negative values must be treated as invalid\n'
    l6 = '\n'
    file.writelines([l1, l2, l3, l4, l5, l6])

Message = 'Enter the thrust reading (any units) from the electronic scale: '
with keyboard.Events() as events:
    for event in events:
        output = []
        if event.key == keyboard.Key.esc:
            print('The program has been terminated by your request.')
            print('Warning: Wait until the capacitor is fully discharged before disconnecting it!')
            GPIO_OFF()
            write_pot(0x00)
            OpAmp_ES('OFF')
            Previous_NS = 0
            HV_start = 0.0
            file.close()
            exit()
        elif event.key == keyboard.Key.shift:
            if str(event) == 'Press(key=Key.shift)':
                NS_stop, OpAmp, HV_actual = HV_up(Previous_NS, factor_up * tau_up)
                Previous_NS = NS_stop
                Current = CurrentSensor(bias, Ch)
                print('Current through the capacitor = ', Current, ' uA')
                try:
                    thrust = float(input(Message))
                except:
                    print('')
                    print('You entered the number incorrectly')
                    print('Try one more time... If incorrectly, the program will be terminated.')
                    print('')
                    try:
                        thrust = float(input(Message))
                    except:
                        print('')
                        print('The program was terminated due to an invalid value for the thrust')
                        GPIO_OFF()
                        write_pot(0x00)
                        OpAmp_ES('OFF')
                        file.close()
                        exit()
                output = np.column_stack([OpAmp, HV_actual, Current, thrust])
                with open(full_name, "a+") as file:
                    np.savetxt(file, output)
                print('')
        elif event.key == keyboard.Key.ctrl:
            if str(event) == 'Press(key=Key.ctrl)':
                NS_stop, OpAmp, HV_actual = HV_down(Previous_NS, factor_down * tau_down)
                Previous_NS = NS_stop
                Current = CurrentSensor(bias, Ch)
                print('Current through the capacitor = ', Current, ' uA')
                try:
                    thrust = float(input(Message))
                except:
                    print('')
                    print('You entered the number incorrectly')
                    print('Try one more time... If incorrectly, the program will be terminated.')
                    print('')
                    try:
                        thrust = float(input(Message))
                    except:
                        print('')
                        print('The program was terminated due to an invalid value for the thrust')
                        GPIO_OFF()
                        write_pot(0x00)
                        OpAmp_ES('OFF')
                        file.close()
                        exit()
                output = np.column_stack([OpAmp, HV_actual, Current, thrust])
                with open(full_name, "a+") as file:
                    np.savetxt(file, output)
                print('')