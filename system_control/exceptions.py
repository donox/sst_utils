
class SstCommandDefinitionException(Exception):
    """Exception in creating a commands.txt file"""
    def __init__(self, value):
        self.value = value

    # __str__ is to print() the value
    def __str__(self):
        return (repr(self.value))