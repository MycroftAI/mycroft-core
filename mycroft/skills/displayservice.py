import time
from mycroft.messagebus.message import Message


class DisplayService():
    """
        DisplayService object for interacting with the display subsystem

        Args:
            emitter: eventemitter or websocket object
    """
    def __init__(self, emitter):
        self.emitter = emitter
        self.emitter.on('mycroft.display.service.pic_info_reply',
                        self._pic_info)
        self.info = None

    def _pic_info(self, message=None):
        """
            Handler for catching returning pic info
        """
        self.info = message.data

    def display(self, file_path_list=None, reset=True, utterance=''):
        """ Start display.

            Args:
                file_path_list: list of paths
                utterance: forward utterance for further processing by the
                           audio service.
        """
        if file_path_list is None:
            file_path_list = []

        if not isinstance(file_path_list, list):
            raise ValueError

        self.emitter.emit(Message('mycroft.display.service.display',
                                  data={'file_list': file_path_list,
                                        'utterance': utterance,
                                        'reset': reset}))

    def add_pictures(self, file_path_list, utterance = ""):
        """ Start display.

            Args:
                file_path: track or list of paths
                utterance: forward utterance for further processing by the
                           audio service.
        """
        if not isinstance(file_path_list, list):
            raise ValueError

        self.emitter.emit(Message('mycroft.display.service.add_pictures',
                                  data={'file_list': file_path_list,
                                        'utterance': utterance}))

    def next(self, utterance = ""):
        """ Change to next pic. """
        self.emitter.emit(Message('mycroft.display.service.next',
                                  data={'utterance': utterance}))

    def close(self, utterance = ""):
        """ Change to next pic. """
        self.emitter.emit(Message('mycroft.display.service.close',
                                  data={'utterance': utterance}))

    def prev(self, utterance = ""):
        """ Change to previous pic. """
        self.emitter.emit(Message('mycroft.display.service.prev',
                                  data={'utterance': utterance}))

    def clear(self, utterance = ""):
        """ Clear Display """
        self.emitter.emit(Message('mycroft.display.service.clear',
                                  data={'utterance': utterance}))

    def set_fullscreen(self, active, utterance=""):
        self.emitter.emit(Message('mycroft.display.service.fullscreen',
                                  data={'utterance': utterance,
                                        "active": active}))

    def set_height(self, height=500, utterance=""):
        """ Reset Display. """
        self.emitter.emit(Message('mycroft.display.service.height',
                                  data={'utterance': utterance,
                                        "width": height}))

    def set_width(self, width=500, utterance = ""):
        """ Reset Display. """
        self.emitter.emit(Message('mycroft.display.service.width',
                                  data={'utterance': utterance, "width":width}))

    def reset(self, utterance = ""):
        """ Reset Display. """
        self.emitter.emit(Message('mycroft.display.service.reset',
                                  data={'utterance': utterance}))

    def pic_info(self, utterance = ""):
        """ Request information of current displaying pic.

            Returns:
                Dict with pic info.
        """
        self.info = None
        self.emitter.emit(Message('mycroft.display.service.pic_info',
                                  data={'utterance': utterance}))
        wait = 5.0
        while self.info is None and wait >= 0:
            time.sleep(0.1)
            wait -= 0.1
        return self.info or {}

    @property
    def is_displaying(self):
        return self.pic_info() != {}
