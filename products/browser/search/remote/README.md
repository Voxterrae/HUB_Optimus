# Optimus Search: remote pilot candidate

Separate .NET 10 API for the eight-reference public catalog from #2082, prepared under #2079. This is a review candidate, not a deployed service. The device-local SearchHost protocol, native defaults and original catalog bytes remain unchanged.

Read [remote protocol](docs/REMOTE_PROTOCOL.md), [OpenAPI](docs/openapi.json), [design](docs/DESIGN.md), [Azure cost comparison](docs/AZURE_COSTS.md) and [decisions before a shared service](docs/NEXT_SERVICE_DECISIONS.md). The [inert Azure proposal](ops/azure/README.md) cannot be activated through its parameter file and has no credential mount.

Prerequisites: .NET SDK10.0.403 and Python3. Runtime uses only the ASP.NET shared framework and two compile-linked existing ranking/model files; no new NuGet package. Original catalog tests additionally require pytest.

From repository root:

```sh
dotnet run --project products/browser/search/remote/tests/Optimus.Search.Remote.Tests --no-launch-profile
python -m unittest discover -s products/browser/search/remote/tests_python -v
python -m unittest discover -s products/browser/search/remote/ops -v
python products/browser/search/remote/ops/azure/validate_proposal.py
dotnet publish products/browser/search/remote/src/Optimus.Search.Remote -c Release -o /absolute/local/output
python products/browser/search/remote/tools/run_live_acceptance.py /absolute/local/output/Optimus.Search.Remote.dll
```

The live acceptance uses disposable random credentials, starts only loopback8080, verifies all eight topics plus an empty result using an independent Python content verifier, checks stdout/stderr silence and stops its own process. It refuses an occupied port. It does not contact Azure or an external source. Test results and review corrections are recorded in [TEST_EVIDENCE](tests/TEST_EVIDENCE.md).

For an operator-controlled local run, provision a private registry using the exact credential contract, set `OPTIMUS_REMOTE_CREDENTIALS_FILE` to its absolute path outside the application directory and run the published DLL. Missing/invalid registry fails closed. Keep `OPTIMUS_REMOTE_CONTAINER_HTTP` unset: default is loopbackHTTP8080. The exact `true` opt-in is only for a private container hop behind reviewed HTTPS ingress, not a local public listener. Registry files and bearer secrets must remain outside the source/image; runtime's lexical app-directory check cannot prove all mount/symlink properties.

No client adapter, public identity registration, external search provider, telemetry sink, deployment workflow, resource creation or production acceptance is included. Per-process resource limits reduce exposure but do not form a distributed quota or Azure monetary cap.
