# PacketRaven 

[![tests](https://github.com/UMDBPP/PacketRaven/workflows/tests/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Atests)
[![build](https://github.com/UMDBPP/PacketRaven/workflows/build/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Abuild)
[![version](https://img.shields.io/pypi/v/packetraven)](https://pypi.org/project/packetraven)
[![license](https://img.shields.io/badge/license-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

PacketRaven is a front-end data aggregator / dashboard, designed to track the progress of high-altitude balloon payload flights via location telemetry.

```bash
pip install packetraven
```

#### Usage:
```bash
packetraven -c W3EAX-8,W3EAX-12 -k <aprs_fi_api_key> 
```
```bash
usage: packetraven [-h] -c CALLSIGNS [-k APIKEY] [-p PORT] [-d DATABASE] [-t TUNNEL] [-l LOG] [-o OUTPUT] [-i INTERVAL] [-g]

optional arguments:
  -h, --help            show this help message and exit
  -c CALLSIGNS, --callsigns [CALLSIGNS]
                        comma-separated list of callsigns to track
  -k APIKEY, --apikey APIKEY
                        API key from https://aprs.fi/page/api
  -p PORT, --port PORT  name of serial port connected to APRS packet radio
  -d DATABASE, --database DATABASE
                        PostGres database table `user@hostname:port/database/table`
  -t TUNNEL, --tunnel TUNNEL
                        SSH tunnel `user@hostname:port`
  -l LOG, --log LOG     path to log file to save log messages
  -o OUTPUT, --output OUTPUT
                        path to output file to save packets
  -i INTERVAL, --interval INTERVAL
                        seconds between each main loop (default: 10)
  -g, --gui             start the graphical interface
```

#### Python API:
to retrieve packets directly from https://aprs.fi:
```python
from packetraven import APRSfiConnection

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

callsigns = ['W3EAX-8', 'W3EAX-12', 'KC3FXX', 'KC3ZRB']

hostname = 'bpp.umd.edu:5432'
database = 'bpp'
table = 'packets'

username = 'username'
password = '1234'

# parameters for an SSH tunnel
ssh_hostname = None
ssh_username = None
ssh_password = None

table = APRSPacketDatabaseTable(hostname, database, table, callsigns, 
                                username=username, password=password, 
                                ssh_hostname=ssh_hostname, ssh_username=ssh_hostname, ssh_password=ssh_password)
table_packets = table.packets

print(table_packets)
```

#### Features:
###### current:
- parse APRS packets from USB radio
- retrieve packets from https://aprs.fi
- synchronize with a PostGreSQL database
- output packets to file
- plot altitude

###### in development:
- flight track plotting
- live track prediction
- Iridium telemetry and commands
- live chase navigation
