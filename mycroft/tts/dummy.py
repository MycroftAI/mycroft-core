import re
class X:
    test = None

    def __init__(self):
        print("Initializing")
        if not X.test:
            print("Setting test for the first time")
            X.test = 1
        print("__init__ complete")

    def do_test(self):
        print("Test is " + str(X.test))
        X.test += 1


class BuggyX:
    test = None

    def __init__(self):
        print("Initializing")
        if not self.test:
            print("Setting test for the first time")
            self.test = 1
        print("__init__ complete")

    def do_test(self):
        print("Test is " + str(self.test))
        self.test += 1
        print("buugy ", BuggyX.test)

a = BuggyX()
b = BuggyX()
a.do_test()

b.do_test()

text = "this is a long sentence to check on multiple breaks. but i want to handle it in one request"
chunks = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\;|\?)\s',
                              text)

print(chunks)