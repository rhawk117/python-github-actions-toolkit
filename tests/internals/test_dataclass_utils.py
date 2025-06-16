'''Tests for action_toolkit.internals.dataclass_utils module'''

import json
from dataclasses import dataclass

import pytest
from action_toolkit.internals.dataclass_utils import (
    dump_dataclass,
    iter_dataclass_dict,
    json_dumps_dataclass,
    iter_dataclass,
)


@dataclass
class SampleDataclass:
    '''Sample dataclass for testing'''
    name: str
    age: int
    email: str | None = None
    active: bool = True


class TestDumpDataclass:
    '''Test cases for dump_dataclass function'''

    def test_basic_dump(self) -> None:
        '''Test basic dataclass to dict conversion'''
        obj = SampleDataclass(name="John", age=30, email="john@example.com")
        result = dump_dataclass(obj)

        assert result == {
            'name': 'John',
            'age': 30,
            'email': 'john@example.com',
            'active': True
        }

    def test_exclude_none(self) -> None:
        '''Test excluding None values'''
        obj = SampleDataclass(name="Jane", age=25, email=None)
        result = dump_dataclass(obj, exclude_none=True)

        assert result == {
            'name': 'Jane',
            'age': 25,
            'active': True
        }
        assert 'email' not in result

    def test_exclude_fields(self) -> None:
        '''Test excluding specific fields'''
        obj = SampleDataclass(name="Bob", age=40, email="bob@example.com")
        result = dump_dataclass(obj, exclude={'age', 'active'})

        assert result == {
            'name': 'Bob',
            'email': 'bob@example.com'
        }

    def test_exclude_both(self) -> None:
        '''Test excluding both None values and specific fields'''
        obj = SampleDataclass(name="Alice", age=35, email=None)
        result = dump_dataclass(obj, exclude_none=True, exclude={'active'})

        assert result == {
            'name': 'Alice',
            'age': 35
        }


class TestIterDataclassDict:
    '''Test cases for iter_dataclass_dict function'''

    def test_basic_iteration(self):
        '''Test basic iteration over dataclass fields'''
        obj = SampleDataclass(name="Test", age=20, email="test@test.com")
        items = list(iter_dataclass_dict(obj))

        expected = [
            ('name', 'Test'),
            ('age', 20),
            ('email', 'test@test.com'),
            ('active', True)
        ]

        assert items == expected

    def test_exclude_none_iteration(self):
        '''Test iteration excluding None values'''
        obj = SampleDataclass(name="Test", age=20, email=None)
        items = list(iter_dataclass_dict(obj, exclude_none=True))

        assert len(items) == 3
        assert ('email', None) not in items

    def test_exclude_fields_iteration(self):
        '''Test iteration excluding specific fields'''
        obj = SampleDataclass(name="Test", age=20, email="test@test.com")
        items = list(iter_dataclass_dict(obj, exclude={'age', 'email'}))

        assert len(items) == 2
        assert items == [('name', 'Test'), ('active', True)]


class TestJsonDumpsDataclass:
    '''Test cases for json_dumps_dataclass function'''

    def test_basic_json_dump(self):
        '''Test basic JSON serialization'''
        obj = SampleDataclass(name="JSON Test", age=30, email="json@test.com")
        result = json_dumps_dataclass(obj)

        parsed = json.loads(result)
        assert parsed == {
            'name': 'JSON Test',
            'age': 30,
            'email': 'json@test.com',
            'active': True
        }

    def test_json_dump_exclude_none(self) -> None:
        '''Test JSON serialization excluding None'''
        obj = SampleDataclass(name="JSON Test", age=30, email=None)
        result = json_dumps_dataclass(obj, exclude_none=True)

        parsed = json.loads(result)
        assert 'email' not in parsed




class TestIterDataclass:
    '''Test cases for iter_dataclass function'''

    def test_basic_field_iteration(self):
        '''Test basic iteration over all fields'''
        obj = SampleDataclass(name="Iter Test", age=45, email=None)
        items = list(iter_dataclass(obj))

        assert len(items) == 4
        assert items == [
            ('name', 'Iter Test'),
            ('age', 45),
            ('email', None),
            ('active', True)
        ]

    def test_nested_dataclass(self) -> None:
        '''Test with nested dataclasses'''
        @dataclass
        class Address:
            street: str
            city: str

        @dataclass
        class Person:
            name: str
            address: Address

        addr = Address(street="123 Main St", city="Anytown")
        person = Person(name="Test Person", address=addr)

        items = list(iter_dataclass(person))
        assert len(items) == 2
        assert items[0] == ('name', 'Test Person')
        assert items[1][0] == 'address'
        assert isinstance(items[1][1], Address)