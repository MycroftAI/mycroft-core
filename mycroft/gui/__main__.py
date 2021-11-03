from mycroft.configuration import setup_locale
from mycroft.gui.service import GUIService
from mycroft.util import wait_for_exit_signal, reset_sigint_handler
from mycroft.util.log import LOG


def on_ready():
    LOG.info("GUI websocket started!")


def on_stopping():
    LOG.info('GUI websocket is shutting down...')


def on_error(e='Unknown'):
    LOG.error('GUI websocket failed: {}'.format(repr(e)))


def main(ready_hook=on_ready, error_hook=on_error, stopping_hook=on_stopping):
    LOG.debug("GUI websocket created")
    try:
        reset_sigint_handler()
        setup_locale()
        service = GUIService()
        service.run()
        ready_hook()
        wait_for_exit_signal()
        service.stop()
        stopping_hook()
    except Exception as e:
        error_hook(e)


if __name__ == "__main__":
    main()
