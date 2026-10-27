async () => {
   const maxShapes = 4;
   const maxShapePaths = 80;
   const settleMs = 1200;
   const shapedKey = "__wreShaped";

   const noiseRules = [
      /google-analytics|googletagmanager|doubleclick|facebook\.com\/tr|bat\.bing|hotjar|fullstory|clarity\.ms|sentry|datadoghq|browser-intake|segment\.(io|com)|mixpanel|amplitude|posthog/i,
      /\/(rum|beacon|collect|telemetry|track|metrics|stats|log|logs|events?|ping|pixel)(\/|\?|$)/i,
   ];
   const unsafeGet = /logout|log_out|signout|sign_out|delete|destroy|remove|unsubscribe|mark|archive|dismiss|accept|confirm/i;

   const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

   const genericSegment = (segment) => {
      const isNumber = /^\d+$/.test(segment);
      const isHash = /^[0-9a-f]{12,}$/i.test(segment);
      const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-/i.test(segment);
      const isLongToken = segment.length > 24 && /\d/.test(segment);

      if (isNumber || isHash || isUuid || isLongToken) {
         return "{id}";
      }

      return segment;
   };

   const urlPattern = (raw) => {
      let url;

      try {
         url = new URL(raw, location.href);
      } catch (error) {
         return null;
      }

      const path = url.pathname.split("/").map(genericSegment).join("/");
      const keys = Array.from(new Set(url.searchParams.keys())).sort();
      const host = url.origin === location.origin ? "" : url.origin;
      const query = keys.length ? "?" + keys.join("&") : "";

      return { host: host, path: path, query: query, pattern: host + path + query };
   };

   const isNoise = (raw) => noiseRules.some((rule) => rule.test(raw));

   const queueKey = "__wreQueue";
   let queue = [];
   try {
      queue = JSON.parse(sessionStorage.getItem(queueKey) || "[]");
   } catch (error) {
      queue = [];
   }

   const pendingKey = "__wrePending";
   const pending = sessionStorage.getItem(pendingKey) || "";
   const landedByReload = Boolean(pending) && new URL(pending, location.href).pathname === location.pathname && !window.__wreTiming;
   const hookedAtLoad = Boolean(window.__wreTiming);

   if (!window.__wreTiming) {
      window.__wreTiming = { clears: 0, full: 0 };
      performance.setResourceTimingBufferSize(5000);
      performance.clearResourceTimings = () => {
         window.__wreTiming.clears += 1;
      };
   }

   sessionStorage.removeItem(pendingKey);
   const nextTarget = landedByReload ? "" : window.__wreNext || queue.shift() || "";

   try {
      sessionStorage.setItem(queueKey, JSON.stringify(queue));
      if (nextTarget) {
         sessionStorage.setItem(pendingKey, nextTarget);
      }
   } catch (error) {
      queue = [];
   }
   let since = 0;
   let softNavigation = "none";

   if (nextTarget) {
      window.__wreNext = "";
      since = performance.now();
      const canTurboVisit = Boolean(window.Turbo && window.Turbo.visit);

      if (canTurboVisit) {
         window.Turbo.visit(nextTarget);
      } else {
         const link = document.createElement("a");
         link.href = nextTarget;
         document.body.appendChild(link);
         link.click();
         link.remove();
      }

      await sleep(1500);
      softNavigation = new URL(nextTarget, location.href).pathname === location.pathname ? "ok" : "failed";
      sessionStorage.removeItem(pendingKey);
   }

   await sleep(settleMs);
   window.scrollTo(0, document.body.scrollHeight);
   await sleep(800);
   window.scrollTo(0, 0);

   const staticAsset = /\.(js|mjs|css|woff2?|ttf|png|jpe?g|gif|svg|webp|ico|map|wasm)(\?|$)/i;
   const resources = performance.getEntriesByType("resource").filter((entry) => /^https?:/.test(entry.name) && entry.startTime >= since);
   const apiEntries = resources.filter((entry) => {
      const isApiInitiator = ["fetch", "xmlhttprequest", "beacon", "other"].includes(entry.initiatorType);
      const isAsset = staticAsset.test(new URL(entry.name).pathname) || /\/assets?(-cdn)?\//.test(entry.name);

      return isApiInitiator && !isAsset;
   });
   const timingHook = window.__wreTiming;
   const loadTruncated = !hookedAtLoad && !since && resources.length >= 249;

   const calls = {};
   const noise = {};

   for (const entry of apiEntries) {
      const parts = urlPattern(entry.name);

      if (!parts) {
         continue;
      }

      const noiseKey = (parts.host || location.host) + parts.path;
      const looksLikeNoise = isNoise(entry.name) || entry.initiatorType === "beacon";

      if (looksLikeNoise) {
         noise[noiseKey] = (noise[noiseKey] || 0) + 1;
         continue;
      }

      const existing = calls[parts.pattern] || { pattern: parts.pattern, via: entry.initiatorType, count: 0, status: entry.responseStatus || 0, bytes: 0, sameOrigin: !parts.host };
      existing.count += 1;
      existing.bytes = Math.max(existing.bytes, entry.encodedBodySize || 0);
      calls[parts.pattern] = existing;
   }

   const shapeOf = (node, path, out, depth) => {
      if (out.length >= maxShapePaths || depth > 5) {
         return;
      }

      if (Array.isArray(node)) {
         out.push(path + "[] x" + node.length);
         if (node.length) {
            shapeOf(node[0], path + "[]", out, depth + 1);
         }

         return;
      }

      if (node && typeof node === "object") {
         for (const key of Object.keys(node)) {
            const value = node[key];
            const kind = value === null ? "null" : Array.isArray(value) ? "array" : typeof value;
            const isContainer = kind === "object" || kind === "array";

            if (!isContainer) {
               out.push(path + "." + key + ":" + kind);
            }

            shapeOf(value, path + "." + key, out, depth + 1);
         }
      }
   };

   let shaped = [];
   try {
      shaped = JSON.parse(sessionStorage.getItem(shapedKey) || "[]");
   } catch (error) {
      shaped = [];
   }

   const shapes = [];
   const candidates = apiEntries.filter((entry) => {
      const parts = urlPattern(entry.name);
      const isFresh = parts && calls[parts.pattern] && calls[parts.pattern].sameOrigin && !shaped.includes(parts.pattern);
      const isSafe = !unsafeGet.test(entry.name);

      return isFresh && isSafe;
   });

   for (const entry of candidates.slice(0, maxShapes)) {
      const parts = urlPattern(entry.name);

      if (shaped.includes(parts.pattern)) {
         continue;
      }

      shaped.push(parts.pattern);

      try {
         const response = await fetch(entry.name, { credentials: "include", headers: { "accept": "application/json, text/html;q=0.5" } });
         const contentType = response.headers.get("content-type") || "";
         const headerNames = Array.from(response.headers.keys()).sort();
         const record = { pattern: parts.pattern, status: response.status, type: contentType.split(";")[0], headerNames: headerNames };

         if (contentType.includes("json")) {
            const paths = [];
            shapeOf(await response.json(), "$", paths, 0);
            record.shape = paths;
         } else {
            const text = await response.text();
            record.bytes = text.length;
         }

         shapes.push(record);
      } catch (error) {
         shapes.push({ pattern: parts.pattern, error: String(error).slice(0, 80) });
      }

      await sleep(400);
   }

   try {
      sessionStorage.setItem(shapedKey, JSON.stringify(shaped));
   } catch (error) {
      shapes.push({ note: "sessionStorage unavailable, shapes may repeat" });
   }

   const linkGroups = {};
   for (const anchor of document.querySelectorAll("a[href]")) {
      const parts = urlPattern(anchor.getAttribute("href"));
      const isInternal = parts && !parts.host && !anchor.getAttribute("href").startsWith("#");

      if (!isInternal) {
         continue;
      }

      const group = linkGroups[parts.pattern] || { pattern: parts.pattern, count: 0, sample: new URL(anchor.href).pathname };
      group.count += 1;
      linkGroups[parts.pattern] = group;
   }

   const paginationLinks = Array.from(document.querySelectorAll("a[rel=next], a[href*='page='], a[href*='after='], a[href*='cursor='], a[href*='before=']"))
      .map((anchor) => urlPattern(anchor.getAttribute("href")))
      .filter(Boolean)
      .map((parts) => parts.pattern);

   const loadMore = Array.from(document.querySelectorAll("button, a")).filter((element) => /^(load more|show more|next|older|newer)$/i.test((element.textContent || "").trim())).length;

   const forms = Array.from(document.querySelectorAll("form")).map((form) => {
      const fieldNames = Array.from(form.elements).map((field) => field.name).filter(Boolean);
      const action = urlPattern(form.getAttribute("action") || location.href);

      return {
         method: (form.getAttribute("method") || "get").toUpperCase(),
         action: action ? action.pattern : "",
         fields: Array.from(new Set(fieldNames)).slice(0, 20),
      };
   });

   const navigation = performance.getEntriesByType("navigation")[0] || {};
   const embeddedJson = Array.from(document.querySelectorAll("script[type='application/json'], script[type='application/ld+json'], react-app, [data-target$='embeddedData']"))
      .map((element) => element.id || element.getAttribute("data-target") || element.tagName.toLowerCase())
      .slice(0, 15);
   const apiCallCount = Object.values(calls).filter((call) => call.via !== "other").length;
   const hasHydrationData = Boolean(document.getElementById("__NEXT_DATA__") || window.__NUXT__ || embeddedJson.length);
   const isServerRendered = apiCallCount <= 2 || (hasHydrationData && apiCallCount <= 4);

   let jsCookieNames = [];
   try {
      jsCookieNames = document.cookie.split(";").map((pair) => pair.split("=")[0].trim()).filter(Boolean);
   } catch (error) {
      jsCookieNames = [];
   }

   return {
      url: urlPattern(location.href).pattern,
      title: document.title.slice(0, 80),
      status: since ? 0 : navigation.responseStatus || 0,
      softNavigation: softNavigation,
      queueLeft: queue.length,
      render: isServerRendered ? "server" : "api",
      timing: { hookedAtLoad: hookedAtLoad, landedByReload: landedByReload, truncated: loadTruncated, clearCalls: timingHook.clears, bufferFull: timingHook.full, resources: resources.length },
      framework: {
         next: Boolean(document.getElementById("__NEXT_DATA__")),
         nuxt: Boolean(window.__NUXT__),
         apollo: Boolean(window.__APOLLO_CLIENT__),
         turbo: Boolean(window.Turbo || document.querySelector("meta[name^='turbo']")),
         reactRoot: Boolean(document.querySelector("[data-reactroot], #root, #__next, react-app")),
         webpackChunks: Object.keys(window).filter((key) => key.startsWith("webpackChunk")).length,
         serviceWorker: Boolean(navigator.serviceWorker && navigator.serviceWorker.controller),
         embeddedJson: embeddedJson,
      },
      csrf: {
         meta: Array.from(document.querySelectorAll("meta")).map((meta) => meta.name).filter((name) => /csrf|xsrf|token|nonce/i.test(name)),
         inputs: Array.from(new Set(Array.from(document.querySelectorAll("input[type=hidden]")).map((input) => input.name).filter((name) => /csrf|xsrf|token|authenticity/i.test(name)))),
      },
      jsCookieNames: jsCookieNames,
      calls: Object.values(calls),
      noise: noise,
      shapes: shapes,
      links: Object.values(linkGroups).sort((left, right) => right.count - left.count).slice(0, 60),
      pagination: { links: Array.from(new Set(paginationLinks)).slice(0, 5), loadMoreControls: loadMore },
      forms: forms.slice(0, 15),
      sockets: resources.filter((entry) => /^wss?:/.test(entry.name)).length,
   };
}
