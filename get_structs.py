from common import *


def getString(data):
    return '"{data}"'.format(data=data.replace('"', '\\"'))

class CppSourceWriter(object):
    _OUT_FILE = 'out.json'
    _OUT_IO = 'out'
    _COUT_IO = 'std::cout'
    _NEWLINE = 'std::endl'

    _INCLUDES = ('iostream', 'fstream', 'xmmintrin.h')

    _INCLUDE_FMT = r'#include <{header}>'
    _PRAGMA_FMT = r'#pragma {pragmaType}({pragmaArgs})'
    _DEFINITION_DECLARATION_FMT = r'{defType} {defName};'
    _FIELD_FMT = r'"{indent}{fieldName}: " << {fieldValue} << {delimiter}'

    def __init__(self, sourceName):
        super(CppSourceWriter, self).__init__()

        self.__file = None
        self.__indentLevel = 0
        self.__sortedDefs = {}
        self.__sourceName = sourceName

    def __enter__(self):
        self.__file = open(self.__sourceName, 'wb')
        self.__indentLevel = 0
        self.__sortedDefs = sortDefinitions()

        return self

    def __exit__(self, *args):
        self.__file.close()
        self.__file = None
        self.__sortedDefs = {}

        print '{fileName} was generated'.format(fileName=self.__sourceName)
        print '---DONE---'

    def write(self, data, newLined=True, indentLevel=None):
        write(
            self.__file, data,
            newLined=newLined,
            indentLevel=indentLevel or self.__indentLevel
        )

    def newLine(self):
        self.write('', indentLevel=0)

    def pragma(self, pragmaType, pragmaArgs):
        self.write(self._PRAGMA_FMT.format(
            pragmaType=pragmaType, pragmaArgs=pragmaArgs
        ))

    def addIncludes(self):
        for headerFileName in self._INCLUDES:
            self.__include(headerFileName)

    def addDefsDeclarations(self):
        for defData in self.__sortedDefs:
            self.__addDefDeclaration(defData)

    def addDefs(self):
        for defData in self.__sortedDefs:
            self.__addDef(defData)

    def startMain(self):
        self.write('int main() {')
        self.__indentLevel += 1
        self.write('std::ofstream {outIO}({outFile}, std::ios::binary);'.format(
            outIO=self._OUT_IO,
            outFile=getString(self._OUT_FILE)
        ))

    def outFileWrite(self, data):
        self.__ioWrite(self._OUT_IO, data)

    def coutWrite(self, data):
        self.__ioWrite(self._COUT_IO, data)

    def endMain(self):
        self.write('out.close();')
        self.newLine()
        self.coutWrite(getString('Definitions info wroted to "{outFile}"'.format(outFile=self._OUT_FILE)))
        self.coutWrite(getString('---DONE---'))
        self.newLine()
        self.write('return 0;')
        self.__indentLevel -= 1
        self.write('}')

    def __addDefDeclaration(self, defData):
        self.write(self._DEFINITION_DECLARATION_FMT.format(
            defType=defData['type'],
            defName=defData['name']
        ))

    def __addDef(self, defData):
        self.write(getDefCode(defData))
        self.newLine()

        # print 'Definition {defName} writed'.format(defName=defData['name'])

    def __include(self, header):
        self.write(self._INCLUDE_FMT.format(header=header))

    def __ioWrite(self, io, data):
        self.write(' << '.join((io, data, self._NEWLINE)) + ';')


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
            delimiter=getString(delimiter)
        ) + '\n'

    rawJsonData += r'"{indent}}}"'.format(indent=indent)

    if rawMode:
        return rawJsonData

    return ''.join(
        _PRINT_FMT.format(data=line) + '\n'
        for line in rawJsonData.split('\n')
    )

"""
defsInfo = {
    getString(defData['name']): {
        getString('size'): 'sizeof({defName})'.format(defName=defData['name']),
        getString('fieldsOffsets'): {
            'offsetof({defName}, {fieldName})'.format(
                defName=defData['name'],
                fieldName=fieldData.name
            ): fieldData.name
            for fieldData in defData['fields']
            if (not fieldData.bitCount if fieldData.fieldType == FieldType.SimpleField else True)
        }
    }
    for defData in sortedDefs
    if defData['type'] != 'enum'
}

writeNewlined(defsFile, getDictPrintCode(defsInfo))
"""

with CppSourceWriter(DEFINITIONS_FILE_NAME) as source:
    source.addIncludes()
    source.newLine()
    source.addDefsDeclarations()
    source.newLine()
    source.pragma('pack', 'push, 1')
    source.newLine()
    source.addDefs()
    source.newLine()
    source.pragma('pack', 'pop')
    source.newLine()
    source.startMain()


    source.endMain()
