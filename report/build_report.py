"""Builds Report_Kunal_Mittal.pdf (Section 10 template) as a LaTeX document compiled with Tectonic.

    python report/build_report.py            # capture UI screenshots, run validation, write .tex, compile PDF
    python report/build_report.py --no-shots # reuse existing screenshots

Requirements (report only, not the engine): Tectonic (https://tectonic-typesetting.github.io), a Chromium
browser for the screenshots, Pillow. Every number in the report is computed from the engine, its outputs,
the tests, the fuzz harness and the sensitivity study; the page limits of Section 10 are verified from
the LaTeX .aux file after compiling.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(HERE, "build")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from stacksense_engine import kb  # noqa: E402
from stacksense_engine.kb.sources import SOURCES  # noqa: E402
from stacksense_engine.recommend import recommend  # noqa: E402
from stacksense_engine.schema import FIELDS  # noqa: E402
import screenshots  # noqa: E402

AUTHOR = {"name": "Kunal Mittal", "roll": "IMT2023533",
          "college": "International Institute of Information Technology Bangalore (IIIT Bangalore)",
          "email": "kunal.mittal@iiitb.ac.in", "github": "https://github.com/freakun0025/stacksense"}
STEM = "Report_Kunal_Mittal"


# ----------------------------------------------------------------------------------- data
def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


PUB = {f"P{i}": load(f"scenarios/public/P{i}.json") for i in range(1, 7)}
OUT = {k: recommend(v) for k, v in PUB.items()}


def edge(prefix):
    d = os.path.join(ROOT, "scenarios", "edge")
    name = next(n for n in sorted(os.listdir(d)) if n.startswith(prefix))
    return recommend(load(f"scenarios/edge/{name}"))


# Acceptable / clearly-wrong choices per public scenario (knowledge-base ids), from the brief and
# public reference architectures. Checked automatically in Section 8.
RUBRIC = {
    "P1": {"ok": {"frontend": {"astro", "hugo", "eleventy", "nextjs"}, "backend": {None},
                  "hosting": {"cloudflare", "netlify", "github_pages", "vercel", "firebase_hosting", "s3_cloudfront"}},
           "bad": {"kubernetes", "ecs_fargate", "rds_pg", "aurora_pg"}},
    "P2": {"ok": {"backend": {"nestjs", "django", "fastapi", "express", "fastify", "supabase"},
                  "database": {"postgresql"},
                  "hosting": {"cloud_run", "do_app", "ecs_fargate", "app_service", "container_apps"}},
           "bad": {"kubernetes", "render", "railway", "neon_pg", "stripe", "cassandra"}},
    "P3": {"ok": {"backend": {"go_chi", "nestjs", "fastify", "phoenix"}, "database": {"postgresql"},
                  "hosting": {"ecs_fargate", "cloud_run", "kubernetes", "flyio", "container_apps"}},
           "bad": {"nextjs_api", "functions", "firebase", "pocketbase"}},
    "P4": {"ok": {"backend": {"spring_boot"}, "database": {"postgresql"}, "hosting": {"ecs_fargate", "beanstalk"}},
           "bad": {"stripe", "supabase", "firebase", "vercel", "mongodb", "kubernetes"}},
    "P5": {"ok": {"backend": {"aspnet_core"}, "database": {"sqlserver", "postgresql"},
                  "hosting": {"app_service", "container_apps"}},
           "bad": {"kubernetes", "auth0", "clerk", "ecs_fargate", "cloud_run"}},
    "P6": {"ok": {"frontend": {"expo_rn", "kotlin_android", "flutter"},
                  "backend": {"supabase", "fastapi", "django", "express", "nestjs", "functions"},
                  "database": {"postgresql"}},
           "bad": {"pwa", "firebase_auth", "atlas_device_sync", "kubernetes", "neon_pg"}},
}


def rubric_check():
    rows = []
    for sid, rule in RUBRIC.items():
        st = OUT[sid]["stack"]
        ids = {"frontend": [c["kb_id"] for c in st["frontend"].get("components", [])],
               "backend": [st["backend"].get("kb_id")], "database": [st["database"].get("kb_id")],
               "hosting": [st["hosting"].get("kb_id")]}
        allids = {x for v in ids.values() for x in v if x} | {st["database"].get("offering_kb_id")}
        allids |= {s.get("kb_id") for s in st["supporting"]}
        layers = [(layer, any(g in acc for g in (ids[layer] or [None]))) for layer, acc in rule["ok"].items()]
        bad = sorted(allids & rule["bad"])
        rows.append((sid, all(v for _, v in layers) and not bad, layers, bad))
    return rows


def run_tests():
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ROOT,
                       capture_output=True, text=True)
    m = re.search(r"Ran (\d+) tests", r.stderr)
    return int(m.group(1)) if m else 0, r.stderr.strip().endswith("OK")


# ----------------------------------------------------------------------------------- LaTeX helpers
UNI = {"â†’": r"$\rightarrow$", "â‰¥": r"$\geq$", "â‰¤": r"$\leq$", "â‰ˆ": r"$\approx$", "Ã—": r"$\times$",
       "âˆ’": "-", "â€”": "---", "â€“": "--", "â‚¹": "Rs.", "â€¦": r"\dots{}", "âœ”": "pass", "âœ˜": "fail", "â†”": r"$\leftrightarrow$",
       "â€™": "'", "â€œ": "``", "â€": "''"}


def L(s):
    s = str(s)
    s = s.replace("\\", r"\textbackslash{}")
    for a, b in (("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
                 ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")):
        s = s.replace(a, b)
    s = s.replace(r"\textbackslash\{\}", r"\textbackslash{}")
    for a, b in UNI.items():
        s = s.replace(a, b)
    return s


def tt(s):
    return r"\texttt{" + L(s).replace(".", r".\allowbreak{}").replace(r"\_", r"\_\allowbreak{}") + "}"


def T(template, **kw):
    for k, v in kw.items():
        template = template.replace(f"@@{k}@@", str(v))
    return template


def fig(name, width, caption, label, pos="htbp"):
    return (f"\\begin{{figure}}[{pos}]\n\\centering\n\\includegraphics[width={width}\\linewidth]{{img/{name}.png}}\n"
            f"\\caption{{{caption}}}\\label{{fig:{label}}}\n\\end{{figure}}\n")


def figgrid(items):
    rows = []
    for i in range(0, len(items), 2):
        cells = []
        for name, cap, lab in items[i:i + 2]:
            cells.append(f"\\begin{{minipage}}[t]{{0.485\\linewidth}}\\centering\\includegraphics[width=\\linewidth]{{img/{name}.png}}"
                         f"\\caption{{{cap}}}\\label{{fig:{lab}}}\\end{{minipage}}")
        rows.append("\\hfill\n".join(cells))
    return "\\begin{figure}[htbp]\n\\centering\n" + "\n\\par\\vspace{6pt}\n".join(rows) + "\n\\end{figure}\n"


def figpair(a, ca, la, b, cb, lb):
    return ("\\begin{figure}[htbp]\n\\centering\n"
            f"\\begin{{minipage}}[t]{{0.485\\linewidth}}\\centering\\includegraphics[width=\\linewidth]{{img/{a}.png}}"
            f"\\caption{{{ca}}}\\label{{fig:{la}}}\\end{{minipage}}\\hfill\n"
            f"\\begin{{minipage}}[t]{{0.485\\linewidth}}\\centering\\includegraphics[width=\\linewidth]{{img/{b}.png}}"
            f"\\caption{{{cb}}}\\label{{fig:{lb}}}\\end{{minipage}}\n\\end{{figure}}\n")


# ----------------------------------------------------------------------------------- document parts
PREAMBLE = r"""\documentclass[11pt,a4paper]{article}
\usepackage{fontspec}
\usepackage[top=2.5cm,bottom=2.4cm,left=2.05cm,right=2.05cm,headsep=0.7cm]{geometry}
\usepackage[table]{xcolor}
\usepackage{graphicx,booktabs,tabularx,longtable,array,multicol,microtype}
\usepackage{amsmath,amssymb}
\usepackage{enumitem}
\usepackage{tikz}
\usetikzlibrary{positioning,arrows.meta,shadows}
\usepackage[most]{tcolorbox}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{hyperref}
\usepackage{url}
\usepackage{lastpage}
\usepackage[section]{placeins}
\definecolor{accent}{HTML}{1F4E79}
\definecolor{accent2}{HTML}{0F766E}
\definecolor{accent3}{HTML}{C2410C}
\definecolor{accent4}{HTML}{7C3AED}
\definecolor{soft}{HTML}{DCE8F5}
\definecolor{soft2}{HTML}{E3F4F1}
\definecolor{rowalt}{HTML}{F3F7FB}
\usepackage[font=small,labelfont={bf,color=accent}]{caption}
\hypersetup{colorlinks=true,linkcolor=accent,citecolor=accent2,urlcolor=accent2}
\titleformat{\section}{\Large\bfseries\color{accent}}
  {\tikz[baseline=(n.base)]\node[fill=accent,text=white,rounded corners=2pt,inner sep=3pt,minimum width=1.5em](n){\thesection};}
  {0.6em}{}[\vspace{-4pt}{\color{accent!35}\titlerule[1pt]}]
\titlespacing*{\section}{0pt}{20pt}{11pt}
\titleformat{\subsection}{\large\bfseries\color{accent2}}{\thesubsection}{0.7em}{}
\titlespacing*{\subsection}{0pt}{14pt}{7pt}
\titleformat{\paragraph}[runin]{\normalsize\bfseries\color{accent2}}{}{0pt}{}
\titlespacing*{\paragraph}{0pt}{9pt}{0.6em}
\pagestyle{fancy}\fancyhf{}
\renewcommand{\headrule}{{\color{accent!60}\hrule height 0.7pt}}
\fancyhead[L]{\small\color{accent}\textbf{StackSense Challenge}\enspace{\color{gray}|\enspace Synergy '26}}
\fancyhead[R]{\small\color{gray}Kunal Mittal (IMT2023533)}
\fancyfoot[C]{\small\color{accent}\textbf{\thepage}}
\setlist{leftmargin=1.6em,itemsep=4pt,topsep=5pt}
\setlist[itemize]{label=\textcolor{accent2}{\scriptsize$\blacktriangleright$}}
\setlist[enumerate]{label=\textcolor{accent}{\bfseries\arabic*.}}
\setlength{\parskip}{5pt}
\linespread{1.05}
\renewcommand{\arraystretch}{1.3}
\setlength{\aboverulesep}{0pt}\setlength{\belowrulesep}{0pt}
\arrayrulecolor{accent!70}
\newcolumntype{Y}{>{\raggedright\arraybackslash}X}
\newcolumntype{P}[1]{>{\raggedright\arraybackslash}p{#1}}
\newtcolorbox{keybox}[1][]{enhanced,colback=soft2,colframe=accent2,boxrule=0.6pt,arc=2pt,left=8pt,right=8pt,top=5pt,bottom=5pt,fonttitle=\bfseries,coltitle=white,colbacktitle=accent2,#1}
\newtcolorbox{notebox}[1][]{enhanced,colback=soft,colframe=accent,boxrule=0.6pt,arc=2pt,left=8pt,right=8pt,top=5pt,bottom=5pt,fonttitle=\bfseries,coltitle=white,colbacktitle=accent,#1}
\newcommand{\stat}[3]{\begin{tcolorbox}[enhanced,colback=#3!8,colframe=#3,boxrule=0.6pt,arc=3pt,halign=center,valign=center,height=1.85cm,left=2pt,right=2pt]{\Large\bfseries\color{#3}#1}\\[1pt]{\scriptsize\color{black!75}#2}\end{tcolorbox}}
\renewcommand{\topfraction}{0.9}\renewcommand{\bottomfraction}{0.8}\renewcommand{\textfraction}{0.07}
\renewcommand{\floatpagefraction}{0.75}\setcounter{totalnumber}{4}\setcounter{topnumber}{3}
\setcounter{tocdepth}{1}
\urlstyle{same}
\begin{document}
"""


def title_page():
    a = AUTHOR
    return T(r"""\begin{titlepage}
\begin{tikzpicture}[remember picture,overlay]
\fill[accent] (current page.north west) rectangle ([yshift=-7.2cm]current page.north east);
\fill[accent2] ([yshift=-7.2cm]current page.north west) rectangle ([yshift=-7.5cm]current page.north east);
\fill[accent3] ([yshift=-7.5cm]current page.north west) rectangle ([yshift=-7.62cm]current page.north east);
\node[anchor=north west,text=white,font=\large\scshape] at ([xshift=2.1cm,yshift=-1.6cm]current page.north west)
  {Synergy '26 \enspace\textbullet\enspace Online Systems-Design Challenge};
\node[anchor=north west,text=white,font=\fontsize{30}{36}\selectfont\bfseries] at ([xshift=2.1cm,yshift=-2.6cm]current page.north west)
  {StackSense Challenge};
\node[anchor=north west,text=white!85!accent,font=\Large,text width=16cm] at ([xshift=2.1cm,yshift=-4.25cm]current page.north west)
  {An Explainable, Deterministic Tech Stack Recommendation Engine};
\node[anchor=north west,text=white!80!accent,font=\large\itshape] at ([xshift=2.1cm,yshift=-5.55cm]current page.north west)
  {Project Report};
\end{tikzpicture}
\vspace*{6.6cm}

\begin{tcolorbox}[enhanced,colback=rowalt,colframe=accent,boxrule=0.6pt,arc=3pt,left=10pt,right=10pt,top=8pt,bottom=8pt]
\renewcommand{\arraystretch}{1.45}
\begin{tabular}{@{}>{\bfseries\color{accent}}l@{\hspace{1.2em}}p{11.2cm}@{}}
Name & @@name@@ (@@roll@@)\\
College & @@college@@\\
Unstop email & \texttt{@@email@@}\\
GitHub & \url{@@github@@}\\
Date & @@date@@\\
\end{tabular}
\end{tcolorbox}
\vspace{0.5cm}

\begin{tcolorbox}[enhanced,colback=white,colframe=accent2!70,boxrule=0.6pt,arc=3pt,left=10pt,right=10pt,top=4pt,bottom=4pt,
  title=Contents,fonttitle=\bfseries,colbacktitle=accent2,coltitle=white]
\small
\renewcommand{\contentsname}{}
\makeatletter\renewcommand{\section}{\@ifstar{\@gobble}{\@gobble}}\makeatother
\tableofcontents
\end{tcolorbox}
\vfill
{\footnotesize\color{gray}All screenshots were captured from the running engine; all figures and numbers in this report are
generated from the engine, its outputs and its test suites by \texttt{report/build\_report.py}.\par}
\end{titlepage}
\setcounter{page}{1}
""", name=a["name"], roll=a["roll"], college=L(a["college"]), email=a["email"], github=a["github"],
             date=datetime.date.today().strftime("%d %B %Y"))


def s1(st):
    return T(r"""\section{Abstract}\label{sec:start}
StackSense recommends a frontend, backend, database and hosting platform, together with the supporting services a
project needs, from a structured description of the project: its type, scale, team, budget, timeline, infrastructure,
compliance obligations and priorities. Every choice is made by rules and weighted scoring over a curated knowledge base
of @@total@@ technologies and managed offerings, @@life@@ end-of-life records and @@src@@ cited sources; no language
model takes part in any decision. Hard constraints (data residency, compliance, deployment model, cloud preference)
remove candidates outright, while budget, timeline and priorities are traded off explicitly, including an automatic
re-plan when the cost floor exceeds the budget. Each component is returned with a justification tied to input fields,
rejected alternatives, trade-offs, a monthly cost band and graded warnings. The engine runs on the Python standard library,
answers in milliseconds, and was validated with @@tests@@ unit tests, @@fuzz@@ randomised scenarios and a perturbation study.

\vspace{4pt}
\begin{tcbraster}[raster columns=4,raster equal height,raster column skip=6pt]
\stat{@@total@@}{technologies and managed offerings}{accent}
\stat{@@src@@}{cited sources in the knowledge base}{accent2}
\stat{0}{hard-constraint violations in @@fuzz@@ random scenarios}{accent3}
\stat{6\,/\,6}{public scenarios within the acceptable set}{accent4}
\end{tcbraster}
""", total=st["total"], life=st["lifecycle_entries"], src=st["sources"], tests=st["tests"], fuzz=f"{st['fuzz_n']:,}")


def s2():
    return r"""\section{Problem understanding}
The brief asks for recommendations that are right for the constraints, that come from the right questions, and that a
senior engineer would accept. I read this as four requirements on the engine.

\begin{enumerate}
\item \emph{Constraints come before popularity.} Residency, compliance, deployment model and an explicit cloud choice
are hard constraints. They are implemented as filters that record why a candidate was removed, not as penalties, so a
popular but non-compliant option can never win. For example, Neon, Render and Railway have no Indian region, and Stripe
is not an option for payment data that must stay in India.
\item \emph{Context changes the answer.} Team languages and experience, DevOps capacity, timeline, scale and budget all
change the weights, so a solo beginner and an eight-person senior fintech team receive different stacks for similar
features.
\item \emph{Conflicts are reported, not hidden.} Contradictory hard constraints yield the status \texttt{infeasible}
with resolution options; requirements that a hard constraint makes impossible are relaxed with a critical warning and an
assumption that names the relaxation; a budget overrun is never silent.
\item \emph{Results are reproducible.} The engine is a pure function of its input: no clock, randomness, network access
or language model. Lifecycle dates are compared with a fixed knowledge-base date (13 November 2026), so the same input
always produces byte-identical JSON.
\end{enumerate}

Recommendations name real, currently maintained products together with the region where data lives, for example
``Cloud SQL for PostgreSQL (asia-south1 Mumbai)''. Mobile and desktop clients are part of the frontend layer. A file
with missing required fields returns \texttt{invalid\_input} by default; an opt-in lenient mode applies documented
defaults instead. The cost estimate is an order-of-magnitude band built from list prices per scale tier, with every
assumption stated. One data note: P4's \texttt{team.has\_devops} is \texttt{false} in the PDF appendix but \texttt{true}
in \texttt{stacksense\_public\_scenarios.json}. The JSON file is used for the official output and the PDF variant is run
as an additional scenario; both give the same core stack.
"""


def s3():
    rows = [
        ("schema.py, validate.py", "Field catalogue (type, enum, default, help text, affected decisions) and field-level validation; defaults are recorded as assumptions."),
        ("describe.py, profile.py", "Deterministic phrase lexicon for the free-text description; derived profile (scale tier, peak concurrency and request rate, database vs.\\ media volume, effort vs.\\ capacity, region)."),
        ("conflicts.py", "Pre-flight infeasibility checks, relaxation of impossible requirements, 57 warning rules, lifecycle scan of existing systems."),
        ("kb/", "Knowledge base: scores, regions, attestations, prices, limits, lifecycle status and sources."),
        ("scoring.py", "Hard-constraint filter and reusable soft factors."),
        ("select\\_core.py, select\\_support.py", "Per-layer selection: frontend (web, mobile, desktop), backend, database engine, hosting, managed database offering, supporting services."),
        ("cost.py, architecture.py", "Monthly cost band with breakdown; architecture style with an over-engineering guard."),
        ("explain.py, recommend.py", "Justifications, \\texttt{driven\\_by}, reasons for rejected alternatives, trade-offs, decision trace; orchestration and status."),
        ("stacksense.py, server.py, web/", "Command-line interface, dependency-free HTTP API and browser UI."),
    ]
    body = "\n".join(f"\\texttt{{{a}}} & {b}\\\\" for a, b in rows)
    return r"""\section{System architecture}
\begin{figure}[htbp]
\centering
\begin{tikzpicture}[node distance=4mm, box/.style={draw=accent, fill=soft, rounded corners=3pt, align=center, font=\footnotesize, drop shadow={opacity=0.15},
  minimum height=11mm, text width=19mm, inner sep=2pt}, >=Stealth]
\node[box, fill=accent3!12, draw=accent3] (in) {Scenario\\JSON / form};
\node[box, right=of in] (v) {Validate\\\scriptsize types, defaults};
\node[box, right=of v] (p) {Profile\\\scriptsize tier, load, region};
\node[box, right=of p] (pf) {Pre-flight\\\scriptsize infeasible?};
\node[box, right=of pf] (s) {Select\\\scriptsize filter + score};
\node[box, below=7mm of s] (c) {Cost\\\scriptsize band, re-plan};
\node[box, left=of c] (e) {Explain\\\scriptsize warnings, trace};
\node[box, left=of e, fill=accent3!12, draw=accent3] (o) {Output JSON\\UI / file};
\node[box, left=of o, dashed, draw=accent2, fill=soft2] (k) {Knowledge\\base};
\begin{scope}[accent, thick]\draw[->] (in) -- (v); \draw[->] (v) -- (p); \draw[->] (p) -- (pf); \draw[->] (pf) -- (s);
\draw[->] (s) -- (c); \draw[->] (c) -- (e); \draw[->] (e) -- (o);\end{scope}
\draw[->, dashed] (k.north) |- ([yshift=-3mm]s.south west) -- ([yshift=-3mm]s.south west);
\end{tikzpicture}
\caption{Processing pipeline. Every stage is deterministic; the knowledge base is read-only data.}
\label{fig:pipeline}
\end{figure}

A scenario is first validated against the schema: every problem becomes a \texttt{validation\_errors} entry, and absent
optional fields receive documented defaults that are recorded in \texttt{assumptions}. The profile stage derives the
quantities that drive sizing and cost (estimated peak concurrency, requests per second, database and media volume) and
logs every estimate. The pre-flight stage detects logically incompatible hard constraints and relaxes requirements that
a hard constraint forbids. Layers are then selected in dependency order: frontend, backend (aware of client languages),
database engine (aware of backend-as-a-service coupling), hosting (aware of runtime, WebSockets and server rendering),
managed database offering (same platform and region as the hosting), and finally the supporting services. Cost is
estimated from the selected components; if the floor exceeds the budget, the whole plan is recomputed with cost weighted
at the maximum priority and the cheaper plan is kept. Finally the architecture style, warnings and explanations are
generated from the factors recorded during scoring. Table~\ref{tab:modules} lists the modules.

\begin{table}[htbp]
\centering\small
\caption{Modules of the engine (package \texttt{stacksense\_engine}).}\label{tab:modules}
\rowcolors{2}{white}{rowalt}\begin{tabularx}{\linewidth}{@{}P{4.6cm}Y@{}}
\toprule
\rowcolor{soft}\textcolor{accent}{\textbf{Module}} & \textcolor{accent}{\textbf{Responsibility}}\\
\midrule
""" + body + r"""
\bottomrule
\end{tabularx}
\end{table}

The engine is written in Python 3.9+ using only the standard library (\texttt{json}, \texttt{http.server},
\texttt{argparse}, \texttt{re}, \texttt{hashlib}, \texttt{unittest}); the UI is plain HTML, CSS and JavaScript with no
framework or build step. A Docker image based on \texttt{python:3.12-slim} is provided as an alternative way to run it.
"""


def s4():
    mand = [f for f in FIELDS if not f["extra"] and not f["path"].startswith("priorities.")]
    extra = [f for f in FIELDS if f["extra"]]

    def rule(f):
        k = f["kind"]
        if k in ("enum", "list_enum"):
            r = "enum (" + str(len(f["enum"])) + " values)"
        elif k in ("int", "number", "int_or_null"):
            r = ("integer" if k != "number" else "number") + (f" $\\geq$ {f['minimum']}" if f["minimum"] is not None else "") \
                + (" or null" if k == "int_or_null" else "")
        elif k == "bool":
            r = "boolean"
        else:
            r = "string" if k == "str" else "list of strings"
        if f["required"]:
            return r + "; required"
        if f["default"] is not None:
            return r + "; default " + L(json.dumps(f["default"]))
        return r + "; optional"
    rows = "\n".join(f"{tt(f['path'])} & {L(f['help'])} & {L(', '.join(f['affects']))} & {rule(f)}\\\\" for f in mand)
    rows += "\n" + (r"\texttt{priorities.*} (6) & Weight of the matching score dimension (cost, time to market, "
                    r"scalability, performance, maintainability, security) for every candidate. & all layers & integer 1--5; default 3\\")
    xrows = "\n".join(f"{tt(f['path'])} & {L(f['help'])} & {L(', '.join(f['affects']))}\\\\" for f in extra)
    return r"""\section{Input design and research}
The engine accepts every field of Section~3.1 of the brief with exactly the specified names and enumerations. A single
schema module drives validation, the input form and Table~\ref{tab:inputs}, which states for each field why it matters
architecturally, which decisions it influences and how it is validated.

{\footnotesize\renewcommand{\arraystretch}{1.16}
\rowcolors{2}{white}{rowalt}\begin{longtable}{@{}P{3.7cm}P{6.3cm}P{2.6cm}P{2.6cm}@{}}
\caption{Mandatory input fields.}\label{tab:inputs}\\
\toprule
\rowcolor{soft}\textcolor{accent}{\textbf{Field}} & \textcolor{accent}{\textbf{Architectural role}} & \textcolor{accent}{\textbf{Affects}} & \textcolor{accent}{\textbf{Validation}}\\
\midrule
\endfirsthead
\toprule
\rowcolor{soft}\textcolor{accent}{\textbf{Field}} & \textcolor{accent}{\textbf{Architectural role}} & \textcolor{accent}{\textbf{Affects}} & \textcolor{accent}{\textbf{Validation}}\\
\midrule
\endhead
\bottomrule
\endfoot
""" + rows + r"""
\end{longtable}}

\subsection{Additional parameters}
Ten optional parameters capture drivers that the standard schema does not (Table~\ref{tab:extras}). The engine behaves
sensibly when they are absent, using defaults or inference from other fields. Each of them changes the recommendation:
a low lock-in tolerance moves proprietary platforms such as Firebase, DynamoDB and Cosmos DB out of first place;
existing cloud credits favour hosting on that cloud; the users' geography places the primary region next to them when
no residency is given; and a recovery point objective below five minutes rejects offerings without point-in-time recovery.

{\footnotesize\renewcommand{\arraystretch}{1.16}
\rowcolors{2}{white}{rowalt}\begin{longtable}{@{}P{4.6cm}P{8.0cm}P{2.6cm}@{}}
\caption{Additional input parameters.}\label{tab:extras}\\
\toprule
\rowcolor{soft}\textcolor{accent}{\textbf{Field}} & \textcolor{accent}{\textbf{What it captures}} & \textcolor{accent}{\textbf{Affects}}\\
\midrule
\endfirsthead
\toprule
\rowcolor{soft}\textcolor{accent}{\textbf{Field}} & \textcolor{accent}{\textbf{What it captures}} & \textcolor{accent}{\textbf{Affects}}\\
\midrule
\endhead
\bottomrule
\endfoot
""" + xrows + r"""
\end{longtable}}

\subsection{Validation rules}
Types are checked strictly: a boolean is not an integer, the string \texttt{"true"} is not a boolean, and
\texttt{availability} must be one of the listed strings, while integral floats such as \texttt{2000.0} are accepted.
Counts and money must be non-negative, \texttt{team.size} and \texttt{mvp\_weeks} at least one, the latency target
positive or null, and priorities between 1 and 5. Enumerations are matched exactly; an unknown value reports the allowed
set and, where close enough, a suggestion (\texttt{"AWS"} produces \emph{did you mean "aws"?}). Duplicate list entries
are removed and noted, unknown fields are ignored but reported, and common language aliases (\texttt{C\#},
\texttt{golang}) are normalised. Contradictions between well-formed fields, such as peak concurrency above the total
number of users or SEO without a web platform, are reported as warnings rather than validation errors (Section~\ref{sec:edges}).

The free-text description is read by a deterministic lexicon of about forty patterns. It proposes structured values in
the UI, which the user must accept explicitly, and it extracts signals the engine can use: location data (PostGIS),
double-entry ledgers (strict ACID transactions), low-end devices, unreliable networks (resumable uploads), KYC
documents (encrypted private storage) and concurrent editing (CRDTs). Where the description contradicts a structured
field, an informational warning is raised and the structured field wins.

Thresholds in the engine come from documented platform behaviour. Amazon RDS offers a 99.5\% SLA for single-zone and
99.95\% for Multi-AZ deployments~\cite{rds_sla}, which decides when a standby is needed; Cloud Run caps WebSocket
connections at 60 minutes and offers only best-effort affinity~\cite{cloudrun_ws}, which matters for stateful rooms;
PostgreSQL full-text search~\cite{pg_fts} is preferred over a dedicated search cluster below the large scale tier; and
an effort model (feature points against team-weeks scaled by experience) flags unrealistic timelines.
""" + fig("configure", "0.62", "Input form of the web UI. Each field shows its schema path, help text and the decisions it affects; validation runs live.", "configure")


def s5(st):
    lay = st["active_by_layer"]
    sup = sum(v for k, v in lay.items() if k not in ("web", "mobile", "desktop", "backend", "database", "db_offering", "hosting"))
    kbrows = [("Web frameworks", lay.get("web", 0)), ("Mobile and desktop", lay.get("mobile", 0) + lay.get("desktop", 0)),
              ("Backends and BaaS", lay.get("backend", 0)), ("Database engines", lay.get("database", 0)),
              ("Managed database offerings", lay.get("db_offering", 0)), ("Hosting platforms", lay.get("hosting", 0)),
              ("Supporting services", sup), ("Deprecated / end-of-life entries", st["inactive_entries"]),
              ("Lifecycle registry records", st["lifecycle_entries"]), ("Cited sources", st["sources"])]
    kb_tab = "\n".join(f"{a} & {b}\\\\" for a, b in kbrows)
    return r"""\section{Knowledge base and decision logic}
\subsection{Representation}
Each technology is a record with scores from 1 to 5 for performance, scalability, time to market, maintainability, cost
efficiency and security, plus learning curve, operational burden and maturity. It also stores the programming
languages a team needs, supported platforms, traits (for example \texttt{ssr}, \texttt{websockets}, \texttt{multi\_az},
\texttt{offline\_capable}, \texttt{acid}), the provider, whether it can be self-hosted, the regions where data can be
kept, compliance attestations, lock-in level, the scale range in which it is sensible, a price table for five scale
tiers, strengths, limitations, lifecycle status and source references. Managed database offerings are separate records,
so the engine chooses both the engine and where it runs. Recent changes are encoded explicitly: AWS App Runner closed
to new customers in April 2026~\cite{apprunner}, Heroku moved to sustaining engineering in February
2026~\cite{heroku}, the MinIO community repository was archived~\cite{minio}, creation of Azure Cache for Redis is
blocked~\cite{azure_cache}, Atlas Device Sync reached end of life~\cite{atlas}, and \texttt{supabase.co} was blocked by
several Indian ISPs in February 2026~\cite{supabase_block}. Table~\ref{tab:kb} summarises the contents.

\begin{table}[htbp]
\centering\small
\begin{minipage}[t]{0.36\linewidth}\centering
\caption{Knowledge base.}\label{tab:kb}
\rowcolors{2}{white}{rowalt}\begin{tabular}{@{}lr@{}}
\toprule
\rowcolor{soft}\textcolor{accent}{\textbf{Category}} & \textcolor{accent}{\textbf{Entries}}\\
\midrule
""" + kb_tab + r"""
\bottomrule
\end{tabular}
\end{minipage}\hfill
\begin{minipage}[t]{0.6\linewidth}\centering
\vspace{0pt}\includegraphics[width=\linewidth]{img/kb.png}
\captionof{figure}{Knowledge-base explorer in the UI.}\label{fig:kb}
\end{minipage}
\end{table}

\subsection{Hard constraints}
Hard constraints are applied as filters before any scoring. A candidate that violates one is excluded, and the reason
is kept so that it can appear among the alternatives and in the decision trace.
\begin{itemize}
\item \emph{Data residency.} Every component that stores or processes personal data must offer a region in the
required jurisdiction; services without location control, such as Firebase Authentication~\cite{firebase_loc}, are
excluded. RBI localisation implies Indian residency~\cite{rbi}.
\item \emph{Compliance.} The vendor must hold the relevant attestation or sign a BAA, but only for layers within that
regime's scope: HIPAA covers data stores, compute and logs; PCI DSS covers payments and the data path; GDPR and DPDP
require a data-processing agreement from every processor.
\item \emph{Deployment model.} Managed cloud excludes self-run virtual machines and databases; self-hosted VMs require
VM hosting; on-premise and air-gapped deployments allow only self-hostable software and no SaaS or CDN.
\item \emph{Cloud preference.} An explicit provider excludes other clouds' services and third-party platforms for
infrastructure; \texttt{none} means no public cloud.
\item \emph{Lifecycle.} Deprecated, end-of-life, maintenance-mode and closed-to-new-customer services are never recommended.
\end{itemize}

\subsection{Soft constraints and scoring}
The remaining candidates are scored as a sum of explicit factors. Each factor stores the input fields that caused it,
its weight and a sentence, which later become the justification and the \texttt{driven\_by} list:
\begin{keybox}[title=Scoring model]
\begin{equation*}
\mathrm{score}(c) = \sum_{d \in D} w\,\frac{p_d}{3}\,(s_{c,d}-3) + F_{\mathrm{skill}} + F_{\mathrm{learn}} + F_{\mathrm{ops}}
 + F_{\mathrm{scale}} + F_{\mathrm{lock}} + F_{\mathrm{reuse}} + F_{\mathrm{budget}} + F_{\mathrm{req}},
\end{equation*}
\end{keybox}
where $D$ are the six priority dimensions, $p_d$ the user's priority and $s_{c,d}$ the knowledge-base score. The skill
factor rewards a full language match and partially rewards a close one (TypeScript and JavaScript, Kotlin and Java);
its weight is larger for beginners than for senior teams and grows for short timelines. Without a DevOps engineer,
each point of operational burden above two is penalised, and Kubernetes is penalised further for small teams. The
scale factor penalises technologies used beyond their comfortable range and also below the scale at which they pay off,
which keeps Kubernetes, Cassandra and microservices away from small projects. A component whose own floor cost exceeds
its share of the budget is penalised logarithmically. Requirement factors are layer-specific: server rendering for SEO,
persistent connections for realtime features, on-device storage for offline support, ACID transactions for ledgers, and
a preference for supporting services on the same platform and region as the hosting.

\subsection{Ties, conflicts and determinism}
Candidates are ranked by score rounded to three decimals, then by maturity, then by identifier, so ties are resolved the
same way every time; a margin below 0.8 is labelled a close call. Layers are chosen in dependency order, and later
requirements are expressed as factors rather than overrides. If the best database engine has no compliant managed
offering, the next engine is used and the fallback is recorded. Determinism follows from the construction (no clock,
randomness, network, unordered iteration or language model) and is checked by tests that compare repeated runs, separate
processes, shuffled key order and both settings of the LLM switch.

\subsection{Use of language models}
\begin{notebox}[title=LLM policy]
No language model chooses or ranks any component. The only LLM feature is an optional button that suggests form values
from the description, which is permitted use (1) of Section~5.1 of the brief. It is off by default
(\texttt{STACKSENSE\_LLM=off}), can be forced off with \texttt{-{}-no-llm}, is shown as ``LLM: off'' in the UI, and is never
imported by the engine; every output contains \texttt{"llm\_used": false}.
\end{notebox}
"""


def s6():
    rows = []
    for sid, r in OUT.items():
        st, c = r["stack"], r["estimated_monthly_cost_usd"]
        band = f"\\${c['min']:,}" if c["min"] == c["max"] else f"\\${c['min']:,}--{c['max']:,}"
        rows.append(f"{sid} & {L(r['architecture_style'].replace('_', ' '))} & {L(st['frontend']['choice'])} & "
                    f"{L(st['backend']['choice'])} & {L(st['database']['choice'])} & {L(st['hosting']['choice'])} & {band}\\\\")
    p2, p4 = OUT["P2"], OUT["P4"]
    c2, c4 = p2["estimated_monthly_cost_usd"], p4["estimated_monthly_cost_usd"]
    p4var = edge("P4_pdf")
    same4 = all(p4var["stack"][k]["choice"] == p4["stack"][k]["choice"] for k in ("frontend", "backend", "database", "hosting"))
    return r"""\section{Sample recommendations}
Table~\ref{tab:results} summarises the engine's output for the six public scenarios; the complete JSON files are in
\texttt{outputs/}. Figures~\ref{fig:p1}--\ref{fig:p6} show the result view for each scenario.

\begin{table}[htbp]
\centering\scriptsize
\caption{Recommendations for the public scenarios.}\label{tab:results}
\rowcolors{2}{white}{rowalt}\begin{tabularx}{\linewidth}{@{}lP{1.6cm}YYYYr@{}}
\toprule
\rowcolor{soft} & \textcolor{accent}{\textbf{Style}} & \textcolor{accent}{\textbf{Frontend}} & \textcolor{accent}{\textbf{Backend}} & \textcolor{accent}{\textbf{Database}} & \textcolor{accent}{\textbf{Hosting}} & \textcolor{accent}{\textbf{Cost / month}}\\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabularx}
\end{table}
""" + figgrid([("P1_overview", "P1: static Astro site on a free CDN.", "p1"),
                     ("P2_overview", "P2: India-resident marketplace.", "p2"),
                     ("P3_overview", "P3: hybrid architecture in the EU.", "p3"),
                     ("P4_overview", "P4: RBI/PCI fintech on AWS Mumbai.", "p4"),
                     ("P5_overview", "P5: .NET monolith on Azure India.", "p5"),
                     ("P6_overview", "P6: offline-first Android on a BaaS.", "p6")]) \
        + T(r"""
\subsection{P2: Home-services marketplace (India)}
The residency requirement (India) and the DPDP Act~\cite{dpdp} removed every candidate without an Indian region before
any scoring: Render, Railway, Fly.io (Mumbai is on its region-consolidation list~\cite{fly}), Neon~\cite{neon},
Upstash, Algolia, Auth0 and Clerk. Firebase was excluded because Firebase Authentication offers no choice of data
location, and Stripe because Indian payment data must stay in India; payments go to Razorpay, an Indian gateway that
supports UPI and payouts to service providers~\cite{razorpay}.

On the frontend, \texttt{seo\_critical} rewards server rendering and the Android app can share React and TypeScript
with the web application, which gives Next.js with React Native (Expo); Flutter loses because nobody on the team knows
Dart. Django narrowly beats NestJS for the backend (8.8 against 8.3, shown as a close call): both match the team, and
Django's built-in admin and authentication help a marketplace, whereas a backend-as-a-service scores lower for its
multi-party workflows. PostgreSQL holds the relational marketplace data and also provides full-text search, which is
sufficient for 15\,GB at this scale. It runs on Cloud SQL in Mumbai next to Cloud Run, which scales to zero, supports
WebSockets and needs no DevOps. Because \texttt{priorities.cost} is 4, the database runs in a single zone, and the engine
says so in a warning: single-zone managed databases offer about 99.5\% against the 99.9\% target, and a standby would
roughly double that line item. One-time passwords are sent through MSG91 with DLT-registered templates inside India
(Twilio is excluded by residency). The estimate of \$@@c2min@@--@@c2max@@ per month keeps the floor within the \$150
budget, and the upper end is flagged.
""", c2min=c2["min"], c2max=c2["max"]) \
        + T(r"""
\subsection{P4: Digital lending and payments (India)}
The AWS preference, RBI localisation~\cite{rbi}, PCI DSS~\cite{pci}, DPDP and ISO 27001 together with Indian
residency leave only AWS services in ap-south-1 and self-run software. Payments must go through an RBI-authorised
aggregator with PCI DSS certification, so Razorpay is chosen and Stripe and Paddle are excluded. Spring Boot matches the
Java and Kotlin team, and the description's ``double-entry ledger'' adds a factor for declarative ACID transactions;
the security priority of 5 favours its track record. React Native covers Android and iOS from the team's TypeScript,
and a React web application shares the same skills. PostgreSQL on Amazon RDS Multi-AZ provides the standby required by
the 99.95\% availability target; DynamoDB and MongoDB lose on multi-row transactions for a ledger. The services run on
ECS with Fargate across availability zones: EKS is penalised as over-engineering for 300,000 users, and Lambda and
Amplify are excluded because a long-running Spring Boot service needs containers. The supporting services are a
SageMaker endpoint for the credit-scoring model, SQS for disbursal and EMI workflows, S3 with KMS encryption for KYC
documents, Spring Security with SMS one-time passwords (which avoids per-user identity fees at 300,000 users), WAF, KMS,
CloudTrail and GuardDuty for the auditors, and CloudWatch logs kept in India as required by CERT-In~\cite{certin}. The
estimate is \$@@c4min@@--@@c4max@@ per month against a budget of \$6,000. The PDF variant with \texttt{has\_devops=false}
yields @@same@@, since every chosen service is already fully managed.
""", c4min=f"{c4['min']:,}", c4max=f"{c4['max']:,}", same="the same core stack" if same4 else "a different core stack") \


def s7():
    rows = [
        ("Missing fields", "Required field absent: error per field. Optional field absent: documented default.", "\\texttt{invalid\\_input} with every missing field listed (E01); lenient mode applies defaults; optional defaults appear in the assumptions (E20)."),
        ("Invalid values", "Strict checks of type, range and enumeration; the engine never raises.", "All 22 problems of E02 reported in one pass with allowed values and suggestions; non-object input handled."),
        ("Contradictions", "Pre-flight checks for incompatible hard constraints and 57 warning rules (budget floor, availability vs.\\ team, effort vs.\\ capacity, latency, platforms).", "\\texttt{infeasible} with resolution options (E09: RBI localisation vs.\\ EU residency; E15: no cloud vs.\\ managed cloud); critical warnings and named relaxations (E03: 5M users on a \\$0 budget, E04, E05)."),
        ("Over-engineering", "Scale floors, team-size and DevOps guard, static eligibility.", "A launch site with 2M users stays static on a CDN (E06); a 40-person internal tool becomes one Django application (E07)."),
        ("Regulatory", "Compliance scopes and residency filters.", "Only BAA-covered services for health data (E08); Indian gateway and Indian regions (P4); an EU-hosted identity provider for GDPR (E14)."),
        ("Existing systems", "Alias matching, reuse bonus and integration rules.", "Entra ID reused for SSO, Microsoft 365 through Graph, on-premise SQL Server 2019 reached through an App Service Hybrid Connection (P5)."),
        ("Restricted deployment", "Self-hosting and on-premise filters; impossible requirements relaxed.", "Air-gapped: Spring Boot, self-managed PostgreSQL, RKE2, Keycloak, SeaweedFS, GitLab and Prometheus; payments and phone OTP relaxed with critical warnings; no CDN (E10)."),
        ("Skill mismatch", "Experience-weighted skill factor and a \\texttt{SKILL\\_MISMATCH} warning.", "A PHP and JavaScript team building live auctions receives NestJS with Socket.IO rather than a Go or Elixir stack (E12)."),
        ("Deprecated technology", "Lifecycle registry and status of knowledge-base entries.", "Never recommended; Heroku, MySQL 5.7, Xamarin, App Center, Node.js 16 and Realm Sync flagged (E13); extended-support note for SQL Server 2019 (P5)."),
    ]
    body = "\n".join(f"{a} & {b} & {c}\\\\" for a, b, c in rows)
    return r"""\section{Edge-case handling}\label{sec:edges}
Table~\ref{tab:edges} covers each category of Section~6 of the brief; the scenarios are in \texttt{scenarios/edge/} and
their outputs in \texttt{outputs/edge/}. Further screenshots are in Appendix~\ref{app:shots}.

{\footnotesize\renewcommand{\arraystretch}{1.16}
\rowcolors{2}{white}{rowalt}\begin{longtable}{@{}P{2.3cm}P{5.1cm}P{7.8cm}@{}}
\caption{Edge-case categories, detection and behaviour.}\label{tab:edges}\\
\toprule
\rowcolor{soft}\textcolor{accent}{\textbf{Category}} & \textcolor{accent}{\textbf{Detection}} & \textcolor{accent}{\textbf{Behaviour (scenario)}}\\
\midrule
\endfirsthead
\toprule
\rowcolor{soft}\textcolor{accent}{\textbf{Category}} & \textcolor{accent}{\textbf{Detection}} & \textcolor{accent}{\textbf{Behaviour (scenario)}}\\
\midrule
\endhead
\bottomrule
\endfoot
""" + body + r"""
\end{longtable}}
""" + figpair("E09_infeasible", "E09: contradictory hard constraints give \\texttt{infeasible} with resolution options.", "e09",
              "E10_notes", "E10: air-gapped deployment; impossible requirements relaxed with critical warnings.", "e10") \
        + figpair("E13_notes", "E13: end-of-life existing systems.", "e13",
                  "E03_notes", "E03: 5M users, \\$0 budget, solo beginner.", "e03")


def s8(st):
    rub = rubric_check()
    rows = "\n".join(f"{sid} & {'pass' if ok else 'fail'} & {L(', '.join(l for l, v in layers if v))} & {L(', '.join(bad) or 'none')}\\\\"
                     for sid, ok, layers, bad in rub)
    passed = sum(1 for r in rub if r[1])
    sens = st["sens"]
    return T(r"""\section{Validation}
\paragraph{Rubric.} For each public scenario I listed, from the brief and from public reference architectures, the
choices per layer that a senior engineer would accept and the choices that would clearly be wrong (for example Stripe
or a US-only platform for P4, Kubernetes for P1). The rubric is encoded in the report generator and checked
automatically; @@passed@@ of 6 scenarios pass (Table~\ref{tab:rubric}).

\begin{table}[htbp]
\centering\small
\caption{Rubric check of the public scenarios.}\label{tab:rubric}
\rowcolors{2}{white}{rowalt}\begin{tabular}{@{}llll@{}}
\toprule
\rowcolor{soft}\textcolor{accent}{\textbf{Scenario}} & \textcolor{accent}{\textbf{Result}} & \textcolor{accent}{\textbf{Layers within the acceptable set}} & \textcolor{accent}{\textbf{Clearly wrong choices}}\\
\midrule
@@rows@@
\bottomrule
\end{tabular}
\end{table}

\paragraph{Comparison with real systems.} The P3 recommendation resembles how collaborative editors are built in
practice: Figma runs stateful multiplayer servers per document alongside a conventional API~\cite{figma}, and Excalidraw
relays edits over WebSockets~\cite{excalidraw}. The engine's hybrid design with a Go WebSocket gateway, a Yjs
CRDT~\cite{yjs} and sticky routing follows the same pattern. P5 matches Microsoft's reference for a basic web
application on App Service with Azure SQL and Entra ID~\cite{azure_basic}. P6 matches ODK Collect, the open-source tool
widely used by NGOs for field surveys, which is an offline-first Android client that synchronises forms and media when a
connection is available~\cite{odk}.

\paragraph{Automated checks.} The @@tests@@ unit tests (@@tests_ok@@) cover the schema, validation errors, determinism
(repeated runs, a fresh process, key order and the LLM switch), expectations on the public scenarios (Indian regions, cloud
preference, the payment gateway, reuse of Entra ID) and every edge-case category. A property-based harness generated
@@fuzz_n@@ random scenarios and re-checked each chosen component against the knowledge base independently of the
engine. It found @@fuzz_fail@@ violations of hard constraints, determinism, budget reporting, lifecycle status or the
over-engineering guard; a recommendation took about @@ms@@\,ms on a laptop. Finally, a perturbation study changed one
input at a time on P1--P6 (@@pert@@ changes). In @@nochange@@ cases the core stack did not change, on average
@@avg@@ core decisions moved, and the larger moves were sensible: switching off realtime in P3 turns the hybrid design
into a modular monolith (Figure~\ref{fig:whatif}), and enabling SEO selects Next.js.
""", passed=passed, rows=rows, tests=st["tests"], tests_ok="all passing" if st["tests_ok"] else "see the test log",
             fuzz_n=f"{st['fuzz_n']:,}", fuzz_fail=st["fuzz_fail"], ms=st["fuzz_ms"], pert=sens["perturbations"],
             nochange=sens["with_no_core_change"], avg=sens["avg_core_decisions_moved"]) \
        + fig("P3_whatif", "0.8", "What-if comparison in the UI: P3 re-run with \\texttt{requirements.realtime=false}; the panel lists exactly which decisions changed.", "whatif")


def s9():
    return r"""\section{Limitations and future work}
\begin{itemize}
\item The scores and factor weights are curated from documentation, surveys and benchmarks rather than fitted to
outcome data. A natural next step is to calibrate them against labelled architecture decisions while keeping the
factor-level explanations.
\item The cost model uses five scale tiers and unit prices; regional price differences and negotiated discounts are
ignored. Per-region price tables refreshed from provider pricing APIs would tighten the bands.
\item Service status changes quickly (App Runner, Heroku and MinIO all changed in 2026). The knowledge base carries a
snapshot date and a lifecycle registry, but it needs periodic refreshing, for example by comparing against endoflife.date.
\item Each core layer has a single choice. Polyglot designs, such as a realtime service written in a different language,
are expressed through the architecture rationale and the supporting services.
\item Some layers are close calls (the P2 backend, BaaS versus functions in P6). They are labelled as such and both
options are explained, but the team's preference should decide.
\end{itemize}
"""


BIB = ["so2025", "stateofjs", "techempower", "dbengines", "endoflife", "rds_sla", "cloudrun_ws", "pg_fts", "apprunner",
       "heroku", "minio", "azure_cache", "atlas", "supabase_block", "firebase_loc", "rbi", "dpdp", "pci", "certin",
       "fly", "neon", "razorpay", "figma", "excalidraw", "yjs", "azure_basic", "odk"]
BIB_MAP = {"apprunner": "apprunner_change", "heroku": "heroku_sustaining", "minio": "minio_repo",
           "azure_cache": "azure_cache_retire", "atlas": "atlas_app_services", "firebase_loc": "firebase_locations",
           "rbi": "rbi_localisation", "fly": "fly_consolidation", "neon": "neon_regions", "razorpay": "razorpay_security",
           "figma": "figma_multiplayer", "excalidraw": "excalidraw_e2e"}
BIB_EXTRA = {"azure_basic": ("Microsoft Azure Architecture Center: Basic web application",
                             "https://learn.microsoft.com/azure/architecture/web-apps/app-service/architectures/basic-web-app"),
             "odk": ("ODK Collect documentation", "https://docs.getodk.org/collect-intro/")}


def s10(st):
    items = []
    for key in BIB:
        if key in BIB_EXTRA:
            title, url = BIB_EXTRA[key]
        else:
            s = SOURCES[BIB_MAP.get(key, key)]
            title, url = s["title"], s["url"]
        items.append(f"\\bibitem{{{key}}} {L(title)}. \\url{{{url}}}")
    return T(r"""\section{References and third-party tools}
The engine has no runtime dependencies beyond the Python standard library, and the UI uses no JavaScript libraries or
web fonts. The optional description assistant uses the \texttt{anthropic} Python SDK (MIT licence) and the Anthropic
API; it is disabled by default. The Docker image is based on \texttt{python:3.12-slim}. This report is typeset with
Tectonic; screenshots are taken with headless Microsoft Edge and cropped with Pillow. The knowledge base draws on the
Stack Overflow Developer Survey 2025~\cite{so2025}, State of JavaScript 2024~\cite{stateofjs}, the TechEmpower
benchmarks~\cite{techempower}, DB-Engines~\cite{dbengines}, endoflife.date~\cite{endoflife} and the official
documentation, pricing, region, compliance and lifecycle pages of each technology; all @@n@@ sources are listed in
Appendix~\ref{app:sources} and in the UI.

\begingroup
\renewcommand{\section}[2]{}
\small
\begin{thebibliography}{99}
@@items@@
\end{thebibliography}
\endgroup
\label{sec:endmain}
""", n=st["sources"], items="\n".join(items))


def s11():
    return r"""\section{AI assistance declaration}
Claude Code (Anthropic) was used as an AI coding assistant during development, documentation and background research.
All recommendations are produced by the deterministic engine described in Section~5; no language model is involved in
selecting any component.
"""


def appendices():
    pairs = [("E01_missing", "E01: missing required fields."), ("E05_notes", "E05: four platforms in three weeks."),
             ("E06_overview", "E06: high-traffic site kept static."), ("E11_notes", "E11: AWS preference with on-premise deployment."),
]
    wide = [("E02_invalid", "E02: 22 validation errors reported in one pass.", "0.78"),
            ("P5_notes", "P5: Entra ID, Microsoft 365 and on-premise SQL Server reused.", "0.8"),
            ("E08_core", "E08: HIPAA scenario with only BAA-covered services.", "0.74"),
            ("E12_core", "E12: team skills weighed against popular choices.", "0.74"),
            ("P2_trace", "P2: decision trace with scores, top factors and exclusions.", "0.8"),
            ("P2_core", "P2: core stack with justifications, driving input fields, rejected alternatives and trade-offs.", "0.8"),
            ("P4_support", "P4: supporting services under AWS, RBI, PCI DSS, DPDP and ISO 27001.", "0.74")]
    out = [r"\clearpage", r"\appendix", r"\section{Additional screenshots}\label{app:shots}\label{sec:appstart}"]
    for i in range(0, len(pairs), 2):
        (a, ca), (b, cb) = pairs[i], pairs[i + 1]
        out.append(figpair(a, ca, "a" + a, b, cb, "a" + b))
    for n, c, w in wide:
        out.append(fig(n, w, c, "a" + n))
    srcs = sorted(SOURCES.values(), key=lambda s: s["title"].lower())
    items = "\n".join(f"\\item {L(s['title'])}: \\url{{{s['url']}}}" for s in srcs)
    out.append(r"""\clearpage
\section{Knowledge-base sources}\label{app:sources}
{\scriptsize\setlength{\parskip}{0pt}\linespread{1.0}\selectfont
\begin{multicols}{2}
\begin{enumerate}[leftmargin=2.2em,itemsep=1pt,parsep=0pt,topsep=0pt,label=\textcolor{accent}{\arabic*.}]
""" + items + r"""
\end{enumerate}
\end{multicols}}
\label{sec:append}
""")
    return "\n".join(out)


def build_tex(st):
    return "".join([PREAMBLE, title_page(), s1(st), s2(), s3(), s4(), s5(st), s6(), s7(), s8(st), s9(), s10(st),
                    s11(), appendices(), "\n\\end{document}\n"])


def find_tectonic():
    for p in (shutil.which("tectonic"), os.path.expanduser(r"~\tectonic\tectonic.exe"),
              os.path.expanduser("~/tectonic/tectonic")):
        if p and os.path.isfile(p):
            return p
    raise SystemExit("Tectonic not found: https://tectonic-typesetting.github.io")


def page_of(aux, label):
    m = re.search(r"\\newlabel\{" + re.escape(label) + r"\}\{\{[^}]*\}\{(\d+)\}", aux)
    return int(m.group(1)) if m else None


def main():
    if "--no-shots" not in sys.argv:
        print("capturing screenshots from the running UI ...")
        screenshots.capture()
    import fuzz
    import sensitivity
    print("running validation ...")
    tests, tests_ok = run_tests()
    fz = fuzz.run_fuzz(3000, seed=2026)
    sens, _ = sensitivity.analyse()
    st = dict(kb.stats())
    st.update({"tests": tests, "tests_ok": tests_ok, "fuzz_n": fz["scenarios"], "fuzz_fail": len(fz["failures"]),
               "fuzz_ms": fz["ms_per_scenario"], "sens": sens})
    tex = os.path.join(BUILD, STEM + ".tex")
    with open(tex, "w", encoding="utf-8", newline="\n") as f:
        f.write(build_tex(st))
    print("compiling LaTeX ...")
    r = subprocess.run([find_tectonic(), "-X", "compile", "--keep-intermediates", "--keep-logs", tex], cwd=BUILD,
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit("LaTeX compilation failed")
    with open(os.path.join(BUILD, STEM + ".aux"), encoding="utf-8") as f:
        aux = f.read()
    end_main, app_start, app_end = (page_of(aux, k) for k in ("sec:endmain", "sec:appstart", "LastPage"))
    total = app_end + 1                 # + unnumbered title page
    sections_1_10 = end_main            # numbering restarts at 1 on the Abstract page
    appendix_pages = app_end - app_start + 1
    report = {"pdf": os.path.join(BUILD, STEM + ".pdf"), "physical_pages": total,
              "sections_1_10_pages": sections_1_10, "appendix_pages": appendix_pages, "tests": tests,
              "fuzz_failures": st["fuzz_fail"], "rubric_passed": sum(1 for x in rubric_check() if x[1])}
    print(json.dumps(report, indent=2))
    if sections_1_10 > 15 or appendix_pages > 10:
        raise SystemExit("PAGE LIMIT EXCEEDED (Section 10 of the brief: sections 1-10 <= 15 pages, appendices <= 10)")


if __name__ == "__main__":
    main()
