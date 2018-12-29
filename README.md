# ParadigmaPython
Paradigma Python Handler as connector for FHEM

# Precondition / Needed modules
Perform the following to install required modules :

sudo apt-get install mosquitto mosquitto-clients
pip install paho-mqtt

# How to install ?
cp ./paradigma.py /usr/bin/paradigma.py
sudo crontab -e

--> Make sure the following entry is listed at the end :
5 * * * * python /usr/bin/paradigma.py -l
