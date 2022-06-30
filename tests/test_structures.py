from packetraven.packets.structures import DoublyLinkedList


def test_index():
    list_1 = DoublyLinkedList([0, 5, 4, "foo", 5, 6])

    assert list_1[0] == 0
    assert list_1[0] is list_1.head.value
    assert list_1[3] == "foo"
    assert list_1[-2] == 5
    assert list_1[-1] == 6
    assert list_1[-1] is list_1.tail.value
    assert list_1[:2] == [0, 5]
    assert list_1[[1, 3, 0]] == [5, "foo", 0]


def test_length():
    list_1 = DoublyLinkedList()

    assert len(list_1) == 0

    list_2 = DoublyLinkedList([0, "foo"])

    assert len(list_2) == 2


def test_extend():
    list_1 = DoublyLinkedList([0])
    list_1.extend(["foo", 5])

    assert list_1 == [0, "foo", 5]
    assert list_1.head is not list_1.tail


def test_append():
    list_1 = DoublyLinkedList()
    list_1.append(0)

    assert list_1[0] == 0
    assert list_1[-1] == 0
    assert list_1.head is list_1.tail


def test_insert():
    list_1 = DoublyLinkedList([0, "foo"])
    list_1.insert(0, "bar")

    assert list_1 == ["bar", 0, "foo"]


def test_equality():
    list_1 = DoublyLinkedList([5, 4, "foo"])

    assert list_1 == [5, 4, "foo"]
    assert list_1 == (5, 4, "foo")
    assert list_1 != [5, 4, "foo", 6, 2]


def test_remove():
    list_1 = DoublyLinkedList(["a", "a"])
    list_1.remove("a")

    assert len(list_1) == 0
    assert list_1.head is None
    assert list_1.tail is None

    list_2 = DoublyLinkedList(["a", "b", "c"])
    del list_2[0]
    del list_2[-1]

    assert len(list_2) == 1
    assert list_2[0] == "b"
    assert list_2[-1] == "b"

    list_3 = DoublyLinkedList([0, 5, 4, "foo", 0, 0])
    list_3.remove(0)

    assert list_3 == [5, 4, "foo"]
    assert list_3[0] == 5
    assert list_3[-1] == "foo"
