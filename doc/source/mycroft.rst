mycroft package
===============

mycroft.skills
==============

MycroftSkill class - Base class for all Mycroft skills
------------------

.. autoclass:: mycroft.MycroftSkill
    :members:

CommonIoTSkill class
-------------------
.. autoclass:: mycroft.skills.common_iot_skill.CommonIoTSkill
    :show-inheritance:
    :members:

CommonPlaySkill class
-------------------
.. autoclass:: mycroft.skills.common_play_skill.CommonPlaySkill
    :show-inheritance:
    :members:

CommonQuerySkill class
-------------------
.. autoclass:: mycroft.skills.common_query_skill.CommonQuerySkill
    :show-inheritance:
    :members:

FallbackSkill class
-------------------
.. autoclass:: mycroft.FallbackSkill
    :show-inheritance:
    :members:

AudioService class
-------------------
.. autoclass:: mycroft.skills.audioservice.AudioService
    :show-inheritance:
    :members:

intent_handler decorator
------------------------
.. autofunction:: mycroft.intent_handler

intent_file_handler decorator
-----------------------------
.. autofunction:: mycroft.intent_file_handler

adds_context decorator
----------------------
.. autofunction:: mycroft.adds_context

removes_context decorator
-------------------------
.. autofunction:: mycroft.removes_context


mycroft.util
===============

.. toctree::
    mycroft.util

.. toctree::
    mycroft.util.log

.. toctree::
    mycroft.util.parse
Parsing functions for extracting data from natural speech.

.. toctree::
    mycroft.util.format
Formatting functions for producing natural speech from common datatypes such as numbers, dates and times.

.. toctree::
    mycroft.util.time
A collection of functions for handling local, system and global times.

-----------------
.. automodule::
    mycroft.util.time
