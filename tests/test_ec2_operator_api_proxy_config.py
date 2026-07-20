from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "ops" / "ec2" / "nginx" / "operator-api.conf"


def test_operator_api_proxy_exposes_only_controlled_intake_and_health():
    text = CONFIG.read_text(encoding="utf-8")

    assert "server_name api.huboptimus.dev;" in text
    assert "location = /intake/url" in text
    assert "proxy_pass http://127.0.0.1:8080/intake/url;" in text
    assert "location = /health" in text
    assert "proxy_pass http://127.0.0.1:8080/health;" in text
    assert "location /" in text
    assert "return 404;" in text
    assert "location = /analyze" not in text
    assert "location /analyze" not in text
    assert "proxy_pass http://127.0.0.1:8080/analyze" not in text
    assert "location = /status" not in text
    assert "location /status" not in text
    assert "proxy_pass http://127.0.0.1:8080/status" not in text


def test_operator_api_proxy_has_cors_boundary_for_operator_origin():
    text = CONFIG.read_text(encoding="utf-8")

    assert '"https://huboptimus.dev" $http_origin;' in text
    assert '"https://www.huboptimus.dev" $http_origin;' in text
    assert "Access-Control-Allow-Origin $hub_optimus_cors_origin" in text
    assert 'Access-Control-Allow-Methods "POST, OPTIONS"' in text
    assert 'Access-Control-Allow-Headers "Content-Type"' in text
    assert 'Vary "Origin"' in text


def test_operator_api_proxy_has_abuse_and_size_limits():
    text = CONFIG.read_text(encoding="utf-8")

    assert "limit_req_zone $binary_remote_addr zone=hub_optimus_url_intake:10m rate=12r/m;" in text
    assert "limit_req zone=hub_optimus_url_intake burst=6 nodelay;" in text
    assert "client_max_body_size 8k;" in text
    assert "proxy_connect_timeout 3s;" in text
    assert "proxy_read_timeout 15s;" in text
    assert "proxy_send_timeout 15s;" in text


def test_operator_api_proxy_documents_dns_tls_and_boundary():
    text = CONFIG.read_text(encoding="utf-8")

    assert "DNS requirement:" in text
    assert "api.huboptimus.dev -> EC2 public IPv4" in text
    assert "TLS requirement:" in text
    assert "Publicly expose only controlled URL intake and health." in text
    assert "Do not expose /analyze" in text
