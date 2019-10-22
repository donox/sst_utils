import sys
import os


class DoNothingWell(object):
    def __init__(self, parm1, parm2):
        self.parm1 = parm1
        self.parm2 = parm2

    def print_something(self, message):
        if self.parm1:
            print('Parm 1 Message: {}'.format(self.parm1))
        elif self.parm2:
            print('Parm 2 Message: {}'.format(self.parm2))
        else:
            print('Both parameters were Null - so nothing printed')