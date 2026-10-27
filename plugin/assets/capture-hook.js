(() => {
   if (window.__reCapture) {
      return { installed: false, reason: "already installed", records: window.__reCapture.length };
   }

   const maxRecords = 200;
   const maxBodyChars = 65536;
   const records = [];
   window.__reCapture = records;

   const truncate = (text) => {
      if (typeof text !== "string") {
         return text;
      }

      return text.length > maxBodyChars ? text.slice(0, maxBodyChars) : text;
   };

   const remember = (record) => {
      records.push(record);

      if (records.length > maxRecords) {
         records.shift();
      }
   };

   const bodyText = (body) => {
      if (body == null) {
         return null;
      }

      if (typeof body === "string") {
         return truncate(body);
      }

      if (body instanceof URLSearchParams) {
         return truncate(body.toString());
      }

      if (body instanceof FormData) {
         const fields = [];
         body.forEach((value, key) => fields.push([key, typeof value === "string" ? value : "<file>"]));
         return truncate(new URLSearchParams(fields).toString());
      }

      return "<" + Object.prototype.toString.call(body) + ">";
   };

   const headerNames = (headers) => {
      if (!headers) {
         return [];
      }

      if (headers instanceof Headers) {
         return Array.from(headers.keys());
      }

      if (Array.isArray(headers)) {
         return headers.map((pair) => String(pair[0]).toLowerCase());
      }

      return Object.keys(headers).map((name) => name.toLowerCase());
   };

   const headerPairs = (headers) => {
      if (!headers) {
         return [];
      }

      if (headers instanceof Headers) {
         return Array.from(headers.entries());
      }

      if (Array.isArray(headers)) {
         return headers.map((pair) => [String(pair[0]).toLowerCase(), String(pair[1])]);
      }

      return Object.entries(headers).map((pair) => [pair[0].toLowerCase(), String(pair[1])]);
   };

   const keepPrivately = (record, name, value) => {
      Object.defineProperty(record, name, { value: value, enumerable: false, writable: true });
   };

   const originalFetch = window.fetch;
   window.fetch = async function (input, init) {
      const request = input instanceof Request ? input : null;
      const started = performance.now();
      const record = {
         via: "fetch",
         method: ((init && init.method) || (request && request.method) || "GET").toUpperCase(),
         url: String(request ? request.url : input),
         requestHeaderNames: headerNames((init && init.headers) || (request && request.headers)),
         requestBody: bodyText(init && init.body),
         startedAt: Date.now(),
      };
      keepPrivately(record, "requestHeaders", headerPairs((init && init.headers) || (request && request.headers)));

      try {
         const response = await originalFetch.apply(this, arguments);
         record.status = response.status;
         record.contentType = response.headers.get("content-type");
         record.ms = Math.round(performance.now() - started);
         response.clone().text().then((text) => {
            record.responseBody = truncate(text);
         }, () => {
            record.responseBody = "<unreadable>";
         });
         remember(record);
         return response;
      } catch (error) {
         record.error = String(error);
         remember(record);
         throw error;
      }
   };

   const OriginalXHR = window.XMLHttpRequest;
   const originalOpen = OriginalXHR.prototype.open;
   const originalSend = OriginalXHR.prototype.send;
   const originalSetHeader = OriginalXHR.prototype.setRequestHeader;

   OriginalXHR.prototype.open = function (method, url) {
      this.__reRecord = { via: "xhr", method: String(method).toUpperCase(), url: String(url), requestHeaderNames: [] };
      keepPrivately(this.__reRecord, "requestHeaders", []);
      return originalOpen.apply(this, arguments);
   };

   OriginalXHR.prototype.setRequestHeader = function (name, value) {
      if (this.__reRecord) {
         this.__reRecord.requestHeaderNames.push(String(name).toLowerCase());
         this.__reRecord.requestHeaders.push([String(name).toLowerCase(), String(value)]);
      }

      return originalSetHeader.apply(this, arguments);
   };

   OriginalXHR.prototype.send = function (body) {
      const record = this.__reRecord;

      if (record) {
         const started = performance.now();
         record.requestBody = bodyText(body);
         record.startedAt = Date.now();
         this.addEventListener("loadend", () => {
            record.status = this.status;
            record.contentType = this.getResponseHeader("content-type");
            record.ms = Math.round(performance.now() - started);
            const isText = this.responseType === "" || this.responseType === "text";
            record.responseBody = isText ? truncate(this.responseText) : "<" + this.responseType + ">";
            remember(record);
         });
      }

      return originalSend.apply(this, arguments);
   };

   const shapeOf = (text) => {
      let parsed;

      try {
         parsed = JSON.parse(text);
      } catch (error) {
         return { kind: "text", length: text ? text.length : 0 };
      }

      const paths = {};
      const walk = (node, path, depth) => {
         if (depth > 6) {
            return;
         }

         const kind = node === null ? "null" : Array.isArray(node) ? "array" : typeof node;
         paths[path || "$"] = paths[path || "$"] || new Set();
         paths[path || "$"].add(kind);

         if (Array.isArray(node)) {
            node.slice(0, 20).forEach((item) => walk(item, path + "[]", depth + 1));
         } else if (node && typeof node === "object") {
            Object.keys(node).forEach((key) => walk(node[key], path ? path + "." + key : key, depth + 1));
         }
      };

      walk(parsed, "", 0);
      return Object.fromEntries(Object.entries(paths).map(([path, kinds]) => [path, Array.from(kinds).join("/")]));
   };

   window.__reCaptureDump = (options) => {
      const settings = options || {};
      const matches = records.filter((record) => !settings.match || record.url.includes(settings.match));

      return matches.map((record) => {
         const [path, query] = record.url.split("?");
         const summary = {
            via: record.via,
            method: record.method,
            path: path,
            queryKeys: query ? Array.from(new URLSearchParams(query).keys()) : [],
            status: record.status,
            contentType: record.contentType,
            ms: record.ms,
            requestHeaderNames: record.requestHeaderNames,
            requestBodyLength: record.requestBody ? record.requestBody.length : 0,
            responseBodyLength: record.responseBody ? record.responseBody.length : 0,
            responseShape: record.responseBody ? shapeOf(record.responseBody) : null,
         };

         if (settings.values) {
            summary.url = record.url;
            summary.requestBody = record.requestBody;
            summary.responseBody = record.responseBody;
         }

         return summary;
      });
   };

   return { installed: true };
})();
