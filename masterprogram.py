#!/usr/bin/python

#import all of the required modules
import sys
import time
from neopixel import *
import Adafruit_MCP9808.MCP9808 as MCP9808
from tentacle_pi.TSL2561 import TSL2561
import csv
import RPi.GPIO as GPIO
sys.path.append("/home/pi/SHT31_PAE")#adds the custom SHT31 function
from SHT31 import *
import ConfigParser
import subprocess
import smtplib
from shutil import copyfile
import filecmp
import os.path

#arguments will be in a separate .ini file (sys.argv[1]) which is read in and parsed to get different argument types
inputfile=str(sys.argv[1]) #the input .ini file is given as the first argument when the python script is called

#setup hardware (only ever needs to happen once)
#set up LED indicator light via GPIO 16 (turns on whenever lights are on)
GPIO.setmode(GPIO.BCM)
GPIO.setup(16, GPIO.OUT)

#setup Heater via Powerswitch on GPIO 23
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.OUT)

#set up light moniter
tsl = TSL2561(0x39,"/dev/i2c-1")
tsl.enable_autogain()
tsl.set_time(0x00)

#Turn on temperature sensor
sensor = MCP9808.MCP9808()
sensor.begin()

#determine hostname of computer and start a day counter
hostname=subprocess.check_output(["hostname"]).strip()
lastday=0

#define function for sending warning email if tempearture is out of range:
GMAIL_USER= "bergland.rpi@gmail.com"
GMAIL_PASS="photoperiod!"
SMTP_SERVER="smtp.gmail.com"
SMTP_PORT=587

def send_email(recipient, subject, text):
    smtpserver=smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    smtpserver.ehlo()
    smtpserver.starttls()
    smtpserver.ehlo
    smtpserver.login(GMAIL_USER, GMAIL_PASS)
    header = "To: "+recipient + "\n" + "From: " + GMAIL_USER
    header = header + "\n" + "Subject:" + subject + "\n"
    msg = header + "\n" + text + " \n\n"
    smtpserver.sendmail(GMAIL_USER, recipient, msg)
    smtpserver.close()

#function to read in all aspects of configuration
def readInput(startingfile):
    d={}
    f = open(startingfile, 'r')
    for line in f:
        k, v = line.strip().split('=')
        d[k.strip()] = v.strip()
    f.close()
    return d

#convert numerical dicitonary values to floats and ints
intlist=["LED_COUNT","brightness", "R", "G", "B", "W", "Pulse_R", "Pulse_G", "Pulse_B", "Pulse_W", "R2", "G2", "W2", "B2", "R3", "B3", "G3", "W3"]
def convertInt(dict,intlist):
    for i in intlist:
        dict[i]=int(dict[i])

floatlist=["onTime", "offTime", "checkTime", "highAlarm", "lowAlarm", "Pulse_on", "Pulse_off", "Ramp_ontime", "Ramp_offtime", "heatOn", "heatOff", "color2_offtime", "color3_offtime"]
def convertFloat(dict,floatlist):
    for f in floatlist:
        dict[f]=float(dict[f])

#make a master datafile
def makeOutFile(outfile):
    C =(open(outfile, 'wb'))
    return C

def makeOutWriteable(C):
    WRTR = csv.writer(C)
    return WRTR

def writeHeader(WRTR, C):    #write a header column in master file
    WRTR.writerow(["TimeStamp", "Elapsed", "MCP9808Temp", "SHT31Temp", "Humidity", "Lux", "Lights", "Time_in_hours", "R", "G", "B", "W", "Heater"])
    C.flush()

configpath=inputfile
configcopy=hostname+"-config-"+time.strftime("%Y-%m-%d")+"-copy.log"
copyfile(configpath, configcopy)

#read input file on first time through program and configure
a=readInput(inputfile)
convertInt(a,intlist)
convertFloat(a,floatlist)
#specify LED configuration
LED_COUNT      = a["LED_COUNT"]                 # Number of LED pixels (always 24 in ring).
LED_PIN        = 18                 # GPIO pin connected to the pixels (must support PWM-always 18!).
LED_FREQ_HZ    = 800000             # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 5                  # DMA channel to use for generating signal (try 5)
LED_BRIGHTNESS = a["brightness"]         # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False              # True to invert the signal (when using NPN transistor
LED_CHANNEL    = 0
LED_STRIP      = ws.SK6812_STRIP_RGBW
# Create NeoPixel object with appropriate configuration.
strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL, LED_STRIP)
# Intialize the library (must be called once before other functions).
strip.begin()

#generate data files
outfile_name=hostname+"-restart-"+time.strftime("%Y-%m-%d")+".csv"
c=makeOutFile(outfile_name)
wrtr=makeOutWriteable(c)
writeHeader(wrtr, c)
#determine program start time with current configuration
programstart=time.time()
#indicate that no alarm email has been sent and no time has passed since last alarm
hasAlarmed=False
timeSinceAlarm=0

#start checking the time and performing an infinite loop
while True:
    loopstart=time.time() 
    #check if input file has changed from the backup copy
    new=open(configpath,"r").read()
    old=open(configcopy,"r").read()
    if new != old: #reset everything if configuration file has changed
        print "resetting"
        email_text=hostname+" has started a new program: "+ new
        email_subject=hostname+" has reset"
        send_email("priscilla.erickson@gmail.com", email_subject, email_text)
        a=readInput(inputfile)
        convertInt(a,intlist)
        convertFloat(a,floatlist)
        LED_COUNT      = a["LED_COUNT"]
        LED_BRIGHTNESS = a["brightness"]
        strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL, LED_STRIP)
        strip.begin()
        configcopy=inputfile+time.strftime("%Y-%m-%d")+"copy.log"
        copyfile(configpath,configcopy)
        programstart=time.time()
        outfile_name=hostname+"-restart-"+time.strftime("%Y-%m-%d")+".csv"
        c=makeOutFile(outfile_name)
        wrtr=makeOutWriteable(c)
        writeHeader(wrtr, c)
        hasAlarmed=False
        timeSinceAlarm=0
    else:
        print "no reset"

    #determine current time
    #record start time of loop so that total loop time can be precisely adjusted
    now=time.localtime(time.time()) #current time
    elapsedtime=(time.time()-programstart)/3600 #Elapsed time in hours since program started
    timeStamp=time.strftime("%Y-%m-%d %H:%M:%S", now) #break time into H, M, S
    print timeStamp

    #apply calculation to time to determine time in hours as a decimal
    hour= float(time.strftime("%H "))
    minute= float(time.strftime("%M "))
    second=float(time.strftime("%S "))
    day=float(time.strftime("%d"))
    time_in_hours=hour+minute/60+second/3600

    #make a daily file if needed right after midnight when day counter has turned over
    todaysdate=time.strftime("%Y-%m-%d", now)
    dailyfilename=hostname+"-"+todaysdate+".csv" 
    if lastday == 0 and os.path.isfile(dailyfilename)==False : #program is starting for first time and file doesn't exist; make new file
        df =(open(dailyfilename, 'wb'))
        dfwrtr = csv.writer(df)
        dfwrtr.writerow(["TimeStamp", "Elapsed", "MCP9808Temp", "SHT31Temp", "Humidity", "Lux", "Lights", "Time_in_hours", "R", "G", "B", "W", "Heater"])
        df.flush()
    elif lastday == 0 and os.path.isfile(dailyfilename) == True :#program is starting but file already exists; append
        df =(open(dailyfilename, 'a'))
        dfwrtr = csv.writer(df)
    elif lastday != day :#day has turned over; make a new file
        df=(open(dailyfilename, 'wb'))
        dfwrtr = csv.writer(df)
        dfwrtr.writerow(["TimeStamp", "Elapsed", "MCP9808Temp", "SHT31Temp", "Humidity", "Lux", "Lights", "Time_in_hours", "R", "G", "B", "W", "Heater"])
        df.flush()
    else:
        df =(open(dailyfilename, 'a'))
        dfwrtr = csv.writer(df)
    
    #turn heat on if needed
    if a["Heat"] == "True" and a["heatOn"] <= time_in_hours < a["heatOff"]:
        GPIO.output(23, True)
        print "Heat on!"
        heater=True
    else:
        GPIO.output(23, False)
        print "Heat off"
        heater=False

    #read sensors for temperature, humidity, and light intensity
    currtemp=sensor.readTempC()
    print "MCP9808 Temperature is", currtemp
    SHT31reading=read_SHT31()
    print "SHT31 Temperature is", SHT31reading[0]
    print "SHT31 Humidity is", SHT31reading[1]
    currlux=tsl.lux()
    print "Lux is", currlux

    #Send email if temperature is out of range
    if hasAlarmed==True:
        timeSinceAlarm=time.time()-alarmTime
        
    if (currtemp < a["lowAlarm"] or currtemp > a["highAlarm"]) and (elapsedtime > 0.05) and (hasAlarmed==False or timeSinceAlarm > 14400):
        print 'Alarm!'
        print 'Current temp=', currtemp
        print 'High Alarm=', a["highAlarm"]
        print 'Low Alarm=', a["lowAlarm"]
        subject=hostname+ " has a temperature problem"
        message=hostname+ " has a temperature of " + str(currtemp)
        send_email("priscilla.erickson@gmail.com", subject, message)
        print "Email sent"
        hasAlarmed=True
        alarmTime=time.time()

    else:
        print 'No Alarm'

    #check for light pulse
    if a["Pulse"] == "True" and a["Pulse_on"] <= time_in_hours < a["Pulse_off"]:
        print "Pulsing"
        lights="Pulse"
        GPIO.output(16, True)
        for i in range(a["LED_COUNT"]):
            strip.setPixelColor(i,Color(int(a["Pulse_G"]), int(a["Pulse_R"]),int(a["Pulse_B"]),int(a["Pulse_W"])))
            strip.show()
        currR=a["Pulse_R"]
        currG=a["Pulse_G"]
        currB=a["Pulse_B"]
        currW=a["Pulse_W"]

    #then check for ramping on. Ramp lights are automatically same as first color
    elif a["Ramp_on"] == "True" and (a["Ramp_ontime"] <= time_in_hours < a["onTime"]):
        print "Ramping on"
        Ramp_time=a["onTime"] - a["Ramp_ontime"] #total time that will be spent ramping
        fade=(time_in_hours-a["Ramp_ontime"])/Ramp_time #proportion of ramping that is completed
        lights="increasing"
        tempR=int(float(a["R"])*fade) #calculate a red value based on proporition of ramping completed
        tempG=int(float(a["G"])*fade) #calculate a green value based on proporition of ramping completed
        tempB=int(float(a["B"])*fade) #calculate a blue value based on proporition of ramping completed
        tempW=int(float(a["W"])*fade) #calculate a white value based on proporition of ramping completed
        for i in range(a["LED_COUNT"]):
            GPIO.output(16, True)
            strip.setPixelColor(i,Color(tempG,tempR,tempB,tempW)) #assigns a temporary modulated color value based on ramp progression
            strip.show()
        currR=tempR
        currG=tempG
        currB=tempB
        currW=tempW

    #then check if lights are on main cycle
    elif a["onTime"] <= time_in_hours < a["offTime"]:
        print ' Lights on!'
        lights="on, main"
        GPIO.output(16, True)
        for i in range(LED_COUNT):
            strip.setPixelColor(i,Color(a["G"], a["R"], a["B"], a["W"])) #sets LEDs to main color
            strip.show()
        currR=a["R"]
        currG=a["G"]
        currB=a["B"]
        currW=a["W"]

    #then check if lights should be on color2
    elif a["color2_used"]=="True" and a["offTime"] <= time_in_hours < a["color2_offtime"]:
        print 'Lights on color2!'
        lights="on, color2"
        GPIO.output(16, True)
        for i in range(a["LED_COUNT"]):
            strip.setPixelColor(i,Color(a["G2"],a["R2"],a["B2"],a["W2"])) #sets strip to second color scheme
            strip.show()
        currR=a["R2"]
        currG=a["G2"]
        currB=a["B2"]
        currW=a["W2"]

    #then check if lights should be on color3
    elif a["color3_used"] =="True" and a["color2_offtime"] <= time_in_hours < a["color3_offtime"]:
        print ' Lights on color 3!'
        lights="on, color3"
        GPIO.output(16, True)
        for i in range(a["LED_COUNT"]):
            strip.setPixelColor(i,Color(a["G3"],a["R3"],a["B3"],a["W3"])) #sets lights to third color scheme
            strip.show()
        currR=a["R3"]
        currG=a["G3"]
        currB=a["B3"]
        currW=a["W3"]

    #then check for ramping off. Ramping off will occur for last used color
    elif a["Ramp_off"] == "True" and a["color2_used"] == "False" and a["color3_used"] == "False" and a["offTime"] <= time_in_hours < a["ramp_offtime"]:
        print "Ramping off"
        Ramp_time=a["ramp_offtime"] - a["offTime"] #total time that will be spent ramping down
        fade=(a["ramp_offtime"]-time_in_hours)/Ramp_time #proportion of ramping that is uncompleted
        lights="decreasing main color"
        tempR=int(float(a["R"])*fade) #calculate a red value based on proporition of ramping completed
        tempG=int(float(a["G"])*fade) #calculate a green value based on proporition of ramping completed
        tempB=int(float(a["B"])*fade) #calculate a blue value based on proporition of ramping completed
        tempW=int(float(a["W"])*fade) #calculate a white value based on proporition of ramping completed
        for i in range(a["LED_COUNT"]):
            GPIO.output(16, True)
            strip.setPixelColor(i,Color(tempG,tempR,tempB,tempW))
            strip.show()
        currR=tempR
        currG=tempG
        currB=tempB
        currW=tempW

    #ramping off if 2 colors:
    elif a["Ramp_off"] == "True" and a["color2_used"] == "True" and a["color3_used"] == "False" and a["color2_offtime"] <= time_in_hours < a["Ramp_offtime"]:
        print "Ramping off color2"
        Ramp_time=a["Ramp_offtime"] - a["color2_offtime"] #total time that will be spent ramping down
        fade=(a["Ramp_offtime"]-time_in_hours)/Ramp_time #proportion of ramping that is uncompleted
        lights="decreasing color2"
        tempR=int(float(a["R2"])*fade) #calculate a red value based on proporition of ramping completed
        tempG=int(float(a["G2"])*fade) #calculate a green value based on proporition of ramping completed
        tempB=int(float(a["B2"])*fade) #calculate a blue value based on proporition of ramping completed
        tempW=int(float(a["W2"])*fade) #calculate a white value based on proporition of ramping completed
        for i in range(a["LED_COUNT"]):
            GPIO.output(16, True)
            strip.setPixelColor(i,Color(tempG,tempR,tempB,tempW))
            strip.show()
        currR=tempR
        currG=tempG
        currB=tempB
        currW=tempW

    #ramping off if 3 colors:
    elif a["Ramp_off"] == "True" and a["color2_used"] == "True" and a["color3_used"] == "True" and a["color3_offtime"] <= time_in_hours < a["Ramp_offtime"]:
        print "Ramping off color3"
        Ramp_time=a["Ramp_offtime"] - a["color3_offtime"] #total time that will be spent ramping down
        fade=(a["Ramp_offtime"]-time_in_hours)/Ramp_time #proportion of ramping that is uncompleted
        lights="decreasing color3"
        tempR=int(float(a["R3"])*fade) #calculate a red value based on proporition of ramping completed
        tempG=int(float(a["G3"])*fade) #calculate a green value based on proporition of ramping completed
        tempB=int(float(a["B3"])*fade) #calculate a blue value based on proporition of ramping completed
        tempW=int(float(a["W3"])*fade) #calculate a white value based on proporition of ramping completed
        for i in range(a["LED_COUNT"]):
            GPIO.output(16, True)
            strip.setPixelColor(i,Color(tempG,tempR,tempB,tempW))
            strip.show()
        currR=tempR
        currG=tempG
        currB=tempB
        currW=tempW

    #if none of the above conditions are true, lights should be off
    else:
        print 'Lights off!, LED off'
        GPIO.output(16,False)
        lights="Off"
        for i in range(a["LED_COUNT"]):
            strip.setPixelColor(i,Color(0,0,0,0))
            strip.show()
        currR=0
        currG=0
        currB=0
        currW=0

    #write all the current data to a new line in data file
    
    wrtr.writerow([timeStamp, elapsedtime, currtemp, SHT31reading[0], SHT31reading[1], currlux, lights, time_in_hours, currR, currG, currB, currW, heater])
    dfwrtr.writerow([timeStamp, elapsedtime, currtemp, SHT31reading[0], SHT31reading[1], currlux, lights, time_in_hours, currR, currG, currB, currW, heater])
    c.flush()
    df.flush()

    #assign value to lastday so it will detect when a new calendar day starts
    lastday=day

    # determine how much time to wait so that loop is executed based on checkTime seconds
    time.sleep(a["checkTime"] - ((time.time() - loopstart) % 60.0))

