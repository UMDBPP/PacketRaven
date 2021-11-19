Usage
=====

``packetraven`` command
-----------------------

When you install ``packetraven``, it adds an executable command (``packetraven``) to the command line.

For instance, to listen to a Kenwood TNC plugged into USB COM3, listen to the APRS-IS via https://aprs.fi, and also filter to the callsigns "W3EAX-8" and "W3EAX-14", you can run the following command:

.. code-block:: shell

    packetraven --tnc COM3 --callsigns W3EAX-8,W3EAX-14 --aprsfi-key <api_key>

The ``packetraven`` command takes the following arguments:

.. program-output:: packetraven -h

graphical user interface (GUI)
------------------------------

To start a windowed GUI, add ``--gui`` to any ``packetraven`` command:

.. code-block:: shell

    packetraven --gui
