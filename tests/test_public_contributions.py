"""Public provenance must stay narrower than activity and product claims."""

import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "site/data/contributions.v1.json"
HISTORY = ROOT / "site/data/repository-history.v1.json"


class ContributionLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = {}

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "a" and attrs.get("data-contribution-id"):
            self.links[attrs["data-contribution-id"]] = attrs["href"]


def test_history_index_covers_the_exact_reachable_graph_without_emails():
    assert HISTORY.is_file(), "missing public history index"
    history = json.loads(HISTORY.read_text(encoding="utf-8"))
    through = history["through_commit"]
    commits = subprocess.check_output(
        ["git", "log", "--format=%H%x09%cI", through], cwd=ROOT, text=True
    )
    expected = {tuple(line.split("\t")) for line in commits.splitlines()}
    actual = {(row["sha"], row["committed_at"]) for row in history["commits"]}
    assert actual == expected
    assert len(history["commits"]) == len(actual) == history["reachable_commit_count"]
    roots = subprocess.check_output(
        ["git", "rev-list", "--max-parents=0", through], cwd=ROOT, text=True
    ).splitlines()
    assert roots == [history["history_start_commit"]]
    assert all(set(row) == {"sha", "committed_at"} for row in history["commits"])


def test_external_contributions_keep_original_author_credit_and_acceptance_separate():
    assert DATA.is_file(), "missing public contribution register"
    data = json.loads(DATA.read_text(encoding="utf-8"))
    records = {record["id"]: record for record in data["contributions"]}
    assert len(records) == len(data["contributions"])
    smithy = records["smithy-2351-validation"]
    assert smithy["kind"] == "downstream-validation"
    assert smithy["contributor"]["login"] == "Voxterrae"
    assert smithy["upstream_change"]["author"] == "Alan4506"
    assert smithy["acceptance"] == "not-confirmed"
    assert smithy["hub_remediation_validated"] is False
    dotnet = records["setup-dotnet-804"]
    assert dotnet["status"] == "open"
    assert dotnet["merged_at"] is None
    cdk = records["aws-cdk-39733-follow-up"]
    assert cdk["kind"] == "release-verification-discussion"
    assert cdk["upstream_change"]["author"] == "udondan"
    assert all(record["ai_assistance"] for record in records.values())
    assert data["coverage"]["external_history_complete"] is False
    assert data["coverage"]["pending_sources"]


def test_visible_contribution_links_match_the_public_register():
    assert DATA.is_file(), "missing public contribution register"
    data = json.loads(DATA.read_text(encoding="utf-8"))
    parser = ContributionLinks()
    source = (ROOT / "site/index.html").read_text(encoding="utf-8")
    parser.feed(source)
    assert parser.links == {r["id"]: r["url"] for r in data["contributions"]}
    assert 'id="contributions"' in source
    assert './data/repository-history.v1.json' in source
    assert './obsidian-HUB_Optimus/' in source
    register = (ROOT / "docs/project/CONTRIBUTIONS_REGISTER.md").read_text(encoding="utf-8")
    assert all(r["url"] in register for r in data["contributions"])


def test_proposals_keep_their_issue_evidence_without_inventing_code_dates():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    components = {r["id"]: r for r in data["creations"]["catalogue_components"]}
    for name, issue in (("browser-linux", 2021), ("global-graph", 1880)):
        record = components[name]
        assert record["maturity"] == "issue-only"
        assert record["first_source_commit"] is None
        assert {e["url"] for e in record["evidence"]} == {
            f"https://github.com/Voxterrae/HUB_Optimus/issues/{issue}"
        }


def test_archival_origin_is_distinct_from_the_later_directory_move():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    archive = data["creations"]["historical_creations"][0]
    milestones = [archive.get(key) for key in (
        "first_public_package", "first_individual_documents",
        "archive_separation_commit", "latest_relevant_path_commit",
    )]
    assert all(milestones), "archival publication history must not be lost"
    dates = [r["committer_date"] for r in milestones]
    assert dates == sorted(dates)
    assert milestones[0]["sha"] != milestones[2]["sha"]
    for record in milestones:
        subprocess.run(["git", "cat-file", "-e", record["sha"]], cwd=ROOT, check=True)
