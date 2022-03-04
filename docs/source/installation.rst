Installation
============

To install ``packetraven``, you need `Python greater than or equal to version 3.7 <https://www.python.org/downloads>`_.

Once you have installed Python, and presumably have ``pip`` that comes with the default installation,
you can run the following command to install ``packetraven`` directly from PyPI:

.. code-block:: bash

    pip install packetraven

installing into a virtual environment
-------------------------------------

The above steps detail how to install ``packetraven`` to the system Python installation.
However, you might find the need to install to a virtual environment, such as an `Anaconda <https://conda.io/projects/conda/en/latest/user-guide/install/index.html#regular-installation>`_, ``virtualenv``.

To set up a ``virtualenv`` environment, do the following:

.. code-block:: bash

    pip install virtualenv
    mkdir ~/environments
    virtualenv ~/environments/packetraven
    source ~/environments/packetraven/bin/activate
    pip install packetraven

Then, you can execute from within this environment:

.. code-block:: bash

    source ~/environments/packetraven/bin/activate
    packetraven --gui
    deactivate
