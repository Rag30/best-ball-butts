"""md -> styled HTML -> PDF via headless Chrome; fails if the PDF is longer than 2 pages.
usage (from run dir): uv run -q --with markdown python <pipeline>/make_pdf.py brief.md "Best Ball Butts 2026 - Week N brief" """
import sys, re, glob, subprocess, markdown, os
src, name = sys.argv[1], sys.argv[2]
css = """@page{size:Letter;margin:12mm 13mm}body{font:9.3pt/1.38 Helvetica,Arial,sans-serif;color:#1a201c}
h1{font-size:16pt;margin:0 0 3pt;color:#1d6b47}h2{font-size:11.5pt;margin:9pt 0 3pt;border-bottom:1.5px solid #1d6b47;padding-bottom:1pt}
p{margin:3pt 0}ul{margin:2pt 0;padding-left:15pt}li{margin:1.5pt 0}table{border-collapse:collapse;width:100%;font-size:8.4pt;margin:3pt 0}
th,td{border:1px solid #c9d1cb;padding:1.5pt 4pt}th{background:#e3efe7}tr:nth-child(even) td{background:#f5f7f4}"""
h = markdown.markdown(open(src).read(), extensions=["tables", "sane_lists"])
open("brief.html", "w").write(f"<!doctype html><html><head><meta charset='utf-8'><title>{name}</title><style>{css}</style></head><body>{h}</body></html>")
import shutil
cands = (["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"] + glob.glob("/Applications/Chrome.app/Contents/MacOS/*")
         + ["/opt/pw-browsers/chromium"] + glob.glob("/opt/pw-browsers/chromium*/chrome-linux*/chrome")
         + [shutil.which(x) or "" for x in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")])
chrome = next(p for p in cands if p and os.path.isfile(p) and os.access(p, os.X_OK))  # macOS Chrome, or cloud Chromium
pdf = os.path.abspath(name + ".pdf")
if os.path.exists(pdf): os.remove(pdf)
subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer", f"--print-to-pdf={pdf}", "file://" + os.path.abspath("brief.html")], capture_output=True, timeout=120)
n = len(re.findall(rb"/Type\s*/Page[^s]", open(pdf, "rb").read()))
print(f"{pdf}: {n} pages")
sys.exit(0 if n <= 2 else 3)
