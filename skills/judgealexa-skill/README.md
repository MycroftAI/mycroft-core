# <img src="https://raw.githack.com/FortAwesome/Font-Awesome/master/svgs/solid/robot.svg" card_color="#22A7F0" width="50" height="50" style="vertical-align:bottom"/> Judgealexa
## Setup
  move /skills/judgealexa-skill directory into /opt/mycroft/skills directory
  
## About

## Examples

- "Tell me my score"
- "{insult}"


## Permanent Listening

### mycroft/client/speech/mic.py
 #### wait_until_wakeword():
 - added noise detection
 - threshold is currently hardcoded for Phonum beyerdynamic 
 - increased ww_frames

 #### listen()
  - ww_frames are always loaded into chunk


## Credits

Leon, An and Florian

## Category

**Daily**

## Tags
