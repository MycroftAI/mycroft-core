from os.path import dirname

import tweepy

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'crios'

LOGGER = getLogger(__name__)


class TwitterSkill(MycroftSkill):
    def __init__(self):
        super(TwitterSkill, self).__init__(name="TwitterSkill")
        ACCESS_TOKEN = self.config.get('aToken')
        ACCESS_TOKEN_SECRET = self.config.get('aTokenSecret')
        CONSUMER_KEY = self.config.get('cKey')
        CONSUMER_SECRET = self.config.get('cSecret')
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
        self.api = tweepy.API(auth)

    def initialize(self):
        self.load_data_files(dirname(__file__))
        self.register_regex("that (?P<PostText>.*)")
        self.register_regex("i am (?P<PostText>.*)")
        twitter_intent = (IntentBuilder("TwitterIntent")
                          .require("twitterKeyword")
                          .require("PostText").build())
        self.register_intent(twitter_intent, self.handle_twitter_intent)

    def handle_twitter_intent(self, message):
        try:
            tweet = message.metadata.get("PostText", message)
            post_text = ((tweet) + ' ' + '#mycroftaiskill')
            self.api.update_status(status=post_text)
            self.speak_dialog('twitter.success')
        except Exception as e:
            LOGGER.error("Error: {0}".format(e))
            self.speak_dialog('twitter.fail')

    def stop(self):
        pass


def create_skill():
    return TwitterSkill()
