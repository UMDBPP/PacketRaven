# PacketRaven

[![tests](https://github.com/UMDBPP/PacketRaven/workflows/tests/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Atests)
[![codecov](https://codecov.io/gh/umdbpp/packetraven/branch/master/graph/badge.svg?token=SF5215DHUW)](https://codecov.io/gh/umdbpp/packetraven)
[![build](https://github.com/UMDBPP/PacketRaven/workflows/build/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Abuild)
[![version](https://img.shields.io/pypi/v/packetraven)](https://pypi.org/project/packetraven)
[![license](https://img.shields.io/github/license/umdbpp/packetraven)](https://opensource.org/licenses/MIT)
[![style](https://sourceforge.net/p/oitnb/code/ci/default/tree/_doc/_static/oitnb.svg?format=raw)](https://sourceforge.net/p/oitnb/code)

PacketRaven is a dashboard built to track high-altitude balloon flights from their location telemetry.

```bash
pip install packetraven
```

## Examples:

#### listen to a TNC sending raw APRS strings over USB port COM4:

```bash
packetraven --tnc COM4
```

### listen to APRS.fi, watching specific callsigns:

you need an API key to connect to APRS.fi; you can get one from https://aprs.fi/page/api

```bash
packetraven --apikey <api_key> --callsigns W3EAX-8,W3EAX-14
```

#### listen to a PostGIS database table:

```bash
packetraven --database <username>@<hostname>:5432/<database_name>/<table_name>
```

#### watch a text file for new lines containing raw APRS strings:

```bash
packetraven --tnc http://bpp.umd.edu/archives/Launches/NS-95_2020-11-07/APRS/W3EAX-11/W3EAX-11_raw_NS95.txt
```

#### listen to a TNC on COM3, watching specific callsigns, and synchronize new packets with a database table via SSH tunnel:

```bash
packetraven --tnc COM3 --callsigns W3EAX-8,W3EAX-14 --database <username>@<hostname>:5432/<database_name>/<table_name> --tunnel <ssh_username>@<hostname>:22
```

## Graphical User Interface

to start the GUI, add `--gui` to any `packetraven` command

```bash
packetraven --gui
```

```bash
packetraven --callsigns W3EAX-8,W3EAX-14 --apikey <api_key> --gui
```

## Usage:

```text
usage: packetraven [-h] [--callsigns CALLSIGNS] [--aprsfi-key APRSFI_KEY] [--tnc TNC] [--database DATABASE] [--tunnel TUNNEL] [--igate]
                   [--start START] [--end END] [--log LOG] [--output OUTPUT] [--prediction-output PREDICTION_OUTPUT]
                   [--prediction-ascent-rate PREDICTION_ASCENT_RATE] [--prediction-burst-altitude PREDICTION_BURST_ALTITUDE]
                   [--prediction-descent-rate PREDICTION_DESCENT_RATE] [--prediction-float-altitude PREDICTION_FLOAT_ALTITUDE]
                   [--prediction-float-end-time PREDICTION_FLOAT_END_TIME] [--prediction-api PREDICTION_API] [--interval INTERVAL] [--gui]

optional arguments:
  -h, --help            show this help message and exit
  --callsigns CALLSIGNS
                        comma-separated list of callsigns to track
  --aprsfi-key APRSFI_KEY
                        APRS.fi API key (from https://aprs.fi/page/api)
  --tnc TNC             comma-separated list of serial ports / text files of a TNC parsing APRS packets from analog audio to ASCII (set to
                        `auto` to use the first open serial port)
  --database DATABASE   PostGres database table `user@hostname:port/database/table`
  --tunnel TUNNEL       SSH tunnel `user@hostname:port`
  --igate               send new packets to APRS-IS
  --start START         start date / time, in any common date format
  --end END             end date / time, in any common date format
  --log LOG             path to log file to save log messages
  --output OUTPUT       path to output file to save packets
  --prediction-output PREDICTION_OUTPUT
                        path to output file to save most up-to-date predicted trajectory
  --prediction-ascent-rate PREDICTION_ASCENT_RATE
                        ascent rate to use for prediction (m/s)
  --prediction-burst-altitude PREDICTION_BURST_ALTITUDE
                        burst altitude to use for prediction (m)
  --prediction-descent-rate PREDICTION_DESCENT_RATE
                        descent rate to use for prediction (m/s)
  --prediction-float-altitude PREDICTION_FLOAT_ALTITUDE
                        float altitude to use for prediction (m)
  --prediction-float-end-time PREDICTION_FLOAT_END_TIME
                        float end time to use for prediction
  --prediction-api PREDICTION_API
                        API URL to use for prediction (one of ['https://predict.cusf.co.uk/api/v1/',
                        'https://predict.lukerenegar.com/api/v1.1/'])
  --interval INTERVAL   seconds between each main loop (default: 20)
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
