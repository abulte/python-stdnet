.. _contrib-index:

.. module:: stdnet.apps

================================
Applications
================================

The :mod:`stdnet.apps` module contains applications
which are based on :mod:`stdnet` but are not part of the
core library.
They don't have external dependencies but some of the requires
a :ref:`non vanilla redis <stdnetredis>` implementation and are here
mainly as use cases. In the future they may be removed
and placed into their own installable packages. 

.. toctree::
   :maxdepth: 2
   
   searchengine
   timeseries
   grid