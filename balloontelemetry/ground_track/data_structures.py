"""
from http://ls.pwd.io/2014/08/singly-and-doubly-linked-lists-in-python/
"""


class DoublyLinkedList:
    head = None
    tail = None

    class Node:
        def __init__(self, value, previous_node, next_node):
            self.value = value
            self.previous_node = previous_node
            self.next_node = next_node

        def __eq__(self, other):
            return self.value == other.value

    def append(self, value):
        """
        Appends value to end of list.

        :param value: Value to append.
        """

        new_node = self.Node(value, self.tail, None)

        if self.tail is not None:
            self.tail.next_node = new_node

        self.tail = new_node

        if self.head is None:
            self.head = self.tail

    def extend(self, other):
        """
        Appends all values in given iterable to the end of this list.

        :param other: Iterable whose entries should be appended.
        """

        for entry in other:
            if type(entry) is self.Node:
                entry = entry.value

            self.append(entry)

    def insert(self, value, index: int):
        """
        Inserts value at specified index, element indices following the specified index are incremented by one.

        :param value: Value to insert.
        :param index: Index at which to insert value.
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

    def remove(self, value):
        """
        Removes all instances of value from list.

        :param value: Value to remove.
        """

        current_node = self.head

        while current_node is not None:
            if current_node.value == value:
                if current_node.next_node is not None:
                    current_node.next_node.previous_node = current_node.previous_node

                if current_node.previous_node is not None:
                    current_node.previous_node.next_node = current_node.next_node
                else:
                    self.head = current_node.next_node

            current_node = current_node.next_node

    def index(self, value) -> int:
        """
        Get index of first node with specified value.

        :param value: Value of node.
        :return: index of node
        """

        index = 0
        current_node = self.head

        while current_node is not None:
            if current_node.value == value:
                return index

            current_node = current_node.next_node
            index += 1

    def _node_at_index(self, index: int):
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

        return node_at_index

    def __getitem__(self, index: int):
        return self._node_at_index(index).value

    def __len__(self) -> int:
        length = 0
        current_node = self.head

        while current_node is not None:
            length += 1
            current_node = current_node.next_node

        return length

    def __iter__(self):
        current_node = self.head

        while current_node is not None:
            yield current_node.value
            current_node = current_node.next_node

    def __str__(self) -> str:
        return str(list(self))


if __name__ == '__main__':
    doubly_linked_list = DoublyLinkedList()
    doubly_linked_list.append(0)
    doubly_linked_list.extend([5, 4, 6, 0, 3])
    doubly_linked_list.insert(1, 0)

    print(doubly_linked_list)

    doubly_linked_list.remove(0)

    print(doubly_linked_list)
