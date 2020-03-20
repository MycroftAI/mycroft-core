# Voight Kampff tester

> You’re watching television. Suddenly you realize there’s a wasp crawling on your arm.

The Voight Kampff tester is an integration test system based on the "behave" framework using human readable test cases. The tester connects to the running mycroft-core instance and performs tests. Checking that user utterances returns a correct response.

## Test setup
`test_setup` collects feature files for behave and installs any skills that should be present during the test.

## Running the test
After the test has been setup run `behave` to start the test.

## Feature file
Feature files is the way tests are specified for behave (Read more [here](https://behave.readthedocs.io/en/latest/tutorial.html))

Below is an example of a feature file that can be used with the test suite.
```feature
Feature: mycroft-weather
  Scenario Outline: current local weather question
    Given an english speaking user
     When the user says "<current local weather>"
     Then "mycroft-weather" should reply with "Right now, it's overcast clouds and 32 degrees."

   Examples: local weather questions
        | current local weather |
        | what's the weather like |
        | current weather |
        | tell me the weather |

  Scenario: Temperature in paris
    Given an english speaking user
     When the user says "how hot will it be in paris"
     Then "mycroft-weather" should reply with dialog from "current.high.temperature.dialog"
```

### Given ...

Given is used to perform initial setup for the test case. currently this has little effect and the test will always be performed in english but need to be specified in each test as 

```Given an english speaking user```

### When ...
The When is the start of the test and will inject a message on the running mycroft instance. The current available When is

`When the user says "<utterance>"`

where utterance is the sentence to test.

### Then ...
The "Then" step will verify Mycroft's response, handle a followup action or check for messages on the messagebus.

#### Expected dialog:
`"<skill-name>" should reply with dialog from "<dialog-file>"`

Example phrase:
`Then "<skill-name>" should reply with "<example>"

This will try to map the example phrase to a dialog file and will allow any response from that dialog file. This one is somewhat experimental et the moment.

#### Should contain:
`mycroft reply should contain "<text>"`

This will match any sentence containing the specified text.

#### User reply:
`Then the user says "<utterance>"`

This allows setting up scenarios with conversational aspects, e.g. when using `get_response()` in the skill.

Example:
```feature
Scenario: Bridge of death
  Given an english speaking user
  When the user says "let's go to the bridge of death"
  Then "death-bridge" should reply with dialog from "questions_one.dialog"
  Then the user says "My name is Sir Lancelot of Camelot"
  Then "death-bridge" should reply with dialog from "questions_two.dialog"
  Then the user says "To seek the holy grail"
  Then "death-bridge" should reply with dialog from "questions_three.dialog"
  Then the user says "blue"
```

#### Mycroft messagebus message:
`mycroft should send the message "<message type>"`

This verifies that a specific message is emitted on the messagebus. This can be used to check that a playback request is sent or other action is triggered.
