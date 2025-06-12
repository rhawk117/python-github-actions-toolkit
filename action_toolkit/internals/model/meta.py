from typing import Any, Self
from .options import ModelConfig



def has_model_interface_method(cls: type) -> bool:
    '''Check if the class has a method indicating it is a model interface
    (i.e it has the attribute `_is_model_interface`).

    Parameters
    ----------
    cls : type
        _class to check_

    Returns
    -------
    bool
    '''
    return hasattr(cls, '_is_model_interface')


def cls_name_is_model_interface(cls: type) -> bool:
    '''Check if the class name is 'ModelInterface'.

    Parameters
    ----------
    cls : type
        _the class to check_

    Returns
    -------
    bool
    '''
    return hasattr(cls, '__name__') and cls.__name__ == 'ModelInterface'


def is_model_interface_class(cls: type) -> bool:
    '''Check if a class is a model interface class.

    Parameters
    ----------
    cls : type
        _class to check_

    Returns
    -------
    bool
    '''
    return has_model_interface_method(cls) or cls_name_is_model_interface(cls)

def inherits_from_model_interface(bases: tuple[type, ...]) -> bool:
    if not bases:
        return False

    for base in bases:
        if not hasattr(base, '__mro__'):
            continue

        try:
            if is_model_interface_class(base):
                return True

            for mro_class in base.__mro__:
                if is_model_interface_class(mro_class):
                    return True

        except (AttributeError, TypeError):
            continue

    return False



def _resolve_model_config(cls: type, bases: tuple[type, ...]) -> ModelConfig:
    '''Attempts to resolve the ModelConfig for a model interface class by
    checking the class hierarchy for a parent with an initialized `model_config`
    attribute and returns the first one it finds, if none are found it returns
    a new `ModelConfig` instance.

    Parameters
    ----------
    cls : type
        _the class to traverse_
    bases : tuple[type, ...]
        _the classes bases_

    Returns
    -------
    ModelConfig
        _the resolved model configuration_
    '''
    config: ModelConfig = getattr(cls, 'model_config', None) # type: ignore[assignment]
    if config:
        return config

    for base in bases:
        parent_model_config = getattr(base, 'model_config', None)
        if parent_model_config:
            return parent_model_config

    return ModelConfig()

class ModelInterfaceMeta(type):
    '''Metaclass that automatically applies dataclass decorator with configuration.'''

    def __new__(
        mcs,
        name,
        bases,
        namespace,
        **kwargs
    ) -> Any | Self:
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        if cls_name_is_model_interface(cls):
            return cls

        
