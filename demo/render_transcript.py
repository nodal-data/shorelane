#!/usr/bin/env python3
"""
render_transcript.py — Nodal Context Builder Conversation renderer.

Turns a Claude Code `.jsonl` transcript into a clean, demo-ready HTML page that
reads like a conversation between a **Human Analyst** and the **AI**. Tool calls,
internal reasoning, and system plumbing are stripped out so the focus stays on the
dialogue.

Usage
-----
    python render_transcript.py <path>
    python render_transcript.py <path-to.jsonl>
    python render_transcript.py <directory-of-jsonl>
    python render_transcript.py                      # uses the bundled examples dir

Options
-------
    --out DIR          Where to write the HTML (default: ./output next to this file)
    --show-thinking    Include the AI's internal "thinking" blocks (off by default)
    --open             Open the rendered file in your browser when done

Output files are timestamped (and de-duplicated with a counter), so re-running
never overwrites a previous render.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import os
import re
import sys
import webbrowser
from pathlib import Path
from typing import Iterable

# The folder where example transcripts live (referenced when no path is given).
# Point TRANSCRIPT_EXAMPLES_DIR at your Claude Code project transcript dir.
EXAMPLES_DIR = Path(os.environ.get("TRANSCRIPT_EXAMPLES_DIR", "examples"))

PAGE_TITLE = "Nodal Context Builder Conversation in Claude Code"


# --------------------------------------------------------------------------- #
# Parsing                                                                      #
# --------------------------------------------------------------------------- #

def _iter_records(path: Path) -> Iterable[dict]:
    """Yield decoded JSON objects from a .jsonl file, skipping bad lines."""
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _text_from_content(content) -> str:
    """Collapse a message `content` (str or list of blocks) into plain text,
    keeping only human/AI prose (text blocks). Tool calls/results are ignored."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(parts)
    return ""


def _thinking_from_content(content) -> str:
    if not isinstance(content, list):
        return ""
    parts = [
        b.get("thinking", "")
        for b in content
        if isinstance(b, dict) and b.get("type") == "thinking"
    ]
    return "\n".join(p for p in parts if p)


_SYSTEM_REMINDER_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)
_COMMAND_NAME_RE = re.compile(r"<command-name>(.*?)</command-name>", re.DOTALL)
_COMMAND_ARGS_RE = re.compile(r"<command-args>(.*?)</command-args>", re.DOTALL)
_ANY_TAG_BLOCK_RE = re.compile(
    r"<(command-message|local-command-stdout|command-args|command-name)>.*?</\1>",
    re.DOTALL,
)
_INTERRUPT_RE = re.compile(r"\[Request interrupted[^\]]*\]")


def _clean_human_text(raw: str) -> str | None:
    """Normalize a human turn. Returns cleaned text, or None if it carries no real
    conversational content (pure system noise / interrupts)."""
    text = raw

    # Slash commands like <command-name>/exit</command-name> → "/exit args"
    cmd = _COMMAND_NAME_RE.search(text)
    if cmd:
        name = cmd.group(1).strip()
        args_m = _COMMAND_ARGS_RE.search(text)
        args = (args_m.group(1).strip() if args_m else "")
        return (name + (" " + args if args else "")).strip() or None

    # Drop system reminders and any leftover command plumbing tags.
    text = _SYSTEM_REMINDER_RE.sub("", text)
    text = _ANY_TAG_BLOCK_RE.sub("", text)
    text = _INTERRUPT_RE.sub("", text)
    text = text.strip()

    return text or None


def parse_conversation(path: Path, show_thinking: bool = False) -> list[dict]:
    """Return an ordered list of conversation turns:
        {"role": "human"|"ai", "kind": "text"|"command"|"thinking", "text": str}
    Tool calls, tool results, and meta/system records are excluded.
    """
    turns: list[dict] = []

    for rec in _iter_records(path):
        rtype = rec.get("type")

        if rtype == "user":
            # Exclude tool results, skill-injected meta, and sidechain noise.
            if rec.get("isMeta") or "toolUseResult" in rec or rec.get("isSidechain"):
                continue
            content = rec.get("message", {}).get("content")
            raw = _text_from_content(content)
            if not raw.strip():
                continue
            is_command = "<command-name>" in raw
            cleaned = _clean_human_text(raw)
            if cleaned:
                turns.append(
                    {
                        "role": "human",
                        "kind": "command" if is_command else "text",
                        "text": cleaned,
                    }
                )

        elif rtype == "assistant":
            if rec.get("isSidechain"):
                continue
            content = rec.get("message", {}).get("content")
            if show_thinking:
                thought = _thinking_from_content(content)
                if thought.strip():
                    turns.append(
                        {"role": "ai", "kind": "thinking", "text": thought.strip()}
                    )
            text = _text_from_content(content).strip()
            if text:
                turns.append({"role": "ai", "kind": "text", "text": text})

    return _merge_adjacent(turns)


def _merge_adjacent(turns: list[dict]) -> list[dict]:
    """Merge consecutive same-speaker text bubbles so the AI reads as one voice
    even when its turn was split across tool calls."""
    merged: list[dict] = []
    for t in turns:
        if (
            merged
            and merged[-1]["role"] == t["role"]
            and merged[-1]["kind"] == "text"
            and t["kind"] == "text"
        ):
            merged[-1]["text"] += "\n\n" + t["text"]
        else:
            merged.append(dict(t))
    return merged


# --------------------------------------------------------------------------- #
# Minimal, self-contained Markdown → HTML                                      #
# --------------------------------------------------------------------------- #

def _inline_md(text: str) -> str:
    """Escape, then apply inline markdown: code, bold, italic, links."""
    out = html.escape(text)
    # inline code
    out = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", out)
    # bold (**x** or __x__)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", out)
    # italic (*x*)
    out = re.sub(r"(?<![\*\w])\*([^*\n]+)\*(?![\*\w])", r"<em>\1</em>", out)
    # links [text](url)
    out = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+|file://[^)\s]+)\)",
        r'<a href="\2" target="_blank" rel="noopener">\1</a>',
        out,
    )
    return out


def render_markdown(text: str) -> str:
    """Render a useful subset of Markdown to HTML without external deps:
    fenced code blocks, headers, bullet & numbered lists, blockquotes, paragraphs."""
    lines = text.split("\n")
    htmlparts: list[str] = []
    i = 0
    n = len(lines)

    list_stack: list[str] = []  # 'ul' / 'ol'

    def close_lists():
        while list_stack:
            htmlparts.append(f"</{list_stack.pop()}>")

    while i < n:
        line = lines[i]

        # fenced code block
        fence = re.match(r"^\s*```(\w*)\s*$", line)
        if fence:
            close_lists()
            lang = fence.group(1)
            buf = []
            i += 1
            while i < n and not re.match(r"^\s*```\s*$", lines[i]):
                buf.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            code = html.escape("\n".join(buf))
            cls = f' class="lang-{lang}"' if lang else ""
            htmlparts.append(f"<pre><code{cls}>{code}</code></pre>")
            continue

        # blank line
        if not line.strip():
            close_lists()
            i += 1
            continue

        # headers
        h = re.match(r"^(#{1,6})\s+(.*)$", line)
        if h:
            close_lists()
            level = min(len(h.group(1)) + 1, 6)  # demote a touch for bubble context
            htmlparts.append(f"<h{level}>{_inline_md(h.group(2).strip())}</h{level}>")
            i += 1
            continue

        # blockquote
        if re.match(r"^\s*>\s?", line):
            close_lists()
            quote = re.sub(r"^\s*>\s?", "", line)
            htmlparts.append(f"<blockquote>{_inline_md(quote)}</blockquote>")
            i += 1
            continue

        # unordered list
        ul = re.match(r"^\s*[-*+]\s+(.*)$", line)
        if ul:
            if not list_stack or list_stack[-1] != "ul":
                close_lists()
                list_stack.append("ul")
                htmlparts.append("<ul>")
            htmlparts.append(f"<li>{_inline_md(ul.group(1).strip())}</li>")
            i += 1
            continue

        # ordered list
        ol = re.match(r"^\s*(\d+)[.)]\s+(.*)$", line)
        if ol:
            if not list_stack or list_stack[-1] != "ol":
                close_lists()
                list_stack.append("ol")
                htmlparts.append("<ol>")
            # Use the explicit source number so items separated by blank lines
            # (each in their own <ol>) still count 1, 2, 3, 4 instead of resetting.
            num = ol.group(1)
            htmlparts.append(
                f'<li value="{num}">{_inline_md(ol.group(2).strip())}</li>'
            )
            i += 1
            continue

        # paragraph (gather contiguous non-special lines)
        close_lists()
        buf = [line]
        i += 1
        while i < n and lines[i].strip() and not re.match(
            r"^\s*(```|#{1,6}\s|[-*+]\s|\d+[.)]\s|>\s?)", lines[i]
        ):
            buf.append(lines[i])
            i += 1
        para = "<br>".join(_inline_md(b.strip()) for b in buf)
        htmlparts.append(f"<p>{para}</p>")

    close_lists()
    return "\n".join(htmlparts)


# --------------------------------------------------------------------------- #
# HTML page                                                                    #
# --------------------------------------------------------------------------- #

_CSS = """
:root{
  --bg:#f4f6fb; --card:#ffffff; --ink:#1d2433; --muted:#6b7689;
  --human:#0b5cff; --human-soft:#eaf1ff; --human-bd:#cfe0ff;
  --ai:#0f9d76; --ai-soft:#eafaf4; --ai-bd:#c7efe1;
  --code-bg:#0e1726; --code-ink:#e6edf6;
  --think:#fff7e6; --think-bd:#f3dca0; --think-ink:#7a5b12;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
.page{max-width:880px;margin:0 auto;padding:40px 20px 80px;}
header.hero{text-align:center;margin-bottom:36px;}
.brand{display:inline-flex;align-items:center;gap:10px;font-weight:700;
  letter-spacing:.02em;color:var(--muted);text-transform:uppercase;font-size:12px;}
.brand .dot{width:9px;height:9px;border-radius:50%;background:var(--human);
  box-shadow:0 0 0 4px var(--human-soft);}
h1.title{font-size:28px;line-height:1.25;margin:14px 0 6px;font-weight:760;}
.subtitle{color:var(--muted);font-size:14px;margin:0;}
.meta-row{margin-top:14px;color:var(--muted);font-size:12.5px;}
.legend{display:flex;gap:14px;justify-content:center;margin-top:18px;flex-wrap:wrap;}
.chip{display:inline-flex;align-items:center;gap:8px;font-size:12.5px;font-weight:600;
  padding:5px 11px;border-radius:999px;border:1px solid transparent;}
.chip.human{color:var(--human);background:var(--human-soft);border-color:var(--human-bd);}
.chip.ai{color:var(--ai);background:var(--ai-soft);border-color:var(--ai-bd);}
.avatar{width:22px;height:22px;border-radius:50%;display:inline-grid;place-items:center;
  font-size:11px;font-weight:800;color:#fff;}
.avatar.human{background:var(--human);}
.avatar.ai{background:var(--ai);}

.turn{display:flex;gap:14px;margin:22px 0;align-items:flex-start;}
.turn.ai{flex-direction:row;}
.turn.human{flex-direction:row-reverse;}
.turn .col{max-width:78%;min-width:0;}
.turn.human .col{align-items:flex-end;display:flex;flex-direction:column;}
.who{font-size:12px;font-weight:700;color:var(--muted);margin:2px 6px 6px;
  text-transform:uppercase;letter-spacing:.04em;}
.bubble{border-radius:16px;padding:14px 18px;border:1px solid;word-wrap:break-word;}
.turn.ai .bubble{background:#dcf5e9;border-color:#ade0c8;border-top-left-radius:4px;
  box-shadow:0 1px 2px rgba(20,30,60,.05);}
.turn.human .bubble{background:#d8e7ff;border-color:#b3cdff;
  border-top-right-radius:4px;}
.bubble :first-child{margin-top:0}
.bubble :last-child{margin-bottom:0}
.bubble p{margin:.55em 0}
.bubble h2,.bubble h3,.bubble h4,.bubble h5,.bubble h6{margin:.9em 0 .4em;line-height:1.3}
.bubble ul,.bubble ol{margin:.5em 0;padding-left:1.4em}
.bubble li{margin:.2em 0}
.bubble code{background:#eef1f7;border:1px solid #e1e6f0;border-radius:5px;
  padding:.05em .4em;font-size:.88em;font-family:"SF Mono",ui-monospace,Menlo,Consolas,monospace;}
.bubble pre{background:var(--code-bg);color:var(--code-ink);border-radius:12px;
  padding:14px 16px;overflow:auto;margin:.7em 0;}
.bubble pre code{background:none;border:none;color:inherit;padding:0;font-size:.85em;}
.bubble blockquote{margin:.6em 0;padding:.2em 0 .2em 14px;border-left:3px solid var(--ai-bd);
  color:var(--muted);}
.bubble a{color:var(--human);}

.cmd .bubble{background:#0e1726;border-color:#0e1726;color:#dbe7ff;
  font-family:"SF Mono",ui-monospace,Menlo,Consolas,monospace;font-size:14px;}
.cmd .bubble::before{content:"⌘ ";opacity:.7;}

.turn.think{justify-content:flex-start;}
.turn.think .bubble{background:var(--think);border-color:var(--think-bd);color:var(--think-ink);
  font-style:italic;}
.turn.think .who{color:var(--think-ink);opacity:.8;}

footer.foot{text-align:center;color:var(--muted);font-size:12px;margin-top:50px;
  padding-top:20px;border-top:1px solid #e6e9f2;}
"""


def _turn_html(turn: dict) -> str:
    role = turn["role"]
    kind = turn["kind"]

    if kind == "thinking":
        body = render_markdown(turn["text"])
        return (
            '<div class="turn think ai">'
            '<div class="col">'
            '<div class="who">AI · thinking</div>'
            f'<div class="bubble">{body}</div>'
            "</div></div>"
        )

    if role == "human":
        who = "Human Analyst"
        avatar = '<div class="avatar human">HA</div>'
        cmd_cls = " cmd" if kind == "command" else ""
        if kind == "command":
            body = html.escape(turn["text"])
        else:
            body = render_markdown(turn["text"])
        return (
            f'<div class="turn human{cmd_cls}">'
            f"{avatar}"
            '<div class="col">'
            f'<div class="who">{who}</div>'
            f'<div class="bubble">{body}</div>'
            "</div></div>"
        )

    # AI text
    avatar = '<div class="avatar ai">AI</div>'
    body = render_markdown(turn["text"])
    return (
        '<div class="turn ai">'
        f"{avatar}"
        '<div class="col">'
        '<div class="who">AI</div>'
        f'<div class="bubble">{body}</div>'
        "</div></div>"
    )


def build_html(turns: list[dict], source: Path) -> str:
    rendered = _dt.datetime.now().strftime("%B %d, %Y · %I:%M %p")
    n_human = sum(1 for t in turns if t["role"] == "human" and t["kind"] != "thinking")
    n_ai = sum(1 for t in turns if t["role"] == "ai" and t["kind"] == "text")
    bubbles = "\n".join(_turn_html(t) for t in turns)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(PAGE_TITLE)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="page">
  <header class="hero">
    <div class="brand"><span class="dot"></span> Nodal</div>
    <h1 class="title">{html.escape(PAGE_TITLE)}</h1>
    <p class="subtitle">A conversation between the human analyst and the AI, building the analytics context layer.</p>
    <div class="meta-row">Source: <code>{html.escape(source.name)}</code> · {n_human} analyst messages · {n_ai} AI replies · rendered {rendered}</div>
    <div class="legend">
      <span class="chip human"><span class="avatar human">HA</span> Human Analyst</span>
      <span class="chip ai"><span class="avatar ai">AI</span> AI</span>
    </div>
  </header>
  <main class="thread">
{bubbles}
  </main>
  <footer class="foot">Generated by Nodal · render_transcript.py</footer>
</div>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# Output naming (never overwrite)                                             #
# --------------------------------------------------------------------------- #

def unique_output_path(out_dir: Path, source: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = f"{source.stem}__{stamp}"
    candidate = out_dir / f"{base}.html"
    counter = 2
    while candidate.exists():
        candidate = out_dir / f"{base}-{counter}.html"
        counter += 1
    return candidate


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #

def render_file(source: Path, out_dir: Path, show_thinking: bool) -> Path | None:
    turns = parse_conversation(source, show_thinking=show_thinking)
    if not turns:
        print(f"  ! No conversational content found in {source.name}; skipped.")
        return None
    out_path = unique_output_path(out_dir, source)
    out_path.write_text(build_html(turns, source), encoding="utf-8")
    print(f"  ✓ {source.name} → {out_path}")
    return out_path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Render a Claude Code transcript (.jsonl) as a clean conversation HTML page."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=str(EXAMPLES_DIR),
        help="Path to a .jsonl transcript or a directory of them "
        f"(default: the examples dir {EXAMPLES_DIR}).",
    )
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent / "output"),
        help="Output directory for the HTML (default: ./output next to this script).",
    )
    parser.add_argument(
        "--show-thinking",
        action="store_true",
        help="Include the AI's internal thinking blocks (hidden by default).",
    )
    parser.add_argument(
        "--open", action="store_true", help="Open the rendered HTML in your browser."
    )
    args = parser.parse_args(argv)

    src = Path(args.path).expanduser()
    out_dir = Path(args.out).expanduser()

    if not src.exists():
        print(f"Error: path does not exist: {src}", file=sys.stderr)
        return 1

    if src.is_dir():
        files = sorted(src.glob("*.jsonl"))
        if not files:
            print(f"Error: no .jsonl files found in {src}", file=sys.stderr)
            return 1
        print(f"Rendering {len(files)} transcript(s) from {src} …")
    else:
        files = [src]
        print(f"Rendering {src.name} …")

    produced: list[Path] = []
    for f in files:
        result = render_file(f, out_dir, args.show_thinking)
        if result:
            produced.append(result)

    if not produced:
        print("Nothing was rendered.")
        return 1

    print(f"\nDone. {len(produced)} file(s) written to {out_dir}")
    if args.open:
        webbrowser.open(produced[0].as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
