Configuration File
##################

The configuration file is in YAML format (``.yaml``). 
To run a configuration, see `the Usage section <https://packetraven.readthedocs.io/en/latest/index.html#usage>`_.

.. literalinclude:: ../../examples/example_3.yaml
   :language: yaml

Units are meters, seconds, and meters per second.

More examples can be found at the :doc:`examples` page.

.. _callsigns:

Callsigns (``callsigns``, optional)
===================================

a list of callsigns as strings, including SSIDs

.. code-block:: yaml

 callsigns:
   - KC3SKW-9
   - KC3ZRB

if present, only telemetry with callsigns in this list will be displayed

Time (``time``, optional)
=========================

.. code-block:: yaml

  time:
    start: 2022-03-05 00:00:00
    end: 2022-03-06 00:00:00
    interval: 120

``start`` and ``end`` (optional)
--------------------------------

start and end times by which to filter received telemetry, as either ``yyyy-mm-dd`` or ``yyyy-mm-dd HH:MM:SS``

``interval`` (default ``60``)
-----------------------------

frequency in seconds that PacketRaven will fetch new telemetry

Connections (``connections``)
=============================

connections from which to retrieve telemetry

.. code-block:: yaml

 connections:
   sondehub: {}
   aprs_fi: 
     api_key: 123456.abcdefhijklmnop
   text:
     - port: /dev/ttyUSB0
       baud_rate: 9600
     - path: ~/packets.txt

.. note::
   To define a connection without specifying options (or to use the default options), use empty curly braces: ``sondehub: {}``.
   An empty string, i.e. ``sondehub:``, will not start the connection (it's equivalent to ``sondehub: null`` ).

Text connection (``text``)
--------------------------

text entries can be

1. a text file containing one raw APRS frame per line, optionally prepended by the datetime (separated by a colon)
2. a GeoJSON file of points with packet information in the ``properties``
3. a serial port, from which raw APRS frames can be retrieved as strings

.. code-block:: yaml

  connections:
    text:
      - path: http://bpp.umd.edu/archives/Launches/NS-100_2022_04_09/APRS/NS-100%20normal%20aprs.txt
        callsigns:
          - W3EAX-8
      - path: ~/packets.geojson
      - port: /dev/ttyUSB0
        callsigns: 
          - KC3SKW-8
      - port: COM3
        baud_rate: 9600

File 
^^^^

``path``
""""""""

path to a file (can be a URL)

``callsigns`` (optional)
""""""""""""""""""""""""

see the :ref:`Callsigns <callsigns>` section

Serial
^^^^^^

``port``
""""""""

serial port to connect to, i.e. `COM4` or `/dev/ttyUSB1`

``baud_rate``
"""""""""""""

baud rate with which to connect to serial port

``callsigns`` (optional)
""""""""""""""""""""""""

see the :ref:`Callsigns <callsigns>` section

SondeHub connection (``sondehub``)
----------------------------------

if present, query the database at https://amateur.sondehub.org for telemetry from the given callsigns

``callsigns`` (optional if already defined globally)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

see the :ref:`Callsigns <callsigns>` section

APRSfi Connection (``aprs_fi``)
-------------------------------

if present, query the database at https://aprs.fi for telemetry from the given callsigns

``api_key``
^^^^^^^^^^^

get an API key from https://aprs.fi/page/api

``callsigns`` (optional if already defined globally)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

see the :ref:`Callsigns <callsigns>` section

PostGres Database connection (``postgres``, requires the ``postgres`` feature)
------------------------------------------------------------------------------

.. warning::
   requires compiling with the ``postgres`` feature:
   ..code-block:: shell

     cargo build --release --features postgres

.. code-block:: yaml

  connections:
    postgres:
      hostname: "database_hostname"
      port: 5432
      database: "nearspace"
      table: "packets"
      username: "user1"
      password: "password1"
      tunnel:
      hostname: "ssh_tunnel_hostname"
      port: 22
      username: "ssh_user1"
      password: "ssh_password1"

Flight Prediction (``prediction``, optional)
============================================

if present, queries https://predict.sondehub.org for a balloon flight prediction

.. code-block:: yaml

  prediction:
    start:
      coord:
        x: -78.4987
        y: 40.0157
      time: 2022-03-05 10:36:00
    profile:
      ascent_rate: 6.5
      burst_altitude: 25000
      sea_level_descent_rate: 9
    output_file: example_3_prediction.geojson

Launch / starting location and time (``start``)
-----------------------------------------------

.. code-block:: yaml

  prediction:
    start:
      coord:
        x: -78.4987
        y: 40.0157
      time: 2022-03-05 10:36:00

``coord``
^^^^^^^^^

``x`` and ``y`` in WGS84 coordinates

``altitude`` (optional)
^^^^^^^^^^^^^^^^^^^^^^^

altitude in meters

``time``
^^^^^^^^

time of prediction start, as ``yyyy-mm-dd`` or ``yyyy-mm-dd HH:MM:SS``

Standard Profile (``profile``)
------------------------------

.. code-block:: yaml

  prediction:
    profile:
      ascent_rate: 6.5
      burst_altitude: 25000
      sea_level_descent_rate: 9

.. note::
   During a flight, the prediction profile for each track will differ from this default configuration; 
   for instance, on ascent the profile will use the actual ascent rate from telemetry, 
   and during descent the prediction will only include the descent stage.

``ascent_rate``
^^^^^^^^^^^^^^^

expected average ascent rate of the balloon

``burst_altitude``
^^^^^^^^^^^^^^^^^^

expected burst altitude

``sea_level_descent_rate``
^^^^^^^^^^^^^^^^^^^^^^^^^^

expected descent rate of the balloon at sea level

Float Profile (``float``, optional)
-----------------------------------

.. code-block:: yaml

  prediction:
    float:
      duration: 3600
      altitude: 25000
      uncertainty: 500

``duration``
^^^^^^^^^^^^

expected duration of the float

``altitude``
^^^^^^^^^^^^

expected altitude of the float

``uncertainty`` (default ``500``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

leeway that the balloon can be considered "at float altitude"

Prediction Output File (``output_file``, optional)
--------------------------------------------------

path to a GeoJSON file to which to output a predicted flight path

.. code-block:: yaml

  prediction:
    output_file: example_3_prediction.geojson

Telemetry Output File (``output_file``, optional)
=================================================

path to a GeoJSON file to which to output received telemetry

.. code-block:: yaml

  output_file: example_3.geojson
