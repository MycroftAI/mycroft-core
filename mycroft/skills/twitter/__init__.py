from os.path import dirname

import tweepy

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'crios'

LOGGER = getLogger(__name__)

# Place your Twitter API keys here!
ACCESS_TOKEN = ''
ACCESS_TOKEN_SECRET = ''
CONSUMER_KEY = ''
CONSUMER_SECRET = ''

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)


class TwitterSkill(MycroftSkill):
    def __init__(self):
        super(TwitterSkill,self).__init__(name="TwitterSkill")

    def initialize(self):
        self.load_data_files(dirname(__file__))

        twitter_intent = IntentBuilder("TwitterIntent").require("twitterKeyword").build()
        self.register_intent(twitter_intent, self.handle_twitter_intent)

    def handle_twitter_intent(self, message):
        try:
            post_text = 'I am a pink fluffy unicorn' + ' ' + ' #mycroftaiskill'
            api.update_status(status=post_text)
            self.speak_dialog('twitter.success')
        except Exception as e:
            LOGGER.error("Error: {0}".format(e))
            self.speak_dialog('twitter.failure')

    def stop(self):
        pass


def create_skill():
    return TwitterSkill()