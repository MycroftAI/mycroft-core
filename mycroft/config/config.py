from abc import ABC
from pathlib import Path
from typing import List

import xdg
import yaml

MYCROFT_CONFIG_FILE_NAME = "mycroft_config.yaml"
SERVER_OVERRIDE = "server"
SYSTEM_OVERRIDE = "system"
USER_OVERRIDE = "user"


def _get_config_override(name, value, override):
    override_value = override.get(name)
    if type(override_value, dict):
        override_value.update(value)

    return override_value


class _LocationConfig:
    def __init__(self, location):
        city = location["city"]
        self.city_code = city["code"]
        self.city_name = city["name"]
        state = city["state"]
        self.state_code = state["code"]
        self.state_name = state["name"]
        country = state["country"]
        self.country_code = country["code"]
        self.country_name = country["name"]
        self.latitude = location["coordinate"]["latitude"]
        self.longitude = location["coordinate"]["longitude"]
        self.timezone_code = location["timezone"]["code"]
        self.timezone_name = location["timezone"]["name"]
        self.timezone_dst_offset = location["timezone"]["dstOffset"]
        self.timezone_offset = location["timezone"]["offset"]


class _ApiConfig:
    def __init__(self, server):
        self.url = server["url"]
        self.version = server["version"]
        self.update = server["update"]
        self.metrics = server["metrics"]
        self.sync_skill_settings = ["sync_skill_settings"]


class _ConfigFiles(ABC):
    _default = None
    _server = None
    _system = None
    _user = None

    def __init__(self, file_name):
        self.file_name = file_name

    @property
    def default(self):
        if self._default is None:
            self._default = self._load(Path(__file__).parent)

        return self._default

    @property
    def server(self):
        if self._server is None:
            self._system = self._load(
                Path(xdg.BaseDirectory.xdg_cache_home, "mycroft")
            )

        return self._server

    @property
    def system(self):
        if self._system is None:
            self._server = self._load(Path("/etc/mycroft"))

        return self._system

    @property
    def user(self):
        if self._user is None:
            self._user = self._load(
                Path(xdg.BaseDirectory.load_first_config("mycroft"))
            )

        return self._user

    def _load(self, config_directory: Path):
        config_file_path = config_directory.joinpath(self.file_name)
        if config_file_path.is_file():
            with open(config_file_path) as config_file:
                config = yaml.safe_load(config_file)
        else:
            config = {}

        return config

    def reset(self):
        self._default = None
        self._system = None
        self._user = None


class MycroftConfig(ABC):
    _default_mycroft_config = None
    _server_mycroft_config = None
    _user_mycroft_config = None
    _system_mycroft_config = None

    def __init__(self):
        self.mycroft_config_files = _ConfigFiles(MYCROFT_CONFIG_FILE_NAME)
        self.service_config_files = None

    @property
    def language(self) -> str:
        overrides = [SERVER_OVERRIDE]
        config_value = self._get_mycroft_config("lang", overrides)

        return config_value

    @property
    def imperial_measurement_unit(self) -> bool:
        overrides = [SERVER_OVERRIDE]
        config_value = self._get_mycroft_config("system_unit", overrides)

        return config_value == "english"

    @property
    def metric_measurement_unit(self) -> bool:
        overrides = [SERVER_OVERRIDE]
        config_value = self._get_mycroft_config("system_unit", overrides)

        return config_value == "metric"

    @property
    def time_format_12_hour(self) -> bool:
        overrides = [SERVER_OVERRIDE]
        config_value = self._get_mycroft_config("time_format", overrides)

        return config_value == "half"

    @property
    def time_format_24_hour(self) -> bool:
        overrides = [SERVER_OVERRIDE]
        config_value = self._get_mycroft_config("time_format", overrides)

        return config_value == "full"

    @property
    def date_format_mdy(self) -> bool:
        overrides = [SERVER_OVERRIDE]
        config_value = self._get_mycroft_config("date_format", overrides)

        return config_value == "MDY"

    @property
    def date_format_dmy(self) -> bool:
        overrides = [SERVER_OVERRIDE]
        config_value = self._get_mycroft_config("date_format", overrides)

        return config_value == "DMY"

    @property
    def open_dataset_opt_in(self):
        overrides = [SERVER_OVERRIDE]
        config_value = self._get_mycroft_config("opt_in", overrides)

        return config_value

    @property
    def confirm_listening(self):
        overrides = []
        config_value = self._get_mycroft_config("confirm_listening", overrides)

        return config_value

    @property
    def location(self):
        overrides = [SERVER_OVERRIDE]
        config_value = self._get_mycroft_config("location", overrides)

        return _LocationConfig(config_value)

    @property
    def data_directory(self):
        overrides = []
        config_value = self._get_mycroft_config("data_dir", overrides)

        return config_value

    @property
    def server_api(self):
        overrides = []
        config_value = self._get_mycroft_config("server", overrides)

        return config_value

    @property
    def log_level(self):
        overrides = [SYSTEM_OVERRIDE]
        config_value = self._get_mycroft_config("log_level", overrides)

        return config_value

    @property
    def log_format(self):
        overrides = [SYSTEM_OVERRIDE]
        config_value = self._get_mycroft_config("log_format", overrides)

        return config_value

    @property
    def platform(self):
        overrides = [SYSTEM_OVERRIDE]
        config_value = self._get_mycroft_config("platform", overrides)

        return config_value

    def _get_mycroft_config(self, config_name, allowed_overrides):
        config_value = self._get_config_value(
            config_name, allowed_overrides, self.mycroft_config_files
        )

        return config_value

    def _get_service_config(self, config_name, allowed_overrides):
        config_value = self._get_config_value(
            config_name, allowed_overrides, self.service_config_files
        )

        return config_value

    @staticmethod
    def _get_config_value(config_name, allowed_overrides, config_files):
        config_value = config_files.default[config_name]
        override_value = None
        if config_name in config_files.user:
            override_value = _get_config_override(
                config_name, config_value, config_files.user
            )
        else:
            if SYSTEM_OVERRIDE in allowed_overrides:
                override_value = _get_config_override(
                    config_name, config_value, config_files.system
                )
            if SERVER_OVERRIDE in allowed_overrides:
                override_value = _get_config_override(
                    config_name, config_value, config_files.server
                )

        return override_value or config_value


class _MsmConfig:
    def __init__(self, config):
        self.directory = config["directory"]
        self.versioned = config["versioned"]
        self.repo_cache = config["repo"]["cache"]
        self.repo_url = config["repo"]["url"]
        self.repo_branch = config["repo"]["branch"]


class _PadatiousConfig:
    def __init__(self, config):
        self.intent_cache = config["intent_cache"]
        self.train_delay = config["train_delay"]
        self.single_thread = config["single_thread"]


class SkillServiceConfig(MycroftConfig):
    def __init__(self):
        super().__init__()
        self.service_config_files = _ConfigFiles("skill_config.yaml")

    @property
    def msm(self) -> _MsmConfig:
        overrides = [SYSTEM_OVERRIDE]
        config_value = self._get_service_config("msm", overrides)

        return _MsmConfig(config_value)

    @property
    def upload_manifest(self) -> bool:
        overrides = [SYSTEM_OVERRIDE]
        config_value = self._get_service_config(
            "upload_skill_manifest", overrides
        )

        return config_value

    @property
    def directory(self) -> Path:
        overrides = [SYSTEM_OVERRIDE]
        config_value = self._get_service_config("directory", overrides)

        return Path(config_value).expanduser()

    @property
    def auto_update(self) -> bool:
        overrides = [SYSTEM_OVERRIDE]
        config_value = self._get_service_config("auto_update", overrides)

        return config_value

    @property
    def hot_reload(self) -> bool:
        overrides = [SYSTEM_OVERRIDE]
        config_value = self._get_service_config("hot_reload", overrides)

        return config_value

    @property
    def blacklisted_skills(self) -> List[str]:
        overrides = [SYSTEM_OVERRIDE]
        config_value = self._get_service_config(
            "blacklisted_skills", overrides
        )

        return config_value

    @property
    def idle_display_skill(self):
        overrides = [SYSTEM_OVERRIDE]
        config_value = self._get_service_config(
            "idle_display_skill", overrides
        )

        return config_value


class _WebsocketConfig:
    def __init__(self, config):
        self.host = config["host"]
        self.port = config["port"]
        self.route = config["route"]
        self.ssl = config["ssl"]


class MessageBusServiceConfig(MycroftConfig):
    def __init__(self):
        super().__init__()
        self.service_config_files = _ConfigFiles("message_bus_config.yaml")

    @property
    def websocket(self):
        overrides = [SYSTEM_OVERRIDE]
        config_value = self._get_service_config("websocket", overrides)

        return _WebsocketConfig(config_value)


class EnclosureServiceConfig(MycroftConfig):
    def __init__(self):
        super().__init__()
        self.service_config_files = _ConfigFiles("enclosure_config.yaml")

    @property
    def arduino_comm_port(self):
        overrides = [SYSTEM_OVERRIDE]
        config_value = self._get_service_config("port", overrides)

        return config_value

    @property
    def arduino_comm_rate(self):
        overrides = [SYSTEM_OVERRIDE]
        config_value = self._get_service_config("rate", overrides)

        return config_value

    @property
    def arduino_comm_timeout(self):
        overrides = [SYSTEM_OVERRIDE]
        config_value = self._get_service_config("timeout", overrides)

        return config_value

    @property
    def self_test_on_boot(self):
        overrides = [SYSTEM_OVERRIDE]
        config_value = self._get_service_config("test", overrides)

        return config_value

    @property
    def dbus_address(self):
        overrides = [SYSTEM_OVERRIDE]
        config_value = self._get_service_config("dbus", overrides)

        return config_value["bus_address"]

    @property
    def dim_display_seconds(self):
        overrides = [SYSTEM_OVERRIDE]
        config_value = self._get_service_config("idle_dim_timeout", overrides)

        return config_value


class ListenerConfig(MycroftConfig):
    def __init__(self):
        super().__init__()
        self.service_config_files = _ConfigFiles("listener_config.yaml")

    @property
    def sample_rate(self):
        overrides = []
        config_value = self._get_service_config("sample_rate", overrides)

        return config_value

    @property
    def save_wake_words(self):
        overrides = []
        config_value = self._get_service_config("record_wake_words", overrides)

        return config_value

    @property
    def save_utterances(self):
        overrides = []
        config_value = self._get_service_config("save_utterances", overrides)

        return config_value

    @property
    def disable_wake_word_upload(self):
        overrides = []
        config_value = self._get_service_config("wake_word_upload", overrides)

        return config_value["disable"]

    @property
    def wake_word_upload_url(self):
        overrides = []
        config_value = self._get_service_config("wake_word_upload", overrides)

        return config_value["url"]

    @property
    def mute_microphone_during_output(self):
        overrides = []
        config_value = self._get_service_config(
            "mute_during_output", overrides
        )

        return config_value

    @property
    def percent_volume_while_listening(self):
        overrides = []
        config_value = self._get_service_config(
            "duck_while_listening", overrides
        )

        return config_value

    @property
    def phoneme_duration(self):
        overrides = []
        config_value = self._get_service_config("phoneme_duration", overrides)

        return config_value

    @property
    def multiplier(self):
        overrides = []
        config_value = self._get_service_config("multiplier", overrides)

        return config_value

    @property
    def energy_ratio(self):
        overrides = []
        config_value = self._get_service_config("energy_ratio", overrides)

        return config_value

    @property
    def wake_word(self):
        overrides = []
        config_value = self._get_service_config("wake_word", overrides)

        return config_value

    @property
    def wake_from_sleep_word(self):
        overrides = []
        config_value = self._get_service_config("stand_up_word", overrides)

        return config_value

    @property
    def utterance_recording_timeout(self):
        overrides = []
        config_value = self._get_service_config("recording_timeout", overrides)

        return config_value

    @property
    def silence_timeout(self):
        overrides = []
        config_value = self._get_service_config(
            "recording_timeout_with_silence", overrides
        )

        return config_value

    @property
    def use_precise(self):
        overrides = []
        config_value = self._get_service_config("precise", overrides)

        return config_value["use_precise"]

    @property
    def precise_distribution_url(self):
        overrides = []
        config_value = self._get_service_config("precise", overrides)

        return config_value["dist_url"]

    @property
    def precise_model_url(self):
        overrides = []
        config_value = self._get_service_config("precise", overrides)

        return config_value["model_url"]
