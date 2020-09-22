# PacketRaven 

[![tests](https://github.com/UMDBPP/PacketRaven/workflows/tests/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Atests)
[![build](https://github.com/UMDBPP/PacketRaven/workflows/build/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Abuild)

PacketRaven is a front-end data aggregator / dashboard, designed to track the progress of high-altitude balloon payload flights via location telemetry.

```bash
pip install packetraven
```

#### Usage:
to start the client, run the following:
```bash
packetraven
```
```bash
usage: packetraven [-h] [-k APIKEY] [-c CALLSIGNS] [-s] [-p PORT] [-l LOG] [-o OUTPUT] [-t INTERVAL] [-g]

optional arguments:
  -h, --help            show this help message and exit
  -k APIKEY, --apikey APIKEY
                        API key from https://aprs.fi/page/api
  -c CALLSIGNS, --callsigns CALLSIGNS
                        comma-separated list of callsigns to track
  -s, --skipserial      skip attempting to connect to APRS packet radio
  -p PORT, --port PORT  name of serial port connected to APRS packet radio
  -l LOG, --log LOG     path to log file to save log messages
  -o OUTPUT, --output OUTPUT
                        path to output file to save packets
  -t INTERVAL, --interval INTERVAL
                        seconds between each main loop
  -g, --gui             start the graphical interface

```

#### Python API:
to retrieve packets directly from https://aprs.fi:
```python
from packetraven import DEFAULT_CALLSIGNS, APRSfiConnection

callsigns = ['W3EAX-8', 'W3EAX-12', 'KC3FXX', 'KC3ZRB']
api_key = '' # enter your APRS.fi API key here - you can get a free API key from https://aprs.fi/page/api

aprs_fi = APRSfiConnection(callsigns, api_key)
aprs_fi_packets = aprs_fi.packets

print(aprs_fi_packets)
```
or parse packets from a radio sending parsed APRS over a USB connection:
```python
from packetraven import APRSPacketRadio
 
serial_port = None # leave None to let PacketRaven guess the port name  

radio = APRSPacketRadio(serial_port)
radio_packets = radio.packets

print(radio_packets)
```
or connect to a PostGreSQL database running PostGIS:
```python
from packetraven import APRSPacketDatabaseTable

hostname = 'bpp.umd.edu:5432' 
database = 'bpp'
table = 'packets'

username = 'username'
password = '1234'

table = APRSPacketDatabaseTable(hostname, database, table, username=username, password=password)
table_packets = table.packets

print(table_packets)
```

#### Features:
###### current:
- parse APRS packets from USB radio
- retrieve packets from https://aprs.fi
- output packets to file
- plot altitude

###### in development:
- flight track plotting
- live track prediction
- Iridium telemetry and commands
- live chase navigation
