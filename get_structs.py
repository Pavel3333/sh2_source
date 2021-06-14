from common import *


_DEFINITION_DECLARATION_FMT = r'{defType} {defName};'

_HEADER = """
#include <iostream>
#include <fstream>
#include <xmmintrin.h>

#pragma pack(push, 1)
"""

_PRINT_FMT = getIndented(1, r'out << {data} << std::endl;')

_MAIN_FUNCTION_START = """
#pragma pack(pop)

int main() {
    std::ofstream out("out.json", std::ios::binary);
"""

_FIELD_FMT = r'"{indent}\"{fieldName}\": " << {fieldValue} << "{delimiter}"'

_MAIN_FUNCTION_END = """
    out.close();

    std::cout << "Definitions info wroted to \'out.json\'" << std::endl;
    std::cout << "---DONE---" << std::endl;

    return 0;
}
"""


def getDictPrintCode(dictData, indentLevel=0, rawMode=False):
    indent = getIndented(indentLevel, '')
    rawJsonData = '"{"\n'

    dictDataSize = len(dictData)

    for i, (key, value) in enumerate(dictData.iteritems()):
        delimiter = ',' if i != dictDataSize - 1 else ''

        if isinstance(value, dict):
            value = getDictPrintCode(value, indentLevel + 1, rawMode=True)

        rawJsonData += _FIELD_FMT.format(
            indent=getIndented(indentLevel + 1, ''),
            fieldName=key,
            fieldValue=value,
            delimiter=delimiter
        ) + '\n'

    rawJsonData += r'"{indent}}}"'.format(indent=indent)

    if rawMode:
        return rawJsonData

    return ''.join(
        _PRINT_FMT.format(data=line) + '\n'
        for line in rawJsonData.split('\n')
    )

sortedDefs = sortDefinitions()
with open(DEFINITIONS_FILE_NAME, 'wb') as defsFile:
    for defData in sortedDefs:
        declaration = _DEFINITION_DECLARATION_FMT.format(
            defType=defData['type'],
            defName=defData['name']
        )
        writeNewlined(defsFile, declaration)

    writeRaw(defsFile, '\n')
    writeNewlined(defsFile, _HEADER)

    for defData in sortedDefs:
        # print 'Definition %s writed' % defData['name']
        writeNewlined(defsFile, getDefCode(defData))
        writeRaw(defsFile, '\n')

    writeRaw(defsFile, _MAIN_FUNCTION_START)

    defsInfo = {
        defData['name']: {
            'size': 'sizeof({defName})'.format(defName=defData['name']),
            'fieldsOffsets': {
                fieldData.name: 'offsetof({defName}, {fieldName})'.format(
                    defName=defData['name'], fieldName=fieldData.name
                )
                for fieldData in defData['fields']
                if (not fieldData.bitCount if fieldData.fieldType == FieldType.SimpleField else True)
            }
        }
        for defData in sortedDefs
        if defData['type'] != 'enum'
    }

    writeNewlined(defsFile, getDictPrintCode(defsInfo))
    
    writeRaw(defsFile, _MAIN_FUNCTION_END)


print '{fileName} was generated'.format(fileName=DEFINITIONS_FILE_NAME)
print '---DONE---'
