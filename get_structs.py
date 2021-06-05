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
        if name in _CPP_BUILTIN_NAMES:
            name = '_' + name

        rawType = self.__getRawType(type_)
        typeAlias = defsNameAliases.get(rawType)
        if typeAlias is not None:
            type_ = type_.replace(rawType, typeAlias)

        self.__type = type_
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
    def rawType(self):
        return self.__getRawType(self.__type)

    @rawType.setter
    def rawType(self, value):
        self.__type = self.__type.replace(self.rawType, value)

    @property
    def isPointer(self):
        return '*' in self.__type

    @property
    def name(self):
        return self.__name

    @property
    def fieldType(self):
        raise NotImplementedError

    @staticmethod
    def __getRawType(type_):
        return type_.strip(' *')


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
    _SLOTS = ('type', 'rawType', 'name', 'size', 'bitCount')

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
    _SLOTS = ('type', 'rawType', 'name', 'arguments')

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


_CPP_BUILTIN_NAMES = {
    'new', 'delete', 'typedef', 'enum', 'struct', 'union',
    'char', 'int', 'float', 'double', 'try', 'catch', 'throw'
}

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

defsDataByName = {}
defsDataByTypeAndCode = {}
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
        if not field.isPointer and field.type in defsDataByName
    }

    for fieldName in set(defDeps):
        defDeps |= getDefDependencies(defsDataByName[fieldName])

    defsDeps[defName] = defDeps

    return defDeps


def getDefFieldsCode(defData):
    return ''.join('\t%s\n' % field.code for field in defData['fields']).rstrip()


def getDefCode(defData):
    defDataCopy = defData.copy()
    defDataCopy['fieldsCode'] = getDefFieldsCode(defData)
    return SubDefinition._CODE_FMT.format(**defDataCopy)


def sortDefinitions():
    defsOrder = []

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
        remains = len(defsDataByName) - len(defsOrder)
        if not remains:
            break

        for defData in defsDataByName.itervalues():
            if defData in defsOrder:
                continue
                
            defIndex = getDefIndex(defData)
            if defIndex is not None:
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


def aliasDefName(aliasName, realName):
    if aliasName != realName:
        defsNameAliases[aliasName] = realName
        defsDataByName.pop(aliasName, None)


def addDefinition(defType, name, fieldsCode, enumType=None):
    defData = defsDataByName.get(name)
    if defData is not None:
        return defData

    defData = defsDataByTypeAndCode.get((defType, fieldsCode))
    if defData is not None:
        aliasDefName(name, defData['name'])
        return defData

    subDefsData, simpleFieldsCode = parseSubDefs(name, fieldsCode)

    defData = defsDataByName[name] = defsDataByTypeAndCode[(defType, fieldsCode)] = {
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
        
        print 'Processing:', path

        sourceData = open(path, 'r').read()
        sourceData = sourceData.replace('_anon', '_%s_anon' % filename[:-2])
        sourceData = sourceData.replace('<unknown fundamental type (0xa510)>', 'void*')

        matches, _ = parsePattern(sourceData, _DEFINITION_PATTERN)
        for (defType, defName, enumType, defCode) in matches:
            addDefinition(defType, defName, defCode, enumType)

def postProcessDefinitions():
    defsDataByTypeAndCode.clear()

    # Fields primary parsing
    for defName, defData in defsDataByName.iteritems():
        defData['fields'] += parseDefFields(defData)
        defData['fieldsCode'] = getDefFieldsCode(defData)
        defsDataByTypeAndCode[(defData['type'], defData['fieldsCode'])] = defData

    # Filter all duplicates with same code
    for defName, defData in defsDataByName.items():
        sameCodeDefData = defsDataByTypeAndCode.get((defData['type'], defData['fieldsCode']))
        if sameCodeDefData is not None:
            aliasDefName(defName, sameCodeDefData['name'])

    # Rename all fields type to its real (not aliased) names
    for defData in defsDataByName.values():
        for field in defData['fields']:
            realFieldType = defsNameAliases.get(field.rawType)
            if realFieldType is not None:
                field.rawType = realFieldType

    # Build dependencies tree
    for defName, defData in defsDataByName.iteritems():
        getDefDependencies(defData)

postProcessDefinitions()

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
        writeNewlined(defsFile, getDefCode(defData))
        writeRaw(defsFile, '\n')

    writeRaw(defsFile, _MAIN_FUNCTION_START)

    for defData in sortedDefs:
        if defData['type'] != 'enum':
            writeNewlined(defsFile, _STRUCT_SIZE_PRINT_FMT.format(defData['name']))
    
    writeRaw(defsFile, _MAIN_FUNCTION_END)


print '---DONE---'
