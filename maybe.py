from typing import TypeVar, Generic, Union, Callable, Any

T = TypeVar('T')
A = TypeVar('A')
B = TypeVar('A')

class Maybe(Generic[T]):
    def __init__(self) -> None:
        self.val = None # type: T

    def __repr__(self) -> str:
        return f'Maybe({self.val!r})'

    def map(self, f: Callable[[T], A]) -> 'Maybe[A]':
        return self

    def bind(self, f: Callable[[T], 'Maybe[A]']) -> 'Maybe[A]':
        return self

    def otherwise(self, f: Callable[[], 'Maybe[A]']) -> 'Maybe[A]':
        return f()

    def isEmpty(self) -> bool:
        return True

    def isNonEmpty(self) -> bool:
        return False

    def get(self) -> T:
        raise TypeError("get on Nothing")

    def getDefault(self, default: T) -> T:
        return default

    def getElse(self, getDefault: Callable[[], T]) -> T:
        return getDefault()

    def either(self, j: Callable[[T], A], n: Callable[[], A]) -> A:
        return n()

class Just(Maybe):
    def __init__(self, val: T) -> None:
        self.val = val

    def __repr__(self) -> str:
        return f'Just({self.val!r})'

    def map(self, f: Callable[[T], A]) -> Maybe[A]:
        return Just(f(self.val))

    def bind(self, f: Callable[[T], Maybe[A]]) -> Maybe[A]:
        return f(self.val)

    def otherwise(self, f: Callable[[], 'Maybe[A]']) -> 'Maybe[A]':
        return self

    def isEmpty(self) -> bool:
        return False

    def isNonEmpty(self) -> bool:
        return True

    def get(self) -> T:
        return self.val

    def getDefault(self, default: T) -> T:
        return self.val

    def getElse(self, getDefault: Callable[[], T]) -> T:
        return self.val

    def either(self, j: Callable[[T], A], n: Callable[[], A]) -> A:
        return j(self.val)

class Nothing(Maybe):
    def __repr__(self) -> str:
        return 'Nothing'

