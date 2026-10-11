// Offscreen WKWebView snapshot of an HTML banner at an exact pixel scale, with the theme set
// through NSAppearance so prefers-color-scheme in the page follows it.
//
// usage: render_html --input FILE --out FILE [--width 900] [--height 300] [--scale 2]
//                    [--theme light|dark] [--transparent] [--manifest FILE] [--read-root DIR]
//                    [--full-height] [--settle 0.3] [--timeout 20]
//
// WKWebView renders at the main screen's backing scale, so the page zoom is set to
// scale / backingScale and the frame scaled the same way; the snapshot then comes out at
// exactly width * scale pixels on a 1x or a 2x screen. getBoundingClientRect stays in CSS
// pixels under pageZoom, which is what the manifest records. The snapshot waits for
// document.fonts.ready, then a settle delay for layout. --full-height grows the frame to the
// document's scroll height before the snapshot (for page mocks). --manifest writes every
// element carrying data-text (or every element with its own text when none is marked) with
// its box, computed color, font and nearest painted background, plus the loaded fonts.
// macOS only. Compile with swiftc -O, or run regenerate.sh, which caches the build.

import AppKit
import Foundation
import WebKit

struct Options {
   var input = ""
   var out = ""
   var width = 900.0
   var height = 300.0
   var scale = 2.0
   var theme = "light"
   var transparent = false
   var manifest: String?
   var readRoot: String?
   var fullHeight = false
   var settle = 0.3
   var timeout = 20.0
}

func fail(_ message: String, code: Int32 = 2) -> Never {
   FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
   exit(code)
}

func parseOptions() -> Options {
   var options = Options()
   let arguments = Array(CommandLine.arguments.dropFirst())
   var index = 0

   func value(_ flag: String) -> String {
      index += 1

      guard index < arguments.count else {
         fail("missing value for " + flag)
      }

      return arguments[index]
   }

   while index < arguments.count {
      let flag = arguments[index]

      switch flag {
      case "--input": options.input = value(flag)
      case "--out": options.out = value(flag)
      case "--width": options.width = Double(value(flag)) ?? options.width
      case "--height": options.height = Double(value(flag)) ?? options.height
      case "--scale": options.scale = Double(value(flag)) ?? options.scale
      case "--theme": options.theme = value(flag)
      case "--transparent": options.transparent = true
      case "--manifest": options.manifest = value(flag)
      case "--read-root": options.readRoot = value(flag)
      case "--full-height": options.fullHeight = true
      case "--settle": options.settle = Double(value(flag)) ?? options.settle
      case "--timeout": options.timeout = Double(value(flag)) ?? options.timeout
      default: fail("unknown argument " + flag)
      }

      index += 1
   }

   let hasPaths = !options.input.isEmpty && !options.out.isEmpty

   if !hasPaths {
      fail("usage: render_html --input FILE --out FILE [--width W --height H --scale S --theme light|dark --transparent --manifest FILE --read-root DIR --full-height --settle SEC --timeout SEC]")
   }

   return options
}

let manifestScript = """
(() => {
   const marked = Array.from(document.querySelectorAll("[data-text]"));
   const hasOwnText = (element) => Array.from(element.childNodes).some((node) => node.nodeType === 3 && node.textContent.trim().length > 0);
   const elements = marked.length > 0 ? marked : Array.from(document.body.querySelectorAll("*")).filter(hasOwnText);
   const paintedBackground = (start) => {
      let node = start;
      while (node && node !== document.documentElement) {
         const color = getComputedStyle(node).backgroundColor;
         const isPainted = color && color !== "rgba(0, 0, 0, 0)" && color !== "transparent";
         if (isPainted) { return color; }
         node = node.parentElement;
      }
      const rootColor = getComputedStyle(document.documentElement).backgroundColor;
      return rootColor === "rgba(0, 0, 0, 0)" ? null : rootColor;
   };
   const boxes = elements.map((element) => {
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return {
         text: (element.dataset.text || element.textContent).trim(),
         role: element.dataset.role || "text",
         x: rect.left, y: rect.top, width: rect.width, height: rect.height,
         color: style.color,
         fontFamily: style.fontFamily,
         fontSize: parseFloat(style.fontSize),
         fontWeight: style.fontWeight,
         background: paintedBackground(element)
      };
   });
   const fonts = [];
   document.fonts.forEach((face) => fonts.push({ family: face.family.replace(/["']/g, ""), weight: face.weight, style: face.style, status: face.status }));
   return JSON.stringify({
      boxes: boxes,
      fonts: fonts,
      bodyBackground: getComputedStyle(document.body).backgroundColor,
      htmlBackground: getComputedStyle(document.documentElement).backgroundColor,
      scrollWidth: document.documentElement.scrollWidth,
      scrollHeight: document.documentElement.scrollHeight,
      title: document.title
   });
})()
"""

final class Snapper: NSObject, WKNavigationDelegate {
   let view: WKWebView
   let options: Options
   let zoom: Double
   let backingScale: Double

   init(options: Options) {
      self.options = options
      backingScale = Double(NSScreen.main?.backingScaleFactor ?? 1.0)
      zoom = options.scale / backingScale
      view = WKWebView(frame: NSRect(x: 0, y: 0, width: options.width * zoom, height: options.height * zoom))
      super.init()
      view.pageZoom = zoom
      view.navigationDelegate = self
      let appearanceName: NSAppearance.Name = options.theme == "dark" ? .darkAqua : .aqua
      view.appearance = NSAppearance(named: appearanceName)

      if options.transparent {
         view.setValue(false, forKey: "drawsBackground")
      }
   }

   func load() {
      let input = URL(fileURLWithPath: options.input)
      let readRoot = URL(fileURLWithPath: options.readRoot ?? input.deletingLastPathComponent().path)
      view.loadFileURL(input, allowingReadAccessTo: readRoot)
   }

   func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
      fail("load failed: " + error.localizedDescription, code: 1)
   }

   func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
      view.callAsyncJavaScript("await document.fonts.ready; return document.fonts.size;", arguments: [:], in: nil, in: .page) { _ in
         DispatchQueue.main.asyncAfter(deadline: .now() + self.options.settle) {
            self.growIfNeeded {
               self.collectManifest { manifest in
                  self.snapshot(manifest: manifest)
               }
            }
         }
      }
   }

   func growIfNeeded(_ next: @escaping () -> Void) {
      if !options.fullHeight {
         next()
         return
      }

      view.evaluateJavaScript("document.documentElement.scrollHeight") { result, _ in
         let height = (result as? Double) ?? self.options.height
         self.view.frame = NSRect(x: 0, y: 0, width: self.options.width * self.zoom, height: ceil(height) * self.zoom)
         DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) { next() }
      }
   }

   func collectManifest(_ next: @escaping ([String: Any]) -> Void) {
      view.evaluateJavaScript(manifestScript) { result, error in
         var manifest: [String: Any] = [:]

         if let text = result as? String, let data = text.data(using: .utf8), let parsed = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            manifest = parsed
         } else if let error {
            manifest["manifestError"] = error.localizedDescription
         }

         next(manifest)
      }
   }

   func snapshot(manifest: [String: Any]) {
      let config = WKSnapshotConfiguration()
      config.snapshotWidth = NSNumber(value: view.frame.width)

      view.takeSnapshot(with: config) { image, error in
         guard let image, let tiff = image.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff) else {
            fail("snapshot failed: " + (error?.localizedDescription ?? "no image"), code: 1)
         }

         guard let png = rep.representation(using: .png, properties: [:]) else {
            fail("png encoding failed", code: 1)
         }

         do {
            try png.write(to: URL(fileURLWithPath: self.options.out))
         } catch {
            fail("cannot write " + self.options.out + ": " + error.localizedDescription, code: 1)
         }

         let expectedWidth = Int((self.options.width * self.options.scale).rounded())
         let widthMatches = rep.pixelsWide == expectedWidth

         if !widthMatches {
            FileHandle.standardError.write("warning: snapshot is \(rep.pixelsWide) px wide, expected \(expectedWidth)\n".data(using: .utf8)!)
         }

         self.writeManifest(manifest, pixelsWide: rep.pixelsWide, pixelsHigh: rep.pixelsHigh)
         print("rendered \(self.options.out) \(rep.pixelsWide)x\(rep.pixelsHigh) theme=\(self.options.theme) scale=\(self.options.scale) zoom=\(self.zoom) backing=\(self.backingScale)")
         exit(0)
      }
   }

   func writeManifest(_ page: [String: Any], pixelsWide: Int, pixelsHigh: Int) {
      guard let path = options.manifest else {
         return
      }

      var manifest = page
      manifest["input"] = options.input
      manifest["out"] = options.out
      manifest["theme"] = options.theme
      manifest["cssWidth"] = options.width
      manifest["cssHeight"] = options.fullHeight ? view.frame.height / zoom : options.height
      manifest["scale"] = options.scale
      manifest["pixelWidth"] = pixelsWide
      manifest["pixelHeight"] = pixelsHigh
      manifest["transparent"] = options.transparent
      manifest["backingScale"] = backingScale
      manifest["zoom"] = zoom

      guard let data = try? JSONSerialization.data(withJSONObject: manifest, options: [.prettyPrinted, .sortedKeys]) else {
         fail("manifest encoding failed", code: 1)
      }

      do {
         try data.write(to: URL(fileURLWithPath: path))
      } catch {
         fail("cannot write manifest: " + error.localizedDescription, code: 1)
      }
   }
}

let options = parseOptions()
let app = NSApplication.shared
let snapper = Snapper(options: options)
snapper.load()
DispatchQueue.main.asyncAfter(deadline: .now() + options.timeout) {
   fail("timeout after \(options.timeout) s", code: 3)
}
app.run()
