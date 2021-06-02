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

_STRUCT_DEF_TEMPLATE = r'typedef struct ([\w\d_]+);$'
_STRUCT_START_TEMPLATE = r'^struct ([\w\d_]+)$'
_STRUCT_END_TEMPLATE = r'^\};$'
_STRUCT_FIELD_PARSE_TEMPLATE = r'^\s+([\w\d *]+) ([\w\d]+)\s*([\[\d\]]+)?\s*(:\s*[\d]+)?;'
_SUBSTRUCT_START_TEMPLATE_1 = r'^\s*struct\s*$'
_SUBSTRUCT_START_TEMPLATE_2 = r'^\s*{\s*$'
_SUBSTRUCT_END_TEMPLATE = r'^\s*};\s*$'
_FUNCTION_PARSE_TEMPLATE = r'^\s*([\w\d *]+)\(\*([\w\d ]+)\)\(([\w\d *,]+)\);'

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


def isSubstructureContent(line):
    return not any(
        re.match(template, line)
        for template in (
            _SUBSTRUCT_START_TEMPLATE_1,
            _SUBSTRUCT_START_TEMPLATE_2,
            _SUBSTRUCT_END_TEMPLATE
        )
    )


structsDefs = set()
structsData = {}
structsFields = defaultdict(list)
functions = defaultdict(list)
structsOrder = []

def sortStructFields():
    fields = structsFields.copy()
    for structName in fields.keys():
        print 'structName:', structName
        fieldsData = fields.pop(structName)
        for fieldData in fieldsData:
            print '\tname:', fieldData['name']
            print '\ttype:', fieldData['type']
            

for root, directories, files in os.walk('./'):
    if not root.endswith('/'):
        root += '/'

    for filename in files:
        if not filename.endswith('.c') or filename == _STRUCT_FILE_NAME:
            continue

        path = (root + filename)[len('./'):]
        
        print 'Processing:', path

        lastFoundStructName = None
        lastFoundStructData = ''

        with open(path, 'r') as source:
            for line in source:
                preparedLine = line.replace('_anon', '_%s_anon' % filename[:-2]).replace('<unknown fundamental type (0xa510)>', 'void')
                
                if lastFoundStructName is not None:
                    lastFoundStructData += preparedLine
                    
                    endMatch = re.match(_STRUCT_END_TEMPLATE, preparedLine)
                    if endMatch is not None:
                        # print '\tStruct %s ended' % lastFoundStructName
                        structsData[lastFoundStructName] = lastFoundStructData
                        lastFoundStructName = None
                else:
                    defMatch = re.match(_STRUCT_DEF_TEMPLATE, preparedLine)
                    if defMatch is not None:
                        structsDefs.add(preparedLine)
                        continue
                    
                    startMatch = re.match(_STRUCT_START_TEMPLATE, preparedLine)
                    if startMatch is None:
                        continue

                    foundStructName = startMatch.group(1)
                    if foundStructName in structsData:
                        continue

                    # print '\tStruct %s started' % foundStructName
                    lastFoundStructName = foundStructName
                    lastFoundStructData = preparedLine


for structName, structData in structsData.iteritems():
    # print 'structName:', structName 
    for line in structData.split('\n')[1:-1]:
        if not isSubstructureContent(line):  # TODO: union / enum processing
            continue

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
    for structDef in sorted(structsDefs):
        writeRaw(structsFile, structDef)

    writeRaw(structsFile, '\n\n')
    
    for structName, structData in structsData.iteritems():
        print 'Struct %s writed' % structName
        writeNewlined(structsFile, structData)

    writeRaw(structsFile, _MAIN_FUNCTION_START)

    for structName in structsData:
        writeNewlined(structsFile, _STRUCT_SIZE_PRINT_FMT.format(structName))
    
    writeRaw(structsFile, _MAIN_FUNCTION_END)

print '---DONE---'
