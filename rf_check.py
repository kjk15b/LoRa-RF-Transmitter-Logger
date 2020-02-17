#!/bin/python3

# Author: Kolby Kiesling
# Email: kjk15b@acu.edu
# Date: 02/09/2020
# This program serves to generate random data to send to another Raspberry Pi
# utilizing the Adafruit RFM69 LoRa bonnet.


import time
import busio
from digitalio import DigitalInOut, Direction, Pull
import board
import adafruit_ssd1306
import adafruit_rfm69
import numpy as np
import datetime as dt

import serial

dev = "/dev/ttyACM1"

try:
    udev = serial.Serial(dev, 9600, timeout=1)
except:
    print("Error opening conection")

btnA = DigitalInOut(board.D5)
btnA.direction = Direction.INPUT
btnA.pull = Pull.UP

btnB = DigitalInOut(board.D6)
btnB.direction = Direction.INPUT
btnB.pull = Pull.UP

btnC = DigitalInOut(board.D12)
btnC.direction = Direction.INPUT
btnC.pull = Pull.UP

i2c = busio.I2C(board.SCL, board.SDA)

reset_pin = DigitalInOut(board.D4)
display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, reset=reset_pin)

display.fill(0)
display.show()
width = display.width
height = display.height

CS = DigitalInOut(board.CE1)
RESET = DigitalInOut(board.D25)
#spi = busio.SPI(board.SCK, MOSI=board.MOSI, MIS0=board.MISO)
spi = busio.SPI(board.SCK, MOSI=board.MOSI)

prev_packet = None

rfm69 = adafruit_rfm69.RFM69(spi, CS, RESET, 915.0)

rfm69.encryption_key = b'\x01\x02\x03\x04\x05\x06\x07\x08\x01\x02\x03\x04\x05\x06\x07\x08'

data = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] # time, temp, conductivity, ammonium, nitrate, oxygen, turbidity, pH, longitude, lattitude
data_set = [[], [], [], [], [], [], [], [], [], []] # for logging data
t_stamp = 0


while True:
    #for i in range(5):
        #print(udev.readline())
    display.fill(0)
    packet = None
    display.text("Abilene Buoy Systems", 0, 0, 1)
    
    
    for i in range(len(data)):
        if i == 0:
            #t_stamp = (t_stamp + 1) % 23
            #data[0] = str(t_stamp) + ":00" # fake timestamp
            now = dt.datetime.today()
            t_stamp = str(now.month) + "/" + str(now.day) + "|" + str(now.hour) + ":" + str(now.minute)
            data[i] = t_stamp
        else:
            #data[i] = np.random.normal() * np.sqrt(i) + i *np.sqrt(i) # make some fake data
            # Check the arduino for new data
            line = ""
            for j in range(5):
                line = udev.readline()
                if len(line.split()) == 9:
                    break # we found all of our data
            if len(line.split()) == 9:
                x = line.split() # split up our data
                for j in range(len(x)):
                    try:
                        x[j] = float(x[j].decode("utf-8"))
                    except:
                        x[j].append(-999)
                
                #for k in range(len(x)):
                    #print(x)
                
                data[i] = x[i-1] # assign the data
                #data[i] = -1
                #print("Data length:\t", len(data), " Split length:\t", len(x))
            else:
                data[i].append(-1)
            
        data_set[i].append(data[i]) # append for logging


    if len(data_set[0]) == 120:
        now = dt.datetime.today()
        fname = str(now.month) + "_" + str(now.day) + "_" + str(now.year) + "_" + str(now.hour) + str(now.minute) + "_" + ".csv"
        
        headers = "Date,Temperature [C],Conductivity [mS/cm],Ammonium [mg/L],Nitrate [mg/L],Oxygen [mg/L],Turbidity [NTU],pH,Longitude [Deg],Latitude [Deg]\n"
        
        save_file = open(fname, "w")
        save_file.write(headers) # add the headers for later analysis
        
        for i in range(len(data_set[0])):
            line = str(data_set[0][i]) + "," + str(round(data_set[1][i], 2)) + "," + str(round(data_set[2][i], 2)) + "," + str(round(data_set[3][i], 2)) + "," + str(round(data_set[4][i], 2)) + "," + str(round(data_set[5][i], 2)) + "," + str(round(data_set[6][i], 2)) + "," + str(round(data_set[7][i], 2)) + "," + str(round(data_set[8][i], 2)) + "," + str(round(data_set[9][i], 2)) + "\n"
            save_file.write(line)
            
        save_file.close()
        print("Data written to:\t", fname)
        data_set = [[], [], [], [], [], [], [], [], [], []] # for logging data

    # append to a string for encoding
    send_str = ""
    for i in range(len(data)):
        if i == 0:
            send_str += data[i]
        else:
            send_str += " " + str(round(data[i], 2))
        
        
    packet = rfm69.receive()
    if packet is None:
        display.show()
        #display.text("- Wating for PKT -", 15, 20, 1)
        
        send_data = bytes(str(send_str), "utf-8")
        length = len(send_data)
        
        print("Sending string:\n", send_str, "\n\n")
        display.text("- Sending PKT -", 15, 20, 1)
        
        if length <= 60:
            for i in range(50): # 25 times seemed to not be enough to get the data across
                rfm69.send(send_data)
    else:
        # auto send data, but also look for op-mode
        #pckt_str = str(packet, "utf-8") # fetch the data and perform conversions
        pckt_str = "m"
        display.fill(0)
        display.text("- Received PKT -", 15, 20, 1)
        if pckt_str == "m":
            display.text("Manual Mode", 0, 0, 1)
        else:
            display.text("Autonomous Mode", 0, 0, 1)
    
    display.show()
    time.sleep(60)
