'''
**alias_generators.py**

Contains functions to convert strings between different naming conventions for
alias generation in data models.

'''
import re
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from .types import AliasFn, AliasTypes


def snake_case(string: str) -> str:
    '''
    Converts strings from camelCase or PascalCase to snake_case format.

    Parameters
    ----------
    string : str
        The original string in camelCase or PascalCase format

    Returns
    -------
    str
        The string converted to snake_case format

    Examples
    --------
    Basic camelCase conversion:
    >>> snake_case("firstName")
    'first_name'
    >>> snake_case("lastName")
    'last_name'

    Handling acronyms and multiple capitals:
    >>> snake_case("XMLHttpRequest")
    'xml_http_request'
    >>> snake_case("ID")
    'id'
    '''
    step1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", string)
    step2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", step1)
    return step2.lower()


def camel_case(string: str) -> str:
    '''
    Converts a string from snake_case to camelCase

    Parameters
    ----------
    string : str
        The original string in snake_case format

    Returns
    -------
    str
        The string converted to camelCase format

    Examples
    --------
    Basic snake_case conversion:
    >>> camel_case("first_name")
    'firstName'
    >>> camel_case("last_name")
    'lastName'

    Multiple word conversion:
    >>> camel_case("user_profile_image")
    'userProfileImage'
    >>> camel_case("name")
    'name'
    '''
    components = string.split("_")
    return components[0] + "".join(word.capitalize() for word in components[1:])

def kebab_case(string: str) -> str:
    '''
    Converts a string to kebab-case format used in HTML, URLs and YML
    handling both snake_case and camelCase input formats.

    Parameters
    ----------
    string : str
        The original string in snake_case or camelCase format

    Returns
    -------
    str
        The string converted to kebab-case format

    Example
    --------
    Snake case conversion:
    >>> kebab_case("first_name")
    'first-name'
    '''
    return snake_case(string).replace("_", "-")

def pascal_case(string: str) -> str:
    '''
    Converts a name from snake_case to PascalCase.

    This function transforms strings from Python's snake_case convention
    to PascalCase (also known as UpperCamelCase), where the first letter of
    each word is capitalized. This format is commonly used in C# properties,
    class names, and some XML schemas.

    Parameters
    ----------
    string : str
        The original string in snake_case format

    Returns
    -------
    str
        The string converted to PascalCase format

    Examples
    --------
    Basic conversion:
    >>> pascal_case("first_name")
    'FirstName'
    >>> pascal_case("last_name")
    'LastName'

    Multiple words:
    >>> pascal_case("user_profile_image")
    'UserProfileImage'
    >>> pascal_case("api_response_data")
    'ApiResponseData'

    Single words:
    >>> pascal_case("name")
    'Name'
    >>> pascal_case("id")
    'Id'
    '''
    components = string.split("_")
    return "".join(word.capitalize() for word in components)


ALIAS_MAP: Final[dict[str, AliasFn]] = {
    'snake': snake_case,
    'camel': camel_case,
    'kebab': kebab_case,
    'pascal': pascal_case
}

def get_alias_generator(alias_type: str | AliasTypes) -> AliasFn:
    '''
    Resolves the `AliasType` to its corresponding alias generator
    function.

    Parameters
    ----------
    alias_type : AliasType | str
        The alias type to get the generator for.

    Returns
    -------
    AliasFn
        The alias generator function.

    Raises
    ------
    ValueError
        If the alias type is not supported.
    '''
    if alias_type not in ALIAS_MAP:
        raise ValueError(
            f"unsupported alias type: {alias_type}\n"
            "Supported types are: "
            f"{','.join(map(str, ALIAS_MAP.keys()))}"
        )
    return ALIAS_MAP[alias_type]

__all__ = ['get_alias_generator']