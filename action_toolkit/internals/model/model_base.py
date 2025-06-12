"""
**model_base.py**

Provides class definition for `ModelBase`, a base class for creating data models and
the `_ModelMeta` metaclass for handling class metadata and typing. Private Utility functions
for dumping and loading models to/from dictionaries and JSON strings are also included, outside
of class definition to avoid expensive refactors.

"""
from collections.abc import Callable, Generator
import dataclasses
import json
from typing import Any, ClassVar, Self, TypeVar, dataclass_transform

from .meta_data import ModelOptions, meta, DATACLASS_KWARGS

T = TypeVar("T", bound="ModelBase")


@dataclass_transform(
    field_specifiers=(meta,),
    kw_only_default=True,
)
class _ModelMeta(type):
    __options__: ClassVar[ModelOptions]
    __custom_flags__: ClassVar[dict[str, Any]]

    def __new__(
        mcls, name: str, bases: tuple[type, ...], ns: dict[str, Any], **kwargs: Any
    ) -> type["_ModelMeta"]:

        opts: ModelOptions = ns.pop("options", ModelOptions())
        if not isinstance(opts, ModelOptions):
            raise TypeError(f"{name}.options must be a ModelOptions instance")

        dataclass_kwargs = {
            k: v
            for k, v in opts.__dict__.items()
            if k in DATACLASS_KWARGS and v is not None
        }
        custom_flags = {
            k: v
            for k, v in opts.__dict__.items()
            if k not in DATACLASS_KWARGS and v is not None
        }

        cls = super().__new__(mcls, name, bases, ns, **kwargs)

        setattr(cls, "__options__", opts)
        setattr(cls, "__custom_flags__", custom_flags)

        return dataclasses.dataclass(**dataclass_kwargs)(cls)


def _get_model_aliases(model: "ModelBase" | type["ModelBase"]) -> dict[str, str]:
    """Get the aliases for the model attributes."""
    if not model.options.serialization_alias_generator:
        return {}

    aliases = {}
    for field in dataclasses.fields(model):
        alias = model.options.serialization_alias_generator(field.name)
        if alias != field.name:
            aliases[field.name] = alias

    return aliases


def _asdict_iterator(
    model: "ModelBase",
    *,
    exclude_attrs: set[str] | None = None,
    exclude_none: bool = False,
    dump_by_alias: bool = False,
    dict_factory: Callable[[list[tuple[str, Any]]], dict[str, Any]] = dict,
) -> Generator[tuple[str, Any], None, None]:
    """Create a dictionary factory for the model."""

    if dump_by_alias and not model.options.serialization_alias_generator:
        raise ValueError(
            "ModelBase: dump_by_alias is True but no alias generator is set in options. Was this a mistake? "
            "\nFix: Set ModelOptions serialization_alias_generator or set dump_by_alias to False."
        )

    model_dict = dataclasses.asdict(model, dict_factory=dict_factory)

    for key, value in model_dict.items():
        if exclude_attrs and key in exclude_attrs:
            continue
        if exclude_none and value is None:
            continue

        if model.options.serialization_alias_generator and dump_by_alias:
            key = model.options.serialization_alias_generator(key)

        yield key, value


def _prepare_loaded_dict(
    model: type["ModelBase"], *, model_dict: dict[str, Any], load_by_alias: bool = False
) -> dict[str, Any]:
    if load_by_alias and not model.options.serialization_alias_generator:
        raise ValueError(
            "ModelBase: load_by_alias is True but no alias generator is set in options. Was this a mistake? "
            "\nFix: Set ModelOptions serialization_alias_generator or set load_by_alias to False."
        )

    if model.options.serialization_alias_generator and load_by_alias:
        alias_list = _get_model_aliases(model)
        for key, alias in alias_list.items():
            if alias in model_dict and key not in model_dict:
                model_dict[key] = model_dict.pop(alias)

    return model_dict


class ModelBase(metaclass=_ModelMeta):

    options: ModelOptions = ModelOptions()

    def dump(
        self,
        *,
        exclude_attrs: set[str] | None = None,
        exclude_none: bool = False,
        dump_by_alias: bool = False,
        dict_factory: Callable[[list[tuple[str, Any]]], dict[str, Any]] = dict,
    ) -> dict[str, Any]:
        """Dump the model to a dictionary."""
        return dict(
            _asdict_iterator(
                self,
                exclude_attrs=exclude_attrs,
                exclude_none=exclude_none,
                dump_by_alias=dump_by_alias,
                dict_factory=dict_factory,
            )
        )

    def json_dumps(
        self,
        *,
        exclude_attrs: set[str] | None = None,
        exclude_none: bool = False,
        dump_by_alias: bool = False,
        dict_factory: Callable[[list[tuple[str, Any]]], dict[str, Any]] = dict,
        **json_dumps_kwargs: Any,
    ) -> str:
        """Dump the model to a JSON string."""
        dumped = self.dump(
            exclude_attrs=exclude_attrs,
            exclude_none=exclude_none,
            dump_by_alias=dump_by_alias,
            dict_factory=dict_factory,
        )
        return json.dumps(dumped, **json_dumps_kwargs)

    @classmethod
    def load(
        cls,
        model_dict: dict[str, Any],
        *,
        load_by_alias: bool = False,
    ) -> Self:
        """Load the model from a dictionary.

        Parameters
        ----------
        model_dict : dict[str, Any]
            _the dictionary to load_
        load_by_alias : bool, optional
            _whether to look to use the alias name as the key
            and to resolve them to the proper attribute_, by default False

        Returns
        -------
        Self
            _description_
        """
        model_kwargs = _prepare_loaded_dict(
            cls, model_dict=model_dict, load_by_alias=load_by_alias
        )
        return cls(**model_kwargs)

    @classmethod
    def json_loads(
        cls,
        json_str: str | bytes | bytearray,
        *,
        load_by_alias: bool = False,
        **json_loads_kwargs: Any,
    ) -> Self:
        """Load the model from a JSON string.

        Parameters
        ----------
        json_str : str | bytes | bytearray
            _the json string_
        load_by_alias : bool, optional
            _load the data by alias_, by default False

        Returns
        -------
        Self
            _the class instance_
        """
        if isinstance(json_str, (bytes, bytearray)):
            json_str = json_str.decode("utf-8")

        model_dict = json.loads(json_str, **json_loads_kwargs)
        return cls.load(model_dict, load_by_alias=load_by_alias)

    def items(
        self,
        *,
        exclude_attrs: set[str] | None = None,
        exclude_none: bool = False,
        use_aliases: bool = False,
        dict_factory: Callable[[list[tuple[str, Any]]], dict[str, Any]] = dict,
    ) -> Generator[tuple[str, Any], None, None]:
        """iterator over the model's attributes.

        Parameters
        ----------
        exclude_attrs : set[str] | None, optional
            _a set of attribute names to ignore,
            warning: do not use alias names_, by default None
        exclude_none : bool, optional
            _exclude attributes with a value of none_, by default False
        use_aliases : bool, optional
            _use the ModelConfig() serialization_alias_generator function
            for the key yielded_, by default False
        dict_factory : Callable[[list[tuple[str, Any]]], dict[str, Any]], optional
            _the dict_factory parameter in dataclasses.asdict()_, by default dict

        Yields
        ------
        Generator[tuple[str, Any], None, None]
            _yields the attribute and attribute value as key value pair
            (attribute_name, attribute_value)_
        """
        """Iterate over the model's attributes."""
        yield from _asdict_iterator(
            self,
            exclude_attrs=exclude_attrs,
            exclude_none=exclude_none,
            dump_by_alias=dump_by_alias,
            dict_factory=dict_factory,
        )

    def as_dict(self) -> dict[str, Any]:
        """Convert the model to a dictionary, without any options
        for instances where you don't want to overhead of preparing
        the model for serialization or deserialization with custom options.

        Returns
        -------
        dict[str, Any]
            _the dumped model_
        """
        return dataclasses.asdict(self)
