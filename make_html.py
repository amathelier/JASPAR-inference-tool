#!/usr/bin/env python

"""
Generate an HTML visualization report from JASPAR profile inference results.

Requires (all available in the JASPAR-profile-inference conda environment):
  - pyjaspar  : fetches motif PFMs and metadata from the bundled JASPAR SQLite DB
  - logomaker : renders sequence logos as matplotlib figures
  - matplotlib: backend for logo SVG export
"""

import argparse
import re
import sys
from io import StringIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import logomaker
import pandas as pd
from pyjaspar import jaspardb

JASPAR_BASE_URL = "https://jaspar.elixir.no"

# ─────────────────────────────────────────────
# JASPAR data retrieval via pyjaspar
# ─────────────────────────────────────────────

def fetch_motifs(matrix_ids):
    """
    Fetch pyjaspar Motif objects for all *matrix_ids* in one DB connection.

    Returns a dict {matrix_id: motif}.  Missing IDs are silently skipped.
    """
    jdb = jaspardb()          # connects to the bundled JASPAR2026 SQLite DB
    motifs = {}
    for mid in matrix_ids:
        try:
            motif = jdb.fetch_motif_by_id(mid)
            if motif is not None:
                motifs[mid] = motif
        except Exception:
            pass
    return motifs


def motif_metadata(motif):
    """Return a dict with display-ready TF metadata from a pyjaspar Motif."""
    def _join(val):
        if isinstance(val, (list, tuple)):
            return ", ".join(str(v) for v in val) or "N/A"
        return str(val) if val else "N/A"

    return {
        "name":   motif.name,
        "class":  _join(getattr(motif, "tf_class",  None)),
        "family": _join(getattr(motif, "tf_family", None)),
    }


# ─────────────────────────────────────────────
# Sequence logo SVG generation via logomaker
# ─────────────────────────────────────────────

# Classic DNA colour scheme matching JASPAR's website palette
_DNA_COLORS = {"A": "#109648", "C": "#255C99", "G": "#F7B32B", "T": "#D62839"}


def make_logo_svg(motif):
    """
    Render a sequence logo for *motif* and return an inline SVG string.

    The logo shows information content (bits) per position using the classic
    DNA colour scheme.  Returns None if logo generation fails.
    """
    try:
        counts_df = pd.DataFrame(
            {b: list(motif.counts[b]) for b in "ACGT"}
        )
    except Exception:
        return None

    n_pos = len(counts_df)
    fig_w = max(2.5, n_pos * 0.42)
    fig, ax = plt.subplots(figsize=(fig_w, 1.9))

    try:
        info_df = logomaker.transform_matrix(
            counts_df, from_type="counts", to_type="information"
        )
        logo = logomaker.Logo(
            info_df,
            ax=ax,
            color_scheme=_DNA_COLORS,
            font_name="DejaVu Sans",
            show_spines=False,
        )
        logo.style_spines(spines=["left"], visible=True, linewidth=0.6)
        logo.ax.set_ylabel("bits", fontsize=7, labelpad=2)
        logo.ax.tick_params(labelsize=6, length=2)
        logo.ax.yaxis.set_ticks([0, 1, 2])
        plt.tight_layout(pad=0.25)
    except Exception:
        plt.close(fig)
        return None

    buf = StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", transparent=True)
    plt.close(fig)

    svg = buf.getvalue()
    # Strip the XML declaration so the SVG can be embedded inline
    svg = re.sub(r"<\?xml[^?]*\?>\s*", "", svg).strip()
    return svg


# ─────────────────────────────────────────────
# HTML rendering
# ─────────────────────────────────────────────

def _esc(s):
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _fmt_evalue(v):
    try:
        f = float(v)
        return "0" if f == 0 else "%.2e" % f
    except (ValueError, TypeError):
        return _esc(str(v))


def generate_html_report(results, output_file):
    """
    Write a self-contained HTML visualization to *output_file*.

    Args:
        results:     list of [Query, TF Name, TF Matrix, E-value,
                              Query Start-End, TF Start-End, DBD %ID]
        output_file: path for the HTML file
    """
    by_query = {}
    for row in results:
        by_query.setdefault(row[0], []).append(row)

    unique_matrices = sorted(set(row[2] for row in results))

    # Fetch all motifs from the local JASPAR DB in one pass
    motifs = fetch_motifs(unique_matrices)

    # Generate SVG logos and collect metadata
    logos    = {}
    metadata = {}
    for mid in unique_matrices:
        motif = motifs.get(mid)
        if motif is not None:
            logos[mid]    = make_logo_svg(motif)
            metadata[mid] = motif_metadata(motif)
        else:
            logos[mid]    = None
            metadata[mid] = {"name": "N/A", "class": "N/A", "family": "N/A"}

    html = _build_html(by_query, logos, metadata)
    with open(output_file, "w", encoding="utf-8") as fh:
        fh.write(html)


def _build_html(by_query, logos, metadata):

    n_queries = len(by_query)
    n_results = sum(len(v) for v in by_query.values())

    # ── Navigation ────────────────────────────────────────────────────────────
    nav_items = ""
    for i, (query_id, rows) in enumerate(by_query.items()):
        nav_items += (
            '<li><a href="#q%d" title="%s">%s</a>'
            '<span class="badge">%d</span></li>\n'
            % (i, _esc(query_id), _esc(query_id[:55]), len(rows))
        )

    # ── Result sections ───────────────────────────────────────────────────────
    sections = ""
    for i, (query_id, rows) in enumerate(by_query.items()):
        table_rows = ""
        for row in rows:
            _, tf_name_inferred, matrix_id = row[0], row[1], row[2]
            evalue, q_region, tf_region, dbd_pid = row[3], row[4], row[5], row[6]

            meta = metadata.get(matrix_id, {"name": "N/A", "class": "N/A", "family": "N/A"})
            # Use the name from pyjaspar (canonical) when available
            tf_name = meta["name"] if meta["name"] != "N/A" else tf_name_inferred

            svg = logos.get(matrix_id)
            logo_cell = (
                '<div class="logo-wrap">%s</div>' % svg
                if svg
                else '<span class="na">—</span>'
            )

            jaspar_link = "%s/matrix/%s" % (JASPAR_BASE_URL, matrix_id)

            table_rows += """
            <tr>
              <td class="logo-td">%(logo)s</td>
              <td><a href="%(link)s" target="_blank" rel="noopener noreferrer"
                     class="matrix-link">%(mid)s</a></td>
              <td class="tf-name">%(name)s</td>
              <td>%(cls)s</td>
              <td>%(fam)s</td>
              <td class="num">%(ev)s</td>
              <td class="num">%(pid)s</td>
              <td class="mono">%(qr)s</td>
              <td class="mono">%(tr)s</td>
            </tr>""" % {
                "logo": logo_cell,
                "link": jaspar_link,
                "mid":  _esc(matrix_id),
                "name": _esc(tf_name),
                "cls":  _esc(meta["class"]),
                "fam":  _esc(meta["family"]),
                "ev":   _fmt_evalue(evalue),
                "pid":  _esc(str(dbd_pid)),
                "qr":   _esc(str(q_region)),
                "tr":   _esc(str(tf_region)),
            }

        sections += """
      <section id="q%(i)d" class="query-section">
        <h2 class="query-title">
          <span class="query-label">Query</span>
          <code class="query-id">%(qid)s</code>
          <span class="badge">%(n)d profile%(pl)s</span>
        </h2>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Logo</th>
                <th>Profile ID</th>
                <th>TF Name</th>
                <th>TF Class</th>
                <th>TF Family</th>
                <th>E-value</th>
                <th>DBD %%ID</th>
                <th>Query Region</th>
                <th>TF Region</th>
              </tr>
            </thead>
            <tbody>%(rows)s</tbody>
          </table>
        </div>
      </section>""" % {
            "i":   i,
            "qid": _esc(query_id),
            "n":   len(rows),
            "pl":  "s" if len(rows) != 1 else "",
            "rows": table_rows,
        }

    # ── Legend ─────────────────────────────────────────────────────────────────
    legend_items = "".join(
        '<span class="leg-item">'
        '<span class="leg-dot" style="background:%s"></span>%s'
        "</span>" % (color, base)
        for base, color in _DNA_COLORS.items()
    )

    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>JASPAR Profile Inference Report</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:       #f7f8fa;
      --surface:  #ffffff;
      --border:   #dde1e7;
      --text:     #1a1d23;
      --text-dim: #6b7280;
      --accent:   #1a56db;
      --accent-h: #1341b0;
      --header-h: 52px;
      --nav-w:    230px;
      --radius:   8px;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                   Helvetica, Arial, sans-serif;
      font-size: 14px;
      line-height: 1.5;
      color: var(--text);
      background: var(--bg);
      display: grid;
      grid-template-rows: var(--header-h) 1fr;
      grid-template-columns: var(--nav-w) 1fr;
      min-height: 100vh;
    }

    /* ── Header ── */
    header {
      grid-column: 1 / -1;
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      padding: 0 20px;
      gap: 14px;
    }
    header h1   { font-size: 16px; font-weight: 700; white-space: nowrap; }
    .header-meta { color: var(--text-dim); font-size: 13px; flex: 1; }
    .header-legend {
      display: flex; align-items: center; gap: 8px;
      font-size: 12px; color: var(--text-dim);
    }
    .leg-item { display: flex; align-items: center; gap: 4px; font-weight: 700; }
    .leg-dot  { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }

    /* ── Sidebar ── */
    nav {
      background: var(--surface);
      border-right: 1px solid var(--border);
      overflow-y: auto;
      padding: 10px 0;
      position: sticky;
      top: var(--header-h);
      height: calc(100vh - var(--header-h));
    }
    nav h3 {
      padding: 0 14px 6px;
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      color: var(--text-dim);
    }
    nav ul { list-style: none; }
    nav li  { display: flex; align-items: center; }
    nav a {
      flex: 1; display: block; padding: 5px 14px;
      color: var(--text); text-decoration: none;
      font-size: 12px; overflow: hidden;
      text-overflow: ellipsis; white-space: nowrap;
    }
    nav a:hover { background: var(--bg); color: var(--accent); }
    nav li .badge { margin-right: 8px; font-size: 11px; color: var(--text-dim); }

    /* ── Main content ── */
    main { padding: 24px 28px; overflow-x: hidden; }

    .query-section {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      margin-bottom: 24px;
      overflow: hidden;
    }
    .query-title {
      display: flex; align-items: baseline;
      flex-wrap: wrap; gap: 8px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      background: var(--bg);
      font-size: 13px; font-weight: 600;
    }
    .query-label {
      font-size: 10px; font-weight: 500;
      text-transform: uppercase; letter-spacing: 0.07em;
      color: var(--text-dim);
    }
    code.query-id {
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 12px; font-weight: 400;
      word-break: break-all; flex: 1;
    }
    .query-title .badge { font-size: 12px; font-weight: 400; color: var(--text-dim); }

    .table-scroll { overflow-x: auto; }

    table { width: 100%%; border-collapse: collapse; font-size: 12.5px; }
    thead th {
      background: var(--bg);
      padding: 7px 10px;
      text-align: left;
      font-size: 10px; font-weight: 600;
      text-transform: uppercase; letter-spacing: 0.05em;
      color: var(--text-dim);
      border-bottom: 1px solid var(--border);
      white-space: nowrap;
    }
    tbody tr { border-bottom: 1px solid var(--border); }
    tbody tr:last-child { border-bottom: none; }
    tbody tr:hover { background: #f0f4ff; }
    td { padding: 6px 10px; vertical-align: middle; }
    td.logo-td {
      padding: 4px 8px;
      min-width: 100px;
    }
    .logo-wrap svg {
      display: block;
      max-width: 100%%;
      height: auto;
    }
    .matrix-link {
      color: var(--accent); text-decoration: none;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 11.5px; font-weight: 600;
    }
    .matrix-link:hover { color: var(--accent-h); text-decoration: underline; }
    .tf-name { font-weight: 600; }
    td.num  { font-variant-numeric: tabular-nums; text-align: right; }
    td.mono {
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 11.5px;
    }
    .na { color: var(--text-dim); }

    @media (max-width: 860px) {
      body { grid-template-columns: 1fr; }
      nav  { position: static; height: auto; border-right: none;
             border-bottom: 1px solid var(--border); }
    }
  </style>
</head>
<body>

<header>
  <h1>JASPAR Profile Inference</h1>
  <span class="header-meta">
    %(nq)d quer%(qpl)s &nbsp;·&nbsp; %(nr)d inferred profile%(rpl)s
  </span>
  <div class="header-legend">
    <span>Bases:</span>%(legend)s
  </div>
</header>

<nav>
  <h3>Queries</h3>
  <ul>%(nav)s</ul>
</nav>

<main>%(sections)s</main>

</body>
</html>""" % {
        "nq":      n_queries,
        "qpl":     "y" if n_queries == 1 else "ies",
        "nr":      n_results,
        "rpl":     "" if n_results == 1 else "s",
        "legend":  legend_items,
        "nav":     nav_items,
        "sections": sections,
    }


# ─────────────────────────────────────────────
# Standalone CLI
# ─────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate an HTML report from infer_profile.py TSV output."
    )
    parser.add_argument("tsv_file",  help="TSV results file from infer_profile.py")
    parser.add_argument("html_file", help="output HTML file")
    return parser.parse_args()


def _read_tsv(tsv_file):
    results = []
    with open(tsv_file) as fh:
        header = True
        for line in fh:
            if header:
                header = False
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 7:
                results.append(parts[:7])
    return results


def main():
    args = parse_args()
    results = _read_tsv(args.tsv_file)
    if not results:
        sys.stderr.write("No results found in %s\n" % args.tsv_file)
        sys.exit(1)
    generate_html_report(results, args.html_file)
    sys.stdout.write("HTML report written to %s\n" % args.html_file)


if __name__ == "__main__":
    main()
