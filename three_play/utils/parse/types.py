__all__ = ['as_bool',
           'as_int']

from typing import Union, Any, Type


def as_bool(o: Union[str, bool], default=False):
    """
    Return `o` if already a boolean, otherwise return the boolean value for a
    string. If `o` is None or an empty string, return `default` instead.

    """
    if isinstance(o, bool):
        return o

    if not o:
        return default

    return o.upper() == 'TRUE'


def as_type(o: Any, _type: Type = str, default=None, raise_=True):
    if isinstance(o, _type):
        return o

    if not o:
        return default

    try:
        return _type(o)
    except ValueError:
        if raise_:
            raise
        return default


def as_int(o: Union[str, int], default=0, raise_=True):
    """
    Return `o` if already a int, otherwise return the int value for a
    string. If `o` is None or an empty string, return `default` instead.

    If `o` cannot be converted to an int, raise an error if `raise_` is true,
    other return `default` instead.

    """
    return as_type(o, int, default, raise_)
