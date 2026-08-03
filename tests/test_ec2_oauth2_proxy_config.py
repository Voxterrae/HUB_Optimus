from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "ops" / "ec2" / "oauth2-proxy.cfg.example"
SERVICE = ROOT / "ops" / "ec2" / "oauth2-proxy.service"


def _config() -> tuple[str, dict]:
    text = CONFIG.read_text(encoding="utf-8")
    return text, tomllib.loads(text)


def test_entra_is_single_tenant_confidential_web_client_with_pkce():
    text, config = _config()

    assert config["provider"] == "entra-id"
    assert config["client_id"] == "<MICROSOFT_ENTRA_APPLICATION_CLIENT_ID>"
    assert config["client_secret_file"] == "/etc/hub-optimus/secrets/oauth2-proxy-client-secret"
    assert "client_secret" not in config
    assert config["oidc_issuer_url"] == (
        "https://login.microsoftonline.com/<MICROSOFT_ENTRA_TENANT_ID>/v2.0"
    )
    assert config["entra_id_allowed_tenants"] == ["<MICROSOFT_ENTRA_TENANT_ID>"]
    assert config["redirect_url"] == "https://api.huboptimus.dev/oauth2/callback"
    assert config["code_challenge_method"] == "S256"
    assert "/common" not in text
    assert "/organizations" not in text
    assert "/consumers" not in text


def test_roles_from_the_same_application_are_the_only_authorization_gate():
    _, config = _config()

    assert config["oidc_groups_claim"] == "roles"
    assert config["user_id_claim"] == "sub"
    assert config["allowed_groups"] == ["HUB.Owner", "HUB.Operator"]
    assert config["scope"] == "openid profile email"
    assert config["email_domains"] == ["*"]
    assert "allowed_roles" not in config
    assert "entra_id_allowed_groups" not in config


def test_oidc_discovery_issuer_nonce_tls_and_signatures_are_verified():
    _, config = _config()

    assert config["skip_oidc_discovery"] is False
    assert config["insecure_oidc_skip_issuer_verification"] is False
    assert config["insecure_oidc_skip_nonce"] is False
    assert config["insecure_oidc_allow_unverified_email"] is False
    assert config["ssl_insecure_skip_verify"] is False
    assert config["oidc_enabled_signing_algs"] == ["RS256"]


def test_proxy_is_loopback_auth_request_only_and_trusts_only_loopback_nginx():
    _, config = _config()

    assert config["http_address"] == "127.0.0.1:4180"
    assert config["reverse_proxy"] is True
    assert config["trusted_proxy_ips"] == ["127.0.0.1/32", "::1/128"]
    assert config["upstreams"] == ["static://202"]
    assert config["set_xauthrequest"] is True
    assert config["set_authorization_header"] is False
    assert config["set_basic_auth"] is False
    assert config["pass_access_token"] is False
    assert config["pass_authorization_header"] is False
    assert config["pass_basic_auth"] is False
    assert config["pass_user_headers"] is False
    assert config["skip_auth_strip_headers"] is False
    assert config["request_logging"] is False
    assert config["auth_logging"] is False


def test_redis_holds_session_and_host_cookie_has_exact_security_contract():
    _, config = _config()

    assert config["session_store_type"] == "redis"
    assert config["redis_connection_url"] == "redis://127.0.0.1:6379/0"
    assert config["cookie_name"].startswith("__Host-")
    assert config["cookie_name"] == "__Host-hub_optimus_session"
    assert config["cookie_secret_file"] == "/etc/hub-optimus/secrets/oauth2-proxy-cookie-secret"
    assert "cookie_secret" not in config
    assert "cookie_domains" not in config
    assert config["cookie_secure"] is True
    assert config["cookie_httponly"] is True
    assert config["cookie_samesite"] == "lax"
    assert config["cookie_path"] == "/"
    assert config["cookie_expire"] == "55m"
    assert config["cookie_refresh"] == "0"


def test_service_pins_7_15_3_and_validates_before_start_without_inline_secrets():
    text = SERVICE.read_text(encoding="utf-8")

    binary = "/usr/local/bin/oauth2-proxy-v7.15.3"
    assert f"ExecStartPre=/usr/bin/test -x {binary}" in text
    assert f"{binary} --version" in text
    assert r"v?7\.15\.3" in text
    assert r"7\\.15\\.3" not in text
    assert f"ExecStartPre={binary} --config=/etc/hub-optimus/oauth2-proxy.cfg --config-test" in text
    assert f"ExecStart={binary} --config=/etc/hub-optimus/oauth2-proxy.cfg" in text
    assert "client-secret=" not in text
    assert "cookie-secret=" not in text
    assert "Environment=" not in text
    assert "NoNewPrivileges=true" in text
    assert "ProtectSystem=strict" in text


def test_every_oauth_secret_is_loaded_from_an_external_file():
    _, config = _config()

    secret_keys = {key for key in config if "secret" in key}
    assert secret_keys == {"client_secret_file", "cookie_secret_file"}
    for key in secret_keys:
        assert key.endswith("_file")
        assert config[key].startswith("/etc/hub-optimus/secrets/")
