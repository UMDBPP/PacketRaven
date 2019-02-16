# Huginn
### Balloon payload telemetry over APRS 

A new version of Link-TLM, written in Python 3.7.

##### Installation

1. `pip install pipenv` 
2. `git clone https://github.com/UMDBPP/huginn.git`
3. `cd huginn`
4. `pipenv install`
 
##### Usage

1. `cd huginn`
2. `pipenv run huginn.py`

##### Features

###### Current

- APRS packet parsing over serial
- log to file

###### In-Progress

- altitude plot with `matplotlib`
- flight track plot with `cartopy`

###### Future

- live track prediction
- Iridium telemetry and commands
- live chase navigation
