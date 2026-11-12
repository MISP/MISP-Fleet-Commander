"""Login throttling counts failures per client: behind trusted reverse proxies, the client is read from X-Forwarded-For"""
import pytest

PROXY = "10.0.0.1"


def login(client, email, password, forwardedFor=None):
    headers = {"X-Forwarded-For": forwardedFor} if forwardedFor else {}
    return client.post("/login", json={"email": email, "password": password}, headers=headers,
                       environ_base={"REMOTE_ADDR": PROXY})


def lockOut(client, email, forwardedFor=None):
    for _ in range(5):
        assert login(client, email, "wrong", forwardedFor).status_code == 401


@pytest.fixture()
def trustedProxies(app):
    """Trust this many proxies for the duration of a test"""
    from application import trustProxies
    originalApp, originalValue = app.wsgi_app, app.config.get("TRUSTED_PROXIES")

    def _trust(count):
        app.config["TRUSTED_PROXIES"] = count
        trustProxies(app)
    yield _trust
    app.wsgi_app, app.config["TRUSTED_PROXIES"] = originalApp, originalValue


def test_forwarded_for_is_ignored_without_trusted_proxies(client, make_user):
    make_user("direct@test.local")
    lockOut(client, "direct@test.local", forwardedFor="192.0.2.1")
    # Claiming another address does not get around the lockout
    assert login(client, "direct@test.local", "Password1234", forwardedFor="192.0.2.2").status_code == 429


def test_clients_behind_a_trusted_proxy_are_counted_separately(client, make_user, trustedProxies):
    trustedProxies(1)
    make_user("proxied@test.local")
    lockOut(client, "proxied@test.local", forwardedFor="192.0.2.1")
    assert login(client, "proxied@test.local", "Password1234", forwardedFor="192.0.2.1").status_code == 429
    # Another client behind the same proxy can still log in
    assert login(client, "proxied@test.local", "Password1234", forwardedFor="192.0.2.2").status_code == 200
    # Addresses a client puts in front of the one the proxy appends are not trusted
    assert login(client, "proxied@test.local", "Password1234", forwardedFor="198.51.100.7, 192.0.2.1").status_code == 429


@pytest.mark.parametrize("value", ["-1", "yes", "1.5"])
def test_invalid_trusted_proxies_fail_explicitly(value, trustedProxies):
    with pytest.raises(RuntimeError, match="TRUSTED_PROXIES"):
        trustedProxies(value)


def test_no_proxy_is_trusted_by_default(app):
    from werkzeug.middleware.proxy_fix import ProxyFix
    assert str(app.config["TRUSTED_PROXIES"]) == "0"
    assert not isinstance(app.wsgi_app, ProxyFix)
