from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "ops" / "ec2" / "nginx" / "operator-api.conf"


def _config() -> str:
    return CONFIG.read_text(encoding="utf-8")


def _location(text: str, declaration: str) -> str:
    start = text.index(declaration)
    opening = text.index("{", start)
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise AssertionError(f"unclosed nginx block: {declaration}")


def test_default_hosts_fail_closed_and_http_redirect_uses_a_literal_authority():
    text = _config()

    default_http = _location(text, "server {\n    listen 80 default_server;")
    default_tls = _location(text, "server {\n    listen 443 ssl default_server;")
    http_host = _location(text, "server {\n    listen 80;\n")

    assert "server_name _;" in default_http
    assert "return 444;" in default_http
    assert "server_name _;" in default_tls
    assert "ssl_reject_handshake on;" in default_tls
    assert "server_name api.huboptimus.dev;" in http_host
    assert "return 308 https://api.huboptimus.dev$request_uri;" in http_host
    assert "https://$host" not in text


def test_tls_host_has_certificate_hsts_no_store_and_minimal_public_health():
    text = _config()
    health = _location(text, "location = /health")

    assert "listen 443 ssl http2;" in text
    assert (
        "ssl_certificate "
        "/etc/letsencrypt/live/api.huboptimus.dev/fullchain.pem;" in text
    )
    assert (
        "ssl_certificate_key "
        "/etc/letsencrypt/live/api.huboptimus.dev/privkey.pem;" in text
    )
    assert "ssl_protocols TLSv1.2 TLSv1.3;" in text
    assert (
        'Strict-Transport-Security "max-age=63072000; '
        'includeSubDomains; preload" always;' in text
    )
    assert 'add_header Cache-Control "no-store" always;' in text
    assert "proxy_pass" not in health
    assert "return 200 '{\"status\":\"ok\"}';" in health
    assert "/status" not in text
    assert "127.0.0.1:8080" not in text


def test_oauth2_routes_are_exact_loopback_only_and_header_sanitized():
    text = _config()
    auth = _location(text, "location = /oauth2/auth")
    start = _location(text, "location = /oauth2/start")
    callback = _location(text, "location = /oauth2/callback")
    sign_out = _location(text, "location = /oauth2/sign_out")

    assert "location ^~ /oauth2/" not in text
    assert "internal;" in auth
    assert "access_log off;" in auth
    assert "proxy_pass http://127.0.0.1:4180/oauth2/auth;" in auth
    assert "proxy_pass_request_headers off;" in auth
    assert "proxy_pass_request_body off;" in auth
    assert 'proxy_set_header Authorization "";' in auth

    for block in (start, callback, sign_out):
        assert "access_log off;" in block
        assert "proxy_pass_request_headers off;" in block
        assert "proxy_set_header Cookie $http_cookie;" in block
        assert "proxy_set_header Host api.huboptimus.dev;" in block
        assert "proxy_set_header X-Forwarded-Host api.huboptimus.dev;" in block
        assert "proxy_set_header X-Forwarded-Proto https;" in block
        assert "proxy_next_upstream off;" in block
        assert "proxy_intercept_errors on;" in block


def test_callback_cannot_write_authorization_code_or_state_to_nginx_logs():
    text = _config()
    callback = _location(text, "location = /oauth2/callback")
    callback_failed = _location(text, "location @oauth2_callback_failed")
    callback_method = _location(
        text,
        "location @oauth2_callback_method_not_allowed",
    )

    assert "access_log off;" in callback
    assert "error_log /dev/null crit;" in callback
    assert (
        "error_page 400 401 403 404 408 413 429 500 502 503 504 "
        "= @oauth2_callback_failed;" in callback
    )
    assert "error_page 405 = @oauth2_callback_method_not_allowed;" in callback
    assert "proxy_pass http://127.0.0.1:4180;" in callback
    assert "X-Forwarded-Uri" not in callback
    assert "$request_uri" not in callback
    assert "$args" not in callback
    assert "$arg_code" not in callback
    assert "$arg_state" not in callback
    for terminal in (callback_failed, callback_method):
        assert "internal;" in terminal
        assert "access_log off;" in terminal
        assert "error_log /dev/null crit;" in terminal
        assert "$request_uri" not in terminal
        assert "$args" not in terminal
        assert "$arg_code" not in terminal
        assert "$arg_state" not in terminal
    assert "return 502" in callback_failed
    assert '"authentication_callback_failed"' in callback_failed
    assert "return 405" in callback_method
    assert 'add_header Allow "GET" always;' in callback_method


def test_operator_landing_query_and_every_local_dependency_require_auth():
    text = _config()
    protected = {
        "location ^~ /operator/": ("try_files $uri $uri/ =404;",),
        "location = / {": ("try_files /index.html =404;",),
        "location ^~ /assets/": ("try_files $uri =404;",),
        "location ^~ /i18n/": ("try_files $uri =404;",),
        "location = /styles.css": ("try_files $uri =404;",),
        "location = /globe.js": ("try_files $uri =404;",),
        "location = /app.js": ("try_files $uri =404;",),
    }

    for declaration, expected_lines in protected.items():
        block = _location(text, declaration)
        assert "auth_request /oauth2/auth;" in block
        assert "root /opt/hub-optimus/current/site;" in block
        assert "proxy_pass" not in block
        for expected in expected_lines:
            assert expected in block

    # NGINX exact-location matching ignores the query, so /?lang=... is served
    # by the authenticated root block rather than the public catch-all.
    assert "location = / {" in text
    assert "location ^~ /assets/ {" in text
    assert 'add_header Cache-Control "no-store" always;' in text


def test_intake_is_exact_same_origin_post_and_uses_auth_request():
    text = _config()
    intake = _location(text, "location = /api/intake")

    assert "if ($request_method != POST)" in intake
    assert 'if ($http_origin != "https://api.huboptimus.dev")' in intake
    assert "auth_request /oauth2/auth;" in intake
    assert "$upstream_http_x_auth_request_user" in intake
    assert "$upstream_http_x_auth_request_groups" in intake
    assert "OPTIONS" not in intake
    assert "Access-Control-Allow-Origin" not in text
    assert "Access-Control-Allow-Credentials" not in text
    assert "*" not in "\n".join(
        line for line in text.splitlines() if "Access-Control" in line
    )


def test_intake_constructs_a_header_allowlist_and_cannot_trust_client_identity():
    intake = _location(_config(), "location = /api/intake")

    assert "proxy_pass_request_headers off;" in intake
    assert "proxy_set_header Content-Type $http_content_type;" in intake
    assert "proxy_set_header Origin https://api.huboptimus.dev;" in intake
    assert "proxy_set_header Content-Length" not in intake
    assert (
        "proxy_set_header X-Hub-Internal-Capability "
        "$hub_internal_capability;" in intake
    )
    assert (
        "proxy_set_header X-Hub-Authenticated-Subject "
        "$hub_authenticated_subject;" in intake
    )
    assert (
        "proxy_set_header X-Hub-Authenticated-Roles "
        "$hub_authenticated_roles;" in intake
    )
    assert "proxy_set_header X-Hub-Client-IP $remote_addr;" in intake
    assert "proxy_set_header X-Request-ID $request_id;" in intake
    assert 'proxy_set_header Cookie "";' in intake
    assert 'proxy_set_header Authorization "";' in intake
    assert 'proxy_set_header Proxy-Authorization "";' in intake
    assert 'proxy_set_header X-Auth-Request-Access-Token "";' in intake
    assert 'proxy_set_header X-Forwarded-Access-Token "";' in intake
    assert "X-Auth-Request-Email" not in intake
    assert "X-Auth-Request-Preferred-Username" not in intake


def test_capability_is_external_and_gateway_is_the_only_intake_upstream():
    text = _config()
    intake = _location(text, "location = /api/intake")

    assert (
        "include /etc/hub-optimus/secrets/"
        "operator-intake-capability.conf;" in text
    )
    assert "set $hub_internal_capability" not in text
    assert not (ROOT / "etc" / "hub-optimus" / "secrets").exists()
    assert "proxy_pass http://127.0.0.1:8081/intake/url;" in intake
    assert "127.0.0.1:8080" not in text
    assert "location = /intake/url" not in text
    assert "location = /analyze" not in text


def test_intake_has_ip_rate_connection_body_and_deadline_limits():
    text = _config()
    intake = _location(text, "location = /api/intake")

    assert (
        "limit_req_zone $binary_remote_addr "
        "zone=hub_optimus_intake_per_ip:10m rate=12r/m;" in text
    )
    assert (
        "limit_conn_zone $binary_remote_addr "
        "zone=hub_optimus_connections_per_ip:10m;" in text
    )
    assert "limit_req_status 429;" in text
    assert "limit_conn_status 429;" in text
    assert "limit_req zone=hub_optimus_intake_per_ip burst=6 nodelay;" in intake
    assert "limit_conn hub_optimus_connections_per_ip 4;" in intake
    assert "client_max_body_size 8k;" in intake
    assert "client_body_timeout 5s;" in intake
    assert "proxy_connect_timeout 3s;" in intake
    assert "proxy_read_timeout 15s;" in intake
    assert "proxy_send_timeout 15s;" in intake
    assert "send_timeout 15s;" in intake
    assert "proxy_next_upstream off;" in intake
    assert "proxy_request_buffering on;" in intake
    assert "proxy_http_version 1.0;" in intake
    assert "proxy_intercept_errors off;" in intake


def test_all_required_edge_failures_are_json_with_one_coherent_request_id():
    text = _config()
    errors = {
        405: ("@method_not_allowed", "method_not_allowed"),
        408: ("@request_timeout", "request_timeout"),
        413: ("@request_too_large", "request_too_large"),
        429: ("@rate_limited", "rate_limited"),
        500: ("@internal_error", "internal_error"),
        502: ("@upstream_unavailable", "upstream_unavailable"),
        503: ("@upstream_busy", "upstream_busy"),
        504: ("@upstream_timeout", "upstream_timeout"),
    }

    assert "recursive_error_pages off;" in text
    assert "add_header X-Request-ID req_$request_id always;" in text
    for status, (target, code) in errors.items():
        assert f"error_page {status} = {target};" in text
        block = _location(text, f"location {target}")
        assert "internal;" in block
        assert "default_type application/json;" in block
        assert "<html" not in block.lower()
        assert (
            f"return {status} '{{\"error\":\"{code}\","
            "\"request_id\":\"req_$request_id\"}';" in block
        )

    # NGINX sends the raw ID to the gateway, which derives req_<raw>.  Both
    # gateway envelopes and locally generated edge errors therefore match the
    # public X-Request-ID header.
    intake = _location(text, "location = /api/intake")
    assert "proxy_set_header X-Request-ID $request_id;" in intake
    assert 'add_header X-Request-ID "" always;' not in intake


def test_auth_forbidden_and_not_found_fail_closed_without_redirect_or_html():
    text = _config()
    expected = {
        "@invalid_request": (400, "invalid_request"),
        "@authentication_required": (401, "authentication_required"),
        "@forbidden": (403, "forbidden"),
        "@not_found": (404, "not_found"),
    }

    for target, (status, code) in expected.items():
        block = _location(text, f"location {target}")
        assert "default_type application/json;" in block
        assert (
            f"return {status} '{{\"error\":\"{code}\","
            "\"request_id\":\"req_$request_id\"}';" in block
        )
        assert "<html" not in block.lower()
    assert "@oauth2_sign_in" not in text
    assert "error_page 401 = /oauth2/start" not in text


def test_logout_clears_the_session_and_uses_only_a_fixed_local_return_path():
    text = _config()
    start = _location(text, "location = /oauth2/start")
    sign_out = _location(text, "location = /oauth2/sign_out")
    signed_out = _location(text, "location = /signed-out")

    assert (
        "proxy_pass http://127.0.0.1:4180/oauth2/start?"
        "rd=https%3A%2F%2Fapi.huboptimus.dev%2Foperator%2F;" in start
    )
    assert (
        "proxy_pass http://127.0.0.1:4180/oauth2/sign_out?"
        "rd=%2Fsigned-out;" in sign_out
    )
    assert "$arg_rd" not in sign_out
    assert "$request_uri" not in sign_out
    assert "auth_request" not in signed_out
    assert "<script" not in signed_out.lower()
    assert "https://huboptimus.dev/" in signed_out
    assert "chatgpt.site" not in signed_out
    assert (
        "https://api.huboptimus.dev/oauth2/start?"
        "rd=https%3A%2F%2Fapi.huboptimus.dev%2Foperator%2F" in signed_out
    )
    assert 'add_header Cache-Control "no-store" always;' in text
