#!/usr/bin/env node
// Regression test for stored XSS in the node cards on the index page.
//
//   node tests/test_card_escaping.mjs
//
// Node fields are operator-submitted and the cards are built by string
// interpolation into innerHTML, so an unescaped field is executable markup.
// This extracts the inline <script> from templates/index.html, stubs the few
// DOM calls renderStatus() makes, and renders real payloads through it.
// No browser, no npm install, no running server.
//
// The oracle is structural rather than a blocklist: the same data is rendered
// twice, once with markup in every operator-controlled field and once with
// inert text of the same shape. If the two renders produce the same sequence
// of HTML tags, nothing in the payload became markup. That catches payloads a
// hand-written regex would miss.

import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const html = readFileSync(path.join(root, "templates", "index.html"), "utf8");

const blocks = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)];
if (!blocks.length) {
  console.error("FAIL: no inline <script> found in templates/index.html");
  process.exit(1);
}

// --- minimal DOM ------------------------------------------------------------
let rendered = "";
const element = (id) => ({
  id,
  style: {},
  classList: { add() {}, remove() {} },
  set innerHTML(v) { if (id === "status-container") rendered = v; },
  get innerHTML() { return ""; },
  value: "",
  insertBefore() {},
  appendChild() {},
  firstChild: null,
});

const sandbox = {
  console,
  setTimeout() {}, setInterval() {}, clearInterval() {},
  fetch: async () => ({ json: async () => ({}) }),
  window: { addEventListener() {}, location: { reload() {} } },
  document: {
    getElementById: element,
    querySelectorAll: () => [],
    addEventListener() {},
    createElement: () => element("created"),
  },
  bootstrap: { Collapse: { getInstance: () => null } },
};
vm.createContext(sandbox);
vm.runInContext(blocks[blocks.length - 1][1], sandbox);

let failures = 0;
const check = (name, ok, detail) => {
  console.log(`${ok ? "  ok  " : "  FAIL"} - ${name}`);
  if (!ok) { failures++; if (detail) console.log(`         ${detail}`); }
};

// --- payloads ---------------------------------------------------------------
// Every field an operator controls via the submission form, plus the two the
// server derives from third-party input (paynym alias and profile URL).
const OPERATOR_FIELDS = [
  "name", "jurisdiction", "hardware", "nostr_x", "dojo_version",
  "paynym", "electrum_server", "checked_at", "signature",
];

const PAYLOADS = [
  '<img src=x onerror="alert(1)">',
  "<script>alert(1)</script>",
  '"><svg onload=alert(1)>',
  "'><iframe src=javascript:alert(1)>",
  "</pre><script>alert(1)</script><pre>",
  "<a href=javascript:alert(1)>click</a>",
];
const INERT = "AAAAAAAAAAAA";

const node = (fill, extra = {}) => {
  const n = { status: "Active", pairing: { type: "dojo.api", version: "1.0.0", apikey: fill, url: fill } };
  for (const f of OPERATOR_FIELDS) n[f] = fill;
  n.status = "Active";
  return { ...n, ...extra };
};

const payload = (fill, extra) => ({
  mainnet: [node(fill, extra)],
  testnet: [node(fill, extra)],
  last_update: fill,
  stats: { mainnet_active: 1, mainnet_total: 1, testnet_active: 1, testnet_total: 1 },
});

const tagsOf = (s) => (s.match(/<\/?[a-zA-Z][^\s>/]*/g) || []).join(",");

sandbox.renderStatus(payload(INERT));
const baselineTags = tagsOf(rendered);

for (const p of PAYLOADS) {
  sandbox.renderStatus(payload(p));
  const out = rendered;
  check(
    `no markup is created by: ${p.slice(0, 34)}`,
    tagsOf(out) === baselineTags,
    "the rendered tag sequence changed, so part of the payload became markup",
  );
  check(
    `   …and it is still visible to the reader as text`,
    out.includes("&lt;") || out.includes("&quot;") || out.includes("&#39;"),
  );
}

// --- attribute sinks --------------------------------------------------------
sandbox.renderStatus(payload(INERT, {
  image: "javascript:alert(1)",
  paynym_url: "javascript:alert(1)",
}));
check("a javascript: URL never reaches an attribute", !/javascript:/i.test(rendered));
check(
  "an image with an untrusted src is dropped rather than rendered",
  !rendered.includes("javascript:alert(1)"),
);

// --- the page must still work for well-behaved data -------------------------
sandbox.renderStatus({
  mainnet: [{
    name: "Compiler",
    status: "Active",
    checked_at: "2026-01-01 00:00:00",
    jurisdiction: "North America",
    hardware: "Ryzen 9, 32GB",
    paynym: "+bumpyblank89",
    paynym_url: "https://paynym.rs/+bumpyblank89",
    image: "/static/images/qr/compiler_1234abcd.png",
    pairing: { type: "dojo.api", version: "1.27.0", apikey: "deadbeef", url: "http://abc.onion/v2" },
  }],
  testnet: [],
  last_update: "2026-01-01 00:00:00",
  stats: { mainnet_active: 1, mainnet_total: 1, testnet_active: 0, testnet_total: 0 },
});

check("a normal node still shows its name", rendered.includes("Compiler"));
check("a normal node still links its PayNym",
  rendered.includes('href="https://paynym.rs/+bumpyblank89"'));
check("a normal node still shows its QR image",
  rendered.includes('src="/static/images/qr/compiler_1234abcd.png"'));
check("the apikey is still shown", rendered.includes("deadbeef"));
check("the onion URL is still shown", rendered.includes("http://abc.onion/v2"));
check("the jurisdiction is still shown", rendered.includes("North America"));

// --- the verify modal must keep the exact signed bytes ----------------------
const signedText = '{\n  "pairing": {\n    "url": "http://abc.onion/v2"\n  }\n}';
sandbox.renderStatus({
  mainnet: [{
    name: "Signed", status: "Active", checked_at: "now",
    paynym: "+bumpyblank89",
    pairing_details: signedText,
    signature: "-----BEGIN BITCOIN SIGNED MESSAGE-----\nx\n-----END BITCOIN SIGNATURE-----",
  }],
  testnet: [],
  last_update: "now",
  stats: { mainnet_active: 1, mainnet_total: 1, testnet_active: 0, testnet_total: 0 },
});
const verifyData = vm.runInContext("_verifyData", sandbox);
check(
  "the verify modal keeps the signed text byte for byte",
  verifyData["mainnet-0"] && verifyData["mainnet-0"].message === signedText,
  "escaping the verify payload would make every signature fail to verify",
);

console.log(failures ? `\n${failures} check(s) failed` : `\nall checks passed`);
process.exit(failures ? 1 : 0);
