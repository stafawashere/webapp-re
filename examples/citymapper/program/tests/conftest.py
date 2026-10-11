import functools

import httpx
import pytest

from support import build_context


class RealNetworkBlocked(AssertionError):
   pass


def refuse_real_network(transport, request):
   raise RealNetworkBlocked("a test tried to reach {0}".format(request.url))


@pytest.fixture(autouse=True)
def offline_site(monkeypatch, tmp_path):
   monkeypatch.setattr(httpx.HTTPTransport, "handle_request", refuse_real_network)
   monkeypatch.setenv("CITYMAPPER_ROOT", str(tmp_path / "site-root"))


@pytest.fixture
def make_context(tmp_path):
   return functools.partial(build_context, tmp_path / "site")
