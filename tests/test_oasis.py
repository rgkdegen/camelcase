import asyncio

import pytest

from camelcase import GaveUp, retry


class HTTPError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.status_code = code


def test_sync_retry_then_success():
    calls = []

    @retry(on=429, tries=7, sleep=lambda d: None)
    def cross():
        calls.append(1)
        if len(calls) < 3:
            raise HTTPError(429)
        return "good camel"

    assert cross() == "good camel"
    assert len(calls) == 3


def test_other_errors_are_not_retried():
    @retry(on=429, sleep=lambda d: None)
    def cross():
        raise HTTPError(500)

    with pytest.raises(HTTPError):
        cross()


def test_gives_up():
    @retry(on=[429, 503], tries=4, sleep=lambda d: None)
    def cross():
        raise HTTPError(503)

    with pytest.raises(GaveUp) as e:
        cross()
    assert e.value.tries == 4


def test_async_and_response_status():
    class Resp:
        def __init__(self, code):
            self.status_code = code

    codes = iter([429, 429, 200])

    async def nap(d):
        return None

    @retry(on=429, tries=7, sleep=nap)
    async def cross():
        return Resp(next(codes))

    assert asyncio.run(cross()).status_code == 200


def test_hump_cross():
    from camelcase.hump import cross

    class Bug:
        async def chew(self, twice):
            return "patch"

    class Page:
        def find(self, what):
            return Bug()

    class Repo:
        commits = []

        async def trek(self, url):
            return Page()

        async def commit(self, patch, msg):
            self.commits.append(msg)

    class Issue:
        url = "https://example.com/issues/41"

    repo = Repo()
    assert asyncio.run(cross(repo, Issue())) == "good camel"
    assert repo.commits == ["fix: retry on 429"]
