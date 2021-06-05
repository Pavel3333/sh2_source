from common import *


_DEFINITION_DECLARATION_FMT = r'{defType} {defName};'

_MAIN_FUNCTION_START = """
#include <iostream>
#include <fstream>

int main() {
    std::ofstream out("out.json", std::ios::binary);
    out << "{" << std::endl;
"""

_STRUCT_SIZE_PRINT_FMT = (' ' * 4) + r'out << "    \"{defName}\": " << sizeof({defName}) << "{delimiter}" << std::endl;'

_MAIN_FUNCTION_END = """
    out << "}";
    out.close();

    std::cout << "Struct sizes wroted to \'out.json\'" << std::endl;
    std::cout << "---DONE---" << std::endl;

    return 0;
}
"""


def getDefCode(defData):
    defDataCopy = defData.copy()
    defDataCopy['fieldsCode'] = getDefFieldsCode(defData)
    return SubDefinition._CODE_FMT.format(**defDataCopy)


sortedDefs = sortDefinitions()
with open(DEFINITIONS_FILE_NAME, 'wb') as defsFile:
    for defData in sortedDefs:
        declaration = _DEFINITION_DECLARATION_FMT.format(
            defType=defData['type'],
            defName=defData['name']
        )
        writeNewlined(defsFile, declaration)

    writeRaw(defsFile, '\n')

    for defData in sortedDefs:
        # print 'Definition %s writed' % defData['name']
        writeNewlined(defsFile, getDefCode(defData))
        writeRaw(defsFile, '\n')

    writeRaw(defsFile, _MAIN_FUNCTION_START)

    sortedDefsCount = len(sortedDefs)
    for i, defData in enumerate(sortedDefs):
        if defData['type'] != 'enum':
            writeNewlined(defsFile, _STRUCT_SIZE_PRINT_FMT.format(
                defName=defData['name'],
                delimiter=',' if i != sortedDefsCount - 1 else ''
            ))
    
    writeRaw(defsFile, _MAIN_FUNCTION_END)


print '{fileName} was generated'.format(fileName=DEFINITIONS_FILE_NAME)
print '---DONE---'
