import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
PUBLIC_ORIGIN = "https://huboptimus.dev"
EVIDENCE_REF = "f99bfed196dbcb76c8a29a4bab31559fdb567ee5"
PUBLIC_ROUTES = {
    "/": SITE / "index.html",
    "/404.html": SITE / "404.html",
    "/operator/": SITE / "operator" / "index.html",
}


class PublicHtmlParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.duplicate_ids = set()
        self.references = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        element_id = attrs.get("id")
        if element_id:
            if element_id in self.ids:
                self.duplicate_ids.add(element_id)
            self.ids.add(element_id)

        for attribute in ("href", "src", "data-geo-source"):
            value = attrs.get(attribute)
            if value:
                self.references.append((tag, attribute, value))

        if tag == "meta" and attrs.get("property") == "og:image":
            value = attrs.get("content")
            if value:
                self.references.append((tag, "content", value))


def parse_document(path):
    parser = PublicHtmlParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def route_for_document(path):
    for route, candidate in PUBLIC_ROUTES.items():
        if candidate == path:
            return route
    raise AssertionError(f"public HTML file has no declared route: {path}")


def target_for_public_reference(page_route, reference):
    absolute = urlsplit(urljoin(f"{PUBLIC_ORIGIN}{page_route}", reference))
    if absolute.scheme not in {"http", "https"}:
        raise AssertionError(f"unsupported public URL scheme: {reference}")
    if absolute.netloc != "huboptimus.dev":
        return None, absolute

    public_path = unquote(absolute.path)
    target = (SITE / public_path.lstrip("/")).resolve()
    assert target.is_relative_to(SITE.resolve()), reference
    if public_path.endswith("/") or target.is_dir():
        target /= "index.html"
    return target, absolute


def css_rule_property(source, selector, property_name):
    values = []
    pattern = re.compile(
        rf"{re.escape(selector)}\s*\{{(?P<body>[^{{}}]*)\}}",
        re.MULTILINE | re.DOTALL,
    )
    for match in pattern.finditer(source):
        declarations = re.findall(
            rf"(?:^|;)\s*{re.escape(property_name)}\s*:\s*([^;]+)",
            match.group("body"),
            re.MULTILINE,
        )
        values.extend(value.strip() for value in declarations)
    assert values, f"{selector} has no {property_name} declaration"
    return values[-1]


def custom_properties(source):
    root = re.search(r":root\s*\{(?P<body>[^{}]*)\}", source, re.DOTALL)
    assert root, "CSS :root block is required"
    return dict(
        re.findall(
            r"--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;",
            root.group("body"),
        )
    )


def rgb_from_hex(value):
    assert re.fullmatch(r"#[0-9a-fA-F]{6}", value), value
    return tuple(int(value[index : index + 2], 16) / 255 for index in (1, 3, 5))


def relative_luminance(value):
    def linearize(channel):
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linearize(channel) for channel in rgb_from_hex(value))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground, background):
    lighter, darker = sorted(
        (relative_luminance(foreground), relative_luminance(background)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def test_every_public_html_reference_and_fragment_resolves_in_the_artifact():
    html_files = set(SITE.rglob("*.html"))
    assert html_files == set(PUBLIC_ROUTES.values())

    documents = {path: parse_document(path) for path in html_files}
    for path, document in documents.items():
        assert not document.duplicate_ids, (path, document.duplicate_ids)
        page_route = route_for_document(path)
        for _tag, _attribute, reference in document.references:
            target, absolute = target_for_public_reference(page_route, reference)
            if target is None:
                continue
            assert target.is_file(), (path, reference, target)
            if absolute.fragment:
                assert target.suffix == ".html", (path, reference)
                target_document = documents.get(target) or parse_document(target)
                assert absolute.fragment in target_document.ids, (path, reference)


def test_repository_evidence_links_are_commit_pinned_and_resolve_locally():
    evidence_pattern = re.compile(
        r"^https://github\.com/Voxterrae/HUB_Optimus/"
        r"(?P<kind>blob|tree)/(?P<ref>[0-9a-f]{40})/(?P<path>.+)$"
    )
    checked = []
    live_repository_documents = {
        "https://github.com/Voxterrae/HUB_Optimus/blob/main/IP_NOTICE.md",
        "https://github.com/Voxterrae/HUB_Optimus/blob/main/SECURITY.md",
    }

    for path in PUBLIC_ROUTES.values():
        for tag, attribute, reference in parse_document(path).references:
            if tag != "a" or attribute != "href":
                continue
            if "/blob/main/" in reference or "/tree/main/" in reference:
                assert reference in live_repository_documents
                continue
            match = evidence_pattern.match(reference)
            if not match:
                continue

            repository_path = ROOT / unquote(match.group("path"))
            assert match.group("ref") == EVIDENCE_REF, reference
            if match.group("kind") == "blob":
                assert repository_path.is_file(), reference
            else:
                assert repository_path.is_dir(), reference
            checked.append(reference)

    assert len(checked) == 18


def test_live_external_navigation_targets_are_explicit_and_network_free_in_pytest():
    expected_navigation = {
        "https://github.com/Voxterrae/HUB_Optimus",
        "https://github.com/Voxterrae/HUB_Optimus/blob/main/IP_NOTICE.md",
        "https://github.com/Voxterrae/HUB_Optimus/blob/main/SECURITY.md",
        "https://github.com/Voxterrae/HUB_Optimus/issues",
        "https://github.com/Voxterrae/HUB-Optimus-labs",
    }
    external_navigation = set()

    for path in PUBLIC_ROUTES.values():
        route = route_for_document(path)
        for tag, attribute, reference in parse_document(path).references:
            if tag != "a" or attribute != "href":
                continue
            absolute = urlsplit(urljoin(f"{PUBLIC_ORIGIN}{route}", reference))
            assert absolute.scheme in {"http", "https"}
            if absolute.netloc == "huboptimus.dev":
                continue
            if re.match(
                r"^https://github\.com/Voxterrae/HUB_Optimus/"
                r"(?:blob|tree)/[0-9a-f]{40}/",
                reference,
            ):
                continue
            external_navigation.add(reference)

    assert external_navigation == expected_navigation


def test_reported_dark_surface_normal_text_uses_one_contrast_guarded_token():
    css = (SITE / "styles.css").read_text(encoding="utf-8")
    properties = custom_properties(css)
    muted = properties["text-muted-dark"]
    conservative_dark_surface = properties["graphite-3"]

    selectors = (
        ".truth-strip dt",
        ".globe-toolbar small",
        ".globe-card figcaption",
        ".card-topline > span",
        ".site-footer p",
    )
    for selector in selectors:
        assert css_rule_property(css, selector, "color") == "var(--text-muted-dark)"

    assert contrast_ratio(muted, conservative_dark_surface) >= 4.5


def test_404_and_operator_muted_text_pairs_remain_above_normal_text_minimum():
    not_found = (SITE / "404.html").read_text(encoding="utf-8")
    not_found_foreground = css_rule_property(not_found, ".review-note", "color")
    assert contrast_ratio(not_found_foreground, "#18232f") >= 4.5

    operator = (SITE / "operator" / "index.html").read_text(encoding="utf-8")
    properties = custom_properties(operator)
    assert css_rule_property(operator, ".footer", "color") == "var(--dim)"
    assert css_rule_property(operator, ".topline", "color") == "var(--dim)"
    assert (
        contrast_ratio(
            properties["brand-signal-dim"],
            properties["brand-signal-panel-2"],
        )
        >= 4.5
    )
