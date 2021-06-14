import json

from common import *

_POINTER_OR_ARRAY_CHARS = '*[]'
_DEFS_INFO_FILENAME = 'defs/out.json'
_OPTIONS = """Options:
	0) Show this help message
	1) Choose range of structs sizes
	2) Choose field types
	3) Find definitions by entered params
	4) Clear params
	5) Exit"""

defsInfo = json.load(open(_DEFS_INFO_FILENAME, 'r'))

queryParams = {
    'fieldsParams': set(),
    'defSizeBounds': None,
}

print 'Definitions finder'

def printHelp():
    print _OPTIONS

def findDefs():
    if all(not param for param in queryParams.itervalues()):
        printIndented(1, 'Empty request query')
        return

    def isSuitableField(fields, fieldIndex, fieldTypes):
        fieldsCount = len(fields)
        if fieldIndex < 0:
            fieldIndex = fieldsCount + fieldIndex

        if 0 <= fieldIndex < fieldsCount:
            foundField = fields[fieldIndex]
            for fieldType in fieldTypes:
                fieldRawType = fieldType.strip(' ' + _POINTER_OR_ARRAY_CHARS)
                if fieldRawType not in foundField.rawType:
                    continue

                if foundField.fieldType != FieldType.SimpleField:
                    return True

                foundFieldSize = foundField.size.strip()
                isPointerOrArray = any(char in fieldType for char in _POINTER_OR_ARRAY_CHARS)
                isFoundFieldPointerOrArray = foundField.isPointer or bool(foundFieldSize)
                if isPointerOrArray == isFoundFieldPointerOrArray:
                    return True

        newFields = []
        for field in fields:
            subDefData = defDataByName.get(field.rawType)
            if not field.isPointer and subDefData is not None:
                newFields.extend(subDefData['fields'])
            else:
                newFields.append(field)

        if newFields == list(fields):
            return False

        return isSuitableField(newFields, fieldIndex, fieldTypes)


    def isSuitableDefinition(defData):
        bounds = queryParams['defSizeBounds']
        if bounds is not None:
            if defData['type'] == 'enum':
                return False

            defInfo = defsInfo[defData['name']]
            if not bounds[0] <= defInfo['size'] <= bounds[1]:
                return False

        fieldsParams = queryParams['fieldsParams']
        for (fieldIndex, fieldType) in fieldsParams:
            if not isSuitableField(defData['fields'], fieldIndex, fieldType):
                return False

        return True

    foundDefs = filter(isSuitableDefinition, defDataByName.itervalues())
    if not foundDefs:
        printIndented(1, 'No any definitions found')
        return

    printIndented(1, 'Found definitions:')
    for defData in foundDefs:
        printIndented(2, getDefCode(defData))


printHelp()


while True:
    try:
        option = input('Please choose option: ')
        if option == 0:
            printHelp()
        elif option == 1:
            minBound = input(getIndented(1, 'Please type the size min bound: '))
            maxBound = input(getIndented(1, 'Please type the size max bound: '))
            queryParams['defSizeBounds'] = (minBound, maxBound)
        elif option == 2:
            fieldIndex = input(getIndented(1, 'Please type the field index: '))
            fieldTypes = tuple(filter(bool, raw_input(getIndented(
                1, 'Please type the field types (separated by space): '
            )).split()))
            queryParams['fieldsParams'].add((fieldIndex, fieldTypes))
        elif option == 3:
            findDefs()
        elif option == 4:
            queryParams['fieldsParams'].clear()
            queryParams['defSizeBounds'] = None
        elif option == 5:
            print 'Good bye!'
            break
    except KeyboardInterrupt:
        break
