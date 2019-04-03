# Huginn
### Balloon payload telemetry over APRS

Huginn is a new version of Link-TLM written in Python 3.7

##### Install

1. `git clone https://github.com/UMDBPP/huginn.git`
2. `./huginn/dist/huginn/huginn.exe`

##### Build

1. [Install Anaconda](https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe)
2. Open Anaconda Prompt
3. `conda create huginn python=3.7 cartopy`
4. `conda activate huginn`
5. `pip install haversine aprslib pyserial`

##### Features

###### Current

- APRS packet parsing over serial
- log to file
- altitude plot
- flight track plot

###### Future

- live track prediction
- Iridium telemetry and commands
- live chase navigation
