from mycroft.screen_display.services import DisplayBackend
from mycroft.util.log import getLogger
from mycroft.messagebus.message import Message

from os.path import abspath

import webbrowser

__author__ = 'jarbas'

logger = getLogger(abspath(__file__).split('/')[-2])


class WebBrowserService(DisplayBackend):
    """
        Display backend for webbrowser package. This one is rather limited and
        only implements basic usage.
    """
    def __init__(self, config, emitter, name='WebBrowser'):
        self.config = config
        self.emitter = emitter
        self.name = name
        self._is_Displaying = False
        self.pictures = []
        self.index = 0
        self.emitter.on('mycroft.display.service.WebBrowser', self._display)

    def _display(self, message=None):
        """
        Open file with webbrowser module, this will either use browser or
        default system executable for pictures
        """
        logger.info(self.name + '_display')
        if len(self.pictures) == 0:
            logger.error("No picture to display")
            return
        path = self.pictures[self.index]
        self._is_Displaying = True
        webbrowser.open(path)

    def display(self):
        logger.info('Call WebBrowserDisplay')
        self.emitter.emit(Message('mycroft.display.service.WebBrowser'))

    def add_pictures(self, picture_list):
        for picture in picture_list:
            self.pictures.insert(0, picture)

    def next(self):
        """
            Skip to next pic in playlist.
        """
        logger.info('Call WebBrowserNext')
        self.index += 1
        if self.index > len(self.pictures):
            self.index = 0
        self._display()

    def previous(self):
        """
            Skip to previous pic in playlist.
        """
        logger.info('Call WebBrowserPrevious')
        self.index -= 1
        if self.index < 0:
            self.index = len(self.pictures)
        self._display()

    def reset(self):
        """
            Reset Display.Clear Picture List, Clear Screen
        """
        logger.info('Call WebBrowserReset')
        self.index = 0
        self.pictures = []

    def clear(self):
        """
            Clear Display. Not implemented in webbrowser module
        """
        self._is_Displaying = False

    def stop(self):
        logger.info('WebBrowserDisplayStop')
        self.reset()
        self.clear()


def load_service(base_config, emitter):
    backends = base_config.get('backends', [])
    services = [(b, backends[b]) for b in backends
                if backends[b]['type'] == 'webbrowser']
    instances = [WebBrowserService(s[1], emitter, s[0]) for s in services]
    return instances
