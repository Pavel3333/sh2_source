import os
import re
from collections import defaultdict

def writeRaw(fil, data):
    fil.write(data) 

def writeNewlined(fil, data):
    writeRaw(fil, data + '\n') 

def writeIndented(fil, indent, data):
    writeNewlined(fil, ('\t' * indent) + data)

_STRUCT_FILE_NAME = 'offsets.c'

_DEFENITION_FLAGS = re.MULTILINE | re.DOTALL
_DEFINITION_TEMPLATE = r'^(\w+) ([\w\d_]+)$.' '\{$.' '(.+?)$.' '\};'
_DEFENITION_FIELD_TEMPLATE = r'^\s*' '([\w\d *]+)' '\s+' '([\w\d_]+)' '\s*' '([\[\d\]]+)*?' '\s*' '(:\s*[\d]+)?;$.?'
_FUNCTION_PARSE_TEMPLATE   = r'^\s*' '([\w\d *]+)' '\s*' '\(\*([\w\d ]+)\)' '\s*' '\(([\w\d *,]*)\);$.?'
_SUBDEF_TEMPLATE = r'^\s*' '(\w+)$.' '\s*' '\{$.' '(.+?)$.' '\s*' '\};$.?'

_DEFINITION_DECLARATION_FMT = r'typedef {defType} {defName};'

_MAIN_FUNCTION_START = """
#include <stdio.h>

int main() {
    printf("structsSizes = {\\n");
"""

_STRUCT_SIZE_PRINT_FMT = (' ' * 4) + r'printf("    \"{0}\": %d,\n", sizeof({0}));'

_MAIN_FUNCTION_END = """
    printf("}\\n");

    return 0;
}
"""

defsData = defaultdict(dict)

def sortDefinitions():
    defsOrder = []
    for defsType, currentDefsData in defsData.iteritems():
        for defData in currentDefsData.itervalues():
            defIndex = len(defsOrder)
            for fieldData in defData['fields']:
                fieldRawName = fieldData['name'].strip(' *')
                # print '\t\tfieldRawType:', fieldRawType
                foundData = None
                for i, anyDefData in enumerate(defsOrder):
                    if fieldRawName == anyDefData['name'].strip(' *'):  # TODO: fields iteration
                        print fieldData['name'], anyDefData['name']
                        defIndex = min(defIndex, i)

            if defIndex:
                print '\tdefName:', defData['name']
                print '\tdefIndex:', defIndex
            defsOrder.insert(defIndex, defData)

    return defsOrder


def parseTemplate(data, template, flags=_DEFENITION_FLAGS):
    matches = re.findall(template, data, flags=flags)
    otherData = re.sub(template, '', data, flags=flags)

    return matches, otherData


def parseSubDefs(defName, defCode):
    subDefsData = []
    subDefsMatches, otherCode = parseTemplate(defCode, _SUBDEF_TEMPLATE)
    for i, (subDefType, subDefCode) in enumerate(subDefsMatches):
        subDefName = '%s_%s_%d' % (defName, subDefType, i)
        subDefData = addDefenition(subDefType, subDefName, subDefCode)
        if subDefData is not None:
            subDefsData.append(subDefData)

    return subDefsData, otherCode


def parseSimpleFields(defCode):
    simpleFieldsData = []
    simpleFieldsMatches, otherCode = parseTemplate(defCode, _DEFENITION_FIELD_TEMPLATE)
    for fieldType, fieldName, fieldSize, fieldBitCount in simpleFieldsMatches:
        # print '\t\tfieldType: %s, fieldName: %s, fieldSize: %s, fieldBitCount: %s' % (fieldType, fieldName, fieldSize, fieldBitCount)
        simpleFieldsData.append({  # TODO: OOP
            'type': fieldType,
            'name': fieldName,
            'size': fieldSize,
            'bitCount': fieldBitCount
        })

    return simpleFieldsData, otherCode


def parseFunctions(defCode):
    functionsData = []
    functionsMatches, otherCode = parseTemplate(defCode, _FUNCTION_PARSE_TEMPLATE)
    for funcType, funcName, funcArgs in functionsMatches:
        functionsData.append({  # TODO: OOP
            'type': funcType,
            'name': funcName,
            'arguments': funcArgs
        })

    return functionsData, otherCode


def addDefenition(defType, defName, defCode):
    currentDefsData = defsData[defType]
    if defCode in currentDefsData:
        return currentDefsData[defCode]

    currentDefsData[defCode] = currentDefData = {
        'type': defType,
        'code': defCode,
        'name': defName,
        'fields': parseDefenition(defName, defCode)
    }

    """
    print '\tAdd {defType} {defName}'.format(
        defType=defType,
        defName=defName
    )
    """
    
    return currentDefData


def parseDefenition(defName, defCode):
    subDefsData, simpleFieldsCode = parseSubDefs(defName, defCode)
    simpleFieldsData, functionsCode = parseSimpleFields(simpleFieldsCode)
    functionsData, otherCode = parseFunctions(functionsCode)

    if otherCode:
        print '\t\tdefName: %s, otherCode: %r' % (defName, otherCode)

    return subDefsData + simpleFieldsData + functionsData


def addDefinitions(rawData, filename):
    matches = re.findall(_DEFINITION_TEMPLATE, rawData, flags=_DEFENITION_FLAGS)
    for (defType, defName, defCode) in matches:
        defName = defName.replace('_anon', '_%s_anon' % filename[:-2])
        defCode = defCode.replace('<unknown fundamental type (0xa510)>', 'void*')

        defData = addDefenition(defType, defName, defCode)


for root, directories, files in os.walk('./'):
    if not root.endswith('/'):
        root += '/'

    for filename in files:
        if not filename.endswith('.c') or filename == _STRUCT_FILE_NAME:
            continue

        path = (root + filename)[len('./'):]
        
        print 'Processing:', path

        sourceData = open(path, 'r').read()
        addDefinitions(sourceData, filename)
        break

defsOrder = sortDefinitions()

raise NotImplementedError('111')        

with open(_STRUCT_FILE_NAME, 'wb') as structsFile:
    for structName in structsData:
        declaration = _DEFINITION_DECLARATION_FMT.format(
            defType='struct',
            defName=structName
        )
        writeNewlined(structsFile, declaration)

    writeRaw(structsFile, '\n\n')
    
    for structName, structData in structsData.iteritems():
        # print 'Struct %s writed' % structName
        writeNewlined(structsFile, structData)

    writeRaw(structsFile, _MAIN_FUNCTION_START)

    for structName in structsData:
        writeNewlined(structsFile, _STRUCT_SIZE_PRINT_FMT.format(structName))
    
    writeRaw(structsFile, _MAIN_FUNCTION_END)

print '---DONE---'
