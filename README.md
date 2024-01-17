# PacketRaven

[![tests](https://github.com/UMDBPP/PacketRaven/workflows/tests/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Atests)
[![docs](https://readthedocs.org/projects/packetraven/badge/?version=latest)](https://packetraven.readthedocs.io/en/latest/?badge=latest)
[![license](https://img.shields.io/github/license/umdbpp/packetraven)](https://opensource.org/licenses/MIT)

PacketRaven is a command-line dashboard that retrieves location telemetry sent by high-altitude balloon payloads.
The program is designed to be run during a flight and display information in a terminal user interface (TUI):
![demo](https://github.com/UMDBPP/PacketRaven/blob/main/docs/demo/demo.gif)

## Features

- retrieve location telemetry from a variety of sources, including
  - https://amateur.sondehub.org
  - https://aprs.fi
  - a TNC-equipped radio connected via USB
  - a text file containing raw APRS frames
  - a GeoJSON file with point geometries and telemetry
- retrieve balloon flight predictions from https://predict.sondehub.org
- plot variables such as altitude and ascent rate over time
- estimate landing time and location

## Instructions

1. Follow [these instructions](https://packetraven.readthedocs.io/en/latest/configuration.html) to create a new configuration file in a text editor, or use the following example:
   ```yaml
   # example.yaml
   connections:
     text:
       - path: ~/raw_aprs_frames.txt
         callsigns: 
           - W3EAX-8
       - path: http://bpp.umd.edu/archives/Launches/NS-111_2022_07_31/APRS/W3EAX-8%20raw.txt
   ```

2. Download an executable from the [Releases page](https://github.com/UMDBPP/PacketRaven/releases).

3. Open a terminal window.

4. Run the executable you downloaded with the `start` subcommand, and give it the path to your configuration file:
   ```shell
   packetraven_Windows.exe start example.yaml
   ```

> [!TIP]
> Add `--help` to any command to show usage instructions.

5. You should now see the user interface. Resize your terminal window or decrease the font size as needed.
   ![starting screen](https://github.com/UMDBPP/PacketRaven/blob/main/docs/images/example1_log.png)

6. The left and right arrow keys (or `Tab` and `Shift+Tab`) cycle through active tabs, and the up and down arrow keys change the current plot (or scroll through log messages).
   ![altitude telemetry plotted over time](https://github.com/UMDBPP/PacketRaven/blob/main/docs/images/example1_altitude.png)

7. To quit, press `q` or `Esc`.

## retrieve predictions

Use `predict` to retrieve a balloon flight prediction:

```shell
packetraven_Windows.exe predict "2023-08-16T10:00:00" -- -79 39 5 30000 9
```

> [!WARNING]
> due to a limitation in the argument parser, you must prepend all negative values with `-- `; for instance, `-79` should be `-- -79`
