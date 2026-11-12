"""A server that does not answer must not hold a worker for minutes: asynchronous requests follow the configured
MISP request timeout, and a full refresh that reached nothing stops early"""
import asyncio
from types import SimpleNamespace

from test_drift import checks, fleet, okStatus  # noqa: F401


def test_async_requests_default_to_the_configured_timeout(app, monkeypatch):
    import aiohttp
    import application.controllers.utils as controllerUtils
    from application.models import utils
    monkeypatch.setattr(controllerUtils, "mispReadTimeout", lambda: 42)
    assert utils.defaultMispTimeout() == 47

    totals = []
    realTimeout = aiohttp.ClientTimeout
    monkeypatch.setattr(aiohttp, "ClientTimeout", lambda total: totals.append(total) or realTimeout(total=total))
    server = SimpleNamespace(url="http://127.0.0.1:9", authkey="key", skip_ssl=True)
    [result] = asyncio.run(utils.asyncFetcher(server, ["/servers/getVersion"]))
    assert "error" in result and totals == [47]
    asyncio.run(utils.asyncFetcher(server, ["/servers/getVersion"], timeout=3))
    assert totals[-1] == 3


def test_a_refresh_that_reached_nothing_skips_the_usage_statistics(fleet, monkeypatch):
    from application import redisModel
    import application.models.servers as serverModel
    user, theFleet, (beta, alpha) = fleet
    requested = []
    unanswered = {"error": "Timeout Exception (65s)"}

    async def silentServer(server, urls, timeout=None):
        requested.extend(urls)
        return [dict(unanswered) for url in urls]
    monkeypatch.setattr(serverModel, "asyncFetcher", silentServer)
    monkeypatch.setattr(redisModel, "setServerWatchedTimestamp", lambda uuid: None)
    asyncio.run(serverModel.fetchServerInfoAsync(beta, {}))
    assert "/users/statistics" not in requested and "/servers/index" in requested

    # One answer, even an error page, means the server is there
    async def oneAnswer(server, urls, timeout=None):
        requested.extend(urls)
        return [{"message": "Forbidden", "_status_code": 403}] + [dict(unanswered) for url in urls[1:]]
    monkeypatch.setattr(serverModel, "asyncFetcher", oneAnswer)
    requested.clear()
    asyncio.run(serverModel.fetchServerInfoAsync(beta, {}))
    assert "/users/statistics" in requested
