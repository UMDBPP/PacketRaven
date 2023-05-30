Configuration File
==================

The configuration file is in YAML format. Units are metric.


Configuration Entries
---------------------

``callsigns``
^^^^^^^^^^^^^

a list of callsigns as strings, including SSIDs if present

.. code-block:: yaml

   callsigns:
     - W3EAX-9
     - W3EAX-11
     - W3EAX-12

``time``
^^^^^^^^

.. code-block:: yaml

   time:
     start: 2022-03-05 00:00:00
     end: 2022-03-06 00:00:00
     interval: 120
   
``start`` and ``end``
"""""""""""""""""""""

start and end times by which to filter received telemetry

``interval``
""""""""""""

the interval that ``packetraven`` fetches new telemetry

``output_file``
^^^^^^^^^^^^^^^

GeoJSON file to output telemetry to

.. code-block:: yaml

   output_file: example_3.geojson

``connections``
^^^^^^^^^^^^^^^

connections from which to retrieve packets

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
   To define a connection with no options (i.e. the ``sondehub`` entry, above), use YAML's empty flow mapping syntax ``sondehub: {}``.
   The empty block mapping syntax (``sondehub: ``) is equivalent to ``sondehub: null`` and will not initiate the connection.

``text``
""""""""

text entries can be

1. a text file containing one raw APRS frame per line, optionally prepended by the datetime (separated by a colon)
2. a GeoJSON file of points with packet information in the ``properties``
3. a serial port, from which raw APRS frames can be retrieved as strings

.. code-block:: yaml

	text:
		- path: http://bpp.umd.edu/archives/Launches/NS-100_2022_04_09/APRS/NS-100%20normal%20aprs.txt
		  callsigns: ["W3EAX-8"]
		- path: ~/packets.geojson
		- port: /dev/ttyUSB0
		  callsigns: ["KC3SKW-8"]
		- port: COM3
		  baud_rate: 9600

.. note::
   File entries use the `path:` entry, while serial port entries use the `port:` and `baud_rate:` entries instead

``sondehub``
""""""""""""

.. code-block:: yaml

	sondehub:
		callsigns: ["KC3SKW-8"]

``aprs_fi``
"""""""""""

.. code-block:: yaml

	aprs_fi:
	    api_key: 123456.abcdefhijklmnop

``postgres``
""""""""""""

.. note::
   Requires the ``postgres`` crate feature

.. code-block:: yaml

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

``prediction``
^^^^^^^^^^^^^^

default prediction profile that will be applied to all callsigns

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
     float:
       duration: 3600
       float_altitude: 25000
       uncertainty: 500
     output_file: example_3_prediction.geojson

.. note::
   During a flight, the prediction profile for each track will differ from this default configuration; 
   for instance, on ascent the profile will use the actual ascent rate from telemetry, 
   and upon descent the prediction will only include the descent stage.

Example Configurations
----------------------

``examples/example_1.yaml``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

watch text file(s) for new lines containing raw APRS frames

.. literalinclude:: ../../examples/example_1.yaml
   :language: yaml

``examples/example_2.yaml``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

listen to a TNC-equipped radio connected to port ``COM3`` and poll https://amateur.sondehub.org and https://aprs.fi

.. literalinclude:: ../../examples/example_2.yaml
   :language: yaml

``examples/example_3.yaml``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. retrieve telemetry from the following connections once every 120 seconds
  - https://amateur.sondehub.org
  - a TNC-equipped radio connected to port ``/dev/ttyUSB0``
  - a text file
2. filter by specific callsigns and constrain to a specific time range
3. retrieve CUSF predictions following the given profile
4. output locations and data to GeoJSON

.. literalinclude:: ../../examples/example_3.yaml
   :language: yaml

