
#!/usr/bin/env python3 -*- coding: utf-8 -*-
"""
Created on Wed Dec 23 08:28:33 2020
Last Rev: Thu April 8th 2021
@author: Liam
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
time2sleep = 1 #Defines the amount of time to rest between measurements


high_thr = 90 #Define a "loud" level reading
low_thr = 70  #Define a "quiet" level reading
              #In between is the "moderate" level

#Definitions of GPIO input and outputs
rled = LED(17)
yled = LED(27)
gled = LED(22)
IR_LED = LED(6)
ind = LED(13);IR_LED.on();
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
OS = 0 #Define tuning parameter OS, which can be used to calibrate meter
NF =30 #Define the noise floor of the microphone, any data under this is invalid
sens = -26 #Define the sensitivity of the mic from datasheet
mic_ref = pow(10, (sens/20))*((1<<(BD - 1))-1) #Equation for calculating mic_sens in mV/Pa

#Define some constants to be used by the program
#Some are depenedent upon 
samp_short = (fs / 8) #Specifies a "short" time scale of .125 seconds as defined by IEC standards
samp_long = (fs) #Specifies a "long" time scale of 1 second * the chose LEQ length
bank_size = int(samp_short/16) #Number of frames per "buffer", chosen at (0.125/16)*fs = 375 
int_time = 128 #Define the number of chuncks to iterate over to form one LAeq_db value
window_size = 5 #Size of moving average window
send_rate =  60   #Rate to send data, times per hour
num_sec = int((((60/send_rate) * 60) + (60/send_rate))/2) ##Allocate space for 15 * 60 samples + 15 for a buffer



#Preallocate memory for our arrays
long_avg = []
long_RMS = []
avg = array.array('f') #Used to hold moving buffer of rms readings
long_avg = array.array('f') #Used to hold spl values to average and send to dashboard
b, a = (([ 0.23430179, -0.46860358, -0.23430179, 0.93720717, -0.23430179, -0.46860358, 0.23430179]), ([ 1., -4.11304341, 6.55312175, -4.99084929, 1.7857373 ,-0.2461906 ,  0.01122425]))

#Define sos DC blocking filter: designed in MATLAB
sos = [[0.9992, -1.9983, 0.9991, 1, -1.9988, 0.9988],
       [1,      -2,      1,      1, -1.9995, 0.9995 ]]
       
URL = "https://us-central1-noise-monitor-9da34.cloudfunctions.net/noiseLevel"

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
    x = sosfilt(sos, x)
    
    return x

def squaresum(n) : 
    # Iterate i from 1  
    # and n finding  
    # square of i and 
    # add to sum.
    sm = sum(i*i for i in n)
    return sm

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
    """
    avgsum = 0
    N=len(avg);
    for j in range(N):
        avgsum += 10**(avg[j]/20)
    avg = 20 * log10(avgsum/(N))
    return (avg)
     

    
def calibrate(OS):
    long_db = 0
    long_sum = 0
    leq_buffer = 0
    long_samples = 0
    print("Calibrating to reference. Please place mic in front of 94dB - 1kHz source.")
    while(abs(long_db-ref_1k) > .01 or isnan(abs(long_db-ref_1k))):
        shorts = []
        print(f"Starting calibration...")
        for i in range(int_time):
            
            samps, cont = read_samples()
            long_sum += samps
            long_samples += bank_size
            #After one second has been read in, calculate a spl_
        if long_samples >= fs:
            long_rms = sqrt(long_sum/(long_samples)) #Subtract the amount of NUL (0) Values
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
    for i in range(int(round(level))):
        print("#", end = '')
    print('')
    return

def display_leds(avg):
    if avg <= low_thr:
        gled.on()
    elif avg > low_thr and avg <= high_thr:
        yled.on()
    elif avg > high_thr:
        rled.on()
    time.sleep(time2sleep)
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
    PARAMS = {'room':room,'noise':noise, 'status': status}
    r = requests.get(url = URL, params = PARAMS)
    if r.status_code == 200:
        print("Data successfully sent to server.")
    else:
        print("Failed to send data to server")
def start_up():
    leds = [gled, yled, rled]
    for i in range(3):
        for j in range(3):
            leds[j].on()
            sleep(.5)
            leds[j].off()
            
def processSamps():
    pass

def main():
    os.system('clear')
    open_csv()
    start_up()
    start_stream()
    #OS Value for working prototype
    OS = -2.611
    #os.system('clear')
    #Uncomment calibrate function to preform calibration
    #Input a 94dB sin at 1kHz until calibration has finished.
    #Offset value will be set accordingly
    #OS = calibrate(OS)

    #set accumulative sums and such to zero to begin
    leq_samples=0
    leq_sum=0
    leq_db=0
    leq_rms = 0
    long_samples = 0
    long_sum = 0
    leq_buffer = 0
    OF = 10 #Throw out first 10 sets of samples
    print("Press Crtl+C to terminate while statement")
    try:
        send_buffer = 0
        long_avg = array.array('f')
        #loop through until interupt is issued
        while stream.is_active():
            #Clear queue each time through
            #sum_sqr_weight.clear()
            #Iterate through 128 times, each time collecting 375 samples
            #
            #Each time a check that calculates short term spl values is used
            #to verify it isnt above mic OL or below mic noise level
            #
            #Add the square A-weighted level to our leq_sum 
            #When enough samples have been taken in calculate leq_db over 1 minute
            for i in range(int_time):
                if IR_SENSOR.is_pressed:
                    #print("IR SENSOR COVERED")
                    rled.on()
                else:
                    ind.off()
                #Read in block of 375 samples and store the weighted squaresum value
                sqr_sum = read_samples()
                short_RMS = sqrt(sqr_sum/bank_size)
                short_spl = OS + ref_1k + 20 * log10(short_RMS/mic_ref)
                if short_spl > mic_OL:
                    short_spl = 120
                    rled.on()
                elif short_spl < NF:
                    short_spl = 30
                    rled.on()
                leq_sum += sqr_sum
                leq_samples += bank_size
                long_samples += 1
                long_sum += short_RMS
            #After reading 128*375 samples, compute 'long' sound pressure readings.
            #Store in array to be used for a moving average
            long_rms = (long_sum/(long_samples))
            long_sum = 0
            long_samples = 0
            avg.append(long_rms)
            #If we've read in enough data->start taking a moving avg
            #Moving average acts as a filter where quick fluctuations in sound pressue
            #are ignored.
            #
            #Append this moving average to a list to average and send to dashboard
            if leq_buffer > window_size-1+OF: 
                #Average the readings in moving buffer
                average = OS + ref_1k + 20 * log10((sum(avg[0:window_size])/len(avg))/mic_ref)
                #Push into list
                long_avg.append(average)
                print(f"LAEQ: {average} at {datetime.datetime.now()}")
                display_leds(average)
                #Clear the first element from array so only window_size elements 
                #are stored at any given time
                avg.pop(0)
            #If we've read in a 60 seconds of data->start taking moving avg
            if send_buffer >= num_sec-(60/send_rate):
                #Average the long_spl readings in moving buffer
                
                #leq_db = OS + ref_1k + 20 * np.log10(leq_rms/mic_ref)
                t0 = datetime.datetime.now()
                leq_db = (avg_db(long_avg))
                print(f"Time in avg_db: {datetime.datetime.now()-t0}")
                t0 = datetime.datetime.now()
                leq_rms = sqrt(leq_sum/(leq_samples))
                leq = OS + ref_1k + 20 * log10((leq_rms/(leq_samples)))
                print(f"Time in rms-spl: {datetime.datetime.now()-t0}")
                #display_leds(leq_db)
                #Send status to dashboard
                if leq_db >= high_thr:
                    status = "LOUD"
                elif leq_db < high_thr and leq_db >= low_thr:
                    status = "WARNING"
                else:
                    status = "GOOD"
                send_status(1424, leq_db, status)
                print(f"{leq_db}...")
                print(f"{leq}...")
                #Reset LEQ buffer to window size
                send_buffer = 0
                leq_sum = 0
                leq_samples = 0
                long_avg = array.array('f')
            send_buffer+=1
            leq_buffer+=1
            
                

    except KeyboardInterrupt:
        print("Stopping monitor...")
        pass
    file.close()
    stream.stop_stream()
    stream.close()
    audio.terminate()
    
    
if __name__ == "__main__":
    main()

