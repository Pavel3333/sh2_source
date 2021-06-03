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
_SUBDEF_TEMPLATE = r'^\s*(\w+)$.' '\s*\{$.' '(.+?)$.' '\s*\};$.?'

_FUNCTION_PARSE_TEMPLATE = r'^\s*([\w\d *]+)\(\*([\w\d ]+)\)\(([\w\d *,]+)\);'

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
structsFields = defaultdict(list)
functions = defaultdict(list)

def sortStructFields():
    structsOrder = []
    fields = structsFields.copy()
    for structName in fields.keys():
        structIndex = 0
        # print 'structName:', structName
        fieldsData = fields.pop(structName)
        for fieldData in fieldsData:
            fieldRawType = fieldData['type'].strip(' *')
            if fieldRawType in structsOrder:
                structIndex = max(structIndex, structsOrder.index(fieldRawType))

        # print '\tstructIndex:', structIndex
        structsOrder.insert(structIndex, structName)

def parseSubDefs(defName, defCode):
    subDefsData = []
    subDefsMatches = re.findall(_SUBDEF_TEMPLATE, defCode, flags=_DEFENITION_FLAGS)
    otherCode = re.sub(_SUBDEF_TEMPLATE, '', defCode, flags=_DEFENITION_FLAGS)
    for i, (subDefType, subDefCode) in enumerate(subDefsMatches):
        subDefName = '%s_%s_%d' % (defName, subDefType, i)
        subDefData = addDefenition(subDefType, subDefName, subDefCode)
        if subDefData is not None:
            subDefsData.append(subDefData)

    return subDefsData, otherCode


def parseSimpleFields(defCode):
    simpleFieldsData = []
    simpleFieldsMatches = re.findall(_DEFENITION_FIELD_TEMPLATE, defCode, flags=_DEFENITION_FLAGS)
    otherCode = re.sub(_DEFENITION_FIELD_TEMPLATE, '', defCode, flags=_DEFENITION_FLAGS)
    for fieldType, fieldName, fieldSize, fieldBitCount in simpleFieldsMatches:
        # print '\t\tfieldType: %s, fieldName: %s, fieldSize: %s, fieldBitCount: %s' % (fieldType, fieldName, fieldSize, fieldBitCount)
        simpleFieldsData.append({  # TODO: OOP
            'type': fieldType,
            'name': fieldName,
            'size': fieldSize,
            'bitCount': fieldBitCount
        })

    return simpleFieldsData, otherCode


def addDefenition(defType, defName, defCode):
    currentDefsData = defsData[defType]
    if defCode in currentDefsData:
        return None

    currentDefsData[defCode] = currentDefData = {
        'type': defType,
        'code': defCode,
        'name': defName,
        'fields': []
    }

    # print '\tAdd {defType} {defName}'.format(
    #     defType=defType,
    #     defName=defName
    # )
    
    return currentDefData

def parseDefenition(defName, defCode):
    subDefsData, simpleFieldsCode = parseSubDefs(defName, defCode)
    simpleFieldsData, otherCode = parseSimpleFields(simpleFieldsCode)

    if otherCode:
        print '\t\tdefName: %s, otherCode: %r' % (defName, otherCode)

    return subDefsData + simpleFieldsData

def addDefinitions(rawData, filename):
    matches = re.findall(_DEFINITION_TEMPLATE, rawData, flags=_DEFENITION_FLAGS)
    for (defType, defName, defCode) in matches:
        defName = defName.replace('_anon', '_%s_anon' % filename[:-2])
        defCode = defCode.replace('<unknown fundamental type (0xa510)>', 'void*')

        defData = addDefenition(defType, defName, defCode)
        if defData is None:
            continue

        defData['fields'].extend(parseDefenition(defName, defCode))

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


raise NotImplementedError('111')
for structName, defData in defsData.iteritems():
    # print 'structName:', structName 
    for line in structData.split('\n')[1:-1]:
        match = re.match(_FUNCTION_PARSE_TEMPLATE, line)
        if match:
            functions[structName].append({  # TODO: OOP
                'returnType': match.group(1),
                'name': match.group(2),
                'arguments': match.group(3)
            })
            """
            print '\treturn type: %s, name: %s, arguments: (%s)' % (
                match.group(1),
                match.group(2),
                match.group(3)
            )
            """
            continue
        print '\t' + line

sortStructFields()        

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
