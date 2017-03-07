#!/bin/bash

sleep 30
hn=$(hostname)
cd /home/pi/$hn
git pull

if pgrep -f "masterprogram.py" > /dev/null
then
    echo "Running"
else
    echo "Stopped"
    sudo python /home/pi/$hn/masterprogram.py /home/pi/$hn/config.txt & 
    sleep 15
    if pgrep -f "masterprogram.py" > /dev/null
    then
    	sudo python /home/pi/$hn/restart_email.py
	echo 'program restarted'
    else
    	sudo python /home/pi/$hn/restart_fail_email.py
	echo 'program did not start'
    fi
fi
