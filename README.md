# ParadigmaPython
Paradigma Python Handler as connector for FHEM

# Precondition / Needed modules
Perform the following to install required modules :

sudo apt-get install mosquitto mosquitto-clients
pip install paho-mqtt

# How to install the old version of paradigma.py?
cp ./paradigma.py /usr/bin/paradigma.py
sudo crontab -e

--> Make sure the following entry is listed at the end :
5 * * * * python /usr/bin/paradigma.py -l



# How to install the new version of paradigma_brige
Paradigma bridge is the new version which supports the full memory map of the paradigma as well as the MQTT interface to read and modify variables.
The module can be executed using the command line:

ptyhon3 -m paradigma_bridge.main.py


# Message of Paradigma
Deine synchrone Funktion ist im Kern ein blockierender Rahmen-Parser für ein Byteprotokoll mit dieser Struktur:
CMD∣LEN∣PAYLOAD 
0…LEN−1
​	
 ∣CHKSUM
wobei ein gültiger Rahmen mit einem der Startbytes
{0x0A,0xFC,0xFD}
beginnt und die Summenbedingung gilt:
(CMD+LEN+∑PAYLOAD+CHKSUM)mod256=0

