import os
import re
from fields import *


DEFINITIONS_FILE_NAME = 'defs/definitions.cpp'

_DEFINITION_FLAGS = re.MULTILINE | re.DOTALL
_DEFINITION_PATTERN = r'^(\w+) ([\w\d_]+)(\s*:\s*[\w\d ]+\s*)?$.' '\{$.' '(.+?)$.' '\};'

defDataByName = {}
defDataByTypeAndCode = {}
defDepsByName = {}


def getIndented(level, data):
    indent = '\t' * level
    return indent + data.replace('\n', '\n' + indent)


def writeRaw(fil, data):
    fil.write(data) 


def writeNewlined(fil, data):
    writeRaw(fil, data + '\n') 


def writeIndented(fil, level, data):
    writeNewlined(fil, getIndented(level, data))


def printRaw(*args):
    print ' '.join(args)


def printIndented(level, *args):
    printRaw(getIndented(level, *args))


def getDefDependencies(defData):
    defName = defData['name']
    defDeps = defDepsByName.get(defName)
    if defDeps is not None:
        return defDeps

    defDeps = {
        field.type
        for field in defData['fields']
        if not field.isPointer and field.type in defDataByName
    }

    for fieldName in set(defDeps):
        defDeps |= getDefDependencies(defDataByName[fieldName])

    defDepsByName[defName] = defDeps

    return defDeps


def getDefFieldsCode(defData):
    return getIndented(1, ''.join(
        '%s\n' % field.code
        for field in defData['fields']).rstrip()
    )


def getDefCode(defData):
    defDataCopy = defData.copy()
    defDataCopy['fieldsCode'] = getDefFieldsCode(defData)
    return SubDefinition._CODE_FMT.format(**defDataCopy)


def parsePattern(data, pattern, flags=_DEFINITION_FLAGS):
    matches = re.findall(pattern, data, flags=flags)
    otherData = re.sub(pattern, '', data, flags=flags)

    return matches, otherData


def parseSubDefs(defName, defCode):
    subDefsData = []
    subDefsMatches, otherCode = parsePattern(defCode, SubDefinition.CODE_PATTERN)
    for i, (subDefType, enumType, subDefCode) in enumerate(subDefsMatches):
        subDefName = '%s_%s_%d' % (defName, subDefType, i)
        subDefData = addDefinition(subDefType, subDefName, subDefCode, enumType)
        if subDefData is not None:
            subDefName = subDefData['name']
            subDefsData.append(SimpleField(subDefName, '%s_%s_%d' % (subDefName, subDefType, i)))

    return subDefsData, otherCode


def parseFieldsCode(code, fieldCls):
    matches, otherCode = parsePattern(code, fieldCls.CODE_PATTERN)
    data = [fieldCls(*match) for match in matches]

    return data, otherCode


def aliasDefName(aliasName, realName):
    if aliasName != realName:
        defsNameAliases[aliasName] = realName
        defDataByName.pop(aliasName, None)


def addDefinition(defType, name, fieldsCode, enumType=None):
    defData = defDataByName.get(name)
    if defData is not None:
        return defData

    defData = defDataByTypeAndCode.get((defType, fieldsCode))
    if defData is not None:
        aliasDefName(name, defData['name'])
        return defData

    subDefsData, simpleFieldsCode = parseSubDefs(name, fieldsCode)

    defData = defDataByName[name] = defDataByTypeAndCode[(defType, fieldsCode)] = {
        'type': defType,
        'enumType': enumType or '',
        'name': name,
        'fields': subDefsData,
        'fieldsCode': simpleFieldsCode
    }
    
    return defData


def parseDefFields(defData):
    fieldsCode = defData['fieldsCode']

    if defData['type'] == 'enum':
        enumData, otherCode = parseFieldsCode(fieldsCode, EnumField)
        return enumData
    else:
        simpleFieldsData, functionsCode = parseFieldsCode(fieldsCode, SimpleField)
        functionsData, otherCode = parseFieldsCode(functionsCode, FunctionField)
        return simpleFieldsData + functionsData


def postProcessDefinitions():
    defDataByTypeAndCode.clear()

    # Fields primary parsing
    for defName, defData in defDataByName.iteritems():
        defData['fields'] += parseDefFields(defData)
        defData['fieldsCode'] = getDefFieldsCode(defData)
        defDataByTypeAndCode[(defData['type'], defData['fieldsCode'])] = defData

    # Filter all duplicates with same code
    for defName, defData in defDataByName.items():
        sameCodeDefData = defDataByTypeAndCode.get((defData['type'], defData['fieldsCode']))
        if sameCodeDefData is not None:
            aliasDefName(defName, sameCodeDefData['name'])

    # Rename all fields type to its real (not aliased) names
    for defData in defDataByName.values():
        for field in defData['fields']:
            realFieldType = defsNameAliases.get(field.rawType)
            if realFieldType is not None:
                field.rawType = realFieldType

    # Build dependencies tree
    for defName, defData in defDataByName.iteritems():
        getDefDependencies(defData)

def sortDefinitions():
    defsOrder = []

    def getDefIndex(defData):
        defName = defData['name']
        defDeps = defDepsByName[defName]
        processedDefs = set()
        if not defDeps - processedDefs:
            return 0

        defIndex = None
        for i, processedDefData in tuple(enumerate(defsOrder)):
            processedDefs.add(processedDefData['name'])

            if not defDeps - processedDefs:
                return i + 1

        return None

    while True:
        remains = len(defDataByName) - len(defsOrder)
        if not remains:
            break

        for defData in defDataByName.itervalues():
            if defData in defsOrder:
                continue
                
            defIndex = getDefIndex(defData)
            if defIndex is not None:
                defsOrder.insert(defIndex, defData)

    return defsOrder


for root, directories, files in os.walk('./'):
    if not root.endswith('/'):
        root += '/'

    for filename in files:
        if not filename.endswith('.c') or filename == DEFINITIONS_FILE_NAME:
            continue

        path = (root + filename)[len('./'):]
        
        # print 'Processing:', path

        sourceData = open(path, 'r').read()
        sourceData = sourceData.replace('_anon', '_%s_anon' % filename[:-2])
        sourceData = sourceData.replace('<unknown fundamental type (0xa510)>', '__m128')

        matches, _ = parsePattern(sourceData, _DEFINITION_PATTERN)
        for (defType, defName, enumType, defCode) in matches:
            addDefinition(defType, defName, defCode, enumType)


postProcessDefinitions()
