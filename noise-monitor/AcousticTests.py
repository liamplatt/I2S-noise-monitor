#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testing script, just graphs and saves csv of measured levels as various frequencies
Created on Thu Apr 15 08:32:29 2021

@author: Liam
"""
import numpy as np
import csv
import pyaudio
from scipy.signal import lfilter
from matplotlib import pyplot as plt
import datetime, os
#Definitions of ALSA information
dev_ind = 1 #Define the ALSA index of the I2S mic
c = 1 #Define the number of channels to record
fs = 48000 #Define the sample rate of the mic
BD = 24 #Define bit depth of data 
BD_samp = 32 #Define bit depth to read in
samp_type = pyaudio.paInt32 #Specifies what data type to store samples as
bank_size = 375
sum_sqr_weight = []
b, a = (([ 0.23430179, -0.46860358, -0.23430179, 0.93720717, -0.23430179, -0.46860358, 0.23430179]), ([ 1., -4.11304341, 6.55312175, -4.99084929, 1.7857373 ,-0.2461906 ,  0.01122425]))
OS = -2.611

def open_csv(name):
    """
    Opens CSV file and writes column headers
    Input
    -------
    String: Name, ommitting the .csv

    Returns
    -------
    None.

    """
    name = name + ".csv"
    global writer, file
    file = open(name, 'w', newline='')
    writer = csv.writer(file)
    writer.writerow(["Applied SPL (dB)", "Normalized Amplitude (dBFS)", "Frequency (Hz)", "Frequency Weighting (dB)", "Read Level (dB)", "Expected Level (dB)", "Deviation (dB)", "Type 2 Upper Tolerence (dB)", "Type 2 ULower Tolerence (dB)", "Pass/Fail"])
    return
def squaresum(n) : 
    # Iterate i from 1  
    # and n finding  
    # square of i and 
    # add to sum.
    sm = sum(i*i for i in n)
    return sm

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
    data_shifted = [0] * bank_size
    #convert value from 32 bit to 24 bit by shifting 8 bits
    #                                   <--------usable--------->
    #Data being read in will be in form 00000000 0000000 00000000 00000000
    #We shift over the data 8 bits to the right, effectively dividing by 2**8
    for n in range(len(data)):
        sample = (data[n] >> (BD_samp-BD))
        data_shifted[n] = sample
    rms_shifted = squaresum(weight_signal(data_shifted))
    return rms_shifted
def avg_db(avg):
   """
   """
   avgsum = 0
   N=len(avg)
   for j in range(N):
       avgsum += 10**(avg[j]/20)
   avg = 20 * np.log10(avgsum/(N))
   return (avg)   

def testFreqResp():
    #Function designed to test the overall system characteristics
    #Inputs in sine waves of frequencies specified by the IEC
    #Each sine wave should have an amplitude of the reference value 420436
    #This value is found with the equation 10^(mic_ref/20) * 2^(BD-1)
    #Each sin wave should be inputted at 94dB, checked against ref meter
    short_length = 375
    fs = 48e3
    cal = 420426
    ref_1k = 94
    mic_ref = 420426
    inf = 'NA'
    #Note: Testing parameters taken from MATLAB weightingFilter.m
    #Reworked for python
    test_freqs = [10, 12.5, 16, 20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 
                  315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 
                  5000, 6300, 8000, 10000, 12500, 16000, 20000]
    a_weight_dB = [-70.4, -63.4, -56.7, -50.5, -44.7, -39.4, -34.6, -30.2, -26.2, -22.5, 
                -19.1, -16.1, -13.4, -10.9, -8.6, -6.6, -4.8, -3.2, -1.9, -0.8, 0, 0.6, 1, 1.2, 1.3,
                1.2, 1, 0.5, -0.1, -1.1, -2.5, -4.3, -6.6, -9.3]
    lowerTol = [inf, inf, inf, 3.5, 3.5, 3.5, 2.5, 2.5 ,2.5, 2.5, 2, 2, 2, 2, 1.9, 1.9, 1.9,
                1.9, 1.9, 1.9, 1.4, 1.9, 2.6, 2.6, 3.1, 3.1, 3.6, 4.1, 5.1, 5.6, inf, inf, inf, inf]
    upperTol = [5.5, 5.5, 5.5, 3.5, 3.5, 3.5, 2.5, 2.5, 2.5, 2.5, 2, 2, 2, 2, 1.9, 1.9, 1.9,
                1.9, 1.9, 1.9, 1.4, 1.9, 2.6, 2.6, 3.1, 3.1, 3.6, 4.1, 5.1, 5.6, 5.6, 6, 6, 6]
    test = dict()
    
    
    #Set up dictionary with freqs as keys
    for freq in test_freqs:
        test[freq] = 0
    start_stream()
    
    #Read through a few sets of samples to clear any startup deviations
    for i in range(200):
        read_samples()
        sum_sqr_weight.clear()
    
    #Run through each test frequency, asking user to play sin at given frequency
    #All sins are at 94dB
    for freq in test_freqs:
        spls = []
        sum_sqr_weight.clear()
        slow_sum = 0
        slow_samps = 0
        inp = input(f"Ready to input 94dB sin at {freq}Hz?")
        if inp == 'n':
            break
        #Iterate through to collect 1 sec of data
        for i in range(128):
            samp = read_samples()
            slow_sum += samp
            slow_samps += bank_size
            sig_rms = np.sqrt((samp)/bank_size)
            short_spl = OS + ref_1k + 20 * np.log10(sig_rms/mic_ref)
            spls.append(short_spl)
        rms = np.sqrt(slow_sum/slow_samps)
        spl = OS + ref_1k + 20 * np.log10(rms/mic_ref)
        print(spl)
        avg = avg_db(spls)
        test[freq] = spl
        print(avg)
    print(test)  
    open_csv("validateFreqs")
    testDev = dict()
    expect = dict()
    for i in range(len(test.keys())):
        freq = test_freqs[i]
        print(freq)
        print(test.get(freq))
        #Subtract to find our "goal" or expected value for each frequency
        state = "FAIL"
        dev = (test.get(freq)-(94+(a_weight_dB[i])))
        expect[freq] = (94+(a_weight_dB[i]))
        print(dev)
        #Check deviation from expected value and assign state to either PASS of FAIL
        if (dev < 0):
            if lowerTol[i] == "NA":
                state = "PASS"
            else:
                if (dev >= -1*lowerTol[i]):
                    state = "PASS"
                else:
                    state = "FAIL"
        elif(dev>0):
            if (dev <= upperTol[i]):
                state = "PASS"
            else:
                state = "FAIL"
        else:
            pass
        testDev[freq] = dev
        
        writer.writerow([str(94), 0, test_freqs[i], a_weight_dB[i], test.get(freq), 94+(a_weight_dB[i]), dev, upperTol[i], lowerTol[i], state])
    
    """plt.plot(test_freqs, normalized_amp)
    plt.xscale('log')
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Amplitude (dBFS)")
    plt.title("Frequency Response of IIR A-weighted Filter")
    plt.show()"""
    """fig, ax = plt.subplots(1, 1)
    ax.semilogx(test_freqs, test.values())
    ax.semilogx(test_freqs, testDev.values())
    ax.semilogx(test_freqs, expect.values())
    ax.legend(["Measured values", "Deviation", "Expected values"])
    fig.show()"""
    file.close()
    
def testLinearity():
    #----------------------------------------------------#
    #Function to test system linearity                   #
    #Tests at 4kHz at a variety of sound pressure levels #
    #Outputs test to CSV file                            #
    #----------------------------------------------------#
    start_stream()
    int_time = 128
    
    test_levels = {30:0, 35:0, 40:0, 45:0, 50:0, 55:0, 60:0, 65:0, 70:0, 75:0, 80:0, 85:0, 90:0, 95:0, 100:0}
    short_length = 375
    test_freq = 4000
    fs = 48e3
    cal = 420426
    ref_1k = 94
    mic_ref = 420426
    window_size = 40
    OS = 0.739 
    
    for test in test_levels.keys():
        ready_state = input(f"Are you ready for a 4kHz sin at {test}dB SPL?")
        if ready_state == 'n':
            break
        avg = []
        average = None
        #Reset accumulators for each test
        long_samples = 0
        long_sum = 0
        stop = True
        leq_buffer = 0
        buff = 0
        #Keep looping until values have been computed
        while stop:
            
            for i in range(int_time):
                #
                sqr_sum = read_samples()
                short_RMS = np.sqrt(sqr_sum/bank_size)
                short_spl = OS + ref_1k + 20 * np.log10(short_RMS/mic_ref)
                long_samples += 1
                long_sum += short_RMS
            #After reading 128*375 samples, compute 'long' sound pressure readings.
            #Store in array to be used for a moving average
            long_rms = (long_sum/(long_samples))
            long_db = OS + ref_1k + 20 * np.log10(long_rms/mic_ref)
            print(long_db)
            os.system('clear')
            long_sum = 0
            long_samples = 0
            avg.append(long_rms)
            #If we've read in enough data->start taking a moving avg
            #Moving average acts as a filter where quick fluctuations in sound pressue
            #are ignored.
            #
            #Append this moving average to a list to average and send to dashboard
            if buff == window_size: 
                #Average the readings in moving buffer
                #ave = OS + ref_1k + 20 * np.log10((sum(avg[0:window_size])/len(avg))/mic_ref)
                #Push into list
                print("Throwing out startup samples...")
                avg.clear()
            elif buff > window_size: 
                leq_buffer+=1
            if leq_buffer > 10: 
                #Average the readings in moving buffer
                average = OS + ref_1k + 20 * np.log10((sum(avg)/len(avg))/mic_ref)
                #Push into list
                print(f"LAEQ: {average}")
                
                #Clear the first element from array so only window_size elements 
                #are stored at any given time
                avg.clear()
                test_levels[test] = average
                stop = False
            buff+=1
        
    #once computed, check against expected levels and write to csv
    open_csv("validateSPL")
    for test in test_levels.keys():
        dev = test_levels[test] - test+1
        
        writer.writerow([test, "", 4000, "", test_levels[test], test+1, dev, "", "", "NA"])
    file.close()
    print("Done saving CSV")
    
def testLin():
    #Definitions of I2S mic characteristics from datasheet 
    mic_OL = 120.0 #Define acoustic OL point from datasheet
    ref_1k = 94.0 #Define the mic reference in dB at 1k from datasheet
    OS = 0 #Define tuning parameter OS, which can be used to calibrate meter
    NF =30 #Define the noise floor of the microphone, any data under this is invalid
    sens = -26 #Define the sensitivity of the mic from datasheet
    mic_ref = pow(10, (sens/20))*((1<<(BD - 1))-1) #Equation for calculating mic_sens in mV/Pa
    linTest = dict()
    for i in range(0, pow(2, 24)):
        short_RMS = i
        short_spl = OS + ref_1k + 20 * np.log10(short_RMS/mic_ref)
        linTest[i] = short_spl    
    print(linTest)
if __name__ == "__main__":
    testLin()
    user_choice = input("Which test would you like to run? (Freq or line)")
    if user_choice == "freq":
        testFreqResp()
    elif user_choice == "line":
        testLinearity()
    else:
        print("Invalid input")
    
    
    
    
    
    
    
    
    