mycroft package
===============

.. toctree::
    mycroft.util

.. toctree::
    mycroft.util.parse

mycroft.util.time - time handling functions
-----------------
.. automodule::
    mycroft.util.time
    :members:

Api class
---------
.. autoclass:: mycroft.Api
    :members:


mycroft.skills
==============

MycroftSkill class - base class for all Mycroft skills
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

