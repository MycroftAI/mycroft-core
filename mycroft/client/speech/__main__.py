# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from threading import Lock

from mycroft import dialog
from mycroft.enclosure.api import EnclosureAPI
from mycroft.client.speech.listener import RecognizerLoop
from mycroft.configuration import Configuration
from mycroft.identity import IdentityManager
from mycroft.lock import Lock as PIDLock  # Create/Support PID locking file
from mycroft.messagebus.message import Message
from mycroft.util import (
    create_daemon,
    reset_sigint_handler,
    start_message_bus_client,
    wait_for_exit_signal
)
from mycroft.util.log import LOG
from mycroft.util.process_utils import ProcessStatus, StatusCallbackMap

bus = None  # Mycroft messagebus connection
lock = Lock()
loop = None
config = None


def handle_record_begin():
    """Forward internal bus message to external bus."""
    LOG.info("Begin Recording...")
    context = {'client_name': 'mycroft_listener',
               'source': 'audio'}
    bus.emit(Message('recognizer_loop:record_begin', context=context))


def handle_record_end():
    """Forward internal bus message to external bus."""
    LOG.info("End Recording...")
    context = {'client_name': 'mycroft_listener',
               'source': 'audio'}
    bus.emit(Message('recognizer_loop:record_end', context=context))


def handle_no_internet():
    LOG.debug("Notifying enclosure of no internet connection")
    context = {'client_name': 'mycroft_listener',
               'source': 'audio'}
    bus.emit(Message('enclosure.notify.no_internet', context=context))


def handle_awoken():
    """Forward mycroft.awoken to the messagebus."""
    LOG.info("Listener is now Awake: ")
    context = {'client_name': 'mycroft_listener',
               'source': 'audio'}
    bus.emit(Message('mycroft.awoken', context=context))


def handle_wakeword(event):
    LOG.info("Wakeword Detected: " + event['utterance'])
    bus.emit(Message('recognizer_loop:wakeword', event))


def handle_utterance(event):
    LOG.info("Utterance: " + str(event['utterances']))
    context = {'client_name': 'mycroft_listener',
               'source': 'audio',
               'destination': ["skills"]}
    if 'ident' in event:
        ident = event.pop('ident')
        context['ident'] = ident
    bus.emit(Message('recognizer_loop:utterance', event, context))


def handle_unknown():
    context = {'client_name': 'mycroft_listener',
               'source': 'audio'}
    bus.emit(Message('mycroft.speech.recognition.unknown', context=context))


def handle_speak(event):
    """
        Forward speak message to message bus.
    """
    context = {'client_name': 'mycroft_listener',
               'source': 'audio'}
    bus.emit(Message('speak', event, context))


def handle_complete_intent_failure(event):
    """Extreme backup for answering completely unhandled intent requests."""
    LOG.info("Failed to find intent.")
    data = {'utterance': dialog.get('not.loaded')}
    context = {'client_name': 'mycroft_listener',
               'source': 'audio'}
    bus.emit(Message('speak', data, context))


def handle_sleep(event):
    """Put the recognizer loop to sleep."""
    loop.sleep()


def handle_wake_up(event):
    """Wake up the the recognize loop."""
    loop.awaken()


def handle_mic_mute(event):
    """Mute the listener system."""
    loop.mute()


def handle_mic_unmute(event):
    """Unmute the listener system."""
    loop.unmute()


def handle_mic_listen(_):
    """Handler for mycroft.mic.listen.

    Starts listening as if wakeword was spoken.
    """
    loop.responsive_recognizer.trigger_listen()


def handle_mic_get_status(event):
    """Query microphone mute status."""
    data = {'muted': loop.is_muted()}
    bus.emit(event.response(data))


def handle_paired(event):
    """Update identity information with pairing data.

    This is done here to make sure it's only done in a single place.
    TODO: Is there a reason this isn't done directly in the pairing skill?
    """
    IdentityManager.update(event.data)


def handle_audio_start(event):
    """Mute recognizer loop."""
    if config.get("listener").get("mute_during_output"):
        loop.mute()


def handle_audio_end(event):
    """Request unmute, if more sources have requested the mic to be muted
    it will remain muted.
    """
    if config.get("listener").get("mute_during_output"):
        loop.unmute()  # restore


def handle_stop(event):
    """Handler for mycroft.stop, i.e. button press."""
    loop.force_unmute()


def handle_open():
    # TODO: Move this into the Enclosure (not speech client)
    # Reset the UI to indicate ready for speech processing
    EnclosureAPI(bus).reset()


def on_ready():
    LOG.info('Speech client is ready.')


def on_stopping():
    LOG.info('Speech service is shutting down...')


def on_error(e='Unknown'):
    LOG.error('Audio service failed to launch ({}).'.format(repr(e)))


def connect_loop_events(loop):
    loop.on('recognizer_loop:utterance', handle_utterance)
    loop.on('recognizer_loop:speech.recognition.unknown', handle_unknown)
    loop.on('speak', handle_speak)
    loop.on('recognizer_loop:record_begin', handle_record_begin)
    loop.on('recognizer_loop:awoken', handle_awoken)
    loop.on('recognizer_loop:wakeword', handle_wakeword)
    loop.on('recognizer_loop:record_end', handle_record_end)
    loop.on('recognizer_loop:no_internet', handle_no_internet)


def connect_bus_events(bus):
    # Register handlers for events on main Mycroft messagebus
    bus.on('open', handle_open)
    bus.on('complete_intent_failure', handle_complete_intent_failure)
    bus.on('recognizer_loop:sleep', handle_sleep)
    bus.on('recognizer_loop:wake_up', handle_wake_up)
    bus.on('mycroft.mic.mute', handle_mic_mute)
    bus.on('mycroft.mic.unmute', handle_mic_unmute)
    bus.on('mycroft.mic.get_status', handle_mic_get_status)
    bus.on('mycroft.mic.listen', handle_mic_listen)
    bus.on("mycroft.paired", handle_paired)
    bus.on('recognizer_loop:audio_output_start', handle_audio_start)
    bus.on('recognizer_loop:audio_output_end', handle_audio_end)
    bus.on('mycroft.stop', handle_stop)


def main(ready_hook=on_ready, error_hook=on_error, stopping_hook=on_stopping,
         watchdog=lambda: None):
    global bus
    global loop
    global config

    callbacks = StatusCallbackMap(on_ready=ready_hook, on_error=error_hook,
                                  on_stopping=stopping_hook)
    status = ProcessStatus('speech', callback_map=callbacks)
    status.set_started()
    try:
        reset_sigint_handler()
        PIDLock("voice")
        config = Configuration.get()
        bus = start_message_bus_client("VOICE")
        connect_bus_events(bus)
        status.bind(bus)

        # Register handlers on internal RecognizerLoop bus
        loop = RecognizerLoop(watchdog)
        connect_loop_events(loop)
        create_daemon(loop.run)

    except Exception as e:
        error_hook(e)
    else:
        status.set_ready()
        wait_for_exit_signal()
        status.set_stopping()


if __name__ == "__main__":
    main()
