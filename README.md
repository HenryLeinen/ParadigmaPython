# ParadigmaPython
Paradigma Python Handler as connector for FHEM using MQTT.

This python script interacts with a *Paradigma* USB interface to query data from a Paradigma Heating system. I have tested it with my *Paradigma Pelletti Mini*.

# Precondition / Needed modules
## Software
Perform the following to install required modules :

sudo apt-get install mosquitto mosquitto-clients
pip install paho-mqtt

## Hardware
You will need to have a usb interface to talk to your paradigma system.


# How to install ?
cp ./paradigma.py /usr/bin/paradigma.py
sudo crontab -e

--> Make sure the following entry is listed at the end :
5 * * * * python /usr/bin/paradigma.py -l
