from mycroft.util.log import LOG
import wave
from mycroft.util.signal import (
    check_for_signal
)
import datetime
import os


__author__ = "reginaneon"

text_permission = check_for_signal(
    'transcribe_text_permission', 0)  # starting default is off
audio_permission = check_for_signal('keep_audio_permission', 0)
# text_permission = create_signal('transcribe_text_permission')
# audio_permission = create_signal('keep_audio_permission')


class Transcribe:
    """
    Name: Transcribe
    Purpose: Writes the transcription file.
    Imports data to the new, more precise text file, containing
             the lines needed.
    """
    @classmethod
    def write_transcribed_files(self, audio, text):
        # save the audio before it is sent off:
        globstamp = str(datetime.datetime.now())
        globdate = str(datetime.date.today())

        # check_for_signal('keep_audio_permission', 0)

        if check_for_signal('transcribe_text_permission', -1):
            # if trans_values.text_permission:
            filename1 = "/var/log/mycroft/ts_transcripts/" + \
                        globdate + ".txt"

            try:
                os.makedirs("/var/log/mycroft/"
                            "ts_transcripts/")
            except OSError:
                if not os.path.isdir("/var/log/mycroft/"
                                     "ts_transcripts/"):
                    raise

            with open(filename1, 'a+') as filea:
                filea.write(globstamp + " " + text + "\n")
                LOG.info("Transcribing Permission Granted: "
                         "Text Input Saved Successfully")

        else:
            LOG.warning("Transcribing Permission Denied")

        if check_for_signal('keep_audio_permission', -1):
            LOG.info("Audio Save Permission Granted")
            try:
                os.makedirs("/var/log/mycroft/"
                            "ts_transcript_audio_segments/" +
                            globdate)
            except OSError:
                if not os.path.isdir("/var/log/mycroft/"
                                     "ts_transcript_audio_segments/" +
                                     globdate):
                    raise

            filename = "/var/log/mycroft/ts_transcript_audio_segments/" +\
                       globdate + \
                       "/" + (globstamp + " " + text).decode("utf8") + " .wav"

            waveFile = wave.open(filename, 'wb')
            waveFile.setnchannels(1)
            waveFile.setsampwidth(2)
            waveFile.setframerate(16000)
            waveFile.writeframes(audio)
            waveFile.close()

            LOG.info(
                "Transcribing Permission Granted: The Audio Recording of "
                "User's Input Saved in Full Format")

        else:
            LOG.info("Audio Save Permission Denied")
