"""This file will check a system level OpenVoiceOS specific config file

The ovos config is json with comment support like the regular mycroft.conf

Default locations tried by order until a file is found
- /etc/OpenVoiceOS/ovos.conf
- /etc/mycroft/ovos.conf

XDG locations are then merged over the select default config (if found)

Examples config:

{
   // check xdg directories OR only check old style hardcoded paths 
   "xdg": true,

   // the "name of the core",
   //         eg, OVOS, Neon, Chatterbox...
   //  all XDG paths should respect this
   //        {xdg_path}/{base_folder}/some_resource
   // "mycroft.conf" paths are derived from this
   //        ~/.{base_folder}/mycroft.conf
   "base_folder": "OpenVoiceOS",

   // the filename of "mycroft.conf",
   //      eg, ovos.conf, chatterbox.conf, neon.conf...
   // "mycroft.conf" paths are derived from this
   //        ~/.{base_folder}/{config_filename}
   "config_filename": "mycroft.conf",

   // override the default.conf location, allows changing the default values
   //     eg, disable backend, disable skills, configure permissions
   "default_config_path": "/etc/OpenVoiceOS/default_mycroft.conf",

   // this is intended for derivative products, if a module name is present
   // in sys.modules then the values below will be used instead
   //     eg, chatterbox/mycroft/ovos/neon can coexist in the same machine
   "module_overrides": {
        "chatterbox": {
            "xdg": false,
            "base_folder": "chatterbox",
            "config_filename": "chatterbox.conf",
            "default_config_path": "/opt/chatterbox/chatterbox.conf"
        },
        "neon_core": {
            "xdg": true,
            "base_folder": "neon",
            "config_filename": "neon.conf",
            "default_config_path": "/opt/neon/neon.conf"
        }
   },
   // essentially aliases for the above, useful for microservice architectures
   "submodule_mappings": {
        "chatterbox_stt": "chatterbox",
        "chatterbox_playback": "chatterbox",
        "chatterbox_admin": "chatterbox",
        "chatterbox_blockly": "chatterbox",
        "chatterbox_gpio_service": "chatterbox",
        "neon_speech": "neon_core",
        "neon_audio": "neon_core",
        "neon_enclosure": "neon_core"
   }
}
"""
from ovos_utils.configuration import get_ovos_config, is_using_xdg
