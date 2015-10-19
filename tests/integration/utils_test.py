from kirin.utils import str_to_date
import datetime


def test_valid_date():
    res = str_to_date('20151210')
    assert res == datetime.date(2015, 12, 10)


def test_invalid_date():
    res = str_to_date('aaaa')
    assert res == None
