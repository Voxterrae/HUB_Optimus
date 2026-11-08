"""Local mutation checks for the deliberately non-deployable Azure proposal."""

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path


AZURE = Path(__file__).resolve().parent / "azure"
SPEC = importlib.util.spec_from_file_location("azure_proposal", AZURE / "validate_proposal.py")
PROPOSAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROPOSAL)


class AzureProposalTests(unittest.TestCase):
    def setUp(self):
        self.template = PROPOSAL.load_json(AZURE / "main.proposal.json")
        self.parameters = PROPOSAL.load_json(AZURE / "parameters.draft.json")
        self.manifest = PROPOSAL.load_json(AZURE / "promotion-manifest.draft.json")
        self.environment, self.app = self.template["resources"]

    def validate(self):
        return PROPOSAL.validate(self.template, self.parameters, self.manifest)

    def test_review_files_are_inert(self):
        self.assertTrue(self.validate())

    def test_true_or_truthy_activation_parameters_rejected(self):
        for activation in (True, "true", "false", 1, 0, None):
            with self.subTest(activation=activation):
                self.parameters["parameters"]["deployEnabled"]["value"] = activation
                with self.assertRaises(PROPOSAL.ProposalError):
                    self.validate()

    def test_gate_cannot_be_opened_by_allowed_value_edit(self):
        for allowed_values in ([False, True], [True], [], [0]):
            with self.subTest(allowed_values=allowed_values):
                self.template["parameters"]["deployEnabled"]["allowedValues"] = allowed_values
                with self.assertRaises(PROPOSAL.ProposalError):
                    self.validate()

    def test_true_or_missing_gate_default_rejected(self):
        for value in (True, "false", 0, None):
            with self.subTest(value=value):
                self.template["parameters"]["deployEnabled"]["defaultValue"] = value
                with self.assertRaises(PROPOSAL.ProposalError):
                    self.validate()

    def test_all_resources_require_exact_false_only_gate(self):
        for index in range(len(self.template["resources"])):
            for condition in (True, False, "[true()]", None):
                candidate = copy.deepcopy(self.template)
                candidate["resources"][index]["condition"] = condition
                with self.subTest(index=index, condition=condition), self.assertRaises(PROPOSAL.ProposalError):
                    PROPOSAL.validate(candidate, self.parameters, self.manifest)

    def test_extra_or_nested_resources_rejected(self):
        for resource_type in ("Microsoft.OperationalInsights/workspaces", "Microsoft.Insights/components", "Microsoft.ContainerRegistry/registries", "Microsoft.Storage/storageAccounts", "Microsoft.Insights/diagnosticSettings", "Microsoft.Resources/deployments"):
            candidate = copy.deepcopy(self.template)
            candidate["resources"].append({"type": resource_type, "condition": PROPOSAL.CONDITION})
            with self.subTest(resource_type=resource_type), self.assertRaises(PROPOSAL.ProposalError):
                PROPOSAL.validate(candidate, self.parameters, self.manifest)
        self.app["resources"] = [{"type": "Microsoft.Insights/diagnosticSettings"}]
        with self.assertRaises(PROPOSAL.ProposalError):
            self.validate()

    def test_public_or_plaintext_or_alternate_port_ingress_rejected(self):
        for name, value in (("external", True), ("external", 0), ("allowInsecure", True), ("allowInsecure", 0), ("transport", "tcp"), ("targetPort", 80), ("additionalPortMappings", [{"targetPort": 8081}])):
            candidate = copy.deepcopy(self.template)
            candidate["resources"][1]["properties"]["configuration"]["ingress"][name] = value
            with self.subTest(name=name), self.assertRaises(PROPOSAL.ProposalError):
                PROPOSAL.validate(candidate, self.parameters, self.manifest)

    def test_cpu_memory_replica_and_revision_expansion_rejected(self):
        mutations = [
            ("scale", "minReplicas", 1), ("scale", "maxReplicas", 2),
            ("resources", "cpu", 0.5), ("resources", "memory", "1Gi"),
            ("configuration", "activeRevisionsMode", "Multiple"),
            ("configuration", "maxInactiveRevisions", 10),
        ]
        for scope, key, value in mutations:
            candidate = copy.deepcopy(self.template)
            props = candidate["resources"][1]["properties"]
            target = props["configuration"] if scope == "configuration" else props["template"]["scale"] if scope == "scale" else props["template"]["containers"][0]["resources"]
            target[key] = value
            with self.subTest(scope=scope, key=key), self.assertRaises(PROPOSAL.ProposalError):
                PROPOSAL.validate(candidate, self.parameters, self.manifest)

    def test_probe_thresholds_and_intervals_remain_bounded(self):
        for index in (0, 1):
            for key, value in (("periodSeconds", 0), ("periodSeconds", 241), ("failureThreshold", 0), ("failureThreshold", 30), ("timeoutSeconds", 2)):
                candidate = copy.deepcopy(self.template)
                candidate["resources"][1]["properties"]["template"]["containers"][0]["probes"][index][key] = value
                with self.subTest(index=index, key=key, value=value), self.assertRaises(PROPOSAL.ProposalError):
                    PROPOSAL.validate(candidate, self.parameters, self.manifest)

    def test_log_storage_registry_or_credential_mount_requires_promotion_review(self):
        self.environment["properties"]["appLogsConfiguration"]["destination"] = "log-analytics"
        with self.assertRaises(PROPOSAL.ProposalError):
            self.validate()
        self.environment["properties"]["appLogsConfiguration"]["destination"] = "none"
        for key, value in (("registries", []), ("secrets", []), ("dapr", {"enabled": True})):
            self.app["properties"]["configuration"][key] = value
            with self.subTest(key=key), self.assertRaises(PROPOSAL.ProposalError):
                self.validate()
            del self.app["properties"]["configuration"][key]
        self.app["properties"]["template"]["volumes"] = [{"name": "credentials", "storageType": "Secret"}]
        with self.assertRaises(PROPOSAL.ProposalError):
            self.validate()

    def test_unknown_activation_parameter_or_secret_reference_rejected(self):
        self.parameters["parameters"]["externalIngress"] = {"value": True}
        with self.assertRaises(PROPOSAL.ProposalError):
            self.validate()
        del self.parameters["parameters"]["externalIngress"]
        self.parameters["parameters"]["imageDigestRef"] = {"reference": {"keyVault": {"id": "unreviewed"}, "secretName": "secret"}}
        with self.assertRaises(PROPOSAL.ProposalError):
            self.validate()

    def test_mutable_image_tags_rejected(self):
        self.parameters["parameters"]["imageDigestRef"]["value"] = "registry.invalid/remote:latest"
        with self.assertRaises(PROPOSAL.ProposalError):
            self.validate()

    def test_inferred_scope_or_approval_rejected(self):
        self.manifest["scope"]["subscriptionId"] = "guessed"
        with self.assertRaises(PROPOSAL.ProposalError):
            self.validate()
        self.manifest["scope"]["subscriptionId"] = None
        for gate in ("permissions", "economics", "release", "credentials", "networkAndPrivacy"):
            self.manifest[gate]["approved"] = True
            with self.subTest(gate=gate), self.assertRaises(PROPOSAL.ProposalError):
                self.validate()
            self.manifest[gate]["approved"] = False

    def test_application_does_not_receive_inline_credentials_or_unrestricted_http(self):
        container = self.app["properties"]["template"]["containers"][0]
        container["env"] = [{"name": "ASPNETCORE_URLS", "value": "http://*:80"}]
        with self.assertRaises(PROPOSAL.ProposalError):
            self.validate()
        container["env"] = [{"name": "OPTIMUS_REMOTE_CREDENTIALS", "value": "inline material"}]
        with self.assertRaises(PROPOSAL.ProposalError):
            self.validate()

    def test_docker_recipe_is_narrow_and_cannot_build_with_defaults(self):
        recipe = (AZURE / "Dockerfile").read_text(encoding="utf-8")
        image_args = [line for line in recipe.splitlines() if line.startswith("ARG DOTNET_")]
        self.assertEqual(len(image_args), 2)
        for line in image_args:
            self.assertIn("registry.invalid/", line)
            self.assertIn("@sha256:" + "0" * 64, line)
        self.assertNotIn("COPY .", recipe)
        self.assertNotIn("ADD ", recipe)
        self.assertNotIn("credentials.json", recipe)
        self.assertIn("USER 1654:1654", recipe)
        self.assertIn('ENTRYPOINT ["dotnet", "Optimus.Search.Remote.dll"]', recipe)
        search_root = AZURE.parents[2]
        for relative in ("remote/src/Optimus.Search.Remote/Optimus.Search.Remote.csproj", "src/Optimus.Search/LocalSearchIndex.cs", "src/Optimus.Search/SearchModels.cs", "catalog/public-pilot-v0.1.json", "catalog/public-pilot-v0.1.provenance.json"):
            with self.subTest(relative=relative):
                self.assertTrue((search_root / relative).is_file())

    def test_docker_build_enforces_the_repository_sdk_version(self):
        search_root = AZURE.parents[2]
        sdk_version = PROPOSAL.load_json(search_root / "global.json")["sdk"]["version"]
        recipe = (AZURE / "Dockerfile").read_text(encoding="utf-8")
        context_rules = (AZURE / "Dockerfile.dockerignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("!global.json", context_rules)
        copy_sdk = "COPY global.json ./"
        verify_sdk = f'RUN test "$(dotnet --version)" = "{sdk_version}"'
        restore = "RUN dotnet restore "
        self.assertIn(copy_sdk, recipe)
        self.assertIn(verify_sdk, recipe)
        self.assertLess(recipe.index(copy_sdk), recipe.index(verify_sdk))
        self.assertLess(recipe.index(verify_sdk), recipe.index(restore))

    def test_duplicate_json_properties_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "duplicate.json"
            source.write_text('{"deployEnabled": false, "deployEnabled": true}', encoding="utf-8")
            with self.assertRaises(PROPOSAL.ProposalError):
                PROPOSAL.load_json(source)


if __name__ == "__main__":
    unittest.main()
