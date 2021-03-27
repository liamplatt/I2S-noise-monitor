#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 25 22:33:00 2021

@author: Liam
"""
import numpy as np
import csv
from matplotlib import pyplot as plt
from I2S_MovingAvg_TestPi import avg_db, squaresum, weight_signal
def open_csv():
    """
    Opens CSV file and writes column headers

    Returns
    -------
    None.

    """
    global writer, file
    file = open('Validation.csv', 'w', newline='')
    writer = csv.writer(file)
    writer.writerow(["Applied SPL (dB)", "Normalized Amplitude (dBFS)", "Digital Ampltitude", "Frequency (Hz)", "Frequency Weighting (dB)", "Read Level (dB)", "Expected Level (dB)", "Deviation (dB)", "Type 2 Upper Tolerence (dB)", "Type 2 ULower Tolerence (dB)", "Pass/Fail"])
    return
def test_SPL():
    #Function designed to test the overall system characteristics
    #Inputs in sine waves of frequencies specified by the IEC
    #Each sine wave has an amplitude of the reference value 420436
    #This value is simple 10^(-26/20) * 2^(BD-1)
    print(pow(10, (-26/20))*pow(2, 24-1))
    short_length = 375
    fs = 48e3
    cal = 420426
    ref_1k = 94
    mic_ref = 420426
    #Create static calibration signal
    que = [cal]*375
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
    que = []
    #Define time vector of length 375
    t = np.linspace(0, 1, int(fs))
    normalized_amp = []
    #Create a sine wave at ~94dB (420426) 
    #at frequencies in array test_freqs
    ind = 0
    maxes = []
    for freq in test_freqs:
        #Create sin at freq
        sig = (cal * np.sin(freq*t*2*np.pi))
        que.append(weight_signal(sig))
        maxes.append(max(sig))
        ind+=1
    
    """#Create ramp signal to test range of SPL values
    for i in range(pow(2, 23)):
        que.append(i)
    que_FS = []
    #Create a ramp of dbFS values to demonstrate DR
    for i in range(pow(2, 23)):
        que_FS.append(i/pow(2, 23))
    """
    OS = 3.5
    shorts = []
    short = []
    i = 1
    #Setup figure for plotting
    plt.figure(1)
    avg = 0
    for sin in que:
        spl = []
        #title = "Short Term SPL of 94dB sine wave at " + str(test_freqs[i-1]) + "Hz"
        for i in range(375, len(sin)):
            sig_chunk = squaresum(sin[i-375:i])
            short_spl = OS + ref_1k + 20 * np.log10(sig_chunk/mic_ref)
            rms = sig_chunk/2**23
            normalized_amp.append((20*np.log10(rms)))
            spl.append(short_spl)
        print(".", end = "")
        avg = avg_db(spl)
        shorts.append(avg)
        i+=1
    """plt.plot(test_freqs, normalized_amp)
    plt.xscale('log')
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Amplitude (dBFS)")
    plt.title("Frequency Response of IIR A-weighted Filter")
    plt.show()"""
    open_csv()
    for i in range(len(shorts)):
        #Subtract to find our "goal" or expected value for each frequency
        state = "FAIL"
        dev = (shorts[i]-(94+(a_weight_dB[i])))
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
             
        writer.writerow([str(94), 20*np.log10(maxes[i]/2**23), maxes[i], test_freqs[i], a_weight_dB[i], shorts[i], 94+(a_weight_dB[i]), dev, upperTol[i], lowerTol[i], state])
        plt.plot(test_freqs[i], shorts[i])
        plt.plot(test_freqs[i], 94+a_weight_dB[i]) 
        plt.show()
    file.close()
        
    
   
    
if __name__ == "__main__":
    test_SPL()
