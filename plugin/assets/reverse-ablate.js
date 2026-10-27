async () => {
   const paceMs = 350;
   const maxElements = 40;
   const volatileName = /time|took|timing|ms$|server|trace|request_?id|query_?id|correlation|params|date|now|nonce|cursor|etag/i;
   const browserHeaders = /^(accept-encoding|accept-language|connection|content-length|host|origin|referer|user-agent|sec-.*)$/i;

   const records = window.__reCapture;
   const targetIndex = window.__wreTarget;
   const record = records && records[targetIndex];

   if (!record) {
      return { error: "no target; run assets/reverse-capture.js first or set window.__wreTarget" };
   }

   const isGet = record.method === "GET";
   const readConfirmed = window.__wreReadPost === true;
   const looksLikeRead = isGet || /search|query|graphql|list|find|lookup|suggest/i.test(record.url);
   const mayAblate = isGet || (readConfirmed && looksLikeRead);

   if (!mayAblate) {
      return { error: "target is " + record.method + "; confirm it is a read, then set window.__wreReadPost = true" };
   }

   const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
   const observedUrl = new URL(record.url, location.href);
   const params = Array.from(observedUrl.searchParams.entries());
   const headers = (record.requestHeaders || []).filter((pair) => !browserHeaders.test(pair[0]));

   let bodyKind = "none";
   let bodyFields = {};

   if (record.requestBody) {
      try {
         bodyFields = JSON.parse(record.requestBody);
         bodyKind = "json";
      } catch (error) {
         bodyFields = Object.fromEntries(new URLSearchParams(record.requestBody));
         bodyKind = "form";
      }
   }

   const isPlainObject = bodyFields && typeof bodyFields === "object" && !Array.isArray(bodyFields);

   if (!isPlainObject) {
      bodyFields = {};
      bodyKind = "opaque";
   }

   const encodeBody = (fields) => {
      if (bodyKind === "json") {
         return JSON.stringify(fields);
      }

      if (bodyKind === "form") {
         return new URLSearchParams(fields).toString();
      }

      return isGet ? undefined : record.requestBody;
   };

   const fingerprint = (text) => {
      let parsed;

      try {
         parsed = JSON.parse(text);
      } catch (error) {
         return { "$text": String(Math.round((text || "").length / 500)) };
      }

      const leaves = {};

      const walk = (node, path, depth) => {
         if (depth > 10) {
            return;
         }

         if (Array.isArray(node)) {
            leaves[path + ".length"] = String(node.length);
            node.slice(0, 5).forEach((item, index) => walk(item, path + "[" + index + "]", depth + 1));
            return;
         }

         if (node && typeof node === "object") {
            for (const name of Object.keys(node)) {
               if (!volatileName.test(name)) {
                  walk(node[name], path + "." + name, depth + 1);
               }
            }

            return;
         }

         leaves[path || "$"] = String(node);
      };

      walk(parsed, "", 0);
      return leaves;
   };

   let volatilePaths = new Set();

   const differingPaths = (first, second) => {
      const paths = new Set([...Object.keys(first), ...Object.keys(second)]);
      return Array.from(paths).filter((path) => first[path] !== second[path]);
   };

   const sameResult = (first, second) => differingPaths(first, second).every((path) => volatilePaths.has(path));

   const errorLine = (text) => {
      try {
         const parsed = JSON.parse(text);
         const message = parsed && (parsed.message || parsed.error || (parsed.errors && parsed.errors[0] && parsed.errors[0].message));
         return message ? String(message).slice(0, 80) : null;
      } catch (error) {
         return null;
      }
   };

   let requests = 0;
   let credentialsMode = "include";

   const send = async (keptParams, keptHeaders, keptFields) => {
      const url = new URL(observedUrl.origin + observedUrl.pathname);

      for (const [name, value] of keptParams) {
         url.searchParams.append(name, value);
      }

      const options = { method: record.method, headers: Object.fromEntries(keptHeaders), body: encodeBody(keptFields) };
      let response;

      try {
         response = await fetch(url, { ...options, credentials: credentialsMode });
      } catch (error) {
         const canFallBack = credentialsMode === "include";

         if (!canFallBack) {
            throw error;
         }

         credentialsMode = "same-origin";
         response = await fetch(url, { ...options, credentials: credentialsMode });
      }

      const text = await response.text();
      requests += 1;
      await sleep(paceMs);

      return { status: response.status, print: fingerprint(text), error: errorLine(text) };
   };

   const baseline = await send(params, headers, bodyFields);

   if (baseline.status >= 400) {
      return { error: "full replay failed", baseline: baseline };
   }

   const repeat = await send(params, headers, bodyFields);
   volatilePaths = new Set(differingPaths(baseline.print, repeat.print));

   const elements = [
      ...params.map((pair) => ({ kind: "param", name: pair[0] })),
      ...headers.map((pair) => ({ kind: "header", name: pair[0] })),
      ...Object.keys(bodyFields).map((name) => ({ kind: "field", name: name })),
   ].slice(0, maxElements);

   const without = (element) => {
      const keptParams = element.kind === "param" ? params.filter((pair) => pair[0] !== element.name) : params;
      const keptHeaders = element.kind === "header" ? headers.filter((pair) => pair[0] !== element.name) : headers;
      const keptFields = { ...bodyFields };

      if (element.kind === "field") {
         delete keptFields[element.name];
      }

      return [keptParams, keptHeaders, keptFields];
   };

   const required = [];
   const shapesResult = [];
   const ignored = [];

   for (const element of elements) {
      const outcome = await send(...without(element));
      const label = element.kind + ":" + element.name;
      const failed = outcome.status >= 400 || outcome.error;
      const changed = !sameResult(outcome.print, baseline.print);

      if (failed) {
         required.push(label + " -> " + outcome.status + (outcome.error ? " " + outcome.error : ""));
      } else if (changed) {
         shapesResult.push(label);
      } else {
         ignored.push(label);
      }
   }

   const isIgnored = (kind, name) => ignored.includes(kind + ":" + name);
   const minimalParams = params.filter((pair) => !isIgnored("param", pair[0]));
   const minimalHeaders = headers.filter((pair) => !isIgnored("header", pair[0]));
   const minimalFields = Object.fromEntries(Object.entries(bodyFields).filter(([name]) => !isIgnored("field", name)));
   const minimal = await send(minimalParams, minimalHeaders, minimalFields);
   const minimalHolds = minimal.status < 400 && !minimal.error;

   window.__wreMinimal = { params: minimalParams.map((pair) => pair[0]), headers: minimalHeaders.map((pair) => pair[0]), fields: Object.keys(minimalFields) };

   return {
      method: record.method,
      endpoint: observedUrl.origin + observedUrl.pathname,
      bodyKind: bodyKind,
      credentials: credentialsMode,
      baseline: baseline.status,
      volatile: Array.from(volatilePaths).slice(0, 10),
      required: required,
      changesResult: shapesResult,
      ignored: ignored,
      minimalHolds: minimalHolds,
      requests: requests,
   };
}
