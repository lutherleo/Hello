"use strict";

/*
 * Blueprint theme runtime.
 *
 * - Replaces core's color_mode_switcher: "dark" renders as a cyanotype
 *   blueprint, "light" as a whiteprint. Blueprint is the default when the
 *   visitor has never chosen, regardless of OS preference.
 * - Draws the scoreboard's top-ten graph as SVG step lines in place of
 *   core's ECharts canvas, so it takes the print's colors from CSS.
 * - Fills [data-bp-countdown] blocks in page content with the time to the
 *   CTF's start or end.
 */
(function () {
  var STORAGE_KEY = "theme";

  function storedTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      return null;
    }
  }

  function storeTheme(theme) {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      // Private mode or blocked storage: the choice lasts for this page only.
    }
  }

  var currentTheme = storedTheme() === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-bs-theme", currentTheme);

  function syncSwitches() {
    document.querySelectorAll(".theme-switch").forEach(function (button) {
      var next = currentTheme === "dark" ? "whiteprint" : "blueprint";
      button.setAttribute("aria-label", "Switch to " + next);
      button.setAttribute("title", "Switch to " + next);
      var label = button.querySelector("[data-print-label]");
      if (label) {
        label.textContent = currentTheme === "dark" ? "Blueprint" : "Whiteprint";
      }
    });
  }

  window.addEventListener("DOMContentLoaded", function () {
    syncSwitches();
    document.querySelectorAll(".theme-switch").forEach(function (button) {
      button.addEventListener("click", function (event) {
        event.preventDefault();
        currentTheme = currentTheme === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-bs-theme", currentTheme);
        storeTheme(currentTheme);
        syncSwitches();
      });
    });
  });

  // Countdown: any element with [data-bp-countdown] in page content shows the
  // time to the CTF's start, then to its end, from CTFd's configured times.
  function formatSpan(seconds) {
    var d = Math.floor(seconds / 86400);
    var h = Math.floor((seconds % 86400) / 3600);
    var m = Math.floor((seconds % 3600) / 60);
    var s = Math.floor(seconds % 60);
    function pad(n) {
      return String(n).padStart(2, "0");
    }
    return (d > 0 ? d + "d " : "") + pad(h) + "h " + pad(m) + "m " + pad(s) + "s";
  }

  function startCountdowns() {
    var nodes = document.querySelectorAll("[data-bp-countdown]");
    if (!nodes.length || !window.init) {
      return;
    }
    var start = window.init.start ? Number(window.init.start) : null;
    var end = window.init.end ? Number(window.init.end) : null;

    function render() {
      var now = Date.now() / 1000;
      var label;
      var value;
      if (start && now < start) {
        label = "Job starts in";
        value = formatSpan(start - now);
      } else if (end && now < end) {
        label = "Get out in";
        value = formatSpan(end - now);
      } else if (end && now >= end) {
        label = "Status";
        value = "Job’s done";
      } else {
        label = "Status";
        value = "In progress";
      }
      nodes.forEach(function (node) {
        var l = node.querySelector("[data-bp-countdown-label]");
        var v = node.querySelector("[data-bp-countdown-value]");
        if (l) l.textContent = label;
        if (v) v.textContent = value;
      });
    }

    render();
    setInterval(render, 1000);
  }

  window.addEventListener("DOMContentLoaded", startCountdowns);

  // Crew roles: each challenge category is a specialty on the job. Organizers
  // can rename or add roles with theme_settings.category_roles, e.g.
  // {"category_roles": {"pwn": "The Demolitions", "osint": "The Lookout"}}.
  var CREW_ROLES = {
    pwn: "The Demolitions",
    "binary exploitation": "The Demolitions",
    rev: "The Safecracker",
    reversing: "The Safecracker",
    "reverse engineering": "The Safecracker",
    web: "The Inside Man",
    crypto: "The Codebreaker",
    cryptography: "The Codebreaker",
    forensics: "The Cleaner",
    "incident response": "The Cleaner",
    misc: "The Grifter",
    osint: "The Lookout",
    recon: "The Lookout",
    hardware: "The Wheelman",
    intro: "The Rookie",
  };

  // A made-up wallet ID for each crew on the ledger: a stable hash of the
  // account, shown for flavor. It is not an address on any real chain.
  window.bpWallet = function (seed) {
    var h1 = 0x811c9dc5;
    var h2 = 0x9e3779b9;
    var text = String(seed);
    for (var i = 0; i < text.length; i++) {
      var c = text.charCodeAt(i);
      h1 = Math.imul(h1 ^ c, 0x01000193) >>> 0;
      h2 = Math.imul(h2 ^ c, 0x5bd1e995) >>> 0;
    }
    var hex = (h1.toString(16).padStart(8, "0") + h2.toString(16).padStart(8, "0"));
    return "hb_" + hex.slice(0, 6) + "…" + hex.slice(-4);
  };

  window.bpCrewRole = function (category) {
    var key = String(category || "").trim().toLowerCase();
    var settings = window.init && window.init.themeSettings;
    var custom = settings && settings.category_roles;
    if (custom) {
      for (var name in custom) {
        if (String(name).trim().toLowerCase() === key) {
          return custom[name];
        }
      }
    }
    return CREW_ROLES[key] || "";
  };

  // Scoreboard graph: the top ten drawn as step lines on the sheet's grid.
  // Replaces core's ECharts graph so every stroke and label comes from the
  // theme's CSS variables and follows the print switch with no redraw.
  var PAD = { top: 18, right: 20, bottom: 34, left: 52 };

  function escapeHtml(text) {
    return String(text).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function niceStep(max, count) {
    var raw = max / count;
    var mag = Math.pow(10, Math.floor(Math.log10(raw || 1)));
    var norm = raw / mag;
    var step = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 2.5 ? 2.5 : norm <= 5 ? 5 : 10;
    return step * mag;
  }

  function formatTick(ms, spanMs) {
    var d = new Date(ms);
    var month = d.toLocaleString(undefined, { month: "short" });
    var hh = String(d.getHours()).padStart(2, "0");
    var mm = String(d.getMinutes()).padStart(2, "0");
    return spanMs > 2 * 86400000 ? month + " " + d.getDate() : month + " " + d.getDate() + " " + hh + ":" + mm;
  }

  function buildSeries(data) {
    return Object.keys(data)
      .map(function (key) {
        var entry = data[key];
        var total = 0;
        var points = (entry.solves || [])
          .map(function (solve) {
            return { t: new Date(solve.date).getTime(), v: solve.value || 0 };
          })
          .sort(function (a, b) {
            return a.t - b.t;
          })
          .map(function (p) {
            total += p.v;
            return { t: p.t, score: total };
          });
        return { rank: Number(key), name: entry.name, url: entry.account_url, score: total, points: points };
      })
      .sort(function (a, b) {
        return a.rank - b.rank;
      });
  }

  function drawGraph(series, active, width) {
    var SVG_W = Math.max(280, Math.round(width || 1000));
    var SVG_H = SVG_W < 600 ? 280 : 380;
    var times = [];
    series.forEach(function (s) {
      s.points.forEach(function (p) {
        times.push(p.t);
      });
    });
    if (!times.length) {
      return "";
    }
    var now = Date.now();
    var start = window.init && window.init.start ? Number(window.init.start) * 1000 : null;
    var end = window.init && window.init.end ? Number(window.init.end) * 1000 : null;
    var t0 = Math.min.apply(null, times.concat(start ? [start] : []));
    var t1 = Math.max(Math.max.apply(null, times), end ? Math.min(now, end) : now);
    if (t1 <= t0) {
      t1 = t0 + 3600000;
    }
    var maxScore = Math.max.apply(
      null,
      series.map(function (s) {
        return s.score;
      }).concat([1])
    );
    var step = niceStep(maxScore, 5);
    var yMax = Math.ceil(maxScore / step) * step;

    var plotW = SVG_W - PAD.left - PAD.right;
    var plotH = SVG_H - PAD.top - PAD.bottom;
    function x(t) {
      return PAD.left + ((t - t0) / (t1 - t0)) * plotW;
    }
    function y(v) {
      return PAD.top + plotH - (v / yMax) * plotH;
    }

    var out = [];
    for (var v = 0; v <= yMax + 0.001; v += step) {
      out.push(
        '<line class="bp-graph__grid" x1="' + PAD.left + '" x2="' + (SVG_W - PAD.right) +
          '" y1="' + y(v) + '" y2="' + y(v) + '"/>' +
          '<text class="bp-graph__tick" x="' + (PAD.left - 10) + '" y="' + (y(v) + 4) +
          '" text-anchor="end">' + Math.round(v) + "</text>"
      );
    }
    var xTicks = SVG_W < 600 ? 2 : 5;
    for (var i = 0; i <= xTicks; i++) {
      var t = t0 + ((t1 - t0) * i) / xTicks;
      var anchor = i === 0 ? "start" : i === xTicks ? "end" : "middle";
      out.push(
        '<line class="bp-graph__grid" x1="' + x(t) + '" x2="' + x(t) + '" y1="' + PAD.top +
          '" y2="' + (SVG_H - PAD.bottom) + '"/>' +
          '<text class="bp-graph__tick" x="' + x(t) + '" y="' + (SVG_H - 10) + '" text-anchor="' + anchor +
          '">' + escapeHtml(formatTick(t, t1 - t0)) + "</text>"
      );
    }
    out.push(
      '<path class="bp-graph__axis" d="M' + PAD.left + " " + PAD.top + "V" + (SVG_H - PAD.bottom) + "H" +
        (SVG_W - PAD.right) + '"/>'
    );

    // Draw the leader last so it sits on top of the pack.
    series
      .slice()
      .reverse()
      .forEach(function (s) {
        var d = "M" + x(t0) + " " + y(0);
        s.points.forEach(function (p) {
          d += "H" + x(p.t) + "V" + y(p.score);
        });
        d += "H" + x(t1);
        var state = active === null ? "" : active === s.rank ? " is-active" : " is-dimmed";
        var last = s.points.length ? s.points[s.points.length - 1] : { t: t0, score: 0 };
        out.push(
          '<g class="bp-graph__series' + state + '" style="--series: var(--bp-series-' + s.rank + ')">' +
            '<path d="' + d + '"/>' +
            '<rect x="' + (x(last.t) - 3) + '" y="' + (y(last.score) - 3) + '" width="6" height="6"/>' +
            "</g>"
        );
      });

    return (
      '<svg viewBox="0 0 ' + SVG_W + " " + SVG_H + '" width="' + SVG_W + '" height="' + SVG_H + '" aria-hidden="true" focusable="false">' +
      out.join("") +
      "</svg>"
    );
  }

  document.addEventListener("alpine:init", function () {
    window.Alpine.data("BlueprintGraph", function () {
      return {
        series: [],
        active: null,
        pinned: null,
        bracket: null,
        loaded: false,
        width: 1000,

        async update() {
          var data = await window.CTFd.pages.scoreboard.getScoreboardDetail(10, this.bracket);
          this.series = buildSeries(data || {});
          this.loaded = true;
          var self = this;
          this.$nextTick(function () {
            self.measure();
          });
        },

        svg() {
          var focus = this.active !== null ? this.active : this.pinned;
          return drawGraph(this.series, focus, this.width);
        },

        summary() {
          if (!this.series.length) {
            return "";
          }
          var lead = this.series[0];
          return "Score over time for the top " + this.series.length + ". " + lead.name + " leads with " + lead.score + " points.";
        },

        measure() {
          if (this.$refs.plot && this.$refs.plot.clientWidth) {
            this.width = this.$refs.plot.clientWidth;
          }
        },

        init() {
          var self = this;
          this.$nextTick(function () {
            self.measure();
          });
          window.addEventListener("resize", function () {
            self.measure();
          });
          this.update();
          setInterval(function () {
            self.update();
          }, window.scoreboardUpdateInterval || 300000);
        },
      };
    });
  });
})();
