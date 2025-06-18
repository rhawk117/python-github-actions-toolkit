


from typing import TypeAlias

CommandPropertyValue: TypeAlias = str | int | float | bool | None
CommandValue: TypeAlias = str | int | float | bool | list | dict | None

YAML_BOOLEAN_TRUE = frozenset(['true', 'yes', 'on', 'y', '1'])
YAML_BOOLEAN_FALSE = frozenset(['false', 'no', 'off', 'n', '0'])

StringOrException: TypeAlias = str | Exception