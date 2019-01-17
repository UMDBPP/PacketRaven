import unittest

from balloontelemetry.ground_track import data_structures


class TestDoublyLinkedList(unittest.TestCase):
    def test_len(self):
        empty_list = data_structures.DoublyLinkedList()
        nonempty_list = data_structures.DoublyLinkedList([0, 'foo'])

        self.assertEqual(0, len(empty_list))
        self.assertEqual(2, len(nonempty_list))

    def test_extend(self):
        extended_list = data_structures.DoublyLinkedList([0])
        extended_list.extend(['foo', 5])

        self.assertEqual([0, 'foo', 5], extended_list)
        self.assertTrue(extended_list.head is not extended_list.tail)

    def test_append(self):
        appended_list = data_structures.DoublyLinkedList()
        appended_list.append(0)

        self.assertEqual(0, appended_list[0])
        self.assertEqual(0, appended_list[-1])
        self.assertTrue(appended_list.head is appended_list.tail)

    def test_insert(self):
        inserted_list = data_structures.DoublyLinkedList([0, 'foo'])
        inserted_list.insert('bar', 0)

        self.assertEqual(['bar', 0, 'foo'], inserted_list)

    def test_remove(self):
        removed_list = data_structures.DoublyLinkedList([0, 5, 4, 'foo', 0, 0])

        removed_list.remove(0)

        self.assertEqual([5, 4, 'foo'], removed_list)
        self.assertEqual(5, removed_list.head.value)
        self.assertEqual('foo', removed_list.tail.value)


if __name__ == '__main__':
    unittest.main()
