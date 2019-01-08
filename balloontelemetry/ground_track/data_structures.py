"""
Data structures for ground track class.

__authors__ = ['Zachary Burnett', 'StackOverflow']
"""


class DoublyLinkedList:
    """
    A linked list is a series of node objects, each with a link (object reference) to the next node in the series.
    The majority of the list is only accessible by starting at the first node ("head") and following the links forward.

    node_1 (head) -> node_2 -> node_3

    A doubly-linked list is similar to a linked list, except each node also contains a link to the previous node.
    Doubly-linked lists have an additional "tail" attribute, alongside "head".

    node_1 (head) <-> node_2 <-> node_3 (tail)
    """

    def __init__(self):
        self.head = None
        self.tail = None

    class Node:
        """
        Node within doubly-linked list with three attributes: value, previous node, and next node.
        """

        def __init__(self, value, previous_node, next_node):
            self.value = value
            self.previous_node = previous_node
            self.next_node = next_node

        def __eq__(self, other) -> bool:
            return self.value == other.value

    def append(self, value):
        """
        Append given value as new tail.

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
        Append all values in given iterable to end of list.

        :param other: Iterable whose entries should be appended.
        """

        for entry in other:
            if type(entry) is self.Node:
                entry = entry.value

            self.append(entry)

    def insert(self, value, index: int):
        """
        Insert value at given index.

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
        Remove all instances of given value.

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
        First index of given value.

        :param value: Value to find.
        :return: value index
        """

        index = 0
        current_node = self.head

        while current_node is not None:
            if current_node.value == value:
                return index

            current_node = current_node.next_node
            index += 1

    def count(self, value) -> int:
        """
        Number of instances of given value.

        :param value: Value to count.
        :return: value count
        """

        num_nodes_with_value = 0
        current_node = self.head

        while current_node is not None:
            if current_node.value == value:
                num_nodes_with_value += 1

            current_node = current_node.next_node

        return num_nodes_with_value

    def _node_at_index(self, index: int):
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

        return node_at_index

    def __getitem__(self, index: int):
        """
        Indexing function (for integer indexing of list contents).

        :param index: index
        :return: value at index
        """

        return self._node_at_index(index).value

    def __len__(self) -> int:
        length = 0
        current_node = self.head

        while current_node is not None:
            length += 1
            current_node = current_node.next_node

        return length

    def __iter__(self):
        """
        Generator function iterating over list values, starting at head.

        :return: next value
        """

        current_node = self.head

        while current_node is not None:
            yield current_node.value
            current_node = current_node.next_node

    def __str__(self) -> str:
        return str(list(self))


if __name__ == '__main__':
    doubly_linked_list = DoublyLinkedList()

    doubly_linked_list.append(0)

    # should be [0]
    print(doubly_linked_list)

    # should be True
    print(doubly_linked_list.head is doubly_linked_list.tail)

    doubly_linked_list.extend([5, 4, 6, 0, 3])

    # should be [0, 5, 4, 6, 0, 3]
    print(doubly_linked_list)

    # should be False
    print(doubly_linked_list.head is doubly_linked_list.tail)

    doubly_linked_list.insert(1, 0)

    # should be [1, 0, 5, 4, 6, 0, 3]
    print(doubly_linked_list)

    doubly_linked_list.remove(0)

    # should be [1, 5, 4, 6, 3]
    print(doubly_linked_list)
