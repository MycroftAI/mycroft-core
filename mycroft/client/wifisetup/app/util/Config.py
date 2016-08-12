import ConfigParser
import os


#Config = ConfigParser.ConfigParser()

class AppConfig(ConfigParser.RawConfigParser):
    app_config = './configuration/default.ini'
    Config = ConfigParser.ConfigParser()

    def __init__(self):
        pass
    def create_section(self, section_name):
        self.Config.add_section(section_name)

    def set_option(self, section, option, value):
        self.Config.set(section,option,value)

    def write_file(self):
        with open(self.app_config, 'wb') as configfile:
            self.Config.write(configfile)

    def read_option(self, section, option):
        #self.open_file()
        return self.Config.get(section, option)

    def open_file(self):
        self.Config.readfp(open(self.app_config))

    def ConfigSectionMap(self,section):
        dict1 = {}
        options = self.Config.options(section)
        for option in options:
            try:
                dict1[option] = self.Config.get(section, option)
                if dict1[option] == -1:
                    DebugPrint("skip: %s % option)")
            except:
                print("exception on %s" % option)
                dict1[option] = None
                print dict1[option]
        return dict1


