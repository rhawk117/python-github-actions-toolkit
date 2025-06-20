from typing import TypeAlias


YAML_BOOLEAN_TRUE = frozenset(['true', 'yes', 'on', 'y', '1'])
YAML_BOOLEAN_FALSE = frozenset(['false', 'no', 'off', 'n', '0'])

StringOrException: TypeAlias = str | Exception
