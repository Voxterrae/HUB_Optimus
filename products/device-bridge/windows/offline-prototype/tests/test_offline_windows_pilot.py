"""Behavioral tests for the synthetic offline pilot; Node VM is not a sandbox."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import jsonschema
import pytest

ASSETS = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
SCENARIOS = (
    "approved", "missing_approval", "expired", "invalid_signature",
    "changed_request", "changed_target", "replayed", "cancelled",
    "timeout", "missing_runtime", "unverified_runtime",
)


def run_js(body, *, ui=False):
    if NODE is None:
        pytest.skip("Node unavailable: JS behavior is not certified")
    names = ["fixtures.v0_1.js", "contract.v0_1.js"]
    if ui:
        names.append("ui.v0_1.js")
    sources = [
        (ASSETS / name).read_text(encoding="utf-8")
        if (ASSETS / name).exists() else "" for name in names
    ]
    harness = r"""
const assert = require("node:assert/strict");
const vm = require("node:vm");
const {TextEncoder} = require("node:util");
let forbiddenCalls = 0;
const forbidden = () => { forbiddenCalls++; throw new Error("Forbidden capability"); };
const context = vm.createContext({
  TextEncoder, fetch:forbidden, XMLHttpRequest:forbidden, WebSocket:forbidden,
  localStorage:new Proxy({}, {get:forbidden}), sessionStorage:new Proxy({}, {get:forbidden}),
  indexedDB:new Proxy({}, {get:forbidden}), navigator:new Proxy({}, {get:forbidden}),
  require:forbidden, process:new Proxy({}, {get:forbidden}), collector:forbidden,
  setTimeout:forbidden, setInterval:forbidden,
  Blob:class {constructor(parts,options) {this.parts=parts; this.options=options;}},
  URL:{createObjectURL:() => "blob:fixture", revokeObjectURL:() => {}}
});
for (const source of SOURCES) vm.runInContext(source,context,{timeout:1000});
const contract = context.HUB_DEVICE_BRIDGE_CONTRACT;
const fixtures = context.HUB_DEVICE_BRIDGE_FIXTURES;
assert.ok(contract && fixtures, "Fixture contract and catalog must exist");
const clone = value => JSON.parse(JSON.stringify(value));
const fresh = () => ({nowMs:1000,startedAtMs:1000,cancelled:false,usedApprovalIds:new Set()});
const request = () => fixtures.getFixture("approved").request;
const denied = (value,code) => {
  assert.equal(value.simulated,true); assert.equal(value.state,"denied");
  assert.equal(value.code,code); assert.equal(Object.hasOwn(value,"data"),false);
};
"""
    script = "const SOURCES=" + json.dumps(sources) + ";\n" + harness + body
    script += "\nassert.equal(forbiddenCalls,0);\n"
    # Minimal environment: do not propagate NODE_OPTIONS/NODE_PATH or preload hooks.
    allowed = {"SYSTEMROOT", "WINDIR", "TEMP", "TMP"}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    result = subprocess.run(
        [str(Path(NODE).resolve()), "-"], input=script, text=True,
        encoding="utf-8", capture_output=True, env=env, timeout=20, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_request_is_closed_and_categorizes_unknown_inputs():
    run_js(r"""
assert.ok(Object.isFrozen(contract)); assert.ok(Object.isFrozen(fixtures));
assert.equal(contract.validateRequest(request()).ok,true);
for(const key of ["command","script","path","executable","module"]) {
  assert.equal(contract.validateRequest({...request(),[key]:"anything"}).code,"INVALID_REQUEST");
}
for(const [patch,code] of [
  [{operationId:"shell.run"},"UNKNOWN_OPERATION"],
  [{targetRef:"other"},"UNKNOWN_TARGET"], [{profileRef:"other"},"UNKNOWN_TARGET"],
  [{fields:["windows"]},"UNKNOWN_FIELD"], [{fields:["node","powershell7","windows"]},"UNKNOWN_FIELD"],
  [{requestId:""},"INVALID_REQUEST"], [{nonce:"a".repeat(65)},"INVALID_REQUEST"],
  [{nonce:"é"},"INVALID_REQUEST"], [{schemaVersion:"v2"},"INVALID_REQUEST"]
]) assert.equal(contract.validateRequest({...request(),...patch}).code,code);
for(const value of [null,[],42,"request"]) assert.equal(contract.validateRequest(value).ok,false);
""")


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_scenarios_never_enable_real_execution(scenario):
    run_js("const scenarioId=" + json.dumps(scenario) + r""";
const fixture=fixtures.getFixture(scenarioId);
for(const input of [fixture.request,{...fixture.request,approval:true,testKey:"test"},null]) {
  denied(contract.requestRealExecution(input),"EXECUTOR_DISABLED");
}
denied(contract.requestRealExecution(fixtures.getFixture(scenarioId).request),"EXECUTOR_DISABLED");
assert.ok(contract.validateResult(contract.evaluateFixture(fixture.request,scenarioId,fresh())).ok);
const a=fixtures.getFixture("approved"); a.request.fields[0]="shell";
assert.equal(fixtures.getFixture("approved").request.fields[0],"windows");
""")


@pytest.mark.parametrize(("scenario", "code"), [
    ("missing_approval", "APPROVAL_MISSING"), ("expired", "APPROVAL_EXPIRED"),
    ("invalid_signature", "APPROVAL_INVALID"), ("changed_request", "REQUEST_CHANGED"),
    ("changed_target", "TARGET_CHANGED"), ("replayed", "APPROVAL_REPLAYED"),
    ("cancelled", "CANCELLED"), ("timeout", "TIMED_OUT"),
])
def test_denial_scenarios_release_no_data(scenario, code):
    run_js(f"denied(contract.evaluateFixture(request(),{json.dumps(scenario)},fresh()),{json.dumps(code)});")


def test_binding_replay_cancellation_and_time_boundaries():
    run_js(r"""
denied(contract.evaluateFixture({...request(),requestId:"changed"},"approved",fresh()),"REQUEST_CHANGED");
denied(contract.evaluateFixture({...request(),targetRef:"other"},"approved",fresh()),"TARGET_CHANGED");
denied(contract.evaluateFixture({...request(),profileRef:"other"},"approved",fresh()),"TARGET_CHANGED");
const state=fresh();
assert.equal(contract.evaluateFixture(request(),"approved",state).state,"completed");
denied(contract.evaluateFixture(request(),"approved",state),"APPROVAL_REPLAYED");
denied(contract.evaluateFixture(request(),"approved",{...fresh(),cancelled:true}),"CANCELLED");
denied(contract.evaluateFixture(request(),"approved",{...fresh(),nowMs:11000}),"TIMED_OUT");
denied(contract.evaluateFixture(request(),"approved",{...fresh(),nowMs:60000,startedAtMs:60000}),"APPROVAL_EXPIRED");
denied(contract.evaluateFixture(request(),"unknown",fresh()),"UNKNOWN_SCENARIO");
assert.equal(fixtures.getFixture("unknown").code,"UNKNOWN_SCENARIO");
""")


def test_result_states_are_distinct_closed_and_bounded():
    run_js(r"""
const good=contract.evaluateFixture(request(),"approved",fresh());
assert.equal(contract.validateResult(good).ok,true);
assert.equal(contract.evaluateFixture(request(),"missing_runtime",fresh()).data.node.state,"missing");
assert.equal(contract.evaluateFixture(request(),"unverified_runtime",fresh()).data.node.state,"unverified");
for(const bad of [
 {...good,extra:true}, {...good,simulated:false},
 {...good,data:{...good.data,node:{state:"missing",version:"24"}}},
 {...good,data:{...good.data,node:{state:"available"}}},
 {simulated:true,state:"denied",code:"raw exception"},
 {simulated:true,state:"denied",code:"CANCELLED",data:good.data}
]) assert.equal(contract.validateResult(bad).code,"INVALID_RESULT");
const raw=clone(good); raw.data.node.version="a".repeat(2000);
assert.equal(contract.validateResult(raw).code,"INVALID_RESULT");
raw.data.node.version="é".repeat(2000);
assert.equal(contract.validateResult(raw).code,"RESULT_TOO_LARGE");
raw.data.node.version="\n".repeat(2100);
assert.equal(contract.validateResult(raw).code,"RESULT_TOO_LARGE");
const size=body=>new TextEncoder().encode(JSON.stringify(body)).length;
const oversized={...request(),padding:""};
oversized.padding="a".repeat(4096-size(oversized)+1);
assert.equal(contract.validateRequest(oversized).code,"REQUEST_TOO_LARGE");
oversized.padding=oversized.padding.slice(1);
assert.equal(size(oversized),4096);
assert.equal(contract.validateRequest(oversized).code,"INVALID_REQUEST");
const cyclic={}; cyclic.self=cyclic;
assert.equal(contract.validateResult(cyclic).code,"INVALID_RESULT");
""")


def test_schema_agrees_with_real_fixture_outputs():
    schema_path = ASSETS / "runtime_inventory.v0_1.schema.json"
    assert schema_path.exists(), "Closed fixture schema must exist"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    outputs = json.loads(run_js(r"""
console.log(JSON.stringify({
 request:request(),
 results:fixtures.scenarioIds.map(id=>contract.evaluateFixture(request(),id,fresh()))
}));
"""))
    request_validator = jsonschema.Draft202012Validator({
        "$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": "#/$defs/request"
    })
    request_validator.validate(outputs["request"])
    for result in outputs["results"]:
        jsonschema.validate(result, schema)
    for patch in [{"command": "whoami"}, {"fields": ["windows"]}, {"nonce": "é"}]:
        assert not request_validator.is_valid({**outputs["request"], **patch})
    assert not jsonschema.Draft202012Validator(schema).is_valid(
        {"simulated": True, "state": "denied", "code": "CANCELLED", "data": {}}
    )


DOM_ADAPTER = r"""
const ui=context.HUB_DEVICE_BRIDGE_UI;
assert.ok(ui,"Offline UI API must exist");
assert.ok(Object.isFrozen(ui));
function makeDocument() {
  const elements={}; const downloads=[];
  const makeElement=id=>({
    id,value:"approved",disabled:false,handlers:{},_text:"",
    get textContent(){return this._text;},
    set textContent(value){this._text=String(value);},
    set innerHTML(_){throw new Error("HTML parsing forbidden");},
    addEventListener(name,fn){this.handlers[name]=fn;},
    click(){if(!this.disabled && this.handlers.click) this.handlers.click();},
    remove(){}, setAttribute(){}
  });
  for(const id of ["fixture-scenario","fixture-run","fixture-complete","fixture-cancel",
      "fixture-export","fixture-status","fixture-result","fixture-request"]) elements[id]=makeElement(id);
  return {
    elements,downloads,getElementById:id=>elements[id],
    createElement(tag){
      assert.equal(tag,"a");
      return {click(){downloads.push({href:this.href,download:this.download});},remove(){}};
    },
    body:{appendChild(){}}
  };
}
"""


def test_renderer_preserves_literal_markup_and_discards_invalid_data():
    run_js(DOM_ADAPTER + r"""
const doc=makeDocument();
const result=contract.evaluateFixture(request(),"approved",fresh());
const markup="<img src=x onerror=alert(1)>";
result.data.node.version=markup;
const rendered=ui.renderFixtureResult(doc,result);
assert.equal(rendered.state,"completed");
assert.equal(JSON.parse(doc.elements["fixture-result"].textContent).data.node.version,markup);
result.data.node.version="é".repeat(2200);
denied(ui.renderFixtureResult(doc,result),"RESULT_TOO_LARGE");
assert.equal(doc.elements["fixture-result"].textContent.includes(markup),false);
denied(ui.renderFixtureResult(doc,{simulated:false,state:"completed",data:{}}),"INVALID_RESULT");
""", ui=True)


def test_pending_cancel_is_terminal_and_snapshots_request():
    run_js(DOM_ADAPTER + r"""
const input=request();
const run=ui.createFixtureRun(input,"approved",fresh());
input.nonce="later";
assert.equal(run.complete().state,"completed");
const cancelled=ui.createFixtureRun(request(),"approved",fresh());
denied(cancelled.cancel(),"CANCELLED");
denied(cancelled.complete(),"CANCELLED");
denied(cancelled.complete(),"CANCELLED");
""", ui=True)


def test_controls_require_explicit_completion_and_completed_only_export():
    run_js(DOM_ADAPTER + r"""
const doc=makeDocument();
const controller=ui.mountFixtureUI(doc,contract,fixtures);
assert.equal(doc.elements["fixture-export"].disabled,true);
assert.equal(doc.downloads.length,0);
doc.elements["fixture-run"].click();
assert.equal(doc.elements["fixture-status"].textContent.includes("Pendiente"),true);
assert.equal(doc.elements["fixture-result"].textContent,"");
assert.equal(doc.elements["fixture-export"].disabled,true);
doc.elements["fixture-complete"].click();
assert.equal(JSON.parse(doc.elements["fixture-result"].textContent).state,"completed");
assert.equal(doc.downloads.length,0);
doc.elements["fixture-export"].click();
assert.equal(doc.downloads.length,1);
assert.equal(doc.downloads[0].download,"hub-optimus-device-bridge-fixture.json");
doc.elements["fixture-run"].click();
doc.elements["fixture-cancel"].click();
doc.elements["fixture-complete"].click();
denied(JSON.parse(doc.elements["fixture-result"].textContent),"CANCELLED");
assert.equal(doc.elements["fixture-export"].disabled,true);
doc.elements["fixture-export"].click();
assert.equal(doc.downloads.length,1);
doc.elements["fixture-scenario"].value="missing_approval";
doc.elements["fixture-scenario"].handlers.change();
doc.elements["fixture-run"].click(); doc.elements["fixture-complete"].click();
denied(JSON.parse(doc.elements["fixture-result"].textContent),"APPROVAL_MISSING");
doc.elements["fixture-export"].click(); assert.equal(doc.downloads.length,1);
doc.elements["fixture-scenario"].value="unknown";
doc.elements["fixture-scenario"].handlers.change();
assert.equal(doc.elements["fixture-run"].disabled,true);
denied(contract.requestRealExecution(request()),"EXECUTOR_DISABLED");
""", ui=True)


def test_all_ui_scenarios_have_no_ambient_capability_calls():
    run_js(DOM_ADAPTER + r"""
for(const scenarioId of fixtures.scenarioIds) {
  const doc=makeDocument();
  ui.mountFixtureUI(doc,contract,fixtures);
  doc.elements["fixture-scenario"].value=scenarioId;
  doc.elements["fixture-scenario"].handlers.change();
  doc.elements["fixture-run"].click(); doc.elements["fixture-complete"].click();
  const displayed=JSON.parse(doc.elements["fixture-result"].textContent);
  assert.equal(contract.validateResult(displayed).ok,true);
  if(displayed.state==="denied") {
    assert.equal(doc.elements["fixture-export"].disabled,true);
    assert.equal(Object.hasOwn(displayed,"data"),false);
  }
  doc.elements["fixture-export"].click();
}
const recreated=makeDocument(); ui.mountFixtureUI(recreated,contract,fixtures);
denied(contract.requestRealExecution(request()),"EXECUTOR_DISABLED");
""", ui=True)


def test_raw_properties_and_types_cannot_disappear_in_serialization():
    run_js(r"""
for (const value of [undefined, () => {}]) {
  assert.equal(contract.validateRequest({...request(),command:value}).code,"INVALID_REQUEST");
}
const boxed=request(); boxed.nonce=new String(boxed.nonce);
assert.equal(contract.validateRequest(boxed).code,"INVALID_REQUEST");
const good=contract.evaluateFixture(request(),"approved",fresh());
for (const bad of [
  {...good,extra:undefined},
  {...good,data:{...good.data,command:undefined}},
  {...good,data:{...good.data,node:{state:"missing",version:undefined}}},
  {...good,data:{...good.data,node:{state:"available",version:new String("24")}}}
]) assert.equal(contract.validateResult(bad).code,"INVALID_RESULT");
""")


def test_schema_identifiers_reject_trailing_newline():
    schema = json.loads((ASSETS / "runtime_inventory.v0_1.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator({
        "$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": "#/$defs/request"
    })
    request = json.loads(run_js("console.log(JSON.stringify(request()));"))
    for key in ("requestId", "nonce"):
        assert not validator.is_valid({**request, key: request[key] + "\n"})


def test_export_contains_exact_displayed_synthetic_json_and_refuses_tampering():
    run_js(DOM_ADAPTER + r"""
const blobs=[];
context.URL.createObjectURL=blob=>{blobs.push(blob);return "blob:fixture";};
const doc=makeDocument();
ui.mountFixtureUI(doc,contract,fixtures);
doc.elements["fixture-run"].click();doc.elements["fixture-complete"].click();
const displayed=doc.elements["fixture-result"].textContent;
doc.elements["fixture-export"].click();
assert.equal(blobs.length,1);
assert.equal(blobs[0].parts.join(""),displayed);
const exported=JSON.parse(blobs[0].parts.join(""));
assert.equal(exported.simulated,true);
assert.equal(contract.validateResult(exported).ok,true);
assert.ok(new TextEncoder().encode(displayed).length<=4096);
doc.elements["fixture-result"].textContent="x".repeat(4097);
doc.elements["fixture-export"].click();assert.equal(blobs.length,1);
doc.elements["fixture-result"].textContent=JSON.stringify({...exported,simulated:false});
doc.elements["fixture-export"].click();assert.equal(blobs.length,1);
""", ui=True)
