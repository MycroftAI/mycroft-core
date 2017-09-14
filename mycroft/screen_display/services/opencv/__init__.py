from mycroft.screen_display.services import DisplayBackend
from mycroft.util.log import getLogger
from mycroft.messagebus.message import Message

from os.path import abspath

import imutils
import cv2
import numpy as np


__author__ = 'jarbas'

logger = getLogger(abspath(__file__).split('/')[-2])


class OpenCVService(DisplayBackend):
    """
        Display backend for opencv package.
    """
    def __init__(self, config, emitter, name='OpenCV'):
        self.config = config
        self.emitter = emitter
        self.name = name
        self._is_Displaying = False
        self.pictures = []
        self.index = 0
        self.emitter.on('mycroft.display.service.OpenCV', self._display)
        # image size
        self.width = 500
        self.height = 500
        self.fullscreen = False

    def _display(self, message=None):
        """
        Open file with opencv
        """
        cv2.destroyWindow("OpenCV Display")
        logger.info(self.name + '_display')
        if len(self.pictures) == 0:
            logger.error("No picture to display")
            self.clear()
            return
        path = self.pictures[self.index]
        self._is_Displaying = True
        image = cv2.imread(path)
        if not self.fullscreen:
            image = imutils.resize(image, self.width, self.height)
        cv2.imshow("OpenCV Display", image)
        cv2.waitKey(0)

    def change_width(self, value=500):
        self.width = int(value)

    def change_height(self, value=500):
        self.height = int(value)

    def change_fullscreen(self, value=True):
        return
        self.fullscreen = value
        # TODO fix this, not working, breaks windows after
        cv2.destroyWindow("OpenCV Display")
        if value:
            cv2.namedWindow("OpenCV Display", cv2.WND_PROP_FULLSCREEN)
            cv2.setWindowProperty("OpenCV Display", cv2.WND_PROP_FULLSCREEN,
                                  cv2.WINDOW_FULLSCREEN)
        else:
            cv2.namedWindow("OpenCV Display")
        self.display()

    def add_pictures(self, picture_list):
        logger.info("Adding pictures to OpenCVDisplay")
        self.pictures.extend(picture_list)

    def display(self):
        logger.info('Call OpenCVDisplay')
        self.emitter.emit(Message('mycroft.display.service.OpenCV'))

    def next(self):
        """
            Skip to next pic in playlist.
        """
        logger.info('Call OpenCVNext')
        self.index += 1
        if self.index > len(self.pictures):
            self.index = 0
        self._display()

    def previous(self):
        """
            Skip to previous pic in playlist.
        """
        logger.info('Call OpenCVPrevious')
        self.index -= 1
        if self.index > 0:
            self.index = len(self.pictures)
        self._display()

    def reset(self):
        """
            Reset Display.Clear Picture List, Clear Screen
        """
        logger.info('Call OpenCVReset')
        self.index = 0
        self.fullscreen = False
        self.pictures = []

    def clear(self):
        """
            Clear Display.
        """
        # Create a black image
        image = np.zeros((512, 512, 3), np.uint8)
        if not self.fullscreen:
            image = imutils.resize(image, self.width, self.height)
        cv2.imshow("OpenCV Display", image)
        self._is_Displaying = False
        cv2.waitKey(0)

    def close(self):
        logger.info('OpenCVDisplayStop')
        self.reset()
        self._is_Displaying = False
        cv2.destroyWindow("OpenCV Display")
        cv2.destroyAllWindows()


def load_service(base_config, emitter):
    backends = base_config.get('backends', [])
    services = [(b, backends[b]) for b in backends
                if backends[b]['type'] == 'opencv']
    instances = [OpenCVService(s[1], emitter, s[0]) for s in services]
    return instances
