# `packetraven`

[![tests](https://github.com/UMDBPP/PacketRaven/workflows/tests/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Atests)
[![docs](https://readthedocs.org/projects/packetraven/badge/?version=latest)](https://packetraven.readthedocs.io/en/latest/?badge=latest)
[![license](https://img.shields.io/github/license/umdbpp/packetraven)](https://opensource.org/licenses/MIT)

track high-altitude balloon telemetry from a variety of sources

![demo](/docs/images/demo.gif)

## Installation

To run `packetraven`, download the latest executable for your system from the [Releases page](https://github.com/UMDBPP/PacketRaven/releases)

> **Note**
> Alternatively, you may build the executable yourself from the source code:
> ```shell
> git clone https://github.com/UMDBPP/PacketRaven.git
> cd packetraven
> cargo build --release
> ls target/release
> ```

## Usage

To run ``packetraven``, open a terminal window and type the path to the executable file. 
The program accepts a single argument, which is the path to the YAML configuration file.
For more information on creating configuration files, [read the documentation](https://packetraven.readthedocs.io).

For example, to run ``packetraven`` on ``examples/example_1.yaml``, run the following:
   
```shell
packetraven examples/example_1.yaml
```

![log message screen](/docs/images/example1_log.png)
![altitude telemetry plotted over time](/docs/images/example1_altitude.png)

Use the left and right arrow keys (or `Tab` and `Shift+Tab`) to switch between tabs. 
Similarly, use the up and down arrow keys to switch between plots.
To quit the program, press `q` or `Esc`.