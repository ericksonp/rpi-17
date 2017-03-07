#!/usr/bin/python
import smtplib
import time
import subprocess
hostname=subprocess.check_output(["hostname"]).strip()
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
    
now=time.localtime(time.time())
timeStamp=time.strftime("%Y-%m-%d %H:%M:%S", now)

message_subject=hostname+ " has stopped but has restarted"
message_text="This email confirms that " + hostname + " has restarted its program at " + timeStamp
 
send_email("priscilla.erickson@gmail.com", message_subject, message_text)
