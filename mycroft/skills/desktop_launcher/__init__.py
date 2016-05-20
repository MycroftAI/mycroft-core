import os
import sys
import urllib2
import webbrowser

from adapt.intent import IntentBuilder
from adapt.tools.text.tokenizer import EnglishTokenizer
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

logger = getLogger(__name__)
__author__ = 'seanfitz'

IFL_TEMPLATE = "http://www.google.com/search?&sourceid=navclient&btnI=I&q=%s"


class DesktopLauncherSkill(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self, "DesktopLauncherSkill")
        self.appmap = {}

    def initialize(self):
        try:
            import gio
        except:
            sys.path.append("/usr/lib/python2.7/dist-packages")
            try:
                import gio
            except:
                logger.error("Could not import gio")
                return

        vocab_dir = os.path.join(os.path.dirname(__file__), 'vocab', 'en-us')

        self.load_vocab_files(vocab_dir)
        tokenizer = EnglishTokenizer()

        for app in gio.app_info_get_all():
            name = app.get_name().lower()
            entry = [app]
            tokenized_name = tokenizer.tokenize(name)[0]

            if name in self.appmap:
                self.appmap[name] += entry
            else:
                self.appmap[name] = entry

            self.register_vocabulary(name, "Application")
            if name != tokenized_name:
                self.register_vocabulary(tokenized_name, "Application")
                if tokenized_name in self.appmap:
                    self.appmap[tokenized_name] += entry
                else:
                    self.appmap[tokenized_name] = entry

        self.register_regex("for (?P<SearchTerms>.*)")
        self.register_regex("for (?P<SearchTerms>.*) on")
        self.register_regex("(?P<SearchTerms>.*) on")

        launch_intent = IntentBuilder(
            "LaunchDesktopApplication").require("LaunchKeyword").require(
                "Application").build()
        self.register_intent(launch_intent, self.handle_launch_desktop_app)

        launch_website_intent = IntentBuilder(
            "LaunchWebsiteIntent").require("LaunchKeyword").require(
                "Website").build()
        self.register_intent(launch_website_intent, self.handle_launch_website)

        search_website = IntentBuilder("SearchWebsiteIntent").require(
            "SearchKeyword").require("Website").require(
                "SearchTerms").build()
        self.register_intent(search_website, self.handle_search_website)

    def handle_launch_desktop_app(self, message):
        app_name = message.metadata.get('Application')
        apps = self.appmap.get(app_name)
        if apps and len(apps) > 0:
            apps[0].launch()

    def handle_launch_website(self, message):
        site = message.metadata.get("Website")
        webbrowser.open(IFL_TEMPLATE % (urllib2.quote(site)))

    def handle_search_website(self, message):
        site = message.metadata.get("Website")
        search_terms = message.metadata.get("SearchTerms")
        search_str = site + " " + search_terms
        webbrowser.open(IFL_TEMPLATE % (urllib2.quote(search_str)))

    def stop(self):
        pass


def create_skill():
    return DesktopLauncherSkill()
