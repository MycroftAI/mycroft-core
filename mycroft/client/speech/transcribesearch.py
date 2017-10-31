from mycroft.util.log import LOG
import wave
import string
from mycroft.configuration import ConfigurationManager
from mycroft.util import (
    create_signal,
    check_for_signal
)
import datetime
import os

# audio_location = "/home/regbloom/mycroft-core/scripts/audiorec/userinput/"

__author__ = "reginaneon"

LOG = LOG("TranscribeSearch")
# config = ConfigurationManager.get()
# listener_config = config.get('listener')

text_permission = create_signal('transcribe_text_permission')
audio_permission = create_signal('keep_audio_permission')
# text_permission = check_for_signal('transcribe_text_permission',0)
# audio_permission = check_for_signal('keep_audio_permission',0)


class TranscribeSearch:
    """
    Name: TranscribeSearch
    Purpose: Scans over the transcription file, analyzing it for desired
             outcomes. Imports data to the new,
             more precise text file, containing
             the lines needed.
    """

    def searching_file(self, date_looking, text_looking):

        search_globdate = date_looking
        text_location = "/var/log/mycroft/ts_transcripts/" + \
                        search_globdate + ".txt"

        with open(text_location, 'r+') as s:
            with open("/var/log/mycroft/ts_selected_transcripts/" +
                      search_globdate + ".txt", 'a+') as out:
                lines = s.readlines()

                tot = len(lines)
                line = lines[tot - 1]

                if line.find('i like') != -1:
                    out.write(line)
                    LOG.info("Search: Occasion of '" + text_looking +
                             "' is found")
                    LOG.debug("Success: " + line + " is imported")

                    # brandsFound = set(brandsList).intersection(line)

    def write_transcribed_files(self, audio, text):
        # save the audio before it is sent off:
        globstamp = str(datetime.datetime.now())
        globdate = str(datetime.date.today())

        # check_for_signal('keep_audio_permission', 0)

        if check_for_signal('keep_audio_permission', -1):
            # if trans_values.audio_permission:
            try:
                os.makedirs("/var/log/mycroft/"
                            "ts_transcript_audio_segments/" + globdate)
            except OSError:
                if not os.path.isdir("/var/log/mycroft/"
                                     "ts_transcript_audio_segments/" +
                                     globdate
                                     ):
                    raise

            LOG.info("Audio Save Permission Granted")

            if check_for_signal('transcribe_text_permission', -1):
                # if trans_values.text_permission:
                filename1 = "/var/log/mycroft/ts_transcripts/" + \
                            globdate + ".txt"
                with open(filename1, 'a+') as filea:
                    filea.write(globstamp + " " + text + "\n")
                    LOG.info("Transcribing Permission Granted: "
                             "Text Input Saved Successfully")

                filename = "/var/log/mycroft/ts_transcript_audio_segments/" + \
                           globdate + \
                           "/" + (globstamp + " " + text).decode("utf8") + \
                           " .wav"

            else:
                LOG.warning("Transcribing Permission Denied")
                filename = "/var/log/mycroft/ts_transcript_audio_segments/" + \
                           globdate + \
                           "/" + globstamp + " no_transcription_available.wav"
                LOG.info("Transcribing Permission Denied: "
                         "The Audio Recording of User's Input Saved in "
                         "TimeStamp Format")

            LOG.info(
                "Transcribing Permission Granted: Audio Recording, " +
                filename + " saved.")
            self.save_record(filename, audio)

            self.searching_file(globdate, "i like")
        else:
            LOG.info("Audio Save Permission Denied")

    def save_record(self, wav_name, audio):
        # TODO: use "with"
        waveFile = wave.open(wav_name, 'wb')
        waveFile.setnchannels(1)
        waveFile.setsampwidth(2)
        waveFile.setframerate(16000)
        # waveFile.setsampwidth(self.SAMPLE_WIDTH)
        # waveFile.setframerate(self.SAMPLE_RATE)
        waveFile.writeframes(audio)
        waveFile.close()
