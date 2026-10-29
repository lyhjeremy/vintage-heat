/* Vintage explorer: pick a region, see each vintage's score against its season's
   temperature anomaly, with the fitted line for the region's climate group.
   Data: assets/data.json, written by scripts/export_web.py. No libraries. */
(function () {
  "use strict";
  var root = document.querySelector("[data-explorer]");
  if (!root) return;
  var src = root.getAttribute("data-src");
  var NS = "http://www.w3.org/2000/svg";
  var W = 640, H = 380, M = { l: 54, r: 18, t: 18, b: 52 };
  function size() {
    // a narrower drawing on phones so the labels stay legible after scaling
    var narrow = root.clientWidth < 520;
    W = narrow ? 400 : 640; H = narrow ? 330 : 380;
    M = narrow ? { l: 40, r: 20, t: 14, b: 46 } : { l: 54, r: 18, t: 18, b: 52 };
  }

  function el(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function fmt(x, d) {
    var s = Math.abs(x).toFixed(d);
    return (x < 0 ? "−" : x > 0 ? "+" : "") + s;
  }

  fetch(src).then(function (r) { return r.json(); }).then(function (D) {
    var group = "cool";
    var btns = root.querySelectorAll("[data-group]");
    var sel = root.querySelector("select");
    var fig = root.querySelector(".ex-chart");
    var read = root.querySelector(".ex-read");
    var tbody = root.querySelector("tbody");
    root.querySelector(".ex-skeleton").hidden = true;
    root.querySelector(".ex-body").hidden = false;

    // the temperature axis is shared by every region; the score axis fits each region
    var xs = [];
    D.regions.forEach(function (r) { r.v.forEach(function (p) { xs.push(p[1]); }); });
    var x0 = Math.floor(Math.min.apply(null, xs) * 2) / 2, x1 = Math.ceil(Math.max.apply(null, xs) * 2) / 2;
    var y0 = -2, y1 = 2;
    function X(v) { return M.l + (v - x0) / (x1 - x0) * (W - M.l - M.r); }
    function Y(v) { return H - M.b - (v - y0) / (y1 - y0) * (H - M.t - M.b); }

    function fill() {
      sel.innerHTML = "";
      D.regions.filter(function (r) { return r.group === group; })
        .sort(function (a, b) { return b.n - a.n; })
        .forEach(function (r) {
          var o = document.createElement("option");
          o.value = r.key; o.textContent = r.name + " (" + r.normal.toFixed(1) + " °C)";
          sel.appendChild(o);
        });
      btns.forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-group") === group ? "true" : "false"); });
      draw();
    }

    function draw() {
      var r = D.regions.filter(function (q) { return q.key === sel.value; })[0];
      if (!r) return;
      var g = D.groups[r.group];
      size();
      var ym = 2;
      r.v.forEach(function (p) { ym = Math.max(ym, Math.ceil(Math.abs(p[2]))); });
      y0 = -ym; y1 = ym;
      fig.innerHTML = "";
      var svg = el("svg", { viewBox: "0 0 " + W + " " + H, role: "img" }, fig);
      var t;
      for (t = Math.ceil(y0); t <= y1; t += 1) {
        el("line", { x1: M.l, x2: W - M.r, y1: Y(t), y2: Y(t), "class": t === 0 ? "ex-zero" : "ex-grid" }, svg);
        var lab = el("text", { x: M.l - 8, y: Y(t) + 4, "text-anchor": "end", "class": "ex-tick" }, svg);
        lab.textContent = t === 0 ? "0" : fmt(t, 0);
      }
      for (t = Math.ceil(x0 * 2) / 2; t <= x1 + 1e-9; t += 0.5) {
        el("line", { x1: X(t), x2: X(t), y1: H - M.b, y2: H - M.b + 5, "class": "ex-axis" }, svg);
        var lx = el("text", { x: X(t), y: H - M.b + 19, "text-anchor": "middle", "class": "ex-tick" }, svg);
        lx.textContent = t === 0 ? "0" : fmt(t, 1);
      }
      el("line", { x1: X(0), x2: X(0), y1: M.t, y2: H - M.b, "class": "ex-zero" }, svg);
      var xl = el("text", { x: (M.l + W - M.r) / 2, y: H - 8, "text-anchor": "middle", "class": "ex-label" }, svg);
      xl.textContent = W > 500 ? "Season temperature against the region's 1991-2020 normal (°C)" : "Season vs 1991-2020 normal (°C)";
      var yl = el("text", { x: 14, y: (M.t + H - M.b) / 2, "text-anchor": "middle", "class": "ex-label",
                            transform: "rotate(-90 14 " + (M.t + H - M.b) / 2 + ")" }, svg);
      yl.textContent = W > 500 ? "Score against expectation (points)" : "Score vs expected";
      // fitted line for the group, through the origin over the axis range
      el("line", { x1: X(x0), y1: Y(g.b * x0), x2: X(x1), y2: Y(g.b * x1), "class": "ex-fit" }, svg);
      r.v.forEach(function (p) {
        var c = el("circle", { cx: X(p[1]), cy: Y(p[2]), r: Math.max(3.5, Math.min(11, Math.sqrt(p[3]) * 0.9)), "class": "ex-dot" }, svg);
        var tt = el("title", {}, c);
        tt.textContent = p[0] + ": " + fmt(p[1], 2) + " °C, " + fmt(p[2], 2) + " points, " + p[3] + " reviews";
        if (W > 500) {
          var lab = el("text", { x: X(p[1]) + 8, y: Y(p[2]) - 7, "class": "ex-yr" }, svg);
          lab.textContent = "’" + String(p[0]).slice(2);
        }
      });
      var hot = r.v.slice().sort(function (a, b) { return b[1] - a[1]; })[0];
      var cold = r.v.slice().sort(function (a, b) { return a[1] - b[1]; })[0];
      svg.setAttribute("aria-label", r.name + ": " + r.v.length + " vintages plotted. Warmest season " + hot[0] +
        " scored " + fmt(hot[2], 2) + " points against expectation; coolest " + cold[0] + " scored " + fmt(cold[2], 2) + ".");
      read.innerHTML = "";
      var p1 = document.createElement("p");
      p1.textContent = r.full + ". Normal season " + r.normal.toFixed(1) + " °C (Jones's " + r.band +
        " band), " + r.n.toLocaleString("en-US") + " reviews over " + r.v.length + " vintages. Warmest season: " + hot[0] +
        " (" + fmt(hot[1], 1) + " °C), " + fmt(hot[2], 2) + " points against expectation. Coolest: " + cold[0] +
        " (" + fmt(cold[1], 1) + " °C), " + fmt(cold[2], 2) + " points.";
      var p2 = document.createElement("p");
      p2.className = "ex-note";
      p2.textContent = "Line: the model's estimate for all " + g.regions + " regions in this group, " + fmt(g.b, 2) +
        " points per °C (95% interval " + fmt(g.lo, 2) + " to " + fmt(g.hi, 2) + "). This region's own vintages alone give " +
        fmt(r.slope, 2) + " points per °C, from " + r.v.length + " points, which is noisy.";
      read.appendChild(p1); read.appendChild(p2);
      tbody.innerHTML = "";
      r.v.forEach(function (p) {
        var tr = document.createElement("tr");
        [String(p[0]), fmt(p[1], 2), fmt(p[2], 2), p[4].toFixed(1), String(p[3])].forEach(function (s, i) {
          var td = document.createElement("td"); td.textContent = s; if (i) td.className = "num"; tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
    }

    btns.forEach(function (b) {
      b.addEventListener("click", function () { group = b.getAttribute("data-group"); fill(); });
    });
    sel.addEventListener("change", draw);
    var lastW = root.clientWidth;
    window.addEventListener("resize", function () {
      if (Math.abs(root.clientWidth - lastW) > 40) { lastW = root.clientWidth; draw(); }
    });
    fill();
  }).catch(function () {
    root.querySelector(".ex-skeleton").hidden = true;
    var p = document.createElement("p");
    p.textContent = "The chart data did not load. The figures below show the same results.";
    root.appendChild(p);
  });
})();
