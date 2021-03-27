
#!/usr/bin/env python3 -*- coding: utf-8 -*-
"""
Created on Wed Dec 23 08:28:33 2020
Last Rev: Sun March 14 2021
@author: Liam
"""


#from scipy.signal.filter_design import bilinear
from scipy.signal import lfilter
import scipy
from matplotlib import pyplot as plt
import pyaudio
import wave
import sys
from math import sqrt
import numpy as np
from dataclasses import dataclass
import time, datetime, csv, threading
import time
import random

"""from time import sleep
from gpiozero import LED
import gpiozero as GPIO
"""

time2sleep = 1 #Defines the amount of time to rest between measurements
high_thr = 90 #Define a "loud" level reading
low_thr = 70 #Define a "quiet" level reading
#In between is the "moderate" level
"""rled = LED(17)
yled = LED(27)
gled = LED(22)
IR_LED = LED(6)
ind = LED(7)
IR_SENSOR = GPIO.Button(5)"""
dev_ind = 1 #Define the ALSA index of the I2S mic
c = 1 #Define the number of channels to record
mic_OL = 120.0 #Define acoustic OL point from datasheet
ref_1k = 94.0 #Define the mic reference in dB at 1k from datasheet
OS = 0 #Define tuning parameter OS, which can be used to calibrate meter
NF =30 #Define the noise floor of the microphone, any data under this is invalid
sens = -26 #Define the sensitivity of the mic from datasheet
fs = 48000 #Define the sample rate of the mic
BD = 24 #Define bit depth
BD_samp = 32
samp_type = pyaudio.paInt32 #Specifies what data type to store samples as
samp_short = (fs / 8) #Specifies a "short" time scale of .125 seconds as defined by IEC standards
samp_long = (fs) #Specifies a "long" time scale of 1 second * the chose LEQ length
bank_size = int(samp_short/16) #Number of frames per "buffer", chosen at (0.125/16)*fs = 375 
mic_ref = pow(10, (sens/20))*((1<<(BD - 1))-1);print(mic_ref) #Equation for calculating mic_sens in mV/Pa
int_time = 128 #Define the number of chuncks to iterate over to form one LAeq_db value
window_size = 20 #number of seconds of data for leq period
sum_sqr_weight = [0]* int_time
avg = []
send_rate =  6   #Rate to send data, times per hour
num_sec = ((60/send_rate) * 60) + (60/send_rate) ##Allocate space for 15 * 60 samples + 15 for a buffer
long_avg = [0] * int(round(num_sec)) #Preallocate space for storing average values over a longer period of time

b, a = (([ 0.23430179, -0.46860358, -0.23430179, 0.93720717, -0.23430179, -0.46860358, 0.23430179]), ([ 1., -4.11304341, 6.55312175, -4.99084929, 1.7857373 ,-0.2461906 ,  0.01122425]))
#start audio stream
def start_stream():
    global stream, audio
    """
    Starts Pyaudio stream 
    
    Returns
    -------
    None.

    """
    audio = pyaudio.PyAudio()
    stream = audio.open(format=samp_type,rate=fs,channels=c,input_device_index=dev_ind, input = True, frames_per_buffer = bank_size)


def weight_signal(data):
    """Weights input signal, based on IEC standards for A-weighted filter
    Calculated as follows:
    f1 = 20.598997 #Two pole LP at 20.6Hz
    f2 = 107.65265 #Pole at 108Hz
    f3 = 737.86223 #Pole at 738Hz
    f4 = 12194.217 #Double pole at 12.2k
    a1k = 1.9997 #Attenuation needed at 1k
    numerator = [(2 * np.pi * f4) ** 2 * (10 ** (a1k / 20)), 0, 0, 0, 0]
    denominator = scipy.signal.convolve([1 + 4 * np.pi * f4*(2 * np.pi * f4) ** 2], [1 + 4 * np.pi * f1*(2 * np.pi * f1) ** 2])
    denominator = scipy.signal.convolve(scipy.signal.convolve(denominator, [1, 2 * np.pi * f3]), [1, 2 * np.pi * f2])
    b, a = scipy.signal.bilinear(numerator, denominator, samp_rate)
    b, a = (([ 0.23430179, -0.46860358, -0.23430179, 0.93720717, 
              -0.23430179, -0.46860358, 0.23430179]), 
            ([ 1., -4.11304341, 6.55312175, -4.99084929, 1.7857373 
              ,-0.2461906,  0.01122425]))
    """
    
    x = lfilter(b, a, data)
    return x

def squaresum(n) : 
    # Iterate i from 1  
    # and n finding  
    # square of i and 
    # add to sum.
    N = len(n) 
    sm = sum(i*i for i in n)
    return sqrt(sm/N)

def read_samples():
    """
    Reads in a set of samples,
    Convert to int32, weight the samples, 
    Stores them in queue sum_sqr_weight

    Returns
    -------
    None.

    """
    from_buff = stream.read(bank_size, exception_on_overflow=(False))
    data = np.frombuffer(from_buff,dtype=np.int32)
    weighted = weight_signal(data)
    data_shifted = [0] * bank_size
    rms = squaresum(weighted)
    #convert value from 32 bit to 24 bit by shifting 8 bits
    for n in range(len(data)):
        sample = (data[n] >> (BD_samp-BD))
        data_shifted[n] = sample
        
    print("Before shifting: ")
    print(bin(rms), end="\t")
    print(rms)
    rms_shifted = squaresum(data_shifted)
    print("After shifting: ")
    print(bin(rms_shifted), end="\t")
    print(rms_shifted)
    sum_sqr_weight.append((squaresum()))
    
def avg_db(avg):
    """
    """
    avgsum = 0
    temp=0;
    N=len(avg);
    for j in range(N):
        if avg[j] != 0:
            avgsum += 10**(avg[j]/20)
        else:
            temp+=1
    if N-temp != 0:
        avg = 20 * np.log10(avgsum/(N-temp))
    else:
        avg = NF
    return (avg)
        
      
def print_level(level):
    #level = int(level)
    for i in range(int(round(level))):
        print("#", end = '')
    print('')
    return

"""def display_leds(avg):
    if avg <= low_thr:
        gled.on()
    elif avg > low_thr and avg <= high_thr:
        yled.on()
    elif avg > high_thr:
        rled.on()
    time.sleep(time2sleep)
    rled.off()
    yled.off()
    gled.off()"""
 
def open_csv():
    """
    Opens CSV file and writes column headers

    Returns
    -------
    None.

    """
    global writer, file
    file = open('noise.csv', 'w', newline='')
    writer = csv.writer(file)
    writer.writerow(["Time Stamp", "Avg SPL", "Avg RMS"])
    return


def main():
    open_csv()
    start_stream()
    #IR_LED.on()
    #set sums and such to zero to begin
    long_samples=0
    long_sum=0
    long_db=0
    long_rms = 0
    long_avg = []
    times = []
    print("Press Crtl+C to terminate while statement")
    try:
        leq_buffer = 0
        send_buffer = 0
        #loop through until interupt is issued
        while stream.is_active():
            c = 0
            shorts = [0] * int_time
            sum_sqr_weight.clear()
            #Iterate through 128 times, each time collecting 375 samples
            #Then we calculate short term spl values to verify it isnt above mic OL or below mic noise level
            #Add the square A-weighted level to our leq_sum 
            #When enough samples have been taken in calculate leq_db over 1 second
            for i in range(int_time):
                """if not IR_SENSOR.is_pressed:
                    #print("IR SENSOR COVERED")
                    ind.on()
                else:
                    ind.off()"""
                read_samples()
                short_RMS = sum_sqr_weight[i]
                short_spl = OS + ref_1k + 20 * np.log10(short_RMS/mic_ref)
                shorts[i] = short_spl
                if short_spl > mic_OL:
                    c += 1
                elif short_spl < NF:
                    c += 1
                long_sum += sum_sqr_weight[i]
                long_samples += bank_size
                if i >= 20:
                    return
            #After one second has been read in, calculate a spl_
            if long_samples >= fs:
                long_rms = long_sum/(long_samples-(c*bank_size)) #Subtract the amount of NUL (0) Values
                long_db = OS + ref_1k + 20 * np.log10(long_rms/mic_ref)
                long_sum = 0
                long_samples = 0
                avg.append(long_db)
                print(long_db)
            #If we've read in a certain amount of seconds of data->start taking moving avg
            if leq_buffer > window_size-1: 
                #For debuggin purposes
                print(f"Averaging {leq_buffer-window_size}-{leq_buffer} values...")
                #Average the long_spl readings in moving buffer
                average = (avg_db(avg[leq_buffer-window_size:leq_buffer]))
                #Add then to our long_avg
                long_avg.append(average)
                times.append(datetime.datetime.now())
                #TODO clear any previous avg values
                print(f"LAEQ: {average}")
                writer.writerow([datetime.datetime.now(), average])
                #display_leds(average)
            leq_buffer+=1
            send_buffer+=1
            if send_buffer >= (num_sec - (60/send_rate)+4):
                #Run through long_avg, take avg, throw out any zeros
                noise = avg_db(long_avg)
                long_avg.clear()
                send_buffer = 0
                avg.clear()
                leq_buffer = 0
                #writer.writerow([(datetime.datetime.now()), noise])
                if noise >= high_thr:
                    status = "LOUD"
                elif noise < high_thr and noise >= low_thr:
                    status = "WARNING"
                else:
                    status = "GOOD"
                """send status here"""
                print(status, noise)
                

    except KeyboardInterrupt:
        print("Stopping monitor...")
        pass
    file.close()
    stream.stop_stream()
    stream.close()
    audio.terminate()
    
    
if __name__ == "__main__":
    main()

