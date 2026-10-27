() => {
   const browserHeaders = /^(accept-encoding|accept-language|connection|content-length|host|origin|referer|user-agent|sec-.*)$/i;
   const record = window.__reCapture && window.__reCapture[window.__wreTarget];

   if (!record) {
      return { error: "no target; run assets/reverse-capture.js first" };
   }

   const minimal = window.__wreMinimal;
   const url = new URL(record.url, location.href);
   let headers = (record.requestHeaders || []).filter((pair) => !browserHeaders.test(pair[0]));
   let body = record.requestBody;

   if (minimal) {
      for (const name of Array.from(url.searchParams.keys())) {
         if (!minimal.params.includes(name)) {
            url.searchParams.delete(name);
         }
      }

      headers = headers.filter((pair) => minimal.headers.includes(pair[0]));

      try {
         const fields = JSON.parse(body);
         body = JSON.stringify(Object.fromEntries(Object.entries(fields).filter(([name]) => minimal.fields.includes(name))));
      } catch (error) {
      }
   }

   return {
      method: record.method,
      url: url.href,
      headers: Object.fromEntries(headers),
      body: body,
      origin: location.origin,
      minimal: Boolean(minimal),
   };
}
