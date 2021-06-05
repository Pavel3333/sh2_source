import json

from common import *

_DEFS_SIZES_FILENAME = 'defs/out.json'
_OPTIONS = """Options:
    0) Show this help message
    1) Choose range of structs sizes
    2) Choose field type
    3) Find definitions by entered params
    4) Clear params
    5) Exit"""

defSizeByName = json.load(open(_DEFS_SIZES_FILENAME, 'r'))

print 'Definitions finder'

def printHelp():
    print _OPTIONS

printHelp()

while True:
    try:
        option = input('Please choose option: ')
        if option == 0:
            printHelp()
        elif option == 1:
            pass
        elif option == 2:
            pass
        elif option == 3:
            pass
        elif option == 4:
            pass
        elif option == 5:
            print 'Good bye!'
            break
    except KeyError:
        break
