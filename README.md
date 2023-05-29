# `packetraven`

[![tests](https://github.com/UMDBPP/PacketRaven/workflows/tests/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Atests)
[![docs](https://readthedocs.org/projects/packetraven/badge/?version=latest)](https://packetraven.readthedocs.io/en/latest/?badge=latest)
[![license](https://img.shields.io/github/license/umdbpp/packetraven)](https://opensource.org/licenses/MIT)

track high-altitude balloon telemetry with a TNC-equipped radio connected via USB, or from https://amateur.sondehub.org or https://aprs.fi

## Installation

download the latest compiled executable from the [Releases page](https://github.com/UMDBPP/PacketRaven/releases)

> **Note**
> Alternatively, you can download the source code and compile the program yourself:
> ```shell
> git clone https://github.com/UMDBPP/PacketRaven.git
> cd packetraven
> cargo build --release
> ls target/release
> ```

## Usage

To run ``packetraven``, open a terminal window and type the path to the executable file. 
The program accepts a single argument; the configuration filename.
For more information on creating configuration files, [read the documentation](https://packetraven.readthedocs.io).

For example, to run ``packetraven`` on ``examples/example_1.yaml``, run the following:
   
```shell
packetraven examples/example_1.yaml
```

![log messages tab](docs/source/images/example1_log.png)

Use the left and right arrow keys (or `Tab` and `Shift+Tab`) to switch between tabs:
![track tab w/ plot of altitude over time](docs/source/images/example1_altitude.png)

Use the up and down arrow keys to switch between plots:
![track tab w/ plot of ascent rate over time](docs/source/images/example1_ascent_rates.png)
![track tab w/ plot of ground speed over altitude](docs/source/images/example1_ground_speeds.png)
![track tab w/ plot of unprojected coordinates](docs/source/images/example1_coordinates.png)

To quit the program, press `q` or `Esc`.