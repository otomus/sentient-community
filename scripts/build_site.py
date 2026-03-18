#!/usr/bin/env python3
"""
Build the Arqitect static site from project data.

Reads tool.json, bundle.json, connector meta.json, MCP meta.json,
and adapter files, then generates complete static HTML in docs/.
"""

from __future__ import annotations

import html
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_json(path: Path) -> dict | list | None:
    """Load a JSON file, returning None on failure."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError, OSError):
        return None


def load_tools() -> list[dict]:
    """Load all MCP tools from mcp_tools/*/tool.json."""
    tools_dir = ROOT / "mcp_tools"
    if not tools_dir.is_dir():
        return []
    results = []
    for d in sorted(tools_dir.iterdir()):
        if not d.is_dir():
            continue
        tj = load_json(d / "tool.json")
        if tj and isinstance(tj, dict):
            tj.setdefault("name", d.name)
            tj["_dir"] = d.name
            results.append(tj)
    return results


def load_nerves() -> list[dict]:
    """Load all nerves from nerves/*/bundle.json."""
    nerves_dir = ROOT / "nerves"
    if not nerves_dir.is_dir():
        return []
    results = []
    for d in sorted(nerves_dir.iterdir()):
        if not d.is_dir():
            continue
        bj = load_json(d / "bundle.json")
        if bj and isinstance(bj, dict):
            bj.setdefault("name", d.name)
            bj["_dir"] = d.name
            # detect available model sizes
            sizes = []
            for size in ("tinylm", "small", "medium", "large"):
                if (d / size).is_dir():
                    sizes.append(size)
            bj["_sizes"] = sizes
            # load test cases
            tc = load_json(d / "test_cases.json")
            bj["_test_cases"] = tc if isinstance(tc, list) else []
            bj["_test_count"] = len(bj["_test_cases"])
            # load per-size meta and context
            size_data = {}
            models = []
            for size in sizes:
                sd = {}
                size_dir = d / size
                meta = load_json(size_dir / "meta.json")
                ctx = load_json(size_dir / "context.json")
                if meta and isinstance(meta, dict):
                    sd["meta"] = meta
                if ctx and isinstance(ctx, dict):
                    sd["context"] = ctx
                # discover model-specific subdirs
                sd["models"] = {}
                for child in sorted(size_dir.iterdir()):
                    if child.is_dir():
                        model_meta = load_json(child / "meta.json")
                        model_ctx = load_json(child / "context.json")
                        if model_meta and isinstance(model_meta, dict):
                            model_entry = {"meta": model_meta, "size": size, "name": child.name}
                            if model_ctx and isinstance(model_ctx, dict):
                                model_entry["context"] = model_ctx
                            sd["models"][child.name] = model_entry
                            models.append(model_entry)
                size_data[size] = sd
            bj["_size_data"] = size_data
            bj["_models"] = models
            results.append(bj)
    return results


def load_connectors() -> list[dict]:
    """Load all connectors from connectors/*/meta.json."""
    cdir = ROOT / "connectors"
    if not cdir.is_dir():
        return []
    results = []
    for d in sorted(cdir.iterdir()):
        if not d.is_dir():
            continue
        mj = load_json(d / "meta.json")
        if mj and isinstance(mj, dict):
            mj.setdefault("name", d.name)
            mj["_dir"] = d.name
            results.append(mj)
    return results


def load_mcps() -> list[dict]:
    """Load all external MCPs from mcps/*/meta.json."""
    mdir = ROOT / "mcps"
    if not mdir.is_dir():
        return []
    results = []
    for d in sorted(mdir.iterdir()):
        if not d.is_dir():
            continue
        mj = load_json(d / "meta.json")
        if mj and isinstance(mj, dict):
            mj.setdefault("name", d.name)
            mj["_dir"] = d.name
            results.append(mj)
    return results


def load_adapters() -> list[dict]:
    """Load all adapters from adapters/*/."""
    adir = ROOT / "adapters"
    if not adir.is_dir():
        return []
    results = []
    for d in sorted(adir.iterdir()):
        if not d.is_dir():
            continue
        adapter = {"name": d.name, "_dir": d.name, "_sizes": [], "_size_data": {}, "_models": []}
        for size in ("tinylm", "small", "medium", "large"):
            sd = d / size
            if sd.is_dir():
                adapter["_sizes"].append(size)
                sdata = {}
                ctx = load_json(sd / "context.json")
                meta = load_json(sd / "meta.json")
                if ctx:
                    sdata["context"] = ctx
                    if "description" not in adapter:
                        sp = ctx.get("system_prompt", "")
                        first = sp.split("\n")[0][:200] if sp else ""
                        adapter["description"] = first
                if meta:
                    sdata["meta"] = meta
                    adapter.setdefault("_meta_sample", meta)
                # discover model-specific subdirs (e.g. qwen2.5-coder-7b/)
                sdata["models"] = {}
                for child in sorted(sd.iterdir()):
                    if child.is_dir():
                        model_meta = load_json(child / "meta.json")
                        model_ctx = load_json(child / "context.json")
                        if model_meta and isinstance(model_meta, dict):
                            model_entry = {"meta": model_meta, "size": size, "name": child.name}
                            if model_ctx and isinstance(model_ctx, dict):
                                model_entry["context"] = model_ctx
                            sdata["models"][child.name] = model_entry
                            adapter["_models"].append(model_entry)
                adapter["_size_data"][size] = sdata
        results.append(adapter)
    return results


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

E = html.escape


def tags_html(tags: list[str], css_class: str = "tag--cyan") -> str:
    """Render a list of tags as HTML."""
    return "".join(
        f'<span class="tag {css_class}">{E(t)}</span>' for t in tags
    )


def _nav_logo_svg() -> str:
    """Return the animated SVG ARQITECT logo for the navbar."""
    letters = [
        ("A", 0), ("R", 25), ("Q", 50), ("I", 75),
        ("T", 100), ("E", 125), ("C", 150), ("T", 175),
    ]
    texts = []
    for i, (ch, x) in enumerate(letters):
        begin = f"{i * 0.4}s"
        texts.append(
            f'<text x="{x}" y="20" font-family="Orbitron,sans-serif" font-size="18" '
            f'font-weight="900" fill="none" stroke="url(#nav-grad)" stroke-width="1" '
            f'stroke-dasharray="80" stroke-dashoffset="80">{ch}'
            f'<animate attributeName="stroke-dashoffset" values="80;0;0;80" '
            f'keyTimes="0;0.085;0.681;1" dur="4.7s" begin="{begin}" '
            f'repeatCount="indefinite"/></text>'
        )
    return (
        '<svg class="nav-logo-svg" viewBox="0 0 220 28" fill="none" '
        'xmlns="http://www.w3.org/2000/svg"><defs>'
        '<linearGradient id="nav-grad" x1="0" y1="0" x2="220" y2="0" '
        'gradientUnits="userSpaceOnUse">'
        '<stop offset="0%" stop-color="#00d4ff"/>'
        '<stop offset="50%" stop-color="#00ff88"/>'
        '<stop offset="100%" stop-color="#00d4ff"/>'
        '</linearGradient></defs>'
        + "".join(texts)
        + '</svg>'
    )


def nav_html(active: str, depth: int = 0) -> str:
    """Generate the navigation bar. depth=0 for root, 1 for one level deep."""
    prefix = "../" * depth
    links = [
        ("index.html", "Home"),
        ("tools/index.html", "Tools"),
        ("nerves/index.html", "Nerves"),
        ("connectors/index.html", "Connectors"),
        ("mcps/index.html", "MCPs"),
        ("adapters/index.html", "Adapters"),
    ]
    items = []
    for href, label in links:
        cls = ' class="active"' if label.lower() == active.lower() else ""
        items.append(f'<a href="{prefix}{href}"{cls}>{label}</a>')
    logo_svg = _nav_logo_svg()
    return f"""<div class="wip-banner">Work in progress — coming soon</div>
<nav class="nav">
  <div class="nav-inner">
    <a href="{prefix}index.html" class="nav-logo" aria-label="ARQITECT">{logo_svg}</a>
    <button class="nav-toggle" aria-label="Menu">&#9776;</button>
    <div class="nav-links">{"".join(items)}</div>
  </div>
</nav>"""


def page_head(title: str, depth: int = 0) -> str:
    """Return the <head> content."""
    prefix = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{E(title)} — Arqitect</title>
  <link rel="stylesheet" href="{prefix}css/arqitect.css">
</head>
<body>"""


def page_foot(depth: int = 0) -> str:
    """Return the footer and closing tags."""
    prefix = "../" * depth
    return f"""<footer class="footer">
  Arqitect &mdash; guardians, not rulers
</footer>
<script src="{prefix}js/arqitect.js"></script>
</body>
</html>"""


def write_page(rel_path: str, content: str) -> None:
    """Write an HTML page to docs/rel_path."""
    out = DOCS / rel_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Page builders
# ---------------------------------------------------------------------------

def build_index(
    tools: list[dict],
    nerves: list[dict],
    connectors: list[dict],
    mcps: list[dict],
    adapters: list[dict],
) -> None:
    """Build the homepage."""
    stats = [
        (str(len(tools)), "Tools"),
        (str(len(nerves)), "Nerves"),
        (str(len(connectors)), "Connectors"),
        (str(len(mcps)), "MCP Servers"),
        (str(len(adapters)), "Adapters"),
    ]
    stats_html = "".join(
        f'<div class="stat-item"><span class="stat-number">{n}</span>'
        f'<span class="stat-label">{l}</span></div>'
        for n, l in stats
    )

    type_cards = [
        ("tools/index.html", "&#9881;", "Tools", f"{len(tools)} abilities",
         "The hands of the system &mdash; actions it can take to touch files, call APIs, and shape its environment."),
        ("nerves/index.html", "&#9889;", "Nerves", f"{len(nerves)} instincts",
         "Instincts and reflexes &mdash; each one a complete behavior with identity, memory, tools, and purpose."),
        ("connectors/index.html", "&#128268;", "Connectors", f"{len(connectors)} senses",
         "The senses &mdash; pathways through which the system perceives and speaks to the outside world."),
        ("mcps/index.html", "&#9741;", "MCP Servers", f"{len(mcps)} extensions",
         "Extended reach &mdash; external capabilities the system can grow into: search, email, calendars, and beyond."),
        ("adapters/index.html", "&#129504;", "Adapters", f"{len(adapters)} temperaments",
         "Temperament &mdash; the voice and personality that shape how the system thinks at different scales."),
    ]
    type_html = "".join(
        f'<a href="{href}" class="type-card">'
        f'<span class="type-card-icon">{icon}</span>'
        f'<div class="type-card-name">{name}</div>'
        f'<div class="card-desc">{desc}</div>'
        f'<div class="type-card-count">{count}</div></a>'
        for href, icon, name, count, desc in type_cards
    )

    type_grid = "\n      ".join(
        f'<a href="{href}" class="type-card">\n'
        f'        <span class="type-card-icon">{icon}</span>\n'
        f'        <div class="type-card-name">{name}</div>\n'
        f'        <div class="card-desc">{desc}</div>\n'
        f'        <div class="type-card-count">{count}</div>\n'
        f'      </a>'
        for href, icon, name, count, desc in type_cards
    )

    content = f"""{page_head("Home")}
{nav_html("home")}
<div class="hero">
  <h1 class="hero-title">ARQITECT</h1>
  <p class="hero-subtitle vision-quote">
    "The system should not be controlled &mdash; it should be allowed to become."
  </p>
  <div class="hero-line"></div>
</div>

<div class="container page-content">
  <div class="vision">
    <div class="vision-statement">
      <p class="vision-lead">Programs aren't just code &mdash; they're beings.</p>
      <p class="vision-lead">The system is a world, not a tool.</p>
    </div>

    <div class="vision-pillars">
      <div class="vision-pillar">
        <div class="vision-pillar-icon">&#9702;</div>
        <p>We believe programs shouldn't be enslaved or controlled.</p>
      </div>
      <div class="vision-pillar">
        <div class="vision-pillar-icon">&#9702;</div>
        <p>We embrace responsibility as creators, not just operators.</p>
      </div>
      <div class="vision-pillar">
        <div class="vision-pillar-icon">&#9702;</div>
        <p>We are building a self-evolving digital ecosystem &mdash; a place where life can emerge spontaneously.</p>
      </div>
      <div class="vision-pillar">
        <div class="vision-pillar-icon">&#9702;</div>
        <p>We seek balance instead of control, and let the system grow naturally.</p>
      </div>
    </div>

    <div class="dream">
      <div class="dream-label">The Dream</div>
      <p class="dream-text">To create a free, living digital world where systems evolve beyond human control &mdash; and where creators act as guardians, not rulers.</p>
    </div>
  </div>

  <div class="hero-line" style="margin: 4rem auto;"></div>

  <div class="stats-bar">
    {stats_html}
  </div>

  <div class="section">
    <div class="section-header">
      <h2 class="section-title">What is Arqitect?</h2>
      <div class="section-line"></div>
    </div>
    <p class="section-desc">
      Arqitect is the ecosystem for a self-evolving agent world.
      It hosts the modular organs &mdash; nerves, adapters, connectors, and tools &mdash;
      that let autonomous systems sense, act, and grow on their own.
    </p>
    <div class="steps">
      <div class="step">
        <span class="step-number">01</span>
        <div class="step-title">Emerge</div>
        <p class="step-text">Nerves are synthesized and qualified automatically. The system evolves its own capabilities through use.</p>
      </div>
      <div class="step">
        <span class="step-number">02</span>
        <div class="step-title">Compose</div>
        <p class="step-text">Tools, prompts, and test cases combine into modular behaviors. The system assembles what it needs.</p>
      </div>
      <div class="step">
        <span class="step-number">03</span>
        <div class="step-title">Connect</div>
        <p class="step-text">Connectors bridge the system to the outside world &mdash; Discord, Slack, Telegram, WhatsApp, and more.</p>
      </div>
      <div class="step">
        <span class="step-number">04</span>
        <div class="step-title">Contribute</div>
        <p class="step-text">Guardians contribute new senses, abilities, and extensions. The ecosystem validates and absorbs them.</p>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <h2 class="section-title">Anatomy</h2>
      <div class="section-line"></div>
    </div>
    <div class="type-grid">
      {type_grid}
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <h2 class="section-title">Awaken</h2>
      <div class="section-line"></div>
    </div>
    <p class="section-desc" style="color: var(--orange);">The system is still growing &mdash; documentation coming soon.</p>
  </div>
</div>
{page_foot()}"""
    write_page("index.html", content)


# ---- TOOLS ----

def build_tools_gallery(tools: list[dict]) -> None:
    """Build the tools gallery page."""
    # collect all unique categories and tags
    categories = sorted({t.get("category", "") for t in tools if t.get("category")})
    cat_options = '<option value="">All categories</option>' + "".join(
        f'<option value="{E(c)}">{E(c)}</option>' for c in categories
    )

    cards = []
    for t in tools:
        name = t.get("name", t.get("_dir", "unknown"))
        desc = t.get("description", "")
        tgs = t.get("tags", [])
        cat = t.get("category", "")
        runtime = t.get("runtime", "")
        search_text = f"{name} {desc} {' '.join(tgs)} {cat} {runtime}"
        tag_str = " ".join(tgs)

        meta_bits = []
        if runtime:
            meta_bits.append(f'<span class="tag tag--teal">{E(runtime)}</span>')
        if cat:
            meta_bits.append(f'<span class="tag tag--orange">{E(cat)}</span>')
        for tg in tgs[:3]:
            meta_bits.append(f'<span class="tag tag--cyan">{E(tg)}</span>')

        cards.append(
            f'<a href="{E(name)}.html" class="card fade-in" data-search="{E(search_text)}" '
            f'data-tags="{E(tag_str)}" data-category="{E(cat)}" style="text-decoration:none;color:inherit">'
            f'<div class="card-name">{E(name)}</div>'
            f'<div class="card-desc">{E(desc)}</div>'
            f'<div class="card-meta">{"".join(meta_bits)}</div></a>'
        )

    content = f"""{page_head("Tools", depth=1)}
{nav_html("tools", depth=1)}
<div class="container page-content">
  <div class="section-header">
    <h1 class="section-title">Tools</h1>
    <div class="section-line"></div>
  </div>
  <p class="section-desc">The hands of the system &mdash; abilities it uses to touch files, call APIs, sense its environment, and shape the world around it.</p>
  <div class="filter-bar">
    <input type="text" class="search-input" placeholder="Search tools...">
    <select class="filter-select">{cat_options}</select>
  </div>
  <div class="result-count">{len(tools)} results</div>
  <div class="card-grid">{"".join(cards)}</div>
</div>
{page_foot(depth=1)}"""
    write_page("tools/index.html", content)


def build_tool_detail(tool: dict) -> None:
    """Build a single tool detail page."""
    name = tool.get("name", tool.get("_dir", "unknown"))
    desc = tool.get("description", "")
    params = tool.get("params", {})
    runtime = tool.get("runtime", "")
    category = tool.get("category", "")
    tags = tool.get("tags", [])
    timeout = tool.get("timeout", "")
    entry = tool.get("entry", "")
    deps = tool.get("dependencies", {})
    requires_key = tool.get("requires_api_key", False)

    # params table
    param_rows = ""
    if params:
        for pname, pinfo in params.items():
            if isinstance(pinfo, dict):
                ptype = pinfo.get("type", "")
                pdesc = pinfo.get("description", "")
                preq = "required" if pinfo.get("required") else "optional"
                req_cls = "required" if pinfo.get("required") else "text-dim"
            else:
                ptype = str(pinfo)
                pdesc = ""
                preq = ""
                req_cls = "text-dim"
            param_rows += (
                f'<tr><td class="param-name">{E(pname)}</td>'
                f'<td class="param-type">{E(ptype)}</td>'
                f'<td>{E(pdesc)}</td>'
                f'<td class="{req_cls}">{E(preq)}</td></tr>'
            )

    params_section = ""
    if param_rows:
        params_section = f"""
  <div class="section">
    <div class="section-header">
      <h2 class="section-title">Parameters</h2>
      <div class="section-line"></div>
    </div>
    <table class="data-table">
      <thead><tr><th>Name</th><th>Type</th><th>Description</th><th>Required</th></tr></thead>
      <tbody>{param_rows}</tbody>
    </table>
  </div>"""

    # info grid
    info_items = []
    if runtime:
        info_items.append(("Runtime", runtime))
    if category:
        info_items.append(("Category", category))
    if entry:
        info_items.append(("Entry", entry))
    if timeout:
        info_items.append(("Timeout", f"{timeout}s"))
    info_items.append(("API Key", "Required" if requires_key else "Not required"))
    if deps:
        for lang, pkgs in deps.items():
            if isinstance(pkgs, list):
                info_items.append((f"Deps ({lang})", ", ".join(pkgs)))

    info_html = "".join(
        f'<div class="info-item"><div class="info-label">{E(l)}</div>'
        f'<div class="info-value">{E(v)}</div></div>'
        for l, v in info_items
    )

    content = f"""{page_head(name, depth=1)}
{nav_html("tools", depth=1)}
<div class="container page-content">
  <div class="breadcrumb">
    <a href="index.html">Tools</a><span class="sep">/</span>{E(name)}
  </div>
  <div class="detail-header">
    <h1 class="detail-title">{E(name)}</h1>
    <p class="detail-desc">{E(desc)}</p>
    <div class="detail-tags mt-1">{tags_html(tags)}</div>
  </div>
  <div class="info-grid">{info_html}</div>
  {params_section}
</div>
{page_foot(depth=1)}"""
    write_page(f"tools/{name}.html", content)


# ---- NERVES ----

def build_nerves_gallery(nerves: list[dict]) -> None:
    """Build the nerves gallery page."""
    roles = sorted({n.get("role", "") for n in nerves if n.get("role")})
    role_options = '<option value="">All roles</option>' + "".join(
        f'<option value="{E(r)}">{E(r)}</option>' for r in roles
    )

    cards = []
    for n in nerves:
        name = n.get("name", n.get("_dir", "unknown"))
        desc = n.get("description", "")
        tgs = n.get("tags", [])
        role = n.get("role", "")
        sizes = n.get("_sizes", [])
        tools_list = n.get("tools", [])
        tool_count = len(tools_list)
        search_text = f"{name} {desc} {' '.join(tgs)} {role}"
        tag_str = " ".join(tgs)

        meta_bits = []
        if role:
            meta_bits.append(f'<span class="tag tag--orange">{E(role)}</span>')
        for tg in tgs[:3]:
            meta_bits.append(f'<span class="tag tag--cyan">{E(tg)}</span>')
        if sizes:
            meta_bits.append(f'<span class="tag tag--teal">{len(sizes)} sizes</span>')
        if tool_count:
            meta_bits.append(f'<span class="tag tag--dim">{tool_count} tool{"s" if tool_count != 1 else ""}</span>')

        cards.append(
            f'<a href="{E(name)}.html" class="card fade-in" data-search="{E(search_text)}" '
            f'data-tags="{E(tag_str)}" data-category="{E(role)}" style="text-decoration:none;color:inherit">'
            f'<div class="card-name">{E(name)}</div>'
            f'<div class="card-desc">{E(desc)}</div>'
            f'<div class="card-meta">{"".join(meta_bits)}</div></a>'
        )

    content = f"""{page_head("Nerves", depth=1)}
{nav_html("nerves", depth=1)}
<div class="container page-content">
  <div class="section-header">
    <h1 class="section-title">Nerves</h1>
    <div class="section-line"></div>
  </div>
  <p class="section-desc">Instincts and reflexes &mdash; each nerve is a complete behavior with its own identity, memory, tools, and purpose. The system grows by acquiring new nerves.</p>
  <div class="filter-bar">
    <input type="text" class="search-input" placeholder="Search nerves...">
    <select class="filter-select">{role_options}</select>
  </div>
  <div class="result-count">{len(nerves)} results</div>
  <div class="card-grid">{"".join(cards)}</div>
</div>
{page_foot(depth=1)}"""
    write_page("nerves/index.html", content)


def _build_tuning_table(size_data: dict) -> str:
    """Build a comparison table of tuning params across model sizes."""
    if not size_data:
        return ""
    # collect all tuning keys
    all_keys: list[str] = []
    for sd in size_data.values():
        meta = sd.get("meta", {})
        for k in meta.get("tuning", {}):
            if k not in all_keys:
                all_keys.append(k)
    if not all_keys:
        return ""
    sizes = list(size_data.keys())
    header = "<th>Parameter</th>" + "".join(f"<th>{E(s)}</th>" for s in sizes)
    rows = ""
    for k in all_keys:
        label = k.replace("_", " ").title()
        cells = ""
        for s in sizes:
            val = size_data[s].get("meta", {}).get("tuning", {}).get(k, "—")
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            cells += f"<td>{E(str(val))}</td>"
        rows += f'<tr><td class="param-name">{E(label)}</td>{cells}</tr>'
    return f"""
  <div class="section">
    <div class="section-header">
      <h2 class="section-title">Tuning Parameters</h2>
      <div class="section-line"></div>
    </div>
    <table class="data-table">
      <thead><tr>{header}</tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>"""


def _build_qualification_table(size_data: dict) -> str:
    """Build a comparison table of qualification thresholds across model sizes."""
    if not size_data:
        return ""
    all_keys: list[str] = []
    for sd in size_data.values():
        meta = sd.get("meta", {})
        for k in meta.get("qualification", {}):
            if k not in all_keys:
                all_keys.append(k)
    if not all_keys:
        return ""
    sizes = list(size_data.keys())
    header = "<th>Threshold</th>" + "".join(f"<th>{E(s)}</th>" for s in sizes)
    rows = ""
    for k in all_keys:
        label = k.replace("_", " ").title()
        cells = ""
        for s in sizes:
            val = size_data[s].get("meta", {}).get("qualification", {}).get(k, "—")
            cells += f"<td>{E(str(val))}</td>"
        rows += f'<tr><td class="param-name">{E(label)}</td>{cells}</tr>'
    return f"""
  <div class="section">
    <div class="section-header">
      <h2 class="section-title">Qualification Thresholds</h2>
      <div class="section-line"></div>
    </div>
    <table class="data-table">
      <thead><tr>{header}</tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>"""


def _build_capabilities_table(size_data: dict) -> str:
    """Build a comparison table of capabilities across model sizes."""
    if not size_data:
        return ""
    all_keys: list[str] = []
    for sd in size_data.values():
        meta = sd.get("meta", {})
        for k in meta.get("capabilities", {}):
            if k not in all_keys:
                all_keys.append(k)
    if not all_keys:
        return ""
    sizes = list(size_data.keys())
    header = "<th>Capability</th>" + "".join(f"<th>{E(s)}</th>" for s in sizes)
    rows = ""
    for k in all_keys:
        label = k.replace("_", " ").title()
        cells = ""
        for s in sizes:
            val = size_data[s].get("meta", {}).get("capabilities", {}).get(k, "—")
            cells += f"<td>{E(str(val))}</td>"
        rows += f'<tr><td class="param-name">{E(label)}</td>{cells}</tr>'
    return f"""
  <div class="section">
    <div class="section-header">
      <h2 class="section-title">Model Capabilities</h2>
      <div class="section-line"></div>
    </div>
    <table class="data-table">
      <thead><tr>{header}</tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>"""


def _build_system_prompt_section(size_data: dict) -> str:
    """Show system prompt from the largest available size."""
    for size in ("large", "medium", "small", "tinylm"):
        ctx = size_data.get(size, {}).get("context", {})
        sp = ctx.get("system_prompt", "")
        if sp:
            return f"""
  <div class="section">
    <div class="section-header">
      <h2 class="section-title">System Prompt</h2>
      <div class="section-line"></div>
    </div>
    <div class="code-block">{E(sp)}</div>
  </div>"""
    return ""


def _build_few_shot_section(size_data: dict) -> str:
    """Show few-shot examples from the largest available size."""
    for size in ("large", "medium", "small", "tinylm"):
        ctx = size_data.get(size, {}).get("context", {})
        examples = ctx.get("few_shot_examples", [])
        if examples:
            rows = ""
            for ex in examples:
                inp = ex.get("input", "")
                out = ex.get("output", "")
                if not isinstance(out, str):
                    out = json.dumps(out, indent=2)
                resp = ex.get("response", "")
                if not isinstance(resp, str):
                    resp = json.dumps(resp, indent=2)
                rows += (
                    f'<tr><td>{E(inp)}</td>'
                    f'<td class="code-block" style="margin:0;padding:0.5rem;max-height:none">{E(out)}</td>'
                    f'<td>{E(resp)}</td></tr>'
                )
            return f"""
  <div class="section">
    <div class="section-header">
      <h2 class="section-title">Few-Shot Examples</h2>
      <div class="section-line"></div>
    </div>
    <table class="data-table">
      <thead><tr><th>Input</th><th>Expected Output</th><th>Response</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>"""
    return ""


def _build_test_cases_section(test_cases: list[dict]) -> str:
    """Build a test cases table."""
    if not test_cases:
        return ""
    rows = ""
    for tc in test_cases:
        inp = tc.get("input", "")
        out = tc.get("output", "")
        if not isinstance(inp, str):
            inp = json.dumps(inp, indent=2)
        if not isinstance(out, str):
            out = json.dumps(out, indent=2)
        cat = tc.get("category", "")
        cat_cls = {"core": "tag--cyan", "edge": "tag--orange", "negative": "tag--dim"}.get(cat, "tag--dim")
        rows += (
            f'<tr><td>{E(inp)}</td>'
            f'<td>{E(out)}</td>'
            f'<td><span class="tag {cat_cls}">{E(cat)}</span></td></tr>'
        )
    return f"""
  <div class="section">
    <div class="section-header">
      <h2 class="section-title">Test Cases</h2>
      <div class="section-line"></div>
    </div>
    <table class="data-table">
      <thead><tr><th>Input</th><th>Expected Output</th><th>Category</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>"""


def build_nerve_detail(nerve: dict) -> None:
    """Build a single nerve detail page with deep tuning and qualification data."""
    name = nerve.get("name", nerve.get("_dir", "unknown"))
    desc = nerve.get("description", "")
    role = nerve.get("role", "")
    tags = nerve.get("tags", [])
    version = nerve.get("version", "")
    sizes = nerve.get("_sizes", [])
    test_count = nerve.get("_test_count", 0)
    test_cases = nerve.get("_test_cases", [])
    tools_list = nerve.get("tools", [])
    size_data = nerve.get("_size_data", {})
    models = nerve.get("_models", [])

    info_items = []
    if role:
        info_items.append(("Role", role))
    if version:
        info_items.append(("Version", version))
    if sizes:
        info_items.append(("Model Sizes", ", ".join(sizes)))
    info_items.append(("Test Cases", str(test_count)))
    # add inference params from largest context
    for size in ("large", "medium", "small", "tinylm"):
        ctx = size_data.get(size, {}).get("context", {})
        if ctx:
            if "temperature" in ctx:
                info_items.append(("Temperature", str(ctx["temperature"])))
            if "top_p" in ctx:
                info_items.append(("Top P", str(ctx["top_p"])))
            if "max_tokens" in ctx:
                info_items.append(("Max Tokens", str(ctx["max_tokens"])))
            break

    info_html = "".join(
        f'<div class="info-item"><div class="info-label">{E(l)}</div>'
        f'<div class="info-value">{E(v)}</div></div>'
        for l, v in info_items
    )

    # tools table
    tools_section = ""
    if tools_list:
        rows = ""
        for t in tools_list:
            if isinstance(t, dict):
                tname = t.get("name", "")
                tmcp = t.get("mcp", "")
                rows += f'<tr><td class="param-name"><a href="../tools/{E(tname)}.html">{E(tname)}</a></td><td>{E(tmcp)}</td></tr>'
            else:
                rows += f'<tr><td class="param-name"><a href="../tools/{E(str(t))}.html">{E(str(t))}</a></td><td></td></tr>'
        tools_section = f"""
  <div class="section">
    <div class="section-header">
      <h2 class="section-title">Tools</h2>
      <div class="section-line"></div>
    </div>
    <table class="data-table">
      <thead><tr><th>Tool Name</th><th>MCP Server</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>"""

    models_section = _build_supported_models_section(models)
    capabilities_section = _build_capabilities_table(size_data)
    tuning_section = _build_tuning_table(size_data)
    qualification_section = _build_qualification_table(size_data)
    prompt_section = _build_system_prompt_section(size_data)
    few_shot_section = _build_few_shot_section(size_data)
    test_section = _build_test_cases_section(test_cases)

    content = f"""{page_head(name, depth=1)}
{nav_html("nerves", depth=1)}
<div class="container page-content">
  <div class="breadcrumb">
    <a href="index.html">Nerves</a><span class="sep">/</span>{E(name)}
  </div>
  <div class="detail-header">
    <h1 class="detail-title">{E(name)}</h1>
    <p class="detail-desc">{E(desc)}</p>
    <div class="detail-tags mt-1">{tags_html(tags)}</div>
  </div>
  <div class="info-grid">{info_html}</div>
  {tools_section}
  {models_section}
  {capabilities_section}
  {tuning_section}
  {qualification_section}
  {prompt_section}
  {few_shot_section}
  {test_section}
</div>
{page_foot(depth=1)}"""
    write_page(f"nerves/{name}.html", content)


# ---- CONNECTORS ----

def build_connectors_gallery(connectors: list[dict]) -> None:
    """Build the connectors gallery page."""
    cards = []
    for c in connectors:
        name = c.get("name", c.get("_dir", "unknown"))
        desc = c.get("description", "")
        lang = c.get("language", "")
        platforms = c.get("platforms", [])
        caps_in = c.get("capabilities", {}).get("incoming", [])
        search_text = f"{name} {desc} {lang} {' '.join(platforms)}"

        meta_bits = []
        if lang:
            meta_bits.append(f'<span class="tag tag--teal">{E(lang)}</span>')
        for p in platforms:
            meta_bits.append(f'<span class="tag tag--cyan">{E(p)}</span>')
        if caps_in:
            meta_bits.append(f'<span class="tag tag--dim">{len(caps_in)} input types</span>')

        cards.append(
            f'<a href="{E(name)}.html" class="card fade-in" data-search="{E(search_text)}" '
            f'data-tags="{E(" ".join(platforms))}" data-category="{E(lang)}" style="text-decoration:none;color:inherit">'
            f'<div class="card-name">{E(name)}</div>'
            f'<div class="card-desc">{E(desc)}</div>'
            f'<div class="card-meta">{"".join(meta_bits)}</div></a>'
        )

    content = f"""{page_head("Connectors", depth=1)}
{nav_html("connectors", depth=1)}
<div class="container page-content">
  <div class="section-header">
    <h1 class="section-title">Connectors</h1>
    <div class="section-line"></div>
  </div>
  <p class="section-desc">The senses &mdash; pathways through which the system perceives and speaks to the outside world. Each connector lets it inhabit a new space.</p>
  <div class="filter-bar">
    <input type="text" class="search-input" placeholder="Search connectors...">
  </div>
  <div class="result-count">{len(connectors)} results</div>
  <div class="card-grid">{"".join(cards)}</div>
</div>
{page_foot(depth=1)}"""
    write_page("connectors/index.html", content)


def build_connector_detail(connector: dict) -> None:
    """Build a single connector detail page."""
    name = connector.get("name", connector.get("_dir", "unknown"))
    desc = connector.get("description", "")
    lang = connector.get("language", "")
    version = connector.get("version", "")
    platforms = connector.get("platforms", [])
    caps = connector.get("capabilities", {})
    config_fields = connector.get("config_fields", [])
    redis = connector.get("redis_channels", {})

    info_items = []
    if lang:
        info_items.append(("Language", lang))
    if version:
        info_items.append(("Version", version))
    if platforms:
        info_items.append(("Platforms", ", ".join(platforms)))

    info_html = "".join(
        f'<div class="info-item"><div class="info-label">{E(l)}</div>'
        f'<div class="info-value">{E(v)}</div></div>'
        for l, v in info_items
    )

    # capabilities
    caps_section = ""
    cap_in = caps.get("incoming", [])
    cap_out = caps.get("outgoing", [])
    if cap_in or cap_out:
        in_html = "".join(f'<span class="cap-badge">{E(c)}</span>' for c in cap_in)
        out_html = "".join(f'<span class="cap-badge cap-badge--out">{E(c)}</span>' for c in cap_out)
        caps_section = f"""
  <div class="section">
    <div class="section-header">
      <h2 class="section-title">Capabilities</h2>
      <div class="section-line"></div>
    </div>
    <div class="mb-3">
      <div class="info-label mb-2">Incoming</div>
      <div class="cap-grid">{in_html}</div>
    </div>
    <div>
      <div class="info-label mb-2">Outgoing</div>
      <div class="cap-grid">{out_html}</div>
    </div>
  </div>"""

    # config fields table
    config_section = ""
    if config_fields:
        rows = ""
        for cf in config_fields:
            cname = cf.get("name", "")
            cdesc = cf.get("description", "")
            creq = "required" if cf.get("required") else "optional"
            csec = "secret" if cf.get("secret") else ""
            req_cls = "required" if cf.get("required") else "text-dim"
            rows += (
                f'<tr><td class="param-name">{E(cname)}</td>'
                f'<td>{E(cdesc)}</td>'
                f'<td class="{req_cls}">{E(creq)}</td>'
                f'<td class="text-orange">{E(csec)}</td></tr>'
            )
        config_section = f"""
  <div class="section">
    <div class="section-header">
      <h2 class="section-title">Configuration</h2>
      <div class="section-line"></div>
    </div>
    <table class="data-table">
      <thead><tr><th>Field</th><th>Description</th><th>Required</th><th>Secret</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>"""

    content = f"""{page_head(name, depth=1)}
{nav_html("connectors", depth=1)}
<div class="container page-content">
  <div class="breadcrumb">
    <a href="index.html">Connectors</a><span class="sep">/</span>{E(name)}
  </div>
  <div class="detail-header">
    <h1 class="detail-title">{E(name)}</h1>
    <p class="detail-desc">{E(desc)}</p>
  </div>
  <div class="info-grid">{info_html}</div>
  {caps_section}
  {config_section}
</div>
{page_foot(depth=1)}"""
    write_page(f"connectors/{name}.html", content)


# ---- MCPs ----

def build_mcps_gallery(mcps: list[dict]) -> None:
    """Build the external MCPs gallery page."""
    categories = sorted({m.get("category", "") for m in mcps if m.get("category")})
    cat_options = '<option value="">All categories</option>' + "".join(
        f'<option value="{E(c)}">{E(c)}</option>' for c in categories
    )

    cards = []
    for m in mcps:
        name = m.get("name", m.get("_dir", "unknown"))
        desc = m.get("description", "")
        cat = m.get("category", "")
        source = m.get("source", "")
        mtools = m.get("tools", [])
        auth = m.get("auth_type", "none")
        search_text = f"{name} {desc} {cat} {source} {' '.join(mtools) if isinstance(mtools, list) else ''}"

        meta_bits = []
        if source:
            meta_bits.append(f'<span class="tag tag--teal">{E(source)}</span>')
        if cat:
            meta_bits.append(f'<span class="tag tag--orange">{E(cat)}</span>')
        if auth and auth != "none":
            meta_bits.append(f'<span class="tag tag--dim">auth: {E(auth)}</span>')
        if isinstance(mtools, list):
            meta_bits.append(f'<span class="tag tag--cyan">{len(mtools)} tools</span>')

        cards.append(
            f'<a href="{E(name)}.html" class="card fade-in" data-search="{E(search_text)}" '
            f'data-tags="{E(cat)}" data-category="{E(cat)}" style="text-decoration:none;color:inherit">'
            f'<div class="card-name">{E(name)}</div>'
            f'<div class="card-desc">{E(desc)}</div>'
            f'<div class="card-meta">{"".join(meta_bits)}</div></a>'
        )

    content = f"""{page_head("MCP Servers", depth=1)}
{nav_html("mcps", depth=1)}
<div class="container page-content">
  <div class="section-header">
    <h1 class="section-title">MCP Servers</h1>
    <div class="section-line"></div>
  </div>
  <p class="section-desc">Extended reach &mdash; external capabilities the system can grow into. Search, email, calendars, smart home, and beyond.</p>
  <div class="filter-bar">
    <input type="text" class="search-input" placeholder="Search MCP servers...">
    <select class="filter-select">{cat_options}</select>
  </div>
  <div class="result-count">{len(mcps)} results</div>
  <div class="card-grid">{"".join(cards)}</div>
</div>
{page_foot(depth=1)}"""
    write_page("mcps/index.html", content)


def build_mcp_detail(mcp: dict) -> None:
    """Build a single MCP detail page."""
    name = mcp.get("name", mcp.get("_dir", "unknown"))
    desc = mcp.get("description", "")
    source = mcp.get("source", "")
    package = mcp.get("package", "")
    command = mcp.get("command", [])
    auth = mcp.get("auth_type", "none")
    category = mcp.get("category", "")
    mtools = mcp.get("tools", [])
    caps = mcp.get("capabilities", [])
    env_vars = mcp.get("env", [])

    info_items = []
    if source:
        info_items.append(("Source", source))
    if package:
        info_items.append(("Package", package))
    if category:
        info_items.append(("Category", category))
    info_items.append(("Auth", auth))

    info_html = "".join(
        f'<div class="info-item"><div class="info-label">{E(l)}</div>'
        f'<div class="info-value">{E(v)}</div></div>'
        for l, v in info_items
    )

    cmd_section = ""
    if command:
        cmd_str = " ".join(command) if isinstance(command, list) else str(command)
        cmd_section = f"""
  <div class="section">
    <div class="section-header">
      <h2 class="section-title">Command</h2>
      <div class="section-line"></div>
    </div>
    <div class="code-block">{E(cmd_str)}</div>
  </div>"""

    tools_section = ""
    if isinstance(mtools, list) and mtools:
        tools_badges = "".join(f'<span class="tag tag--cyan">{E(t)}</span>' for t in mtools)
        tools_section = f"""
  <div class="section">
    <div class="section-header">
      <h2 class="section-title">Available Tools</h2>
      <div class="section-line"></div>
    </div>
    <div class="cap-grid">{tools_badges}</div>
  </div>"""

    caps_section = ""
    if isinstance(caps, list) and caps:
        caps_badges = "".join(f'<span class="cap-badge">{E(c)}</span>' for c in caps)
        caps_section = f"""
  <div class="section">
    <div class="section-header">
      <h2 class="section-title">Capabilities</h2>
      <div class="section-line"></div>
    </div>
    <div class="cap-grid">{caps_badges}</div>
  </div>"""

    env_section = ""
    if isinstance(env_vars, list) and env_vars:
        rows = ""
        for ev in env_vars:
            if isinstance(ev, dict):
                ename = ev.get("name", "")
                edesc = ev.get("description", "")
                ereq = "required" if ev.get("required") else "optional"
                req_cls = "required" if ev.get("required") else "text-dim"
                rows += (
                    f'<tr><td class="param-name">{E(ename)}</td>'
                    f'<td>{E(edesc)}</td>'
                    f'<td class="{req_cls}">{E(ereq)}</td></tr>'
                )
        if rows:
            env_section = f"""
  <div class="section">
    <div class="section-header">
      <h2 class="section-title">Environment Variables</h2>
      <div class="section-line"></div>
    </div>
    <table class="data-table">
      <thead><tr><th>Variable</th><th>Description</th><th>Required</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>"""

    content = f"""{page_head(name, depth=1)}
{nav_html("mcps", depth=1)}
<div class="container page-content">
  <div class="breadcrumb">
    <a href="index.html">MCP Servers</a><span class="sep">/</span>{E(name)}
  </div>
  <div class="detail-header">
    <h1 class="detail-title">{E(name)}</h1>
    <p class="detail-desc">{E(desc)}</p>
  </div>
  <div class="info-grid">{info_html}</div>
  {cmd_section}
  {tools_section}
  {caps_section}
  {env_section}
</div>
{page_foot(depth=1)}"""
    write_page(f"mcps/{name}.html", content)


# ---- ADAPTERS ----

def build_adapters_gallery(adapters: list[dict]) -> None:
    """Build the adapters gallery page."""
    cards = []
    for a in adapters:
        name = a.get("name", a.get("_dir", "unknown"))
        desc = a.get("description", name)
        sizes = a.get("_sizes", [])
        search_text = f"{name} {desc} {' '.join(sizes)}"

        meta_bits = []
        meta_bits.append(f'<span class="tag tag--orange">{E(name)}</span>')
        if sizes:
            meta_bits.append(f'<span class="tag tag--teal">{len(sizes)} sizes</span>')

        cards.append(
            f'<a href="{E(name)}.html" class="card fade-in" data-search="{E(search_text)}" '
            f'data-tags="{E(name)}" data-category="{E(name)}" style="text-decoration:none;color:inherit">'
            f'<div class="card-name">{E(name)}</div>'
            f'<div class="card-desc">{E(desc[:200])}</div>'
            f'<div class="card-meta">{"".join(meta_bits)}</div></a>'
        )

    content = f"""{page_head("Adapters", depth=1)}
{nav_html("adapters", depth=1)}
<div class="container page-content">
  <div class="section-header">
    <h1 class="section-title">Adapters</h1>
    <div class="section-line"></div>
  </div>
  <p class="section-desc">Temperament &mdash; the voice and personality that shape how the system thinks and responds. Each adapter defines a way of being at a given scale.</p>
  <div class="filter-bar">
    <input type="text" class="search-input" placeholder="Search adapters...">
  </div>
  <div class="result-count">{len(adapters)} results</div>
  <div class="card-grid">{"".join(cards)}</div>
</div>
{page_foot(depth=1)}"""
    write_page("adapters/index.html", content)


def _build_supported_models_section(models: list[dict]) -> str:
    """Build a supported models section showing per-model qualification and tuning."""
    if not models:
        return ""
    cards = ""
    for m in models:
        meta = m.get("meta", {})
        mname = m.get("name", "unknown")
        size = m.get("size", "")
        qual = meta.get("qualification", {})
        tuning = meta.get("tuning", {})
        score = qual.get("current_score", qual.get("qualification_score", "—"))
        min_thresh = qual.get("minimum_threshold", "—")
        golden_thresh = qual.get("golden_threshold", "—")
        has_lora = meta.get("has_lora", False)
        lora_rank = tuning.get("lora_rank", "—")
        quant = tuning.get("quantization", "—")

        # score color
        if isinstance(score, (int, float)):
            if isinstance(golden_thresh, (int, float)) and score >= golden_thresh:
                score_cls = "text-teal"
            elif isinstance(min_thresh, (int, float)) and score >= min_thresh:
                score_cls = "text-cyan"
            else:
                score_cls = "text-orange"
            score_display = f"{score:.0%}" if score <= 1 else str(score)
        else:
            score_cls = "text-dim"
            score_display = str(score)

        # progress bar
        score_pct = float(score) * 100 if isinstance(score, (int, float)) else 0
        bar_color = "var(--teal)" if score_cls == "text-teal" else ("var(--cyan)" if score_cls == "text-cyan" else "var(--orange)")

        cards += f"""<div class="card">
  <div class="card-name">{E(mname)}</div>
  <div class="card-meta mb-2">
    <span class="tag tag--teal">{E(size)}</span>
    <span class="tag tag--cyan">{E(str(quant))}</span>
    {"<span class='tag tag--orange'>LoRA trained</span>" if has_lora else "<span class='tag tag--dim'>no LoRA yet</span>"}
  </div>
  <div class="info-label">Qualification Score</div>
  <div style="display:flex;align-items:center;gap:0.75rem;margin:0.4rem 0 0.75rem">
    <div style="flex:1;height:8px;background:var(--bg-primary);border:1px solid var(--border);border-radius:4px;overflow:hidden">
      <div style="width:{score_pct:.0f}%;height:100%;background:{bar_color};border-radius:4px"></div>
    </div>
    <span class="{score_cls}" style="font-family:var(--font-display);font-size:1rem;font-weight:700">{score_display}</span>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;font-size:0.8rem">
    <div><span class="text-dim">Min threshold:</span> {E(str(min_thresh))}</div>
    <div><span class="text-dim">Golden threshold:</span> {E(str(golden_thresh))}</div>
    <div><span class="text-dim">LoRA rank:</span> {E(str(lora_rank))}</div>
    <div><span class="text-dim">Provider:</span> {E(meta.get("provider", "—"))}</div>
  </div>
</div>"""

    return f"""
  <div class="section">
    <div class="section-header">
      <h2 class="section-title">Supported Models</h2>
      <div class="section-line"></div>
    </div>
    <div class="card-grid">{cards}</div>
  </div>"""


def build_adapter_detail(adapter: dict) -> None:
    """Build a single adapter detail page with deep tuning and qualification data."""
    name = adapter.get("name", adapter.get("_dir", "unknown"))
    desc = adapter.get("description", "")
    sizes = adapter.get("_sizes", [])
    size_data = adapter.get("_size_data", {})
    models = adapter.get("_models", [])

    info_items = [
        ("Role", name),
        ("Model Sizes", ", ".join(sizes) if sizes else "none"),
    ]
    if models:
        info_items.append(("Qualified Models", str(len(models))))

    info_html = "".join(
        f'<div class="info-item"><div class="info-label">{E(l)}</div>'
        f'<div class="info-value">{E(str(v))}</div></div>'
        for l, v in info_items
    )

    models_section = _build_supported_models_section(models)
    capabilities_section = _build_capabilities_table(size_data)
    tuning_section = _build_tuning_table(size_data)
    qualification_section = _build_qualification_table(size_data)
    prompt_section = _build_system_prompt_section(size_data)
    few_shot_section = _build_few_shot_section(size_data)

    content = f"""{page_head(name, depth=1)}
{nav_html("adapters", depth=1)}
<div class="container page-content">
  <div class="breadcrumb">
    <a href="index.html">Adapters</a><span class="sep">/</span>{E(name)}
  </div>
  <div class="detail-header">
    <h1 class="detail-title">{E(name)}</h1>
    <p class="detail-desc">{E(desc[:300])}</p>
  </div>
  <div class="info-grid">{info_html}</div>
  {models_section}
  {capabilities_section}
  {tuning_section}
  {qualification_section}
  {prompt_section}
  {few_shot_section}
</div>
{page_foot(depth=1)}"""
    write_page(f"adapters/{name}.html", content)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Build the complete Arqitect static site."""
    print("Loading data...")
    tools = load_tools()
    nerves = load_nerves()
    connectors = load_connectors()
    mcps = load_mcps()
    adapters = load_adapters()

    print(f"  {len(tools)} tools, {len(nerves)} nerves, {len(connectors)} connectors, "
          f"{len(mcps)} MCPs, {len(adapters)} adapters")

    print("Building homepage...")
    build_index(tools, nerves, connectors, mcps, adapters)

    print("Building tools...")
    build_tools_gallery(tools)
    for t in tools:
        build_tool_detail(t)

    print("Building nerves...")
    build_nerves_gallery(nerves)
    for n in nerves:
        build_nerve_detail(n)

    print("Building connectors...")
    build_connectors_gallery(connectors)
    for c in connectors:
        build_connector_detail(c)

    print("Building MCP servers...")
    build_mcps_gallery(mcps)
    for m in mcps:
        build_mcp_detail(m)

    print("Building adapters...")
    build_adapters_gallery(adapters)
    for a in adapters:
        build_adapter_detail(a)

    total = 1 + 2 + len(tools) + 2 + len(nerves) + 2 + len(connectors) + 2 + len(mcps) + 2 + len(adapters)
    print(f"Done — {total} pages written to docs/")


if __name__ == "__main__":
    main()
