from copy import copy
from typing import Any, Generic, Iterable, List, Sequence, T, Union

from numpy import int32, int64


class DoublyLinkedList(Sequence[T]):
    """
    A linked list is a series of node objects, each with a link (object reference) to the next node in the series.
    The majority of the list is only accessible by starting at the first node ("head") and following the links forward.

    node_1 (head) -> node_2 -> node_3

    A doubly-linked list is similar to a linked list, except each node also contains a link to the previous node.
    Doubly-linked lists have an additional "tail" attribute, alongside "head".

    node_1 (head) <-> node_2 <-> node_3 (tail)

    >>> list_1 = DoublyLinkedList([0, 5, 4, 'foo', 5, 6])
    >>> list_1[2]
    4
    >>> list_1.index('foo')
    3

    >>> list_2 = DoublyLinkedList()
    >>> list_2.append('test')
    >>> list_2[0]
    'test'
    >>> list_2.insert(0, 'test2')
    >>> list_2[0]
    'test2'
    """

    def __init__(self, sequence: Sequence = None):
        """
        :param sequence: iterable sequence to populate list
        """

        self.head = None
        self.tail = None

        if sequence is not None:
            self.extend(sequence)

    class Node(Generic[T]):
        """
        entry within doubly-linked list with three attributes: value, previous node, and next node
        """

        def __init__(self, value: T, previous_node, next_node):
            self.value = value
            self.previous_node = previous_node
            self.next_node = next_node

        def __eq__(self, other) -> bool:
            return self.value is other.value or self.value == other.value

        def __gt__(self, other) -> bool:
            return self.value > other.value

        def __lt__(self, other) -> bool:
            return self.value < other.value

        def __str__(self) -> str:
            return str(self.value)

        def __repr__(self) -> str:
            return f'{self.previous_node} -> [{self.value}] -> {self.next_node}'

    def append(self, value: T):
        """
        append given value as new tail

        :param value: value to append
        """

        new_node = self.Node(value, self.tail, None)

        if self.tail is not None:
            self.tail.next_node = new_node

        self.tail = new_node

        if self.head is None:
            self.head = self.tail

    def extend(self, sequence: Sequence[T]):
        """
        append all values in given iterable to end of list

        :param sequence: iterable sequence with which to extend
        """

        for entry in sequence:
            if type(entry) is self.Node:
                entry = entry.value

            self.append(entry)

    def insert(self, index: int, value: T):
        """
        insert value at given index

        :param index: index at which to insert value
        :param value: value to insert
        """

        node_at_index = self._node_at_index(index)

        if node_at_index is not None:
            new_node = self.Node(value, node_at_index.previous_node, node_at_index)

            if node_at_index.previous_node is not None:
                node_at_index.previous_node.next_node = new_node
            else:
                self.head = new_node

            node_at_index.previous_node = new_node
        else:
            if index == 0:
                self.head = self.Node(value, None, None)
                self.tail = self.head
            elif index > 0:
                self.tail = self.Node(value, self.tail, None)
            else:
                self.head = self.Node(value, None, self.head)

    def remove(self, value: T):
        """
        remove all instances of given value

        :param value: value to remove
        """

        current_node = self.head

        while current_node is not None:
            if current_node.value == value:
                self._remove_node(current_node)

            current_node = current_node.next_node

    def index(self, value: T) -> int:
        """
        first index of given value

        :param value: value to find
        :return: value index
        """

        index = 0
        current_node = self.head

        while current_node is not None:
            if current_node.value == value:
                return index

            current_node = current_node.next_node
            index += 1
        else:
            raise ValueError(f'{value} is not in list')

    def count(self, value: T) -> int:
        """
        number of instances of given value

        :param value: value to count
        :return: value count
        """

        return sum([1 for node_value in self if node_value == value])

    def sort(self, inplace: bool = False):
        if inplace:
            instance = self
        else:
            instance = copy(self)
        sorted_values = sorted(instance)
        instance.head = None
        instance.tail = None
        instance.extend(sorted_values)
        return instance

    @property
    def difference(self) -> List[Any]:
        """
        differences between each value

        :return: list of differences
        """

        differences = []
        current_node = self.head

        while current_node is not None and current_node.next_node is not None:
            differences.append(current_node.next_node.value - current_node.value)
            current_node = current_node.next_node

        return differences

    def _node_at_index(self, index: int) -> Node:
        """
        Node indexing function.

        :param index: index
        :return: node at index
        """

        node_at_index = None

        if index >= 0:
            index_counter = 0
            current_node = self.head

            while current_node is not None:
                if index_counter == index:
                    node_at_index = current_node
                    break

                current_node = current_node.next_node
                index_counter += 1
        else:
            index_counter = -1
            current_node = self.tail

            while current_node is not None:
                if index_counter == index:
                    node_at_index = current_node
                    break

                current_node = current_node.previous_node
                index_counter -= 1

        if node_at_index is None:
            raise IndexError('list index out of range')

        return node_at_index

    def _remove_node(self, node: Node):
        if node.next_node is not None:
            node.next_node.previous_node = node.previous_node
        else:
            self.tail = node.previous_node

        if node.previous_node is not None:
            node.previous_node.next_node = node.next_node
        else:
            self.head = node.next_node

    def __getitem__(self, index: Union[int, Iterable[int], slice]) -> Union[Any, List[Any]]:
        if isinstance(index, int) or isinstance(index, int32) or isinstance(index, int64):
            return self._node_at_index(index).value
        elif isinstance(index, Iterable):
            return self.__class__([self.__getitem__(value) for value in index])
        elif isinstance(index, slice):
            slice_parameters = [
                value for value in (index.start, index.stop, index.step) if value is not None
            ]
            if all(slice_parameter is None for slice_parameter in slice_parameters):
                return self
            else:
                return self.__getitem__(range(*slice_parameters))
        else:
            raise ValueError(f'unrecognized index: {index}')

    def __setitem__(self, index: int, value: T):
        self._node_at_index(index).value = value

    def __delitem__(self, index: int):
        self._remove_node(self._node_at_index(index))

    def __iter__(self):
        current_node = self.head

        while current_node is not None:
            yield current_node.value
            current_node = current_node.next_node

    def __reversed__(self):
        current_node = self.tail

        while current_node is not None:
            yield current_node.value
            current_node = current_node.previous_node

    def __contains__(self, item: T) -> bool:
        for value in self:
            if item == value:
                return True
        else:
            return False

    def __len__(self) -> int:
        length = 0
        current_node = self.head

        while current_node is not None:
            length += 1
            current_node = current_node.next_node

        return length

    def __eq__(self, other: 'DoublyLinkedList') -> bool:
        if len(self) == len(other):
            for index in range(len(self)):
                if self[index] != other[index]:
                    return False
            else:
                return True

    def __copy__(self) -> 'DoublyLinkedList':
        return self.__class__(self)

    def __str__(self) -> str:
        return str(list(self))
