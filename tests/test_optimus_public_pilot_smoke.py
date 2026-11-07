"""Governed native execution policy; fixtures never contact providers."""
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/optimus-public-pilot-smoke.yml'
# Set only after the reviewed product/helper commit exists; never use a branch/tag/input.
APPROVED_PRODUCT = '91ce4863d756f429d8fcae19787e56d166d69b82'


def workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding='utf-8'))


def test_pilot_runs_only_exact_reviewed_product_and_requires_gui():
    value = workflow()
    assert re.fullmatch('[0-9a-f]{40}', APPROVED_PRODUCT)
    assert APPROVED_PRODUCT not in {'0' * 40, '0790e0977c170ff8507bb73e0ec7b6e166755892'}
    event = value.get('on', value.get(True))
    assert set(event) == {'workflow_dispatch'}
    assert set(event['workflow_dispatch']['inputs']) == {'source_commit'}
    assert event['workflow_dispatch']['inputs']['source_commit']['default'] == APPROVED_PRODUCT
    job = value['jobs']['windows-smoke']
    assert job['env']['OPTIMUS_SOURCE_COMMIT'] == APPROVED_PRODUCT
    checkout = next(step for step in job['steps'] if str(step.get('uses', '')).startswith('actions/checkout@'))
    assert checkout['with']['ref'] == APPROVED_PRODUCT
    assert checkout['with']['persist-credentials'] is False
    preflight = job['steps'][0]['run']
    assert '-cne $env:OPTIMUS_SOURCE_COMMIT' in preflight
    gui = next(step for step in job['steps'] if step.get('name') == 'Required pilot GUI acceptance (no runtime installation)')
    assert 'if' not in gui
    assert '-Gui' in gui['run'] and '-SourceCommit $env:OPTIMUS_SOURCE_COMMIT' in gui['run']


def test_pilot_workflow_keeps_owner_main_public_read_only_boundaries():
    value = workflow()
    assert value['permissions'] == {'contents': 'read'}
    job = value['jobs']['windows-smoke']
    for guard in ["github.event_name == 'workflow_dispatch'", "github.repository == 'Voxterrae/HUB_Optimus'",
                  "github.repository_id == '1115264109'", 'github.event.repository.private == false',
                  "github.ref == 'refs/heads/main'", "github.actor_id == '249308740'", "github.triggering_actor == 'Voxterrae'"]:
        assert guard in job['if']
    assert job['runs-on'] == 'windows-2022' and job['timeout-minutes'] == 15
    assert value['concurrency']['cancel-in-progress'] is False
    for step in job['steps']:
        assert not any(word in str(step.get('uses', '')).lower() for word in ('upload-artifact', 'cache@', 'setup-dotnet'))
        assert 'continue-on-error' not in step
        assert 'secrets.' not in str(step)
    assert 'real_web_smoke' not in WORKFLOW.read_text() and 'searxng' not in WORKFLOW.read_text().lower()


def test_native_publication_checks_assets_after_all_publishes_before_execution():
    steps = workflow()['jobs']['windows-smoke']['steps']
    build = next(i for i, step in enumerate(steps) if step.get('name') == 'Build production suites and self-contained executables')
    verify = next(i for i, step in enumerate(steps) if step.get('name') == 'Verify fixed public pilot assets after publication')
    service = next(i for i, step in enumerate(steps) if step.get('name') == 'Real packaged host acceptance through Windows PowerShell 5.1')
    assert build < verify < service
    script = steps[verify]['run']
    assert 'Get-FileHash' in script and '-Algorithm SHA256' in script
    assert '8294911789f69f2c1262c80153ca0dddd6189e9a198b586f5fbb3beeb0d665ec' in script
    assert '5312f482daea11727c9c90a683bcf95dce587021aa6c63609b9038756eb05aae' in script
    assert '$publishedHash -cne $sourceHash' in script
    report = steps[-1]
    assert report['if'] == '${{ always() }}'
    assert 'optimus-public-assets.json' in report['run']
