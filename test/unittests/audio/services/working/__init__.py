from mycroft.audio.services import AudioBackend


class WorkingBackend(AudioBackend):
    def __init__(self, config, emitter, name='Working'):
        pass

    def supported_uris(self):
        return ['file', 'http']

    def add_list(self, tracks):
        pass

    def clear_list(self):
        pass

    def play(self):
        pass

    def stop(self):
        pass


def load_service(base_config, emitter):
    instances = [WorkingBackend(base_config, emitter)]
    return instances
