import os
import re
from collections import defaultdict


def writeRaw(fil, data):
    fil.write(data) 


def writeNewlined(fil, data):
    writeRaw(fil, data + '\n') 


def writeIndented(fil, indent, data):
    writeNewlined(fil, ('\t' * indent) + data)


class FieldType:
    SimpleField = 0
    FunctionField = 1
    EnumField = 2


class _BaseDefField(object):
    CODE_PATTERN = None
    _CODE_FMT = None
    _REPR_FMT = None
    _SLOTS = ()

    def __init__(self, type_, name):
        super(_BaseDefField, self).__init__()

        type_ = type_.replace('unsigned long', 'unsigned long long')

        self.__type = (defsNameAliases.get(type_) or type_)
        self.__name = name

    def __iter__(self):
        for slot in self._SLOTS:
            yield slot, getattr(self, slot)

    def __repr__(self):
        return self._REPR_FMT.format(**dict(self))

    @property
    def code(self):
        return self._CODE_FMT.format(**dict(self))

    @property
    def type(self):
        return self.__type

    @property
    def isPointer(self):
        return '*' in self.__type

    @property
    def name(self):
        return self.__name

    @property
    def fieldType(self):
        raise NotImplementedError


class SubDefinition(_BaseDefField):
    CODE_PATTERN = r'^\s*' '(\w+)(\s*:\s*[\w\d ]+\s*)?$.' '\s*' '\{$.' '(.+?)$.' '\s*' '\};$.?'
    _CODE_FMT = '{type} {name}{enumType}\n{{\n{fieldsCode}\n}};'
    _REPR_FMT = 'Definition "{name}" with type "{type}"'

    @property
    def fieldType(self):
        return FieldType.SubDefinition


class SimpleField(_BaseDefField):
    CODE_PATTERN = r'^\s*' '([\w\d *]+)' '\s+' '([\w\d_]+)' '(\s*[\[\d\]]+)*?' '(\s*:\s*[\d]+)?;$.?'
    _CODE_FMT = '{type} {name}{size}{bitCount};'
    _REPR_FMT = 'Field "{name}" with type {type} that have size "{size}" and bit count "{bitCount}"'
    _SLOTS = ('type', 'name', 'size', 'bitCount')

    def __init__(self, type_, name, size=None, bitCount=None):
        super(SimpleField, self).__init__(type_, name)

        self.__size = size or ''
        self.__bitCount = bitCount or ''

    @property
    def fieldType(self):
        return FieldType.SimpleField

    @property
    def size(self):
        return self.__size

    @property
    def bitCount(self):
        return self.__bitCount


class FunctionField(_BaseDefField):
    CODE_PATTERN = r'^\s*' '([\w\d *]+)' '\s*' '\(\*([\w\d ]+)\)' '\s*' '\(([\w\d *,]*)\);$.?'
    _CODE_FMT = '{type}(*{name})({arguments});'
    _REPR_FMT = 'Function "{name}" that returns {type} with arguments ({arguments})'
    _SLOTS = ('type', 'name', 'arguments')

    def __init__(self, type_, name, arguments):
        super(FunctionField, self).__init__(type_, name)

        self.__arguments = arguments

    @property
    def fieldType(self):
        return FieldType.FunctionField

    @property
    def arguments(self):
        return self.__arguments


class EnumField(_BaseDefField):
    CODE_PATTERN = r'^\s*' '([\w\d *]+)' '(\s+=\s*[\w\d_]+)?(\s*,)?$.?'
    _CODE_FMT = '{name}{value}{delimiter}'
    _REPR_FMT = 'Enum field "{name}" with value "{value}"'
    _SLOTS = ('name', 'value', 'delimiter')

    def __init__(self, name, value=None, delimiter=None):
        super(EnumField, self).__init__(type_='', name=name)

        self.__value = value or ''
        self.__delimiter = delimiter or ''

    @property
    def fieldType(self):
        return FieldType.EnumField

    @property
    def value(self):
        return self.__value

    @property
    def delimiter(self):
        return self.__delimiter


_DEFINITIONS_FILE_NAME = 'defs/definitions.cpp'

_DEFINITION_FLAGS = re.MULTILINE | re.DOTALL
_DEFINITION_PATTERN = r'^(\w+) ([\w\d_]+)(\s*:\s*[\w\d ]+\s*)?$.' '\{$.' '(.+?)$.' '\};'
_DEFINITION_DECLARATION_FMT = r'{defType} {defName};'

_MAIN_FUNCTION_START = """
#include <iostream>
#include <fstream>

int main() {
    std::ofstream out("out.json", std::ios::binary);
    out << "{" << std::endl << std::hex;
"""

_STRUCT_SIZE_PRINT_FMT = (' ' * 4) + r'out << "    \"{0}\": 0x" << sizeof({0}) << "," << std::endl;'

_MAIN_FUNCTION_END = """
    out << "}";
    out.close();

    std::cout << "Struct sizes wroted to \'out.json\'" << std::endl;
    std::cout << "---DONE---" << std::endl;

    return 0;
}
"""

defsData = defaultdict(dict)
defsDataByNames = {}
defsDeps = {}
defsNameAliases = {}


def getDefDependencies(defData):
    defName = defData['name']
    defDeps = defsDeps.get(defName)
    if defDeps is not None:
        return defDeps

    defDeps = {
        field.type
        for field in defData['fields']
        if not field.isPointer and field.type in defsDataByNames
    }
    # print defData['name'], defDeps

    for fieldName in set(defDeps):
        defDeps |= getDefDependencies(defsDataByNames[fieldName])

    defsDeps[defName] = defDeps

    return defDeps


def sortDefinitions():
    defsOrder = []
    for defsType, currentDefsData in defsData.iteritems():
        for defData in currentDefsData.itervalues():
            getDefDependencies(defData)

    def getDefIndex(defData):
        defName = defData['name']
        defDeps = defsDeps[defName]
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
        remains = len(defsDataByNames) - len(defsOrder)
        if not remains:
            break

        # print '\tremains:', remains

        for defData in defsDataByNames.itervalues():
            if defData in defsOrder:
                continue
                
            defIndex = getDefIndex(defData)
            if defIndex is not None:
                # print '\t\tadd {name} by index {index}'.format(name=defData['name'], index=defIndex)
                defsOrder.insert(defIndex, defData)

    return defsOrder


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


def addDefinition(defType, name, fieldsCode, enumType=None):
    currentDefsData = defsData[defType]

    defData = defsDataByNames.get(name) or currentDefsData.get(fieldsCode)
    if defData is not None:
        defName = defData['name']
        if name != defName:
            defsNameAliases[name] = defName

        return defData

    subDefsData, simpleFieldsCode = parseSubDefs(name, fieldsCode)

    defData = currentDefsData[fieldsCode] = defsDataByNames[name] = {
        'type': defType,
        'enumType': enumType or '',
        'name': name,
        'fields': subDefsData,
        'fieldsCode': simpleFieldsCode
    }

    """
    print '\tAdd {defType} {defName}'.format(
        defType=defType,
        defName=defName
    )
    """
    
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


for root, directories, files in os.walk('./'):
    if not root.endswith('/'):
        root += '/'

    for filename in files:
        if not filename.endswith('.c') or filename == _DEFINITIONS_FILE_NAME:
            continue

        path = (root + filename)[len('./'):]
        
        # print 'Processing:', path

        sourceData = open(path, 'r').read()
        sourceData = sourceData.replace('_anon', '_%s_anon' % filename[:-2])
        sourceData = sourceData.replace('<unknown fundamental type (0xa510)>', 'void*')

        matches, _ = parsePattern(sourceData, _DEFINITION_PATTERN)
        for (defType, defName, enumType, defCode) in matches:
            addDefinition(defType, defName, defCode, enumType)
        break

for defsType, currentDefsData in defsData.iteritems():
    for defData in currentDefsData.values():
        defData['fields'] = defData['fields'] + parseDefFields(defData)

sortedDefs = sortDefinitions()
with open(_DEFINITIONS_FILE_NAME, 'wb') as defsFile:
    for defData in sortedDefs:
        declaration = _DEFINITION_DECLARATION_FMT.format(
            defType=defData['type'],
            defName=defData['name']
        )
        writeNewlined(defsFile, declaration)

    writeRaw(defsFile, '\n')

    for defData in sortedDefs:
        # print 'Definition %s writed' % defData['name']
        reprDefData = defData.copy()
        reprDefData['fieldsCode'] = ''.join('\t%s\n' % field.code for field in defData['fields']).rstrip()
        writeNewlined(defsFile, SubDefinition._CODE_FMT.format(**reprDefData))
        writeRaw(defsFile, '\n')

    writeRaw(defsFile, _MAIN_FUNCTION_START)

    for defData in sortedDefs:
        if defData['type'] != 'enum':
            writeNewlined(defsFile, _STRUCT_SIZE_PRINT_FMT.format(defData['name']))
    
    writeRaw(defsFile, _MAIN_FUNCTION_END)


print '---DONE---'
