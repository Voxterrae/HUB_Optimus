import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "site" / "operator" / "index.html"
TARGET_VIEWPORTS = (320, 360, 430, 768, 980)


def _source() -> str:
    return INDEX.read_text(encoding="utf-8")


def _styles() -> str:
    match = re.search(r"<style>(?P<css>.*?)</style>", _source(), re.DOTALL)
    assert match, "Operator must keep its static inline stylesheet"
    return match.group("css")


def _responsive_contract() -> str:
    css = _styles()
    start = "/* OPERATOR_RESPONSIVE_1810_START */"
    end = "/* OPERATOR_RESPONSIVE_1810_END */"
    assert css.count(start) == 1
    assert css.count(end) == 1
    return css.split(start, 1)[1].split(end, 1)[0]


def _css_block(source: str, marker: str) -> str:
    start = source.find(marker)
    assert start >= 0, f"missing CSS block: {marker}"
    opening = source.find("{", start + len(marker))
    assert opening >= 0, f"missing opening brace: {marker}"
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    raise AssertionError(f"unterminated CSS block: {marker}")


def _compact(source: str) -> str:
    return re.sub(r"\s+", " ", source).strip()


def test_operator_breakpoints_cover_target_widths_and_zoom_reflow_contract():
    html = _source()
    css = _styles()
    contract = _responsive_contract()

    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in html
    tablet = _compact(_css_block(css, "@media (max-width: 980px)"))
    assert (
        ".status-strip, .system-band, .flow-rail, .row, .output-grid "
        "{ grid-template-columns: 1fr;"
        in tablet
    )
    assert ".system-hero { grid-template-columns: 1fr;" in tablet
    assert ".panel, .panel.third { grid-column: 1 / -1;" in tablet

    compact = _compact(_css_block(contract, "@media (max-width: 560px)"))
    assert (
        ".topline, .footer, .actions, .advanced-shell > summary "
        "{ align-items: stretch; flex-direction: column;"
        in compact
    )
    assert ".actions button { inline-size: 100%;" in compact
    assert ".operator-language-switcher { justify-content: center;" in compact

    phone = _compact(_css_block(contract, "@media (max-width: 430px)"))
    assert ".signal-loader { gap: 0.15rem; padding: 0.5rem;" in phone
    assert ".hero, .panel { padding: 0.85rem;" in phone

    narrow = _compact(_css_block(contract, "@media (max-width: 360px)"))
    assert ".app { inline-size: min(100% - 0.5rem, var(--max));" in narrow
    assert ".hero, .panel { padding: 0.75rem;" in narrow

    assert TARGET_VIEWPORTS == (320, 360, 430, 768, 980)
    assert all(width <= 980 for width in TARGET_VIEWPORTS)
    assert all(width / 2 <= 560 for width in TARGET_VIEWPORTS)


def test_operator_controls_have_wrapping_and_touch_target_contracts():
    contract = _responsive_contract()
    compact = _compact(contract)

    assert (
        ':where(input:not([type="checkbox"]):not([type="radio"]), select, '
        "button, summary, .skip-link, .topline a) { min-block-size: 2.75rem;"
        in compact
    )
    assert (
        'input[type="checkbox"], input[type="radio"] '
        "{ block-size: 1.25rem; inline-size: 1.25rem;"
        in compact
    )
    assert (
        ".choice-control { display: inline-flex; align-items: center; gap: 0.5rem; "
        "min-block-size: 2.75rem; max-inline-size: 100%;"
        in compact
    )
    assert 'class="choice-control"><input id="claim_requires"' in _source()
    assert (
        ':where([role="tablist"], .operator-language-switcher) '
        "{ display: flex; flex-wrap: wrap; max-inline-size: 100%;"
        in compact
    )
    assert (
        '[role="tab"], .operator-language-switcher [data-operator-language] '
        "{ min-block-size: 2.75rem; min-inline-size: 2.75rem;"
        in compact
    )


def test_operator_long_urls_json_and_grid_children_have_reflow_guards():
    html = _source()
    contract = _responsive_contract()
    compact = _compact(contract)

    assert 'id="product_source_url"' in html
    assert 'id="case_json"' in html
    assert 'id="analyze_command"' in html
    assert "body { overflow-wrap: anywhere;" in compact
    assert (
        ":where(.field, .panel, .mini-card, .output-card, .system-cell, "
        ".flow-step, .chip) { min-inline-size: 0;"
        in compact
    )
    assert (
        ":where(input, textarea, select, pre) "
        "{ max-inline-size: 100%; min-inline-size: 0;"
        in compact
    )
    assert (
        ":where(pre, code, .mini-card, .output-card) "
        "{ overflow-wrap: anywhere; word-break: break-word;"
        in compact
    )


def test_operator_rtl_focus_and_reduced_motion_rules_are_structural():
    css = _styles()
    contract = _responsive_contract()
    compact = _compact(contract)

    skip_link = _css_block(css, ".skip-link")
    assert "inset-inline-start: 0.75rem" in skip_link
    assert re.search(r"(^|;)\s*left\s*:", skip_link) is None
    assert not re.search(
        r"(?m)^\s*(?:left|right|margin-left|margin-right|padding-left|padding-right)\s*:",
        contract,
    )
    assert (
        "summary:focus-visible, [role=\"tab\"]:focus-visible "
        "{ outline: 3px solid var(--brand-signal); outline-offset: 3px;"
        in compact
    )

    reduced = _compact(
        _css_block(contract, "@media (prefers-reduced-motion: reduce)")
    )
    assert "html { scroll-behavior: auto;" in reduced
    assert "transition-duration: 0.01ms !important" in reduced
    assert "animation-duration: 0.01ms !important" in reduced
    assert "animation-iteration-count: 1 !important" in reduced
    assert ".signal-loader-cell.is-current { transform: none;" in reduced
