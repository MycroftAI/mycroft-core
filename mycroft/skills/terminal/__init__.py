# Time-stamp: <2017-03-30 14:17:18 dmendyke>   -*- mode: python; -*-
#



##
# Required Mycroft core modules
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

##
# Modules required for this skill
import os
from subprocess import Popen


##
# Written by Daniel Mendyke dmendyke@jaguarlandrover.com
__author__ = 'dmendyke'


##
# Create the logger instance
LOGGER = getLogger( __name__ )  # load the logging functions


##
# This skill class allows Mycroft to open a standard terminal
class TerminalSkill( MycroftSkill ) :

  ## Constructor
  def __init__( self ) :
    # Python 2.7??  Really??  Come on now, isn't it time
    # you stop programming in your parents basement!
    super( TerminalSkill, self ).__init__( name = "TerminalSkill" )

  ## Required function
  #
  # Called by Mycroft in order to set and load intent handler
  def initialize( self ) :
    # load the vob and dialog key words
    #self.load_data_files( dirname( __file__ ) )
    # Build the 'intent' which I am not sure what that really is
    intent = IntentBuilder( "TerminalIntent" ).require( "terminalkeyword" ).build()
    # Tie the 'intent' to the function that performs the intended functionality
    self.register_intent( intent, self.handle_intent )

  ##
  # Performs actual function of this skill - Open a terminal
  def handle_intent( self, message ) :
    try :
      devnull = open( os.devnull, 'wb' )
      Popen( [ 'nohup', '/usr/bin/gnome-terminal' ], stdout = devnull, stderr = devnull )
      self.speak_dialog( 'terminal' )
    except Exception as E :
      LOGGER.error( 'Terminal Skill Error: {}'.format( E ) )

##
# Required function
#
# Called by Mycroft core in order to initialize this skill
def create_skill() : return TerminalSkill()
