"""Contract check for the issue-1531 experimental scenario input."""

from pathlib import Path

from run_scenario import load_validated_scenario


REPO_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = (
    REPO_ROOT
    / "scenarios"
    / "candidates"
    / "mediator_policy_comparison_es.json"
)


def test_mediator_policy_candidate_uses_the_documented_input_shape() -> None:
    scenario = load_validated_scenario(CANDIDATE)

    assert scenario.title == "Comparación explícita de políticas con mediación"
    assert scenario.description == (
        "Escenario sintético de sensibilidad del rango de ofertas con dos "
        "partes negociadoras y una mediación externa; no representa calidad "
        "de mediación, favoritismo ni consenso real."
    )
    assert [role["name"] for role in scenario.roles] == [
        "Parte negociadora A",
        "Parte negociadora B",
        "Mediación externa",
    ]
    assert [role["role"] for role in scenario.roles] == [
        "negotiator",
        "negotiator",
        "mediator",
    ]
    assert scenario.success_criteria == {"offer": 5}
    assert scenario.max_rounds == 5
