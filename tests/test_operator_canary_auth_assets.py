import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'site/operator/index.html'
OPERATOR_AUTH = ROOT / 'site/operator/auth.v1.js'
OPERATOR_RUNTIME_CONFIG = ROOT / 'site/operator/runtime-config.v1.js'
NODE = shutil.which('node')

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_default_private_auth_initialization_never_fetches_or_persists():
    runtime_config = _read(OPERATOR_RUNTIME_CONFIG)
    auth = _read(OPERATOR_AUTH)
    smoke = f"""
const vm = require("node:vm");
const {{webcrypto}} = require("node:crypto");
const {{TextEncoder, TextDecoder}} = require("node:util");
const stored = new Map();
let fetches = 0;
const context = {{
  URL,
  URLSearchParams,
  TextEncoder,
  TextDecoder,
  Uint8Array,
  crypto: webcrypto,
  btoa: (value) => Buffer.from(value, "binary").toString("base64"),
  atob: (value) => Buffer.from(value, "base64").toString("binary"),
  sessionStorage: {{
    getItem(key) {{ return stored.get(key) ?? null; }},
    setItem(key, value) {{ stored.set(key, String(value)); }},
    removeItem(key) {{ stored.delete(key); }}
  }},
  fetch: async () => {{ fetches += 1; throw new Error("disabled auth fetched"); }},
  location: {{assign() {{ throw new Error("disabled auth navigated"); }}}}
}};
context.globalThis = context;
vm.createContext(context);
vm.runInContext({json.dumps(runtime_config)}, context);
vm.runInContext({json.dumps(auth)}, context);
(async () => {{
  const state = await context.HUB_OPTIMUS_OPERATOR_AUTH.initialize();
  if (state.state !== "disabled" || state.enabled || state.authenticated) throw new Error("default not disabled");
  if (fetches !== 0) throw new Error("disabled auth fetched");
  if (stored.size !== 0) throw new Error("disabled auth persisted state");
  if (context.HUB_OPTIMUS_OPERATOR_AUTH.getAccessToken() !== null) throw new Error("disabled token exists");
}})().catch((error) => {{ console.error(error); process.exitCode = 1; }});
"""
    completed = subprocess.run(
        [NODE, "-"], input=smoke, text=True, capture_output=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_private_auth_rejects_non_output_domains_before_any_fetch():
    auth = _read(OPERATOR_AUTH)
    smoke = f"""
const vm = require("node:vm");
const {{webcrypto}} = require("node:crypto");
const {{TextEncoder, TextDecoder}} = require("node:util");
const AUTH_SOURCE = {json.dumps(auth)};
const BASE = {{
  schemaVersion: "1.0",
  enabled: true,
  apiInvokeUrl: "https://abc123.execute-api.eu-west-1.amazonaws.com/",
  authorizationEndpoint: "https://hub-optimus-private.auth.eu-west-1.amazoncognito.com/oauth2/authorize",
  tokenEndpoint: "https://hub-optimus-private.auth.eu-west-1.amazoncognito.com/oauth2/token",
  logoutEndpoint: "https://hub-optimus-private.auth.eu-west-1.amazoncognito.com/logout",
  issuer: "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_example",
  clientId: "4exampleclientid9",
  callbackUrl: "https://huboptimus.dev/operator/",
  logoutUrl: "https://huboptimus.dev/operator/",
  scope: "operator/intake"
}};
async function rejects(config) {{
  let fetches = 0;
  const context = {{
    URL,
    URLSearchParams,
    TextEncoder,
    TextDecoder,
    Uint8Array,
    crypto: webcrypto,
    btoa: (value) => Buffer.from(value, "binary").toString("base64"),
    atob: (value) => Buffer.from(value, "base64").toString("binary"),
    sessionStorage: {{getItem() {{ return null; }}, setItem() {{}}, removeItem() {{}}}},
    fetch: async () => {{ fetches += 1; throw new Error("must not fetch"); }},
    location: {{assign() {{ throw new Error("must not navigate"); }}}},
    HUB_OPTIMUS_OPERATOR_RUNTIME_CONFIG: Object.freeze(config)
  }};
  context.globalThis = context;
  vm.createContext(context);
  vm.runInContext(AUTH_SOURCE, context);
  let code = null;
  try {{ await context.HUB_OPTIMUS_OPERATOR_AUTH.initialize(); }}
  catch (error) {{ code = error.code; }}
  if (code !== "config_invalid") throw new Error(`unexpected config result: ${{code}}`);
  if (fetches !== 0) throw new Error("invalid configuration fetched");
}}
(async () => {{
  await rejects({{...BASE, apiInvokeUrl: "https://collector.example/"}});
  await rejects({{
    ...BASE,
    authorizationEndpoint: "https://login.example/oauth2/authorize",
    tokenEndpoint: "https://login.example/oauth2/token",
    logoutEndpoint: "https://login.example/logout"
  }});
  await rejects({{...BASE, issuer: "https://issuer.example/eu-west-1_example"}});
}})().catch((error) => {{ console.error(error); process.exitCode = 1; }});
"""
    completed = subprocess.run(
        [NODE, "-"], input=smoke, text=True, capture_output=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_mismatched_oauth_callback_consumes_pending_transaction_without_fetch():
    auth = _read(OPERATOR_AUTH)
    smoke = f"""
const vm = require("node:vm");
const {{webcrypto}} = require("node:crypto");
const {{TextEncoder, TextDecoder}} = require("node:util");
const key = "hub_optimus.operator.oauth.pending.v1";
const config = {{
  schemaVersion: "1.0",
  enabled: true,
  apiInvokeUrl: "https://abc123.execute-api.eu-west-1.amazonaws.com/",
  authorizationEndpoint: "https://hub-optimus-private.auth.eu-west-1.amazoncognito.com/oauth2/authorize",
  tokenEndpoint: "https://hub-optimus-private.auth.eu-west-1.amazoncognito.com/oauth2/token",
  logoutEndpoint: "https://hub-optimus-private.auth.eu-west-1.amazoncognito.com/logout",
  issuer: "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_example",
  clientId: "4exampleclientid9",
  callbackUrl: "https://huboptimus.dev/operator/",
  logoutUrl: "https://huboptimus.dev/operator/",
  scope: "operator/intake"
}};
const values = new Map([[key, JSON.stringify({{
  version: 1,
  verifier: "a".repeat(43),
  state: "b".repeat(43),
  nonce: "c".repeat(43),
  createdAt: Date.now(),
  clientId: config.clientId,
  callbackUrl: config.callbackUrl,
  scope: config.scope
}})]]);
let fetches = 0;
const context = {{
  URL,
  URLSearchParams,
  TextEncoder,
  TextDecoder,
  Uint8Array,
  crypto: webcrypto,
  btoa: (value) => Buffer.from(value, "binary").toString("base64"),
  atob: (value) => Buffer.from(value, "base64").toString("binary"),
  sessionStorage: {{
    getItem(name) {{ return values.get(name) ?? null; }},
    setItem(name, value) {{ values.set(name, String(value)); }},
    removeItem(name) {{ values.delete(name); }}
  }},
  fetch: async () => {{ fetches += 1; throw new Error("must not fetch"); }},
  location: {{assign() {{}}}},
  HUB_OPTIMUS_OPERATOR_RUNTIME_CONFIG: Object.freeze(config),
  __HUB_OPTIMUS_OPERATOR_OAUTH_CALLBACK_V1__: Object.freeze({{
    callbackUrl: config.callbackUrl,
    code: Object.freeze(["one-time-code"]),
    state: Object.freeze(["d".repeat(43)])
  }})
}};
context.globalThis = context;
vm.createContext(context);
vm.runInContext({json.dumps(auth)}, context);
(async () => {{
  let code = null;
  try {{ await context.HUB_OPTIMUS_OPERATOR_AUTH.initialize(); }}
  catch (error) {{ code = error.code; }}
  if (code !== "state_mismatch") throw new Error(`unexpected callback result: ${{code}}`);
  if (values.size !== 0) throw new Error("mismatched callback retained transaction");
  if (fetches !== 0) throw new Error("mismatched callback fetched");
}})().catch((error) => {{ console.error(error); process.exitCode = 1; }});
"""
    completed = subprocess.run(
        [NODE, "-"], input=smoke, text=True, capture_output=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_private_auth_uses_pkce_session_transaction_and_memory_only_tokens():
    auth = _read(OPERATOR_AUTH)
    smoke = f"""
const vm = require("node:vm");
const {{webcrypto}} = require("node:crypto");
const {{TextEncoder, TextDecoder}} = require("node:util");
const AUTH_SOURCE = {json.dumps(auth)};
const CONFIG = {{
  schemaVersion: "1.0",
  enabled: true,
  apiInvokeUrl: "https://abc123.execute-api.eu-west-1.amazonaws.com/",
  authorizationEndpoint: "https://hub-optimus-private.auth.eu-west-1.amazoncognito.com/oauth2/authorize",
  tokenEndpoint: "https://hub-optimus-private.auth.eu-west-1.amazoncognito.com/oauth2/token",
  logoutEndpoint: "https://hub-optimus-private.auth.eu-west-1.amazoncognito.com/logout",
  issuer: "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_example",
  clientId: "4exampleclientid9",
  callbackUrl: "https://huboptimus.dev/operator/",
  logoutUrl: "https://huboptimus.dev/operator/",
  scope: "operator/intake"
}};
const values = new Map();
const writes = [];
const sessionStorage = {{
  getItem(key) {{ return values.get(key) ?? null; }},
  setItem(key, value) {{ values.set(key, String(value)); writes.push(String(value)); }},
  removeItem(key) {{ values.delete(key); }}
}};

function contextFor(fetchImpl) {{
  const context = {{
    URL,
    URLSearchParams,
    TextEncoder,
    TextDecoder,
    Uint8Array,
    Date,
    Number,
    String,
    Error,
    Promise,
    crypto: webcrypto,
    btoa: (value) => Buffer.from(value, "binary").toString("base64"),
    atob: (value) => Buffer.from(value, "base64").toString("binary"),
    sessionStorage,
    fetch: fetchImpl,
    assigned: null,
    location: {{ assign(value) {{ context.assigned = value; }} }}
  }};
  context.globalThis = context;
  vm.createContext(context);
  vm.runInContext(`globalThis.HUB_OPTIMUS_OPERATOR_RUNTIME_CONFIG = Object.freeze(${{JSON.stringify(CONFIG)}});`, context);
  return context;
}}

function jwt(payload) {{
  const part = (value) => Buffer.from(JSON.stringify(value)).toString("base64url");
  return `${{part({{alg: "RS256", typ: "JWT"}})}}.${{part(payload)}}.signature`;
}}

(async () => {{
  const loginContext = contextFor(async () => {{ throw new Error("login must not fetch"); }});
  vm.runInContext(AUTH_SOURCE, loginContext);
  await loginContext.HUB_OPTIMUS_OPERATOR_AUTH.login();
  const authorize = new URL(loginContext.assigned);
  if (authorize.searchParams.get("code_challenge_method") !== "S256") throw new Error("S256 missing");
  if (authorize.searchParams.get("scope") !== "openid email operator/intake") throw new Error("scope drift");
  if (authorize.searchParams.get("redirect_uri") !== "https://huboptimus.dev/operator/") throw new Error("callback drift");
  for (const field of ["state", "nonce", "code_challenge"]) {{
    if (!/^[A-Za-z0-9_-]{{43}}$/.test(authorize.searchParams.get(field) || "")) throw new Error(`${{field}} invalid`);
  }}
  const transaction = JSON.parse(Array.from(values.values())[0]);
  if (!/^[A-Za-z0-9_-]{{43}}$/.test(transaction.verifier)) throw new Error("verifier invalid");
  if (writes.some((value) => value.includes("access_token") || value.includes("id_token"))) {{
    throw new Error("token persisted during login");
  }}

  const now = Math.floor(Date.now() / 1000);
  const idToken = jwt({{
    token_use: "id", aud: CONFIG.clientId, iss: CONFIG.issuer,
    sub: "private-user", exp: now + 600, nonce: transaction.nonce
  }});
  const accessToken = jwt({{
    token_use: "access", client_id: CONFIG.clientId, iss: CONFIG.issuer,
    sub: "private-user", exp: now + 600, scope: "openid email operator/intake"
  }});
  const requests = [];
  const callbackContext = contextFor(async (url, options) => {{
    requests.push({{url, options}});
    return {{
      ok: true,
      status: 200,
      async json() {{
        return {{
          access_token: accessToken,
          id_token: idToken,
          refresh_token: "ignored-refresh-token",
          token_type: "Bearer",
          expires_in: 600
        }};
      }}
    }};
  }});
  vm.runInContext(
    `globalThis.__HUB_OPTIMUS_OPERATOR_OAUTH_CALLBACK_V1__ = Object.freeze({{
      callbackUrl: "https://huboptimus.dev/operator/",
      code: Object.freeze(["one-time-code"]),
      state: Object.freeze([${{JSON.stringify(transaction.state)}}])
    }});`,
    callbackContext
  );
  vm.runInContext(AUTH_SOURCE, callbackContext);
  await callbackContext.HUB_OPTIMUS_OPERATOR_AUTH.initialize();
  if (!callbackContext.HUB_OPTIMUS_OPERATOR_AUTH.isAuthenticated()) throw new Error("not authenticated");
  if (callbackContext.HUB_OPTIMUS_OPERATOR_AUTH.getAccessToken() !== accessToken) throw new Error("access token mismatch");
  if (callbackContext.HUB_OPTIMUS_OPERATOR_AUTH.getIntakeEndpoint() !== "https://abc123.execute-api.eu-west-1.amazonaws.com/intake/url") {{
    throw new Error("raw API output not mapped to intake route");
  }}
  if (requests.length !== 1 || requests[0].url !== CONFIG.tokenEndpoint) throw new Error("unexpected fetch target");
  const form = new URLSearchParams(requests[0].options.body);
  if (form.get("code_verifier") !== transaction.verifier || form.get("code") !== "one-time-code") {{
    throw new Error("authorization code exchange is not bound to verifier");
  }}
  if (requests[0].options.body.includes("client_secret")) throw new Error("public client sent a secret");
  if (values.size !== 0) throw new Error("transaction not consumed");
  if (writes.some((value) => value.includes(accessToken) || value.includes(idToken) || value.includes("ignored-refresh-token"))) {{
    throw new Error("token persisted");
  }}

  callbackContext.HUB_OPTIMUS_OPERATOR_AUTH.logout();
  const logout = new URL(callbackContext.assigned);
  if (logout.origin + logout.pathname !== CONFIG.logoutEndpoint) throw new Error("logout endpoint drift");
  if (logout.searchParams.get("logout_uri") !== "https://huboptimus.dev/operator/") throw new Error("logout URI drift");
  if (callbackContext.HUB_OPTIMUS_OPERATOR_AUTH.getAccessToken() !== null) throw new Error("logout kept token");
}})().catch((error) => {{ console.error(error); process.exitCode = 1; }});
"""
    completed = subprocess.run(
        [NODE, "-"], input=smoke, text=True, capture_output=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


def test_canary_assets_are_disabled_and_not_loaded_by_canonical_operator():
    config = _read(OPERATOR_RUNTIME_CONFIG)
    html = _read(INDEX)

    assert 'enabled: false' in config
    assert 'apiInvokeUrl: ""' in config
    assert 'authorizationEndpoint: ""' in config
    assert 'tokenEndpoint: ""' in config
    assert 'logoutEndpoint: ""' in config
    assert 'issuer: ""' in config
    assert 'clientId: ""' in config
    assert 'callbackUrl: "https://huboptimus.dev/operator/"' in config
    assert 'logoutUrl: "https://huboptimus.dev/operator/"' in config
    assert 'scope: "operator/intake"' in config
    assert re.search(r"\bAKIA[0-9A-Z]{16}\b", config) is None
    assert re.search(r"\bBearer\s+[A-Za-z0-9._~-]+", config) is None
    assert '<script src="./runtime-config.v1.js"></script>' not in html
    assert '<script src="./auth.v1.js"></script>' not in html
    assert re.search(r'<script[^>]+src="https?://', html) is None
    sw = _read(ROOT / "site/operator/sw.js")
    assert "runtime-config.v1.js" not in sw
    assert "auth.v1.js" not in sw
