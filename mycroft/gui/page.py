from mycroft.util.log import LOG

class GuiPage:
    """ A representation of a GUI Page

    A GuiPage represents a single GUI Display within a given namespace. A Page
    has a name, a position and can have either Persistence or Duration during
    which it will exist

    Attributes:
         name: the name of the page that is shown in a given namespace, assigned
         by the skill author
         persistent: indicated weather or not the page itself should persists for a
         period of time or unit the it is removed manually
         duration: the duration of the page in the namespace, assigned by the skill
         author if the page is not persistent
         active: indicates whether the page is currently active in the namespace
    """

    def __init__(self, url: str, name: str, persistent: bool, duration: int):
        self.url = url
        self.name = name
        self.persistent = persistent
        self.duration = duration
        self.active = False
