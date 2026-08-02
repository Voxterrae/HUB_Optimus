import json
import os
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
APP = SITE / "app.js"
STYLES = SITE / "styles.css"
NOT_FOUND = SITE / "404.html"
OPERATOR = SITE / "operator" / "index.html"


def extract_css(source):
    match = re.search(r"<style>(?P<css>.*?)</style>", source, re.DOTALL)
    assert match, "inline style block is required"
    return match.group("css")


def css_block(source, marker):
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


def compact_css(source):
    return re.sub(r"\s+", " ", source).strip()


class EntryPointParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.language_buttons = set()
        self.positive_tabindexes = []
        self.skip_links = set()
        self.viewports = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "meta" and attrs.get("name") == "viewport":
            self.viewports.append(attrs.get("content"))
        if tag == "button" and attrs.get("data-language"):
            self.language_buttons.add(attrs["data-language"])
        if tag == "a" and "skip-link" in (attrs.get("class") or "").split():
            self.skip_links.add(attrs.get("href"))

        tabindex = attrs.get("tabindex")
        if tabindex is None:
            return
        try:
            numeric_tabindex = int(tabindex)
        except ValueError:
            return
        if numeric_tabindex > 0:
            self.positive_tabindexes.append((tag, tabindex))


def parse_entry_point(source):
    parser = EntryPointParser()
    parser.feed(source)
    return parser


def run_globe_dom_probe(*, reduced_motion, renderer_available):
    node = shutil.which("node")
    assert node, "Node.js is required to execute the public interaction probe"
    harness = r"""
const fs = require("fs");
const vm = require("vm");

class ClassList {
  constructor() { this.values = new Set(); }
  add(...values) { values.forEach((value) => this.values.add(value)); }
  remove(...values) { values.forEach((value) => this.values.delete(value)); }
  toggle(value, force) {
    if (force === undefined) {
      if (this.values.has(value)) {
        this.values.delete(value);
        return false;
      }
      this.values.add(value);
      return true;
    }
    if (force) this.values.add(value);
    else this.values.delete(value);
    return Boolean(force);
  }
  contains(value) { return this.values.has(value); }
}

class Element {
  constructor(attributes = {}) {
    this.attributes = {...attributes};
    this.classList = new ClassList();
    this.dataset = {};
    this.hidden = false;
    this.listeners = {};
    this.pointerCapture = new Set();
    this.textContent = "";
    this.blurCount = 0;
    this.parentElement = null;
  }
  getAttribute(name) {
    return Object.prototype.hasOwnProperty.call(this.attributes, name)
      ? this.attributes[name]
      : null;
  }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  removeAttribute(name) { delete this.attributes[name]; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  setPointerCapture(pointerId) { this.pointerCapture.add(pointerId); }
  hasPointerCapture(pointerId) { return this.pointerCapture.has(pointerId); }
  releasePointerCapture(pointerId) { this.pointerCapture.delete(pointerId); }
  blur() {
    this.blurCount += 1;
    if (document.activeElement === this) document.activeElement = null;
  }
}

const body = new Element();
body.classList.add("no-js");
const fallback = new Element();
const canvas = new Element({"aria-hidden": "true"});
canvas.dataset.geoSource = "./assets/geo/land-110m.geojson";
canvas.parentElement = {
  querySelector(selector) {
    return selector === ".globe-fallback" ? fallback : null;
  }
};
const motionButton = new Element({"data-i18n": "pauseGlobe"});
motionButton.hidden = true;
const interactiveNote = new Element({"data-i18n": "globeControls"});
interactiveNote.hidden = true;
const fallbackNote = new Element({"data-i18n": "globeFallbackNotice"});

const document = {
  activeElement: null,
  body,
  documentElement: {lang: "en", dir: "ltr"},
  hidden: false,
  title: "",
  querySelector(selector) {
    if (selector === "[data-globe-interactive-note]") return interactiveNote;
    if (selector === "[data-globe-fallback-note]") return fallbackNote;
    return null;
  },
  querySelectorAll(selector) {
    if (selector === "[data-language]") return [];
    if (selector === "[data-i18n]") return [motionButton, interactiveNote, fallbackNote];
    if (selector === "[data-i18n-aria]") return [];
    if (selector === "[data-i18n-alt]") return [];
    return [];
  },
  getElementById(id) {
    if (id === "world-globe") return canvas;
    if (id === "globe-motion") return motionButton;
    return null;
  }
};

const motionListeners = [];
const motionQuery = {
  matches: process.env.REDUCED_MOTION === "1",
  addEventListener(name, callback) {
    if (name === "change") motionListeners.push(callback);
  }
};
const windowListeners = {};
const frames = [];
const drawCalls = [];
let loadCount = 0;
let resizeCount = 0;
const renderer = {
  resize() { resizeCount += 1; },
  loadGeography() { loadCount += 1; },
  draw(state) { drawCalls.push({...state}); },
  destroy() {}
};
const storage = {};
const window = {
  HubOptimusGlobe: {
    create() {
      return process.env.RENDERER_AVAILABLE === "1" ? renderer : null;
    }
  },
  localStorage: {
    getItem(key) { return storage[key] || null; },
    setItem(key, value) { storage[key] = String(value); }
  },
  navigator: {language: "en-US"},
  matchMedia(query) {
    if (query !== "(prefers-reduced-motion: reduce)") {
      throw new Error(`unexpected media query: ${query}`);
    }
    return motionQuery;
  },
  requestAnimationFrame(callback) {
    frames.push(callback);
    return frames.length;
  },
  addEventListener(name, callback) { windowListeners[name] = callback; }
};

function snapshot() {
  return {
    canvas: {
      ariaHidden: canvas.getAttribute("aria-hidden"),
      hidden: canvas.hidden,
      renderer: canvas.dataset.renderer || null,
      tabindex: canvas.getAttribute("tabindex")
    },
    fallbackAriaHidden: fallback.getAttribute("aria-hidden"),
    motion: {
      ariaPressed: motionButton.getAttribute("aria-pressed"),
      hidden: motionButton.hidden,
      text: motionButton.textContent
    },
    notes: {
      fallback: {
        hidden: fallbackNote.hidden,
        text: fallbackNote.textContent
      },
      interactive: {
        hidden: interactiveNote.hidden,
        text: interactiveNote.textContent
      }
    }
  };
}

function dispatch(element, name, event = {}) {
  const callback = element.listeners[name];
  if (!callback) throw new Error(`missing listener: ${name}`);
  callback(event);
}

function keyEvent(key) {
  return {
    key,
    prevented: false,
    preventDefault() { this.prevented = true; }
  };
}

(async () => {
  const context = {
    document,
    fetch: async () => ({
      ok: true,
      json: async () => ({type: "FeatureCollection", features: []})
    }),
    window
  };
  vm.runInNewContext(fs.readFileSync(process.env.APP_PATH, "utf8"), context);
  await new Promise(setImmediate);
  await new Promise(setImmediate);

  const initial = snapshot();
  const initialDrawCount = drawCalls.length;
  let pointer = null;
  if (!canvas.hidden) {
    const pointerDown = {
      pointerId: 7,
      clientX: 20,
      clientY: 20,
      prevented: false,
      preventDefault() { this.prevented = true; }
    };
    dispatch(canvas, "pointerdown", pointerDown);
    const captureAfterDown = canvas.hasPointerCapture(7);
    const pointerCancel = {
      pointerId: 7,
      prevented: false,
      preventDefault() { this.prevented = true; }
    };
    dispatch(canvas, "pointercancel", pointerCancel);
    pointer = {
      cancelPrevented: pointerCancel.prevented,
      captureAfterCancel: canvas.hasPointerCapture(7),
      captureAfterDown,
      downPrevented: pointerDown.prevented
    };
  }
  frames.shift()(1000);
  frames.shift()(1040);
  const reducedMotionDrawCount = drawCalls.length;

  const right = keyEvent("ArrowRight");
  dispatch(canvas, "keydown", right);
  const unsupported = keyEvent("Home");
  dispatch(canvas, "keydown", unsupported);
  const keyboard = {
    draw: drawCalls.length ? drawCalls[drawCalls.length - 1] : null,
    rightPrevented: right.prevented,
    unsupportedPrevented: unsupported.prevented
  };
  const keyboardDrawCount = drawCalls.length;

  motionListeners.forEach((listener) => listener({matches: true}));
  const afterReducedMotionChange = snapshot();
  frames.shift()(1080);
  const changedPreferenceDrawCount = drawCalls.length;
  dispatch(motionButton, "click");
  const afterManualToggle = snapshot();
  frames.shift()(1120);
  const manualToggleDrawCount = drawCalls.length;

  document.activeElement = canvas;
  const contextLost = {
    prevented: false,
    preventDefault() { this.prevented = true; }
  };
  dispatch(canvas, "webglcontextlost", contextLost);
  const afterContextLoss = {
    ...snapshot(),
    activeElementCleared: document.activeElement === null,
    blurCount: canvas.blurCount,
    prevented: contextLost.prevented
  };

  process.stdout.write(JSON.stringify({
    afterContextLoss,
    afterManualToggle,
    afterReducedMotionChange,
    changedPreferenceDrawCount,
    initial,
    initialDrawCount,
    keyboard,
    keyboardDrawCount,
    loadCount,
    manualToggleDrawCount,
    pointer,
    reducedMotionDrawCount,
    resizeCount
  }));
})().catch((error) => {
  process.stderr.write(`${error.stack}\n`);
  process.exitCode = 1;
});
"""
    result = subprocess.run(
        [node, "-e", harness],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
        env={
            **os.environ,
            "APP_PATH": str(APP),
            "REDUCED_MOTION": "1" if reduced_motion else "0",
            "RENDERER_AVAILABLE": "1" if renderer_available else "0",
        },
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_globe_keyboard_reduced_motion_and_focus_fallback_execute_deterministically():
    probe = run_globe_dom_probe(
        reduced_motion=True,
        renderer_available=True,
    )

    assert probe["initial"] == {
        "canvas": {
            "ariaHidden": None,
            "hidden": False,
            "renderer": "webgl",
            "tabindex": "0",
        },
        "fallbackAriaHidden": "true",
        "motion": {
            "ariaPressed": "true",
            "hidden": False,
            "text": "Resume",
        },
        "notes": {
            "fallback": {
                "hidden": True,
                "text": "Static illustration · interactive controls unavailable",
            },
            "interactive": {
                "hidden": False,
                "text": "Drag, swipe, or use the arrow keys to rotate.",
            },
        },
    }
    assert probe["pointer"] == {
        "cancelPrevented": False,
        "captureAfterCancel": False,
        "captureAfterDown": True,
        "downPrevented": False,
    }
    assert probe["loadCount"] == 1
    assert probe["resizeCount"] == 1
    assert probe["initialDrawCount"] == 1
    assert probe["reducedMotionDrawCount"] == 1
    assert probe["keyboard"] == {
        "draw": {"rotation": -3, "tilt": -11},
        "rightPrevented": True,
        "unsupportedPrevented": False,
    }
    assert probe["afterReducedMotionChange"]["motion"] == {
        "ariaPressed": "true",
        "hidden": False,
        "text": "Resume",
    }
    assert probe["changedPreferenceDrawCount"] == probe["keyboardDrawCount"]
    assert probe["afterManualToggle"]["motion"] == {
        "ariaPressed": "false",
        "hidden": False,
        "text": "Pause",
    }
    assert probe["manualToggleDrawCount"] == probe["keyboardDrawCount"] + 1
    assert probe["afterContextLoss"] == {
        "canvas": {
            "ariaHidden": "true",
            "hidden": True,
            "renderer": "static-fallback",
            "tabindex": None,
        },
        "fallbackAriaHidden": None,
        "motion": {
            "ariaPressed": "false",
            "hidden": True,
            "text": "Pause",
        },
        "notes": {
            "fallback": {
                "hidden": False,
                "text": "Static illustration · interactive controls unavailable",
            },
            "interactive": {
                "hidden": True,
                "text": "Drag, swipe, or use the arrow keys to rotate.",
            },
        },
        "activeElementCleared": True,
        "blurCount": 1,
        "prevented": True,
    }


def test_globe_reacts_to_a_new_reduced_motion_preference():
    probe = run_globe_dom_probe(
        reduced_motion=False,
        renderer_available=True,
    )

    assert probe["initial"]["motion"] == {
        "ariaPressed": "false",
        "hidden": False,
        "text": "Pause",
    }
    assert probe["afterReducedMotionChange"]["motion"] == {
        "ariaPressed": "true",
        "hidden": False,
        "text": "Resume",
    }
    assert probe["changedPreferenceDrawCount"] == probe["keyboardDrawCount"]
    assert probe["afterManualToggle"]["motion"] == {
        "ariaPressed": "false",
        "hidden": False,
        "text": "Pause",
    }
    assert probe["manualToggleDrawCount"] == probe["keyboardDrawCount"] + 1
    assert probe["pointer"] == {
        "cancelPrevented": False,
        "captureAfterCancel": False,
        "captureAfterDown": True,
        "downPrevented": False,
    }


def test_globe_without_a_renderer_stays_static_and_out_of_the_tab_order():
    probe = run_globe_dom_probe(
        reduced_motion=False,
        renderer_available=False,
    )

    assert probe["initial"] == {
        "canvas": {
            "ariaHidden": "true",
            "hidden": True,
            "renderer": "static-fallback",
            "tabindex": None,
        },
        "fallbackAriaHidden": None,
        "motion": {
            "ariaPressed": "false",
            "hidden": True,
            "text": "Pause",
        },
        "notes": {
            "fallback": {
                "hidden": False,
                "text": "Static illustration · interactive controls unavailable",
            },
            "interactive": {
                "hidden": True,
                "text": "Drag, swipe, or use the arrow keys to rotate.",
            },
        },
    }
    assert probe["pointer"] is None
    assert probe["loadCount"] == 0
    assert probe["resizeCount"] == 0
    assert probe["initialDrawCount"] == 0
    assert probe["reducedMotionDrawCount"] == 0
    assert probe["changedPreferenceDrawCount"] == 0
    assert probe["manualToggleDrawCount"] == 0
    assert probe["keyboard"] == {
        "draw": None,
        "rightPrevented": False,
        "unsupportedPrevented": False,
    }


def test_focus_motion_rtl_and_responsive_css_contracts_remain_versioned():
    portfolio = STYLES.read_text(encoding="utf-8")
    not_found = extract_css(NOT_FOUND.read_text(encoding="utf-8"))
    operator = extract_css(OPERATOR.read_text(encoding="utf-8"))

    assert "outline: 3px solid var(--signal-amber)" in css_block(
        portfolio,
        ":focus-visible",
    )
    assert "transform: translateY(0)" in css_block(portfolio, ".skip-link:focus")
    reduced_motion = compact_css(
        css_block(portfolio, "@media (prefers-reduced-motion: reduce)")
    )
    assert "html { scroll-behavior: auto;" in reduced_motion
    assert "transition-duration: 0.01ms !important" in reduced_motion
    assert "animation-duration: 0.01ms !important" in reduced_motion
    assert "animation-iteration-count: 1 !important" in reduced_motion

    tablet = compact_css(css_block(portfolio, "@media (max-width: 1120px)"))
    assert ".hero-grid { grid-template-columns: 1fr;" in tablet
    assert ".portfolio-grid { grid-template-columns: repeat(2, minmax(0, 1fr));" in tablet

    mobile = compact_css(css_block(portfolio, "@media (max-width: 760px)"))
    assert (
        ".method-grid, .portfolio-grid, .section-labs, .boundary-layout, "
        ".future-grid, .evidence-cta, .site-footer { grid-template-columns: 1fr;"
        in mobile
    )
    assert ".boundary-row { grid-template-columns: 1fr;" in mobile
    assert ".site-footer { justify-items: start;" in mobile
    assert ".hero h1 { font-size: clamp(1.75rem, 18vw, 5.8rem);" in mobile
    assert ".globe-stage { width: 100%; aspect-ratio: auto;" in mobile

    narrow = compact_css(css_block(portfolio, "@media (max-width: 540px)"))
    assert ".site-header { position: static; grid-template-columns: 1fr;" in narrow
    assert ".language-switcher { flex-wrap: wrap;" in narrow
    assert ".language-switcher button { min-height: 2.75rem; min-width: 2.75rem;" in narrow
    zoom_reflow = compact_css(css_block(portfolio, "@media (max-width: 360px)"))
    assert ".truth-strip { grid-template-columns: 1fr;" in zoom_reflow
    assert ".globe-toolbar { align-items: stretch; flex-direction: column;" in zoom_reflow
    assert ".globe-stage { min-height: clamp(14rem, 100vw, 18rem);" in zoom_reflow
    assert ".site-footer nav { align-items: flex-start; flex-direction: column;" in zoom_reflow
    assert "overflow-wrap: anywhere" in css_block(portfolio, "body")
    language_target = css_block(portfolio, ".language-switcher button")
    assert "min-height: 2.75rem" in language_target
    assert "min-width: 2.75rem" in language_target
    assert "min-height: 2.75rem" in css_block(portfolio, ".globe-toolbar button")
    assert "outline-offset: -4px" in css_block(portfolio, "#world-globe:focus-visible")
    globe_blocks = re.findall(r"#world-globe\s*\{(?P<body>.*?)\}", portfolio, re.DOTALL)
    assert any("touch-action: pan-y pinch-zoom" in block for block in globe_blocks)
    assert "inset-inline-start" in portfolio
    assert "inset-inline-end" in portfolio
    assert "padding-inline" in portfolio
    assert "border-inline-start" in portfolio
    assert "border-inline-end" in portfolio
    assert '[dir="rtl"] [data-i18n]' in portfolio

    operator_focus = compact_css(operator)
    assert (
        "button:focus-visible, input:focus-visible, textarea:focus-visible, "
        "select:focus-visible, a:focus-visible { outline: 3px solid "
        "var(--brand-signal);"
        in operator_focus
    )
    operator_tablet = compact_css(css_block(operator, "@media (max-width: 980px)"))
    assert (
        ".status-strip, .system-band, .flow-rail, .row, .output-grid "
        "{ grid-template-columns: 1fr;"
        in operator_tablet
    )
    assert ".system-hero { grid-template-columns: 1fr;" in operator_tablet
    operator_mobile = compact_css(css_block(operator, "@media (max-width: 560px)"))
    assert ".app { width: min(100% - 0.75rem, var(--max));" in operator_mobile

    not_found_focus = compact_css(not_found)
    assert (
        "a:focus-visible, a:hover, button:focus-visible, button:hover "
        "{ outline: 2px solid #d6a44f;"
        in not_found_focus
    )
    assert '[dir="rtl"] [data-i18n]' in not_found


def test_public_entry_points_declare_viewports_skip_links_and_tab_order():
    documents = {
        "portfolio": (SITE / "index.html").read_text(encoding="utf-8"),
        "not-found": NOT_FOUND.read_text(encoding="utf-8"),
        "operator": OPERATOR.read_text(encoding="utf-8"),
    }
    parsed = {name: parse_entry_point(source) for name, source in documents.items()}

    for name, document in parsed.items():
        assert document.viewports == ["width=device-width, initial-scale=1"], name
        assert document.positive_tabindexes == [], name

    assert "#portfolio" in parsed["portfolio"].skip_links
    assert "portfolio" in parsed["portfolio"].ids
    assert "#product_intake" in parsed["operator"].skip_links
    assert "product_intake" in parsed["operator"].ids
    assert "he" in parsed["not-found"].language_buttons
