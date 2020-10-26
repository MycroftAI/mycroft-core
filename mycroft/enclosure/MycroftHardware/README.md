Abstract base classes for all mycroft custom hardware

Currently we support leds, switches and volume.

Each file represents the minimum functionality a user
can expect of a mycroft class device. For example, a mycroft 
volume must at least support a volume get and volume set as
well as a 'get_capabilities()' method. 

Device capabilities is left to the user but is currently
used to report the class of device and other device specific
information. User defined parameters may be added as well.

