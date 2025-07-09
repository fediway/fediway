import pytest


from modules.mastodon.paperclip import id_partition


def test_id_partition_single_digit_number():
    assert id_partition(1) == "000/000/001"
    assert id_partition(5) == "000/000/005"
    assert id_partition(9) == "000/000/009"


def test_id_partition_two_digit_number():
    assert id_partition(10) == "000/000/010"
    assert id_partition(42) == "000/000/042"
    assert id_partition(99) == "000/000/099"


def test_id_partition_three_digit_number():
    assert id_partition(100) == "000/000/100"
    assert id_partition(456) == "000/000/456"
    assert id_partition(999) == "000/000/999"


def test_id_partition_four_digit_number():
    assert id_partition(1000) == "000/001/000"
    assert id_partition(1234) == "000/001/234"
    assert id_partition(9999) == "000/009/999"


def test_id_partition_five_digit_number():
    assert id_partition(10000) == "000/010/000"
    assert id_partition(12345) == "000/012/345"
    assert id_partition(99999) == "000/099/999"


def test_id_partition_six_digit_number():
    assert id_partition(100000) == "000/100/000"
    assert id_partition(123456) == "000/123/456"
    assert id_partition(651513) == "000/651/513"
    assert id_partition(999999) == "000/999/999"


def test_id_partition_seven_digit_number():
    assert id_partition(1000000) == "001/000/000"
    assert id_partition(1234567) == "001/234/567"
    assert id_partition(9999999) == "009/999/999"


def test_id_partition_eight_digit_number():
    assert id_partition(10000000) == "010/000/000"
    assert id_partition(12345678) == "012/345/678"
    assert id_partition(99999999) == "099/999/999"


def test_id_partition_nine_digit_number():
    assert id_partition(100000000) == "100/000/000"
    assert id_partition(123456789) == "123/456/789"
    assert id_partition(999999999) == "999/999/999"


def test_with_long_number():
    assert id_partition(114782619229607682) == "114/782/619/229/607/682"
