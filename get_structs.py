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
_SUBDEF_TEMPLATE = r'^\s*(\w+)$.' '\s*\{$.' '(.+?)$.' '\s*\};'

_STRUCT_FIELD_PARSE_TEMPLATE = r'^\s+' '([\w\d *]+) ([\w\d]+)' '\s*' '([\[\d\]]+)?' '\s*' '(:\s*[\d]+)?;'

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

def addDefenition(defType, defName, defCode):
    currentDefsData = defsData[defType]
    if defCode in currentDefsData:
        return

    currentDefsData[defCode] = currentDefData = {
        'name': defName
    }
    
    # yield defType, defCode, currentDefData

    print '\tAdd {defType} {defName}'.format(
        defType=defType,
        defName=defName
    )

def addDefinitions(rawData, filename):
    matches = re.findall(_DEFINITION_TEMPLATE, rawData, flags=_DEFENITION_FLAGS)
    for (defType, defName, defCode) in matches:
        defName = defName.replace('_anon', '_%s_anon' % filename[:-2])
        defCode = defCode.replace('<unknown fundamental type (0xa510)>', 'void*')

        addDefenition(defType, defName, defCode)
        addSubDefinitions(defName, defCode)

def addSubDefinitions(defName, defCode):
    matches = re.findall(_SUBDEF_TEMPLATE, defCode, flags=_DEFENITION_FLAGS)
    for i, (subDefType, subDefCode) in enumerate(matches):
        subDefName = '%s_%s_%d' % (defName, subDefType, i)
        subDefCode = subDefCode.replace('<unknown fundamental type (0xa510)>', 'void*')

        addDefenition(subDefType, subDefName, subDefCode)

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
        

        match = re.match(_STRUCT_FIELD_PARSE_TEMPLATE, line)
        if match:
            structsFields[structName].append({  # TODO: OOP
                'type': match.group(1),
                'name': match.group(2),
                'count': match.group(3),
                'bitCount': match.group(4)
            })
            """
            print '\ttype: %s, name: %s, count: %s, bit count: %s' % (
                match.group(1),
                match.group(2),
                match.group(3),
                match.group(4)
            )
            """
            continue

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
