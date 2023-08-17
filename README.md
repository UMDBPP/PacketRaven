# PacketRaven

[![tests](https://github.com/UMDBPP/PacketRaven/workflows/tests/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Atests)
[![docs](https://readthedocs.org/projects/packetraven/badge/?version=latest)](https://packetraven.readthedocs.io/en/latest/?badge=latest)
[![license](https://img.shields.io/github/license/umdbpp/packetraven)](https://opensource.org/licenses/MIT)

PacketRaven is a command-line dashboard that retrieves location telemetry sent by high-altitude balloon payloads.
The program is designed to be run during a flight and display information in a terminal user interface (TUI):
![demo](https://github.com/UMDBPP/PacketRaven/blob/main/docs/images/demo.gif)

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

## Installation

[Download an executable (`packetraven_Windows.exe`, `packetraven_macOS`, or `packetraven_Linux`) from the latest release.](https://github.com/UMDBPP/PacketRaven/releases)

> **Note**\
> Alternatively, you may compile the program yourself:
> ```shell
> git clone https://github.com/UMDBPP/PacketRaven.git
> cd packetraven
> cargo build --release
> ls target/release/packetraven*
> ```

## Usage

### `run`

Run your executable from the terminal with the `run` subcommand and the path to your configuration file:
```shell
./packetraven_Windows.exe run examples/example_1.yaml
```

[Instructions for creating a configuration file can be found in the documentation](https://packetraven.readthedocs.io/en/latest/configuration.html).
Example configurations can be found in the `examples/` folder:

```yaml
connections:
  text:
    - path: ~/raw_aprs_frames.txt
      callsigns: 
        - W3EAX-8
    - path: http://bpp.umd.edu/archives/Launches/NS-111_2022_07_31/APRS/W3EAX-8%20raw.txt
```

You should then see the user interface. Resize your terminal window, or decrease the font size, as needed.
![starting screen](https://github.com/UMDBPP/PacketRaven/blob/main/docs/images/example1_log.png)

The left and right arrow keys (or `Tab` and `Shift+Tab`) cycle through active tabs, 
and the up and down arrow keys change the current plot (or scroll through log messages).
![altitude telemetry plotted over time](https://github.com/UMDBPP/PacketRaven/blob/main/docs/images/example1_altitude.png)

To quit, press `q` or `Esc`.

### `predict`

You can run the `predict` subcommand to retrieve a balloon flight prediction from a Tawhiri API:

```shell
./packetraven_Windows.exe predict "2023-08-16T10:00:00" -- -79 39 5 30000 9
```

> **Note**\
> Negative values must be prepended with `-- `, e.g. `-- -79`.:w
