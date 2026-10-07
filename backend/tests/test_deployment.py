import importlib.util
from pathlib import Path

import pytest


def load(name):
    path = Path(__file__).resolve().parents[2] / "deploy" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("domain", ["https://example.com", "example.com;", "example.com\nlisten 81;", "../example.com", "example.com:443"])
def test_nginx_renderer_rejects_config_injection(domain):
    with pytest.raises(ValueError):
        load("render_nginx").render(domain)


def test_certificate_bootstrap_does_not_require_certificate():
    config = load("render_nginx").render("noticeboard.example.com", https=False)
    assert "acme-challenge" in config
    assert "ssl_certificate" not in config
    assert "proxy_pass" not in config


def test_production_requires_config_without_printing_secret_values():
    errors = load("check_config").validate({"PG_PASSWORD": "private-test-value"})
    assert errors
    assert "private-test-value" not in " ".join(errors)


def test_remote_database_cannot_silently_downgrade_tls():
    errors = load("check_config").validate({
        "PG_HOST": "db.internal", "PG_DATABASE": "noticeboard", "PG_USER": "noticeboard_app",
        "PG_PASSWORD": "test-only", "NOTICEBOARD_JWT_SECRET": "x" * 48, "PG_SSLMODE": "prefer",
    })
    assert errors == ["Remote PostgreSQL requires PG_SSLMODE=verify-full"]


def test_ipv4_certificate_paths_and_proxy_host():
    config = load("render_nginx").render("13.219.9.139")
    assert "server_name 13.219.9.139;" in config
    assert "/etc/letsencrypt/live/13.219.9.139/fullchain.pem" in config
    assert "proxy_set_header Host 13.219.9.139;" in config
