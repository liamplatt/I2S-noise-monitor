

#!/usr/bin/env python3 -*- coding: utf-8 -*-
"""
Created on Wed Dec 23 08:28:33 2020
Last Rev: Thu April 22nd 2021
@author: Liam Platt
Capstone Design Project
"""


#from scipy.signal.filter_design import bilinear
from scipy.signal import lfilter, sosfilt
import pyaudio
import sys
from math import isnan
from numpy import log10, int32, sqrt, frombuffer
import time, datetime, csv
import time, os
from time import sleep
from gpiozero import LED
import gpiozero as GPIO
import requests
import array



high_thr = 90 #Define a "loud" level reading, this will end up being sent from firebase setting
low_thr = 70  #Define a "quiet" level reading

#Definitions of GPIO input and outputs
rled = LED(17)
yled = LED(27)
gled = LED(22)
IR_LED = LED(6)
ind = LED(13)

#Turn on LED for IR sensor
IR_LED.on()
IR_SENSOR = GPIO.Button(5)


#Definitions of ALSA information
dev_ind = 1 #Define the ALSA index of the I2S mic
c = 1 #Define the number of channels to record
fs = 48000 #Define the sample rate of the mic
BD = 24 #Define bit depth of data 
BD_samp = 32 #Define bit depth to read in
samp_type = pyaudio.paInt32 #Specifies what data type to store samples as 


#Definitions of I2S mic characteristics from datasheet 

mic_OL = 120.0 #Define acoustic OL point from datasheet
ref_1k = 94.0 #Define the mic reference in dB at 1k from datasheet
OS=-.719 #Define tuning parameter OS, which can be used to calibrate meter
NF =30 #Define the noise floor of the microphone, any data under this is invalid
sens = -26 #Define the sensitivity of the mic from datasheet

#Equation for calculating mic_sens in mV/Pa 
#sens_db = 20*log10(sens(in mV/Pa) / 94dB)
sens_mv = pow(10, (sens/20))
#This will be the sample value in which a measurement should evaluate to 94dB
mic_ref = sens_mv*((1<<(BD - 1))-1) 


#Max and min values that mic should could read in
INF = 9103309
negINF = 0

#Define some constants to be used by the program
#samp_short and samp_long 
samp_short = (fs / 8) #Specifies a "short" time scale of .125 seconds as defined by IEC standards
samp_long = (fs) #Specifies a "long" time scale of 1 second * the chose LEQ length
bank_size = int(samp_short/16) #Number of frames per "buffer", chosen at (0.125/16)*fs = 375 
int_time = 128 #Define the number of chuncks to iterate over to form one LAeq_db value
window_size = 5 #Size of moving average window
send_rate =  60   #Rate to send data, times per hour
num_sec = int((((60/send_rate) * 60) + (60/send_rate))/2) ##Allocate space for 15 * 60 samples + 15 for a buffer

OF = 10 #How many samples should be thrown out at beggining of capture (mic has startup time of a few ms) 


#Declare arrays
long_avg = []
long_RMS = []

#Using arrays here as they are slightly more efficient
avg = array.array('f') #Used to hold moving buffer of rms readings
long_avg = array.array('f') #Used to hold spl values to average and send to dashboard


# A-weighted filter coefficients from Matlab
b, a = (([ 0.23430179, -0.46860358, -0.23430179, 0.93720717, -0.23430179, -0.46860358, 0.23430179]), ([ 1., -4.11304341, 6.55312175, -4.99084929, 1.7857373 ,-0.2461906 ,  0.01122425]))

# Define sos DC blocking filter: designed in MATLAB
sos = [[0.9992, -1.9983, 0.9991, 1, -1.9988, 0.9988],
       [1,      -2,      1,      1, -1.9995, 0.9995 ]]
       
#Where to send data to firebase
URL = "https://us-central1-noise-monitor-9da34.cloudfunctions.net/noiseLevel"

#start audio stream
def start_stream():
    """
    Starts Pyaudio stream 

    Inputs
    -------
    None.
    
    Returns
    -------
    None.

    """
    global stream, audio
    audio = pyaudio.PyAudio()
    stream = audio.open(format=samp_type,rate=fs,channels=c,input_device_index=dev_ind, input = True, frames_per_buffer = bank_size)


def weight_signal(data):
    """Weights input signal, based on IEC standards for A-weighted filter
       Applies a DC blocker to signal
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
    Inputs
    -------
    Audio signal -> array
    
    Returns
    -------
    Filtered Signal x -> array
    """
    # Apply A-Weighted filter
    x = lfilter(b, a, data)
    # Apply DC Blocker filter
    x = sosfilt(sos, x)
    return x

def squaresum(n) : 
    """
    Inputs
    -------
    Array
    
    Returns
    -------
    Norm of vector -> float
    """
    # Iterate i from 1  
    # and n finding  
    # square of i and 
    # add to sum.
    #Faster than np.linalg.norm()
    sm = sum(i*i for i in n)
    return sm

def read_samples():
    """
    Reads in a set of samples,
    Convert to int32, weight the samples, 
    Stores them in queue sum_sqr_weight

    Inputs
    -------
    None.

    Returns
    -------
    None.

    """
    #Read in data to buffer
    from_buff = stream.read(bank_size, exception_on_overflow=(False))
    data = frombuffer(from_buff, dtype=int32)
    data_shifted = array.array('d')
    #convert value from 32 bit to 24 bit by shifting 8 bits
    #                                   <--------usable--------->
    #Data being read in will be in form 00000000 0000000 00000000 00000000
    #We shift over the data 8 bits to the right, effectively dividing by 2**8
    #Applies a dc blocker to signal using direct difference equation
    for n in range(len(data)):
        sample = (data[n] >> (BD_samp-BD))
        data_shifted.append(sample)
    shifted = squaresum(weight_signal(data_shifted))
    return shifted
    
def avg_db(avg):
    """
    Average a vector of decibel values 
    Inputs
    -------
    Array of decibel values
    
    Returns
    -------
    Avg of those decibel values in dB

    """
    avgsum = 0
    N=len(avg)
    #Transform from dB to avg
    for j in range(N):
        avgsum += 10**(avg[j]/20)
    avg = 20 * log10(avgsum/(N))
    return (avg)
     
    
def calibrate(OS):
    """
    Calibrates the microphone using 94dB 1kHz sine wave.

    Inputs
    -------
    Original OS value

    Returns
    -------
    OS Value calculated from calibration 

    """
    long_db = 0
    long_sum = 0
    leq_buffer = 0
    long_samples = 0
    print("Calibrating to reference. Please place mic in front of 94dB - 1kHz source.")
    while(abs(long_db-ref_1k) > .01 or isnan(abs(long_db-ref_1k))):
        shorts = []
        print(f"Starting calibration...")
        #Run through loop until calibration is set currectly
        for i in range(int_time):
            samps = read_samples()
            long_sum += samps
            long_samples += bank_size
        if long_samples >= fs:
            long_rms = sqrt(long_sum/(long_samples)) 
            long_RMS.append(long_rms)
            long_db = OS + ref_1k + 20 * log10(long_rms/mic_ref)
            long_sum = 0
            shorts.clear()
            long_samples = 0
            avg.append(long_db)
            print(long_db)
        if abs(long_db-ref_1k) < .01:
            if long_db < ref_1k:
                OS+=.001
            elif long_db > ref_1k:
                OS-=.001
        elif abs(long_db-ref_1k) < .1 and abs(long_db-ref_1k) >= .01:
            if long_db < ref_1k:
                OS+=.01
            elif long_db > ref_1k:
                OS-=.01        
        elif abs(long_db-ref_1k) < 1 and abs(long_db-ref_1k) >= .1:
            if long_db < ref_1k:
                OS+=.1
            elif long_db > ref_1k:
                OS-=.1
        elif abs(long_db-ref_1k) >= 10:     
            if long_db < ref_1k:
                OS+=10
            elif long_db > ref_1k:
                OS-=10
        elif abs(long_db-ref_1k) < 10 and abs(long_db-ref_1k) >= 1:  
            if long_db < ref_1k:
                OS+=5
            elif long_db > ref_1k:
                OS-=5
        leq_buffer+=1
            
        print(f"OS: {OS}")     
    return OS


def print_level(level):
    """ 
    Prints a level to the screen
    """
    for i in range(int(round(level))):
        print("#", end = '')
    print('')
    return

def display_leds(avg):
    """ 
    Blinks led corresponding to noise level thresholds
    """
    if avg <= low_thr:
        gled.on()
    elif avg > low_thr and avg <= high_thr:
        yled.on()
    elif avg > high_thr:
        rled.on()
    time.sleep(1)
    rled.off()
    yled.off()
    gled.off()
 
def open_csv():
    """
    Opens CSV file and writes column headers

    Returns
    -------
    None.

    """
    global writer, file
    file = open('noises.csv', 'w', newline='')
    writer = csv.writer(file)
    writer.writerow(["Time Stamp", "Short SPL", "LAEQ 1sec", "LAEQ 10sec"])
    return

def send_status(room, noise, status):
    """
    Sends noise level reading and status to firebase server

    Inputs
    -------
    room: Room that noise monitor is in
    noise: Noise level
    status: One of three values for low, medium, and high noise levels

    Returns
    -------
    None

    """
    PARAMS = {'room':room,'noise':noise, 'status': status}
    try:
        r = requests.get(url = URL, params = PARAMS)
        if r.status_code == 200:
            print("Data successfully sent to server.")
        else:
            print("Failed to send data to server")
    except IOError:
        print("Failed to senf data to server. Will try again soon.")
        return
        
def start_up():
    """
    Simply blinks the leds for a 3 seconds, purely aesthetic
    """
    leds = [gled, yled, rled]
    for i in range(3):
        for j in range(3):
            leds[j].on()
            sleep(.5)
            leds[j].off()
            

def main():
    #Startup audio recording
    start_up()
    start_stream()
    os.system('clear')

    #Uncomment calibrate function to preform calibration
    #Input a 94dB sin at 1kHz until calibration has finished.
    #Offset value will be set accordingly
    #OS = calibrate(OS)

    #Set accumulative sums and such to zero to begin
    long_samples = 0
    long_sum = 0
    leq_db = 0
    leq_buffer = 0
    sensorPressed = 0
    send_buffer = 0
    long_avg = array.array('f')

    print("Press Crtl+C to terminate while statement")
    try:
        #Loop through until interupt is issued
        while stream.is_active():
            #Iterate through 128 times, each time collecting 375 samples
            #
            #Each time a check that calculates short term spl values is used
            #to verify it isnt above mic OL or below mic noise level
            #
            #Add the square A-weighted level to our leq_sum 
            #When enough samples have been taken in calculate leq_db over 1 minute
            for i in range(int_time):
                #Check if the IR sensor is covered
                #Increment up sensorPressed each time
                if IR_SENSOR.is_pressed:
                    rled.on()
                    sensorPressed+=1
                else:
                    ind.off()
                #Read in block of 375 samples and store the weighted squaresum value
                sqr_sum = read_samples()
                #Take RMS by diving by number of sample and taking the sqrt
                short_RMS = sqrt(sqr_sum/bank_size)
                #Calculate a short term SPL used for an over or under indicator
                short_spl = OS + ref_1k + 20 * log10(short_RMS/mic_ref)
                #Discard values that are too low or too high
                if short_spl > mic_OL:
                    short_RMS = INF
                    rled.on()
                elif short_spl < NF:
                    short_RMS = negINF
                    rled.on()
                long_samples += 1
                long_sum += short_RMS
            #After reading 128*375 samples, compute 'long' sound pressure readings.
            #Store in array to be used for a moving average
            long_rms = (long_sum/(long_samples))

            #Reset sums and counters
            long_sum = 0
            long_samples = 0
            avg.append(long_rms)
            
            #If we've read in enough data->start taking a moving avg
            #Moving average acts as a filter where quick fluctuations in sound pressure
            #are ignored
            #Append this moving average to a list to average and send to dashboard
            if leq_buffer > window_size-1+OF: 
                #Average the readings in moving buffer and push into list
                #FIFO
                average = OS + ref_1k + 20 * log10((sum(avg[0:window_size])/len(avg))/mic_ref)
                long_avg.append(average)
                #print(f"LAEQ: {average} at {datetime.datetime.now()}")
                display_leds(average)
                avg.pop(0)
            if send_buffer >= num_sec-(60/send_rate):
                #Average the long_spl readings in moving buffer
                leq_db = (avg_db(long_avg))
                #Check if IR sensor was covered, use LOUD as a status
                if sensorPressed > 128:
                    status = "LOUD"
                else:
                    #Otherwise, set status accordingly
                    if leq_db >= high_thr:
                        status = "LOUD"
                    elif leq_db < high_thr and leq_db >= low_thr:
                        status = "WARNING"
                    else:
                        status = "GOOD"

                #Send status to dashboard
                send_status(1424, leq_db, status)

                #Reset buffer counter
                send_buffer = 0

                #Clear out array and reset IR sensor trigger
                long_avg = array.array('f')
                sensorPressed = 0

            send_buffer+=1
            leq_buffer+=1
    except KeyboardInterrupt:
        print("Stopping monitor...")
        pass
    #Close out of csv file and audio recording
    file.close()
    stream.stop_stream()
    stream.close()
    audio.terminate()
    return
    
if __name__ == "__main__":
    main()
