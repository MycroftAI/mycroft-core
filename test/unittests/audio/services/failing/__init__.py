from mycroft.audio.services import AudioBackend


class FailingBackend(AudioBackend):
    def __init__(self, config, emitter, name='Failing'):
        raise Exception

    def supported_uris(self):
        return ['file', 'http']


def load_service(base_config, emitter):
    instances = [FailingBackend(base_config, emitter)]
    return instances
