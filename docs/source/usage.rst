Usage
=====

``packetraven`` command
-----------------------

When you install ``packetraven``, it adds an executable command (``packetraven``) to the command line:

.. program-output:: packetraven -h

The program can read a YAML configuration file in the following format:

.. code-block:: yaml

    callsigns:
        - W3EAX-9
        - W3EAX-11
        - W3EAX-12

    time:
        start: 2022-03-05
        end: 2022-03-06
        interval: 30

    output:
        filename: ns110.geojson

    log:
        filename: ns110.log

    packets:
        aprs_fi:
            api_key: 123456.abcdefhijklmnop
        text:
            locations:
                - /dev/ttyUSB0
                - ~/packets.txt
        database:
            hostname: localhost
            port: 5432
            database: nearspace
            table: ns110
            username: user1
            password: password1
            tunnel:
                hostname: bpp.umd.edu
                port: 22
                username: user1
                password: password2

    prediction:
        start:
            location:
                - -78.4987
                - 40.0157
            time: 2022-03-05 10:36:00
        profile:
            ascent_rate: 6.5
            burst_altitude: 25000
            sea_level_descent_rate: 9
        output:
            filename: ns110_prediction.geojson

For instance, to listen to a Kenwood TNC plugged into USB COM3, listen to APRS-IS via https://aprs.fi, and also filter to the callsigns "W3EAX-8" and "W3EAX-14", use the following configuration:

.. code-block:: yaml

    # config.yaml

    callsigns:
        - W3EAX-8
        - W3EAX-14

    packets:
        text:
            locations:
                - COM3
        aprs_fi:
            api_key: 123456.abcdefhijklmnop

.. code-block:: shell

    packetraven config.yaml

graphical user interface (GUI)
------------------------------

To start a windowed GUI, add ``--gui`` to any ``packetraven`` command:

.. code-block:: shell

    packetraven --gui
    packetraven config.yaml --gui
