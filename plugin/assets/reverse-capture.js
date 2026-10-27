async () => {
   const settleMs = 1500;
   const maxCandidates = 8;
   const maxBodyPreview = 400;
   const noiseRules = [
      /google-analytics|googletagmanager|doubleclick|facebook\.com\/tr|bat\.bing|hotjar|fullstory|clarity\.ms|sentry|datadoghq|browser-intake|segment\.(io|com)|mixpanel|amplitude|posthog/i,
      /\/(rum|beacon|collect|telemetry|track|metrics|stats|log|logs|events?|ping|pixel)(\/|\?|$)/i,
      /^chrome-extension:|^moz-extension:|telemetry\./i,
   ];
   const secretName = /key|token|secret|auth|sig|session|password|passwd|bearer|credential|csrf|xsrf|nonce/i;
   const readPath = /search|query|graphql|list|get|find|lookup|suggest|autocomplete|feed|browse/i;

   const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
   await sleep(settleMs);

   const records = window.__reCapture;

   if (!records) {
      return { error: "capture hook not installed; run assets/capture-hook.js with format script, then act" };
   }

   const redactQuery = (url) => {
      const redacted = new URL(url, location.href);

      for (const name of Array.from(redacted.searchParams.keys())) {
         if (secretName.test(name)) {
            redacted.searchParams.set(name, "REDACTED");
         }
      }

      return redacted;
   };

   const redactBody = (text) => {
      if (!text) {
         return null;
      }

      let parsed;

      try {
         parsed = JSON.parse(text);
      } catch (error) {
         const asForm = new URLSearchParams(text);
         const formNames = Array.from(asForm.keys());
         const looksLikeForm = formNames.length > 0 && !text.includes("{");

         if (!looksLikeForm) {
            return text.slice(0, maxBodyPreview);
         }

         for (const name of formNames) {
            if (secretName.test(name)) {
               asForm.set(name, "REDACTED");
            }
         }

         return asForm.toString().slice(0, maxBodyPreview);
      }

      const scrub = (node) => {
         if (Array.isArray(node)) {
            return node.map(scrub);
         }

         if (node && typeof node === "object") {
            return Object.fromEntries(Object.entries(node).map(([name, value]) => [name, secretName.test(name) ? "REDACTED" : scrub(value)]));
         }

         return node;
      };

      return JSON.stringify(scrub(parsed)).slice(0, maxBodyPreview);
   };

   const topShape = (text) => {
      let parsed;

      try {
         parsed = JSON.parse(text);
      } catch (error) {
         return text ? "text " + text.length : "empty";
      }

      if (Array.isArray(parsed)) {
         return "array " + parsed.length;
      }

      if (!parsed || typeof parsed !== "object") {
         return typeof parsed;
      }

      return Object.entries(parsed).slice(0, 20).map(([name, value]) => {
         const isList = Array.isArray(value);
         return isList ? name + "[" + value.length + "]" : name;
      }).join(",");
   };

   const candidates = [];
   const noise = {};

   records.forEach((record, index) => {
      const isNoise = noiseRules.some((rule) => rule.test(record.url));

      if (isNoise) {
         const host = record.url.split("/")[2] || record.url.slice(0, 40);
         noise[host] = (noise[host] || 0) + 1;
         return;
      }

      const url = redactQuery(record.url);
      const isGet = record.method === "GET";
      const bodyIsMutation = /^\s*\{?\s*"?query"?\s*:\s*"\s*mutation/i.test(record.requestBody || "");
      const readLike = isGet || (readPath.test(url.pathname) && !bodyIsMutation);
      const isJson = /json/i.test(record.contentType || "");

      candidates.push({
         index: index,
         method: record.method,
         url: url.origin === location.origin ? url.pathname + url.search : url.href,
         status: record.status,
         readLike: readLike,
         json: isJson,
         headerNames: record.requestHeaderNames,
         body: redactBody(record.requestBody),
         response: topShape(record.responseBody),
         bytes: record.responseBody ? record.responseBody.length : 0,
      });
   });

   const score = (candidate) => (candidate.json ? 4 : 0) + (candidate.readLike ? 1 : 0) + Math.min(candidate.bytes / 20000, 3);
   candidates.sort((first, second) => score(second) - score(first));

   if (candidates.length) {
      window.__wreTarget = candidates[0].index;
   }

   return {
      target: candidates.length ? candidates[0].index : null,
      candidates: candidates.slice(0, maxCandidates),
      dropped: candidates.length > maxCandidates ? candidates.length - maxCandidates : 0,
      noise: noise,
   };
}
