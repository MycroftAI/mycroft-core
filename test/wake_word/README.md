# Audio Accuracy Test

This is a small tool running tests against the selected wakeword engine. It supports testing false negatives (wake word not triggering when it should) and false positives (wake word triggering when it should not).

To run this test you first need to setup data to use.

in this folder create a `data` folder with two subdirectories `with_wake_word` and `without_wake_word`:

```
data/
 ├──with_wake_word/
     ├── file1.wav
     ├── file2.wav
     ├── ...
     └── fileN.wav
 ├──without_wake_word/
     ├── file1.wav
     ├── file2.wav
     ├── ...
     └── fileN.wav
```

the wave files in `with_wake_word` will be checked that a wakeword IS triggered and the files in the `without_wake_word` directory will be checked to NOT trigger a wake word.

The test uses the mycroft config and listener directly so make sure your wave files are the correct format (16 kHz sample rate by default) and matches the hotword settings you are using.

The test can either be started using the mycroft startup script

```
./start-mycroft.sh audioaccuracytest
```

from the mycroft-core root folder or invoking the module directly

```
python -m test.audio_accuracy
```
