#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 23 08:28:33 2020

@author: Liam
"""

from numpy import pi, convolve
from scipy.signal.filter_design import bilinear
from scipy.signal import lfilter
import pyaudio
import wave
import sys
import numpy as np
from dataclasses import dataclass
import time, datetime, csv, threading


import time
import random


dev_ind = 1
c = 1
LEQ_length = 1
LEQ_units = "LAeq"
DB_units = "dBA"
weighting = "A_weighting"
mic_OL = 120.0
mic_ref = 94.0
mic_OS = 12
mic_noise = 28
mic_sens = -26
samp_rate = 48000
samp_bits = 32
samp_type = pyaudio.paInt32
samp_short = (samp_rate / 8)
samp_long = (samp_rate * LEQ_length)
bank_size = int(samp_short/16)
banks = 32
#mic_ref_amp = 0.000020**2
mic_ref_amp = pow(10, (mic_sens/20))*((1<<(samp_bits - 1))-1)
print(mic_ref_amp)
INF = 'INF'
negINF = '-INF'
int_time = 128
avgsum = 0
sum_sqr_weight = [np.zeros(int_time)]
avg = [np.zeros(int_time)]
b, a = (([ 0.23430179, -0.46860358, -0.23430179, 0.93720717, -0.23430179, -0.46860358, 0.23430179]), ([ 1., -4.11304341, 6.55312175, -4.99084929, 1.7857373 ,-0.2461906 ,  0.01122425]))
audio = pyaudio.PyAudio()
stream = audio.open(format=samp_type,rate=samp_rate,channels=c,input_device_index=dev_ind, input = True, frames_per_buffer = bank_size)

#applies a weighting to input 'data'
def weight_signal(data):
    return lfilter(b, a, data)

def squaresum(n) : 
    # Iterate i from 1  
    # and n finding  
    # square of i and 
    # add to sum. 
    sm = sum(i*i for i in n)
    return sm 

#reads in a set of samples, convert to int32, store them in queue
def read_samples():
    data = np.frombuffer(stream.read(bank_size, exception_on_overflow=(False)),dtype=np.int32)
    sum_sqr_weight.append((squaresum(weight_signal((data)))))
    
def avg_data(avg, avgsum):
    for j in range(int_time):
        avgsum += avg[j]  
    print(f"avg over {int_time} blocks: {avgsum/int_time} at time: {datetime.datetime.now()}")
    return (avgsum)
    

def main():
    file = open('LAeq2.csv', 'w', newline='')
    writer = csv.writer(file)
    writer.writerow(["Time Stamp", "Level"])
    leq_samples=0
    leq_sum=0
    leq_db=0
    print("Press Crtl+C to terminate while statement")
    try:
        while stream.is_active():
            sum_sqr_weight.clear()
            for i in range(int_time):
                start_time = time.time()
                #tb = time.time()
                read_samples()
                #ta = time.time() - tb
                #print(ta)
                short_RMS = np.sqrt(sum_sqr_weight[i]/ samp_short)
                short_spl = mic_OS + mic_ref + 20 * np.log10(short_RMS/mic_ref_amp)
                if short_spl > mic_OL:
                    leq_sum = 116
                    print(INF)
                elif short_spl < mic_noise:
                    leq_sum = 0
                    print(negINF)
                leq_sum += sum_sqr_weight[i]
                leq_samples += samp_short
                if leq_samples >= samp_rate*LEQ_length:
                    leq_rms = np.sqrt(leq_sum/leq_samples)
                    leq_db = mic_OS + mic_ref + 20 * np.log10(leq_rms/mic_ref_amp)
                    leq_sum = 0
                    leq_samples = 0
                avg.append(leq_db)
                avgsum = 0
            avgsum = avg_data(avg, avgsum)
            writer.writerow([datetime.datetime.now(), avgsum/int_time])
            data = avgsum/int_time
            avg.clear()

    except KeyboardInterrupt:
        print("Stopped!")
        pass
    file.close()
main()

