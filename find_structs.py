import json

from common import *

_POINTER_OR_ARRAY_CHARS = '*[]'
_DEFS_SIZES_FILENAME = 'defs/out.json'
_OPTIONS = """Options:
    0) Show this help message
    1) Choose range of structs sizes
    2) Choose field types
    3) Find definitions by entered params
    4) Clear params
    5) Exit"""

defSizeByName = json.load(open(_DEFS_SIZES_FILENAME, 'r'))

queryParams = {
    'fieldsParams': set(),
    'defSizeBounds': None,
}

print 'Definitions finder'

def printHelp():
    print _OPTIONS

def findDefs():
    if all(not param for param in queryParams.itervalues()):
        print '\tEmpty request query'
        return

    def isSuitableField(fields, fieldIndex, fieldTypes):
        if fieldIndex < len(fields):
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

            defSize = defSizeByName[defData['name']]
            if not bounds[0] <= defSize <= bounds[1]:
                return False

        fieldsParams = queryParams['fieldsParams']
        for (fieldIndex, fieldType) in fieldsParams:
            if not isSuitableField(defData['fields'], fieldIndex, fieldType):
                return False

        return True

    foundDefs = filter(isSuitableDefinition, defDataByName.itervalues())
    if not foundDefs:
        print '\tNo any definitions found'
        return

    print '\tFound definitions:'
    for defData in foundDefs:
        print '\t\tDefinition "{name}" with type "{type}"'.format(**defData)


printHelp()


while True:
    try:
        option = input('Please choose option: ')
        if option == 0:
            printHelp()
        elif option == 1:
            minBound = input('\tPlease type the size min bound: ')
            maxBound = input('\tPlease type the size max bound: ')
            queryParams['defSizeBounds'] = (minBound, maxBound)
        elif option == 2:
            fieldIndex = input('\tPlease type the field index: ')
            fieldTypes = tuple(filter(
                bool,
                raw_input('\tPlease type the field types (separated by space): ').split()
            ))
            queryParams['fieldsParams'].add((fieldIndex, fieldTypes))
        elif option == 3:
            findDefs()
        elif option == 4:
            queryParams.clear()
        elif option == 5:
            print 'Good bye!'
            break
    except KeyboardInterrupt:
        break
