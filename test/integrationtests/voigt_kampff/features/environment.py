from threading import Event, Lock
from time import sleep, monotonic

from msm import MycroftSkillsManager
from mycroft.messagebus.client import MessageBusClient
from mycroft.messagebus import Message
from mycroft.util import create_daemon


def before_all(context):
    bus = MessageBusClient()
    bus_connected = Event()
    bus.once('open', bus_connected.set)

    context.speak_messages = []
    context.speak_lock = Lock()

    def on_speak(message):
        with context.speak_lock:
            context.speak_messages.append(message)

    bus.on('speak', on_speak)
    create_daemon(bus.run_forever)

    context.msm = MycroftSkillsManager()
    # Wait for connection
    print('Waiting for messagebus connection...')
    bus_connected.wait()

    print('Waiting for skills to be loaded...')
    start = monotonic()
    while True:
        response = bus.wait_for_response(Message('mycroft.skills.all_loaded'))
        if response and response.data['status']:
            break
        elif monotonic() - start >= 2 * 60:
            raise Exception('Timeout waiting for skills to become ready.')
        else:
            sleep(1)

    context.bus = bus
    context.matched_message = None


def after_all(context):
    context.bus.close()


def after_feature(context, feature):
    sleep(2)


def after_scenario(context, scenario):
    with context.speak_lock:
        context.speak_messages = []
    context.matched_message = None
