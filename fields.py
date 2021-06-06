defsNameAliases = {}

_CPP_BUILTIN_NAMES = {
    'new', 'delete', 'typedef', 'enum', 'struct', 'union',
    'char', 'int', 'float', 'double', 'try', 'catch', 'throw'
}


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
    _REPR_FMT = 'Field "{name}" with type "{type}" that have size "{size}" and bit count "{bitCount}"'
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
