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

ptyhon3 -m paradigma_bridge.main


# Message of Paradigma
## Nachrichtenformat (Message Frame)

Die Kommunikation mit der Paradigma-Heizung erfolgt über telegrammartige Nachrichtenframes mit fest definiertem Aufbau.  
Jedes Telegramm besteht aus einem Kommandobyte, einem Längenbyte, den Payload-Daten sowie einer abschließenden Checksumme.

### Aufbau des Telegramms

| Byteposition | Feld | Beschreibung |
|---|---|---|
| 0 | Kommando | Befehlsbyte (`0x0A`, `0xFC` oder `0xFD`) |
| 1 | Länge | Anzahl der Payload-Bytes |
| 2..n+1 | Payload | Nutzdaten |
| n+2 | Checksumme | 8-Bit-Prüfsumme |

### Frame-Struktur

```text
┌────────────┬──────────┬──────────────────────┬────────────┐
│ Kommando   │ Länge    │ Payload              │ Checksumme │
│ 1 Byte     │ 1 Byte   │ n Bytes              │ 1 Byte     │
├────────────┼──────────┼──────────────────────┼────────────┤
│ 0x0A       │ 0x03     │ 0x12 0x34 0x56       │ 0xA7       │
└────────────┴──────────┴──────────────────────┴────────────┘
```

### Bedeutung der Kommandobytes

| Kommando | Bedeutung |
|---|---|
| `0x0A` | Standardkommando |
| `0xFC` | Dataset broadcast |
| `0xFD` | Command Response |

### Beispieltelegramm

```text
0A 03 12 34 56 A7
```

Interpretation:

| Feld | Wert |
|---|---|
| Kommando | `0x0A` |
| Payload-Länge | `3` |
| Payload | `12 34 56` |
| Checksumme | `0xA7` |

### Berechnung der Checksumme

Die Checksumme wird als 8-Bit-Zweierkomplement über alle vorherigen Bytes berechnet:

```python
checksum = (~(command + length + sum(payload)) + 1) & 0xFF
```

Mathematisch entspricht dies:

```text
Checksum = (-(Command + Length + ΣPayload)) mod 256
```

Damit gilt stets:

```text
(Command + Length + Payload + Checksum) mod 256 = 0
```
