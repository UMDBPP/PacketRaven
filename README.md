# PacketRaven 

[![tests](https://github.com/UMDBPP/PacketRaven/workflows/tests/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Atests)
[![build](https://github.com/UMDBPP/PacketRaven/workflows/build/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Abuild)
[![version](https://img.shields.io/pypi/v/packetraven)](https://pypi.org/project/packetraven)
[![license](https://img.shields.io/github/license/umdbpp/packetraven)](https://opensource.org/licenses/MIT)

PacketRaven is a front-end data aggregator / dashboard, designed to track the progress of high-altitude balloon payload flights via location telemetry.

```bash
pip install packetraven
```

## Examples:
#### listen to a TNC sending raw APRS strings over USB port COM4:
```cmd
packetraven --tnc COM4
```

### listen to APRS.fi, watching specific callsigns:
you need an API key to connect to APRS.fi; you can get one from https://aprs.fi/page/api
```cmd
packetraven --apikey <api_key> --callsigns W3EAX-8,W3EAX-14
```
#### listen to a PostGIS database table:
```cmd
packetraven --database <username>@<hostname>:5432/<database_name>/<table_name>
```
#### watch a text file for new lines containing raw APRS strings:
```cmd
packetraven --tnc ~\Desktop\aprs_packets.txt
```
#### listen to a TNC on COM3, watching specific callsigns, and synchronize new packets with a database table via SSH tunnel:
```cmd
packetraven --tnc COM3 --callsigns W3EAX-8,W3EAX-14 --database <username>@<hostname>:5432/<database_name>/<table_name> --tunnel <ssh_username>@<hostname>:22
```

## Graphical User Interface
to start the GUI, add `--gui` to any `packetraven` command
```cmd
packetraven --gui
```
```cmd
packetraven --callsigns W3EAX-8,W3EAX-14 --apikey <api_key> --gui
```

## Usage:
```text
usage: packetraven [-h] [--callsigns CALLSIGNS] [--apikey APIKEY] [--tnc TNC] [--database DATABASE]
                   [--tunnel TUNNEL] [--igate] [--start START] [--end END] [--log LOG] [--output OUTPUT]
                   [--interval INTERVAL] [--gui]

optional arguments:
  -h, --help            show this help message and exit
  --callsigns CALLSIGNS
                        comma-separated list of callsigns to track
  --apikey APIKEY       APRS.fi API key (from https://aprs.fi/page/api)
  --tnc TNC             serial port or text file of TNC parsing APRS packets from analog audio to ASCII (set to
                        `auto` to use the first open serial port)
  --database DATABASE   PostGres database table `user@hostname:port/database/table`
  --tunnel TUNNEL       SSH tunnel `user@hostname:port`
  --igate               send new packets to APRS-IS
  --start START         start date / time, in any common date format
  --end END             end date / time, in any common date format
  --log LOG             path to log file to save log messages
  --output OUTPUT       path to output file to save packets
  --interval INTERVAL   seconds between each main loop (default: 5)
  --gui                 start the graphical interface
```

## Python API:
to retrieve packets directly from https://aprs.fi:
```python
from packetraven import APRSfi

callsigns = ['W3EAX-8', 'W3EAX-12', 'KC3FXX', 'KC3ZRB']
api_key = '<api_key>' # enter your APRS.fi API key here - you can get one from https://aprs.fi/page/api

aprs_fi = APRSfi(callsigns, api_key)
aprs_fi_packets = aprs_fi.packets

print(aprs_fi_packets)
```
or parse packets from a TNC sending parsed APRS over a USB connection:
```python
from packetraven import SerialTNC
 
serial_port = 'COM5' # set to `'auto'` to connect to the first open serial port  

tnc = SerialTNC(serial_port)
tnc_packets = tnc.packets

print(tnc_packets)
```
or connect to a PostGreSQL database running PostGIS:
```python
from packetraven import APRSDatabaseTable

callsigns = ['W3EAX-8', 'W3EAX-12', 'KC3FXX', 'KC3ZRB']

hostname = '<hostname>:5432'
database = '<database_name>'
table = 'packets'

username = '<username>'
password = '<password>'

# parameters for an SSH tunnel
ssh_hostname = None
ssh_username = None
ssh_password = None

table = APRSDatabaseTable(hostname, database, table, callsigns, 
                          username=username, password=password, 
                          ssh_hostname=ssh_hostname, ssh_username=ssh_hostname, ssh_password=ssh_password)
table_packets = table.packets

print(table_packets)
```
