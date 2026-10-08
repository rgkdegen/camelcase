from camelcase import to_camel, to_pascal, to_snake
from camelcase.case import find_snake_names


def test_to_camel():
    assert to_camel("stack_trace_url") == "stackTraceUrl"
    assert to_camel("good camel") == "goodCamel"
    assert to_camel("_private_thing") == "_privateThing"
    assert to_camel("already") == "already"
    assert to_camel("HTTP_status-code") == "httpStatusCode"


def test_pascal_and_snake():
    assert to_pascal("good camel") == "GoodCamel"
    assert to_snake("goodCamel") == "good_camel"
    assert to_snake("HTTPServerError") == "http_server_error"


def test_find_snake_names():
    src = "def fetch_page(x):\n    page_url = x\n    ok = 1\n    return page_url == 1\n"
    assert find_snake_names(src) == [(1, "fetch_page"), (2, "page_url")]
