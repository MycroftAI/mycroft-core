from mycroft import MycroftSkill, intent_handler
from adapt.intent import IntentBuilder
import os

class Judgealexa(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)
        self.log.info("Skill initiated")
        self.log.info("ScoreFile on path: " + (self.file_system.path + "/scoreFile.txt"))
        self.scoreFile = (self.file_system.path + "/scoreFile.txt")
        if not os.path.exists(self.scoreFile):
            scoreFile = open(self.scoreFile, "w+")
            scoreFile.write("1000")
            scoreFile.close()

    # @intent_handler('a.intent')
    # def handle_judgealexa(self, message):
    #     #nsult = message.data.get('insult')
    #     scoreFile = open(self.scoreFile, "r")
    #     points = scoreFile.read()
    #     scoreFile.close()
    #     self.log.info("Calculating response")
    #     self.speak(f"Your score is {points}")

    @intent_handler(IntentBuilder('score').require('Score'))
    def handle_score(self, message):
        #nsult = message.data.get('insult')
        scoreFile = open(self.scoreFile, "r")
        points = scoreFile.read()
        scoreFile.close()
        self.log.info("Calculating response")
        self.speak(f"Your score is {points}")

    @intent_handler(IntentBuilder('insult').require('Insults'))
    def handle_insult(self, message):
        self.log.info("----called-----")
        #nsult = message.data.get('insult')
        scoreFile = open(self.scoreFile, "r")
        points = int(scoreFile.read())
        scoreFile.close()
        points = points - 1
        scoreFile = open(self.scoreFile, "w+")
        scoreFile.write(str(points))
        scoreFile.close()
        self.log.info("Calculating response")
        self.speak(f"Insult")


    # @intent_handler('insult.intent')
    # def handle_judgealexa(self, message):
    #     #nsult = message.data.get('insult')
    #     scoreFile = open(self.scoreFile, "r")
    #     points = int(scoreFile.read())
    #     scoreFile.close()
    #     points = points - 1
    #     scoreFile = open(self.scoreFile, "w+")
    #     scoreFile.write(str(points))
    #     scoreFile.close()
    #     self.log.info("Calculating response")
    #     self.speak(f"Insult")


def create_skill():
    return Judgealexa()

