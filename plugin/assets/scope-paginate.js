async () => {
   const waitMs = 2500;
   const staticAsset = /\.(js|mjs|css|woff2?|ttf|png|jpe?g|gif|svg|webp|ico|map|wasm)(\?|$)/i;

   const pattern = (raw) => {
      const url = new URL(raw, location.href);
      const path = url.pathname.split("/").map((segment) => (/^\d+$|^[0-9a-f]{12,}$/i.test(segment) ? "{id}" : segment)).join("/");
      const keys = Array.from(new Set(url.searchParams.keys())).sort();
      const host = url.origin === location.origin ? "" : url.origin;

      return host + path + (keys.length ? "?" + keys.join("&") : "");
   };

   const pageLink = document.querySelector("a[rel=next], a[href*='page='], a[href*='after='], a[href*='cursor=']");
   const moreButton = Array.from(document.querySelectorAll("button")).find((button) => /^(load more|show more|next)$/i.test((button.textContent || "").trim()));
   const control = pageLink || moreButton;

   if (!control) {
      return { clicked: false, reason: "no next link or load-more button" };
   }

   const startUrl = pattern(location.href);
   const startedAt = performance.now();
   const startCount = document.querySelectorAll("li, tr, article, [role=listitem], [role=row]").length;

   control.click();
   await new Promise((resolve) => setTimeout(resolve, waitMs));

   const fresh = performance.getEntriesByType("resource")
      .filter((entry) => entry.startTime >= startedAt && /^https?:/.test(entry.name) && !staticAsset.test(new URL(entry.name).pathname))
      .map((entry) => entry.initiatorType + " " + pattern(entry.name));

   return {
      clicked: true,
      control: pageLink ? "link" : "button",
      from: startUrl,
      to: pattern(location.href),
      softNavigation: performance.getEntriesByType("navigation").length === 1,
      itemsBefore: startCount,
      itemsAfter: document.querySelectorAll("li, tr, article, [role=listitem], [role=row]").length,
      requests: Array.from(new Set(fresh)).slice(0, 15),
   };
}
