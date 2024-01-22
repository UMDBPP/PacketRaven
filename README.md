# PacketRaven

[![tests](https://github.com/UMDBPP/PacketRaven/workflows/tests/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Atests)
[![docs](https://readthedocs.org/projects/packetraven/badge/?version=latest)](https://packetraven.readthedocs.io/en/latest/?badge=latest)
[![license](https://img.shields.io/github/license/umdbpp/packetraven)](https://opensource.org/licenses/MIT)

PacketRaven is a command-line dashboard that retrieves location telemetry sent by high-altitude balloon payloads.
The program is designed to be run during a flight and display information in a terminal user interface (TUI):
![demo](https://github.com/UMDBPP/PacketRaven/blob/main/docs/demo/demo.gif)

## Features

- retrieves location telemetry from a variety of sources, including
  - https://amateur.sondehub.org
  - https://aprs.fi
  - a TNC-equipped radio connected via USB
  - a text file containing raw APRS frames
  - a GeoJSON file with point geometries and telemetry
- retrieves balloon flight predictions from https://predict.sondehub.org
- plots variables such as altitude and ascent rate over time
- estimates landing time (and, if doing a prediction, shows preficted landing location) 

## Instructions

1. Follow [these instructions](https://packetraven.readthedocs.io/en/latest/configuration.html) to create a new configuration file in a text editor, or use the following simple example:
    ```yaml
    # example.yaml
    callsigns:
      - W3EAX-8
    connections:
      sondehub: {}
      text:
        - path: http://bpp.umd.edu/archives/Launches/NS-111_2022_07_31/APRS/W3EAX-8%20raw.txt
        - port: COM3
          baud_rate: 9600
    ```

2. Download an executable from the [Releases page](https://github.com/UMDBPP/PacketRaven/releases).

3. Open a terminal window.

4. Run the executable you downloaded with the `start` subcommand, and give it the path to your configuration file:
    ```shell
    packetraven.exe start example.yaml
    ```

> [!TIP]
> Add `--help` to any command to show usage instructions.

> [!NOTE]
> On MacOS or Linux, you may need to give the file executable permissions to run it:
> ```shell
> chmod +x packetraven
> ```

5. You should now see the user interface. The program starts on the `Log` tab, which displays log messages. Use the **up and down arrow keys** to scroll.
    ![log messages tab](https://github.com/UMDBPP/PacketRaven/blob/main/docs/images/example1_log.png)

> [!NOTE]
> Resize your terminal window, or zoom out / decrease the font size, as needed.

6. Upon receiving new packet(s) from a callsign, a new tab will be created (shown in the top bar) to display info for that callsign. Use the **left right arrow keys** to switch between tabs. 

7. When viewing info for a callsign, use the **up and down arrow keys** to switch between plots.
    ![altitude telemetry plotted over time](https://github.com/UMDBPP/PacketRaven/blob/main/docs/images/example1_altitude.png)

8. To quit, press `q` or `Esc`.

## retrieve predictions

Use `predict` to retrieve a balloon flight prediction:

```shell
packetraven.exe predict "2023-08-16T10:00:00" -- -79 39 5 30000 9
```

> [!WARNING]
> due to a limitation in the argument parser, you must prepend all negative values with `-- `; for instance, `-79` should be `-- -79`
