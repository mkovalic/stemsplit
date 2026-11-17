"""Render the tutorial as a portable HTML page with its Markdown embedded.

Run from the project root with: .venv/bin/python docs/build_preview.py
"""

from html import escape
import json
from pathlib import Path
import re

from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound


ROOT = Path(__file__).resolve().parent
STEM = "how-to-make-a-vocal-separation-engine-for-music"
markdown = (ROOT / f"{STEM}.md").read_text(encoding="utf-8")
formatter = HtmlFormatter(nowrap=True, style="monokai")


def render_fence(tokens, idx, options, env):
    token = tokens[idx]
    language = token.info.strip().split()[0] if token.info.strip() else "text"
    try:
        rendered = highlight(token.content, get_lexer_by_name(language), formatter)
    except ClassNotFound:
        rendered = escape(token.content)
    label = {"bash": "Terminal", "python": "Python", "text": "Text"}.get(language, language)
    return (
        '<figure class="code-block"><figcaption>'
        f'<span>{escape(label)}</span>'
        '<button class="code-copy" type="button" aria-label="Copy code">Copy</button>'
        '</figcaption><pre><code>' + rendered + '</code></pre></figure>\n'
    )


parser = MarkdownIt("commonmark", {"html": False}).enable("table")
parser.renderer.rules["fence"] = render_fence
tokens = parser.parse(markdown)
headings = []
for i, token in enumerate(tokens):
    if token.type == "heading_open":
        title = tokens[i + 1].content
        anchor = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        token.attrSet("id", anchor)
        if token.tag == "h2":
            headings.append((anchor, title))
article = parser.renderer.render(tokens, parser.options, {})
toc = "\n".join(
    f'<li><a href="#{anchor}">{escape(title)}</a></li>' for anchor, title in headings
)
json_source = json.dumps(markdown, ensure_ascii=False).replace("<", "\\u003c")

template = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <link rel="icon" href="data:,">
  <meta name="description" content="Build a vocal separation engine with Demucs and Modal. Separate one song, process a folder in parallel, and estimate costs at scale.">
  <title>How to make a vocal separation engine for music</title>
  <style>
    :root { --bg:#181818; --panel:#222222; --text:#c0c0c0; --strong:#f4f4f2; --muted:#919191; --line:#343434; --accent:#91d94b; --hover:#262626; }
    * { box-sizing:border-box; }
    html { scroll-behavior:smooth; scroll-padding-top:100px; }
    body { margin:0; background:var(--bg); color:var(--text); font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; font-size:16px; line-height:1.65; }
    a { color:var(--accent); text-decoration:none; text-underline-offset:3px; }
    a:hover { text-decoration:underline; }
    a:focus-visible, button:focus-visible, summary:focus-visible { outline:2px solid var(--accent); outline-offset:4px; }
    button { font:inherit; cursor:pointer; color:inherit; }
    .skip { position:absolute; left:20px; top:-80px; padding:8px 14px; background:var(--panel); z-index:20; }
    .skip:focus { top:10px; }
    .site-header { position:sticky; top:0; z-index:10; background:var(--bg); border-bottom:1px solid var(--line); }
    .header-inner { max-width:1200px; margin:auto; padding:16px 32px; display:flex; align-items:center; justify-content:space-between; gap:20px; }
    .wordmark { color:var(--strong); font-size:16px; font-weight:600; letter-spacing:-.3px; }
    .wordmark span { color:var(--accent); font-weight:400; margin-left:5px; }
    .header-link { color:var(--text); font-size:13px; }
    .layout { max-width:1200px; margin:0 auto; padding:44px 32px 100px; display:grid; grid-template-columns:minmax(0,780px) 224px; gap:64px; }
    main { min-width:0; }
    .page-tools { display:flex; align-items:center; justify-content:space-between; gap:20px; margin-bottom:25px; }
    .eyebrow { font-size:12px; color:var(--muted); letter-spacing:.09em; text-transform:uppercase; }
    .copy-wrap { position:relative; }
    .copy-trigger { display:inline-flex; align-items:center; gap:9px; border:1px solid #484848; border-radius:6px; background:transparent; padding:7px 11px; font-size:13px; line-height:20px; white-space:nowrap; }
    .copy-trigger:hover { background:var(--hover); }
    .copy-trigger svg { width:15px; height:15px; }
    .copy-menu { position:absolute; right:0; top:calc(100% + 9px); width:300px; padding:6px; border:1px solid #454545; border-radius:9px; background:#202020; z-index:5; box-shadow:0 12px 32px #0006; }
    .copy-menu[hidden] { display:none; }
    .copy-menu button { display:block; text-align:left; width:100%; border:0; border-radius:5px; background:transparent; padding:11px 12px; line-height:1.45; }
    .copy-menu button:hover { background:#303030; }
    .copy-menu b { display:block; color:var(--strong); font-size:13px; font-weight:500; }
    .copy-menu small { display:block; color:var(--muted); font-size:12px; margin-top:3px; }
    h1, h2 { color:var(--strong); font-weight:550; letter-spacing:-.035em; line-height:1.25; }
    h1 { font-size:38px; margin:0 0 30px; max-width:740px; }
    h2 { margin:52px 0 24px; padding-top:8px; font-size:25px; scroll-margin-top:85px; }
    p { margin:0 0 22px; }
    strong { color:var(--strong); font-weight:600; }
    ul { padding-left:24px; margin:0 0 24px; }
    li { margin:5px 0; }
    code { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:.86em; }
    :not(pre) > code { color:#e1e1de; background:#292929; padding:2px 5px; border:1px solid #333; border-radius:4px; overflow-wrap:anywhere; }
    a code { color:var(--accent); }
    .code-block { margin:23px 0 28px; border:1px solid #343434; border-radius:6px; background:var(--panel); overflow:hidden; }
    figcaption { display:flex; justify-content:space-between; align-items:center; gap:10px; padding:8px 14px; border-bottom:1px solid #343434; color:#a2a2a2; font-size:11px; line-height:18px; }
    .code-copy { background:none; border:none; font-size:11px; padding:1px 3px; }
    .code-copy:hover { color:var(--strong); }
    pre { margin:0; padding:18px 16px 20px; overflow-x:auto; tab-size:4; line-height:1.6; }
    pre code { font-size:13px; color:#d8d8d8; white-space:pre; }
    pre .k, pre .kn, pre .kd, pre .ow { color:#c68bcf; }
    pre .s, pre .s1, pre .s2, pre .sa { color:#dfcf8a; }
    pre .mi, pre .mf { color:#c5a0e1; }
    pre .nf, pre .nc { color:#9bc9e0; }
    pre .nb, pre .bp { color:#8dcac0; }
    pre .c, pre .c1 { color:#8c9184; font-style:italic; }
    pre .o, pre .p { color:#c0c0c0; }
    table { width:100%; border-collapse:collapse; margin:26px 0; font-size:15px; font-variant-numeric:tabular-nums; }
    th { color:var(--strong); font-weight:500; background:var(--panel); }
    th, td { padding:13px 18px; border-bottom:1px solid var(--line); }
    tr:last-child td { color:var(--strong); }
    aside { position:sticky; top:102px; height:max-content; font-size:13px; }
    .toc-label { color:var(--strong); font-weight:500; margin:0 0 16px 14px; }
    .toc { list-style:none; padding:0; border-left:1px solid var(--line); }
    .toc li { margin:0; }
    .toc a { display:block; color:#aaa; padding:9px 0 9px 14px; line-height:1.5; border-left:1px solid transparent; margin-left:-1px; }
    .toc a:hover { color:var(--strong); text-decoration:none; }
    .toc a[aria-current="location"] { border-left-color:var(--accent); color:var(--strong); background:linear-gradient(90deg,#ffffff05,transparent); }
    .aside-download { display:block; margin:25px 0 0 14px; color:var(--muted); font-size:12px; }
    .mobile-toc { display:none; }
    .footer { border-top:1px solid var(--line); margin-top:48px; padding-top:18px; color:var(--muted); font-size:12px; }
    #status { position:fixed; left:50%; bottom:28px; transform:translateX(-50%); padding:10px 18px; border:1px solid #526442; border-radius:7px; background:#24301d; color:#deefd1; font-size:13px; z-index:30; opacity:0; pointer-events:none; transition:opacity .15s; }
    #status.visible { opacity:1; }
    dialog { width:min(780px,calc(100% - 32px)); padding:24px; border:1px solid #555; border-radius:9px; background:var(--panel); color:var(--text); }
    dialog::backdrop { background:#000b; }
    dialog h2 { font-size:20px; margin:0 0 12px; padding:0; }
    dialog p { font-size:14px; margin-bottom:16px; }
    dialog textarea { width:100%; height:50vh; resize:vertical; border:1px solid #555; border-radius:4px; padding:12px; background:var(--bg); color:var(--text); font:12px/1.5 ui-monospace,monospace; }
    dialog form { display:flex; justify-content:flex-end; margin-top:12px; }
    dialog form button { border:1px solid #555; background:transparent; border-radius:4px; padding:6px 16px; }
    @media (max-width:1050px) { .layout { gap:36px; grid-template-columns:minmax(0,1fr) 200px; } h1 { font-size:35px; } }
    @media (max-width:800px) {
      .header-inner { padding:14px 22px; }
      .layout { display:block; max-width:760px; padding:30px 22px 70px; }
      aside { display:none; }
      .mobile-toc { display:block; margin-bottom:27px; border-bottom:1px solid var(--line); padding-bottom:14px; font-size:13px; }
      .mobile-toc summary { cursor:pointer; color:var(--text); }
      .mobile-toc ul { margin-top:12px; margin-bottom:4px; padding-left:18px; }
      h1 { font-size:32px; margin-bottom:27px; }
      h2 { font-size:24px; margin-top:42px; }
    }
    @media (max-width:430px) { body { font-size:15px; } .header-inner { padding:13px 18px; } .header-link { font-size:12px; } .layout { padding-left:18px; padding-right:18px; } h1 { font-size:30px; } .page-tools { gap:12px; } .eyebrow { font-size:10px; } .copy-menu { width:280px; } pre { padding:14px 12px; } pre code { font-size:12px; } th,td { padding:11px 12px; } }
    @media (prefers-reduced-motion:reduce) { html { scroll-behavior:auto; } #status { transition:none; } }
    @media print { body { background:white; color:#222; font-size:11pt; } .site-header,.page-tools,aside,.mobile-toc,.code-copy,.footer,#status { display:none; } .layout { display:block; max-width:none; padding:0; } h1,h2,strong { color:#111; } h1 { font-size:26pt; } h2 { break-after:avoid; font-size:17pt; } a { color:#222; text-decoration:underline; } pre,pre code,pre span,code { color:#222 !important; } .code-block,th,:not(pre)>code { background:#f5f5f5; } pre { white-space:pre-wrap; overflow:visible; } pre code { white-space:pre-wrap; font-size:9pt; } .code-block,table { break-inside:avoid; } }
  </style>
</head>
<body>
  <a class="skip" href="#article">Skip to content</a>
  <header class="site-header"><div class="header-inner">
    <a class="wordmark" href="#">Stem separation<span>Tutorial</span></a>
    <a class="header-link" href="https://modal.com/docs/">Modal documentation ↗</a>
  </div></header>
  <div class="layout">
    <main id="article">
      <div class="page-tools">
        <span class="eyebrow">Audio / Demucs on Modal</span>
        <div class="copy-wrap">
          <button type="button" class="copy-trigger" id="copy-trigger" aria-expanded="false" aria-controls="copy-menu">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V4a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h4"/></svg>
            Copy page
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>
          </button>
          <div class="copy-menu" id="copy-menu" hidden>
            <button type="button" id="copy-markdown"><b>Copy page</b><small>Copy page as Markdown for LLMs</small></button>
            <button type="button" id="download-markdown"><b>Download Markdown</b><small>Save the complete tutorial as a .md file</small></button>
          </div>
        </div>
      </div>
      <details class="mobile-toc"><summary>On this page</summary><ul>__TOC__</ul></details>
      <article>__ARTICLE__</article>
      <footer class="footer">Demucs · Modal · Python<br>Cost example based on a November 17, 2026 sample.</footer>
    </main>
    <aside aria-label="On this page">
      <p class="toc-label">On this page</p>
      <ol class="toc">__TOC__</ol>
      <a class="aside-download" id="aside-download" href="__STEM__.md" download>Download Markdown ↓</a>
    </aside>
  </div>
  <div id="status" role="status" aria-live="polite"></div>
  <dialog id="copy-fallback" aria-labelledby="fallback-title">
    <h2 id="fallback-title">Copy Markdown</h2>
    <p>Automatic copying is unavailable in this browser. The text is selected below; press ⌘C or Ctrl+C to copy it.</p>
    <textarea id="fallback-text" aria-label="Text to copy" readonly></textarea>
    <form method="dialog"><button>Close</button></form>
  </dialog>
  <script type="application/json" id="markdown-source">__MARKDOWN__</script>
  <script>
    const markdown = JSON.parse(document.getElementById('markdown-source').textContent);
    const trigger = document.getElementById('copy-trigger');
    const menu = document.getElementById('copy-menu');
    let statusTimer;
    function announce(text) {
      const status = document.getElementById('status');
      status.textContent = text; status.classList.add('visible');
      clearTimeout(statusTimer); statusTimer = setTimeout(() => status.classList.remove('visible'), 2500);
    }
    function closeMenu() { menu.hidden = true; trigger.setAttribute('aria-expanded', 'false'); }
    trigger.addEventListener('click', () => {
      menu.hidden = !menu.hidden;
      trigger.setAttribute('aria-expanded', String(!menu.hidden));
    });
    document.addEventListener('click', event => { if (!event.target.closest('.copy-wrap')) closeMenu(); });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !menu.hidden) { closeMenu(); trigger.focus(); }
    });
    async function copyText(text, message) {
      try {
        if (!navigator.clipboard) throw new Error('Clipboard unavailable');
        await navigator.clipboard.writeText(text);
        announce(message); return true;
      } catch (_) {
        const helper = document.createElement('textarea');
        helper.value = text; helper.style.position = 'fixed'; helper.style.opacity = '0';
        document.body.appendChild(helper); helper.focus(); helper.select();
        let copied = false;
        try { copied = document.execCommand('copy'); } catch (_) {}
        helper.remove();
        if (copied) { announce(message); return true; }
        const dialog = document.getElementById('copy-fallback');
        const field = document.getElementById('fallback-text');
        field.value = text; dialog.showModal(); field.focus(); field.select();
        return false;
      }
    }
    function downloadMarkdown() {
      const url = URL.createObjectURL(new Blob([markdown], {type:'text/markdown;charset=utf-8'}));
      const anchor = document.createElement('a');
      anchor.href = url; anchor.download = '__STEM__.md';
      document.body.appendChild(anchor); anchor.click(); anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
    document.getElementById('copy-markdown').addEventListener('click', async () => {
      closeMenu(); trigger.focus(); await copyText(markdown, 'Page copied as Markdown');
    });
    document.getElementById('download-markdown').addEventListener('click', () => {
      closeMenu(); trigger.focus(); downloadMarkdown();
    });
    document.getElementById('aside-download').addEventListener('click', event => {
      event.preventDefault(); downloadMarkdown();
    });
    document.querySelectorAll('.code-copy').forEach(button => {
      button.addEventListener('click', async () => {
        const code = button.closest('.code-block').querySelector('code').textContent;
        const copied = await copyText(code, 'Code copied');
        if (copied) { button.textContent = 'Copied'; setTimeout(() => button.textContent = 'Copy', 1800); }
      });
    });
    const sections = [...document.querySelectorAll('article h2')];
    function updateOutline() {
      let current = sections[0];
      for (const section of sections) { if (section.getBoundingClientRect().top <= 170) current = section; }
      for (const link of document.querySelectorAll('.toc a')) {
        if (link.hash === '#' + current.id) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      }
    }
    addEventListener('scroll', updateOutline, {passive:true});
    updateOutline();
  </script>
</body>
</html>
'''

html = (template.replace("__TOC__", toc)
        .replace("__ARTICLE__", article)
        .replace("__STEM__", STEM)
        .replace("__MARKDOWN__", json_source))
(ROOT / f"{STEM}.html").write_text(html, encoding="utf-8")
print(f"Rendered {STEM}.html ({len(markdown.split())} Markdown words, {len(headings)} sections)")
