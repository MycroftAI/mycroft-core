# How to submit an Issue to a Mycroft repository

When submitting an Issue to a Mycroft repository, please follow these guidelines to help us help you. 

## Be clear about the software, hardware and version you are running

For example: 

* I'm running a Mark 1
* With version 0.9.10 of the Mycroft software
* With the standard Wake Word

## Try to provide steps that we can use to replicate the Issue

For example: 

1. Burn the 0.9.10 image to Micro SD card using Etcher
2. Seat the Micro SD card in the RPi 3
3. Boot Picroft
4. Wait 3 minutes
5. The red light will come on indicating that the RPi 3 is overheating
6. Running `htop` via the command line indicates a number of Zombie'd processes

## Be as specific as possible about the expected condition, and the deviation from expected condition. 

This is called _object-deviation format_. Specify the object, then the deviation of the object from an expected condition. 

Example 1: 

* When I say "Hey Mycroft, set your eyes to cadet blue", the eyes turn purple instead of blue. 

Example 2: 

* When I say "Hey Mycroft, what time is it in Paris", the time spoken is out by one hour - it's not observing daylight savings time. 

Example 3: 

* When I run `msm default` on my Mark 1, I receive lots of Git 'locked file' errors on the command line. 

## Provide log files or other output to help us see the error

We will normally require log files or other troubleshooting information to assist you with your Issue. 

This [documentation](https://mycroft.ai/documentation/troubleshooting/) explains how to find log files. 

As of version 0.9.10, the [Support Skill](https://github.com/MycroftAI/skill-support) also helps to automate gathering support information. 

Simply say: 

* "Create a support ticket" _or_
* "You're not working!" _or_
* "Send me debug info"

and the Skill will put together a support package which you can email to us. 

## Upload any files to the Issue that will be useful in helping us to investigate

Please ensure you upload any relevant files - such as screenshots - which will aid us investigating. 
