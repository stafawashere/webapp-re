# Bundles and obfuscation

Read this when the logic you need lives in minified, packed or deliberately obfuscated JavaScript.
Most targets only need the first section. Deobfuscation is expensive and is the last rung, after
the request is identified and the computed field is known to matter.

## Before deobfuscating anything

1. **Source maps.** Check each script for a trailing `//# sourceMappingURL=` and the
   `SourceMap` response header. A public map gives original file names and often original
   identifiers. Over CDP, `Debugger.scriptParsed` reports `sourceMapURL`.
2. **Runtime over source.** Set an XHR breakpoint on the URL fragment (CDP
   `DOMDebugger.setXHRBreakpoint`) and read the call stack at the pause. The frame that writes the
   field names the function, whatever the bundle looks like.
3. **Search, do not read.** Search the parsed scripts for the field name, the header name, or a
   constant from the value. One hit in a 4 MB chunk is cheaper than reading the chunk.

## Webpack, Rollup and Vite bundles

- Webpack 4 and 5: the runtime keeps a module map, `webpackChunk<name>` on `window` (an array
  whose `push` is the loader) and `__webpack_require__` inside. Push a fake chunk to get
  `__webpack_require__`, then `__webpack_require__.m` lists every module factory by id and
  `__webpack_require__.c` the instantiated cache. Search factories with `.toString()`.
- Vite and Rollup emit ES modules. Read the import graph from the `<script type="module">` entry
  and `modulepreload` links; dynamic imports appear as separate chunk files.
- Offline unpacking: `webcrack` (npm) unpacks webpack and browserify bundles and reverses common
  `javascript-obfuscator` transforms; `wakaru` unminifies and recovers transpiled syntax. Both run
  through `npx`, which downloads code, so ask the user before the first use and run them on a
  saved copy of the bundle in a scratch directory, never inside the user's project.

## Obfuscated code

Typical transforms and the reversal for each:

| Transform | Sign | Reversal |
|---|---|---|
| String array | A big array of strings and a decoder called with numeric args | Evaluate the decoder in isolation, inline the results |
| Control-flow flattening | `while(true){switch(order[i++]){...}}` | Recover the order string, re-sequence the cases |
| Dead code and opaque predicates | Branches on constant comparisons | Constant-fold and prune |
| Proxy functions | Tiny wrappers that only call another function | Inline them |
| Packed eval | `eval(function(p,a,c,k,e,d){...})` | Replace `eval` with a capture and read the string |
| VM-based protection | A bytecode interpreter loop | Trace inputs and outputs at runtime; do not decompile |

Use an AST toolchain (`@babel/parser`, `@babel/traverse`, `@babel/generator`) for the reversals,
one transform per pass, re-running the code after each pass to prove behaviour did not change.

When code must run outside the page (to evaluate a decoder or rebuild a signer), run it in a
sandbox: Node's `vm` with a fresh context, no `require`, a timeout, and no network. Never run
recovered code with filesystem or network access.

## Rebuilding a signer

Load the **js-reverse** skill. Its order applies: observe the request and initiator, capture
inputs and outputs at runtime, rebuild in Node from page evidence only, patch the environment one
missing object at a time, and only then clean the code. The output is either a small pure function
the program ports to its own language, or a pinned script the program runs in a sandbox, plus a
finding that records the inputs (time, nonce, path, body hash, user agent) and how to detect that
the algorithm changed.

There is no separate deobfuscation companion skill installed. This file covers that ground for the
web-automation use case.
