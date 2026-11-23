"""Collect public administrative sources; never promotes pending evidence to a release.

HTML extraction uses the standard library. PDF extraction uses project's pypdf.
Run: .venv/Scripts/python.exe scripts/collect_sources.py
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/complementares"
MANIFEST = ROOT / "data/manifests/fontes-complementares.json"
MS = "https://www.gov.br/saude/pt-br/"
DF = "https://www.saude.df.gov.br/"
CEAF = MS + "composicao/sectics/daf/ceaf"
SOURCES = [
    (
        "C01",
        "Farmácia Popular: acesso e representação",
        MS + "composicao/sectics/farmacia-popular",
        "F05",
    ),
    (
        "C02",
        "Farmácias das Unidades Básicas de Saúde",
        DF + "farmacias-unidade-basica-de-saude/",
        "F06",
    ),
    ("C03", "Farmácias da atenção secundária", DF + "farmacias-atencao-secundaria/", "F07"),
    ("C04", "Componente especializado no DF", DF + "componente-especializado/", "F08"),
    ("C05", "CEAF: telecuidado farmacêutico", CEAF + "/telecuidado-farmaceutico", None),
    (
        "C06",
        "Farmácias ambulatoriais: orientações de acesso",
        "https://info.saude.df.gov.br/saude-do-cidadao/painel-infosaude-farmacias-ambulatoriais/",
        "F14",
    ),
    (
        "C07",
        "Farmácias de alto custo: cadastro e retirada",
        "https://info.saude.df.gov.br/saude-do-cidadao/painel-infosaude-farmacias-de-alto-custo/",
        "F14",
    ),
    ("C08", "CEAF: etapas para acesso aos medicamentos", CEAF, None),
    ("C09", "CEAF: perguntas frequentes", CEAF + "/faq", None),
    (
        "C10",
        "Laudo para solicitação, avaliação e autorização de medicamentos (LME)",
        MS + "composicao/sectics/daf/publicacoes/lme.pdf",
        None,
    ),
    ("C11", "CEAF: da incorporação à disponibilização", CEAF + "/inclusao-de-medicamentos", None),
    ("C12", "CEAF: regulamentação e financiamento", CEAF + "/regulamentacao-e-financiamento", None),
    (
        "C13",
        "Componente Básico da Assistência Farmacêutica",
        MS + "composicao/sectics/daf/cbaf",
        None,
    ),
    (
        "C14",
        "Componente Estratégico da Assistência Farmacêutica",
        MS + "composicao/sectics/daf/cesaf",
        None,
    ),
    (
        "C15",
        "Medicamentos da atenção básica e estratégicos: consulta ao elenco",
        MS + "acesso-a-informacao/faq/assistencia-farmaceutica/quais-sao-os-medicamentos-da",
        None,
    ),
    (
        "C16",
        "Portaria 13/2020: formulário LME e instruções de preenchimento",
        "https://bvsms.saude.gov.br/bvs/saudelegis/gm/2020/prt0013_08_01_2020.html",
        None,
    ),
    (
        "C17",
        "Portaria GM/MS 12.091/2026: regras do Farmácia Popular",
        "https://bvsms.saude.gov.br/bvs/saudelegis/gm/2026/prt12091_24_09_2026_rep.html",
        None,
    ),
]
HOSTS = {
    "www.gov.br",
    "www.saude.df.gov.br",
    "saude.df.gov.br",
    "info.saude.df.gov.br",
    "bvsms.saude.gov.br",
}
MAX_BYTES = 25 * 1024 * 1024


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_url(url: str, resolve: bool = True) -> None:
    p = urlsplit(url)
    if (
        p.scheme != "https"
        or p.hostname not in HOSTS
        or p.username
        or p.password
        or p.port not in (None, 443)
    ):
        raise ValueError("URL outside official HTTPS allowlist")
    if p.hostname == "www.gov.br" and not p.path.startswith("/saude/"):
        raise ValueError("Only Ministério da Saúde paths allowed on gov.br")
    if resolve:
        addresses = socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError("Non-public destination")


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url: str, timeout: float = 25, retries: int = 2):
    for attempt in range(retries + 1):
        try:
            safe_url(url)
            request = Request(
                url,
                headers={
                    "User-Agent": "SUS-Administrative-Research/1.0",
                    "Accept-Encoding": "identity",
                },
            )
            with build_opener(SafeRedirect()).open(request, timeout=timeout) as response:
                safe_url(response.url)
                body = response.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    raise ValueError("Response exceeds size limit")
                return body, response.url, dict(response.headers), response.status
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            if isinstance(error, HTTPError) and error.code not in (408, 429, 500, 502, 503, 504):
                raise
            if attempt == retries:
                raise
            time.sleep(min(2**attempt, 4))


class Node:
    def __init__(self, tag="root", attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def nodes(node):
    yield node
    for child in node.children:
        if isinstance(child, Node):
            yield from nodes(child)


def render(node):
    if isinstance(node, str):
        return node
    if node.tag in {"script", "style", "nav", "footer", "noscript", "svg", "iframe", "form"}:
        return ""
    text = "".join(render(child) for child in node.children)
    return (
        "\n" + text + "\n"
        if node.tag in {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "br", "section"}
        else text + (" | " if node.tag in {"td", "th"} else "")
    )


def clean(text):
    return "\n".join(
        line for raw in text.splitlines() if (line := re.sub(r"\s+", " ", raw).strip())
    )


def extract_html(body: bytes, content_type: str):
    match = re.search(r"charset=[\"']?([\w-]+)", content_type, re.I)
    if not match:
        match = re.search(
            r"charset=[\"']?([\w-]+)", body[:8192].decode("ascii", errors="ignore"), re.I
        )
    encoding = match.group(1) if match else "utf-8"
    html = body.decode(encoding, errors="replace")
    doc = Document()
    doc.feed(html)
    all_nodes = list(nodes(doc.root))
    selected = []
    selector = ""
    for key, value in [
        ("id", "content-core"),
        ("id", "content"),
        ("class", "journal-content-article"),
        ("class", "entry-content"),
        ("tag", "article"),
        ("tag", "body"),
    ]:
        selected = [
            n
            for n in all_nodes
            if (n.tag == value if key == "tag" else value in (n.attrs.get(key) or "").split())
        ]
        selected = [n for n in selected if len(clean(render(n))) >= 100]
        if selected:
            selector = f"{key}={value}"
            break
    if not selected:
        raise ValueError("No document content container")
    text = "\n\n".join(dict.fromkeys(clean(render(n)) for n in selected))
    text = re.sub(r"^Menu\nVoltar\n[^\n]*\n", "", text)
    for footer in [
        "Ouvidoria-Geral do SUS\n",
        "Membro da Vaccine Safety Net",
        "Compartilhe:",
        "Compartilhar:",
        "Secretaria de Saúde do Distrito Federal\nDesenvolvido",
        "Saúde\nLegis - Sistema",
    ]:
        text = text.split(footer)[0].strip()
    text = re.sub(r"\nVoltar$", "", text)
    title = next((clean(render(n)) for n in all_nodes if n.tag == "title"), "")
    dates = {}
    for n in all_nodes:
        if n.tag == "meta":
            name = n.attrs.get("property") or n.attrs.get("name") or ""
            if name.lower() in {
                "article:published_time",
                "article:modified_time",
                "date",
                "dcterms.created",
                "dcterms.modified",
            }:
                dates[name] = n.attrs.get("content")
    # Preserve explicit date statements as evidence without guessing publication/validity.
    date_labels = re.findall(
        r"(?:Publicado em|Atualizado em|Publicação|Atualização)[^<>\n]{0,100}", html, re.I
    )
    return text, {
        "html_title": title,
        "extractor": "stdlib.HTMLParser/" + selector,
        "date_metadata": dates,
        "date_labels": date_labels[:10],
    }


def split_chunks(text, limit=1600):
    start = 0
    while start < len(text):
        end = min(start + limit, len(text))
        if end < len(text):
            boundary = text.rfind("\n", start + limit // 2, end)
            if boundary < 0:
                boundary = text.rfind(" ", start + limit // 2, end)
            if boundary > start:
                end = boundary + 1
        yield start, end, text[start:end]
        start = end


def immutable_write(path: Path, body: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != body:
            raise ValueError(f"Refusing to overwrite snapshot: {path}")
    else:
        path.write_bytes(body)


def collect(spec, timeout, retries):
    source_id, title, url, catalog = spec
    record = {
        "source_id": source_id,
        "title": title,
        "source_url": url,
        "url": url,
        "catalog_reference": catalog,
        "review_status": "pending",
        "publication_date": None,
        "valid_from": None,
        "territory": "DF" if ".df.gov.br" in url else "Brasil",
        "publisher": "SES-DF" if ".df.gov.br" in url else "Ministério da Saúde",
        "attempted_at_utc": datetime.now(UTC).isoformat(),
        "status": "failed",
    }
    try:
        body, final, headers, status = fetch(url, timeout, retries)
        headers = {k.lower(): v for k, v in headers.items()}
        sha = digest(body)
        pdf = body.startswith(b"%PDF-")
        if pdf:
            from pypdf import PdfReader

            pages = [
                (i + 1, clean(p.extract_text() or ""))
                for i, p in enumerate(PdfReader(BytesIO(body)).pages)
            ]
            extra = {"extractor": "pypdf", "pages": len(pages)}
        else:
            if "html" not in headers.get("content-type", ""):
                raise ValueError("Expected HTML or PDF")
            text, extra = extract_html(body, headers.get("content-type", ""))
            pages = [(None, text)]
        text = "\n\n".join(t for _, t in pages)
        if len(text) < 180 or not re.search(
            r"medicamento|farm[aá]c|assist[eê]ncia farmac", text, re.I
        ):
            raise ValueError("Insufficient meaningful medication administrative text")
        if any(
            x in text.lower() for x in ["access denied", "verify you are human", "just a moment..."]
        ):
            raise ValueError("Challenge page is not a source")
        text_sha = digest(text.encode())
        stem = f"{source_id}-{sha[:16]}"
        original = RAW / (stem + (".pdf" if pdf else ".html"))
        text_path = RAW / f"{stem}-{text_sha[:12]}.txt"
        immutable_write(original, body)
        immutable_write(text_path, text.encode())
        now = datetime.now(UTC).isoformat()
        record.update(extra)
        record.update(
            status="downloaded",
            collected_at_utc=now,
            final_url=final,
            sha256=sha,
            bytes=len(body),
            http_status=status,
            content_type=headers.get("content-type"),
            http_last_modified=headers.get("last-modified"),
            etag=headers.get("etag"),
            path=original.relative_to(ROOT / "data").as_posix(),
            text_path=text_path.relative_to(ROOT / "data").as_posix(),
            text_sha256=text_sha,
            version=f"snapshot {now[:10]} sha256:{sha[:16]}",
            validation="Snapshot and text extracted; applicability, currency and rights pending",
        )
        chunks = []
        for page, page_text in pages:
            for start, end, part in split_chunks(page_text):
                section = f"page:{page or 'html'}:chars:{start}-{end}"
                chunks.append(
                    {
                        "evidence_id": "ev-"
                        + digest(f"{source_id}|{sha}|{text_sha}|{section}".encode())[:24],
                        "text": part,
                        "review_status": "pending",
                        "territory": record["territory"],
                        "topic": "administrative_source_pending_review",
                        "source": {
                            "source_id": source_id,
                            "url": url,
                            "version": record["version"],
                            "sha256": sha,
                            "page": page,
                            "section": section,
                        },
                        "text_path": record["text_path"],
                    }
                )
        record["chunk_count"] = len(chunks)
        return record, chunks
    except Exception as error:
        record["error"] = f"{type(error).__name__}: {error}"
        return record, []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=25)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.timeout <= 0 or not 0 <= args.retries <= 5 or not 1 <= args.workers <= 8:
        parser.error("Require positive timeout, retries 0..5 and workers 1..8")
    previous = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    old = {s["source_id"]: s for s in previous.get("sources", [])}
    old_chunks_path = RAW / "chunks.jsonl"
    old_chunks = (
        [json.loads(line) for line in old_chunks_path.read_text(encoding="utf-8").splitlines()]
        if old_chunks_path.exists()
        else []
    )
    records, chunks, seen = [], [], set()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda spec: collect(spec, args.timeout, args.retries), SOURCES))
    for record, evidence in results:
        if record["status"] == "downloaded":
            if record["text_sha256"] in seen:
                record["status"] = "duplicate"
                evidence = []
            seen.add(record["text_sha256"])
        if (
            record["status"] == "failed"
            and old.get(record["source_id"], {}).get("status") == "downloaded"
        ):
            failure = record
            record = dict(old[record["source_id"]])
            record["last_failed_attempt"] = failure
            evidence = [c for c in old_chunks if c["source"]["source_id"] == record["source_id"]]
        records.append(record)
        chunks.extend(evidence)
        print(
            record["source_id"],
            record["status"],
            record.get("chunk_count", 0),
            record.get("error", ""),
            flush=True,
        )
    manifest = {
        "schema_version": 1,
        "scope": "17 additional snapshots; pending review, not curated or published",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "path_base": "data/",
        "dependencies": {
            "html": "Python standard library html.parser",
            "pdf": "pypdf>=6,<7 (existing project dependency)",
        },
        "chunks_path": "raw/complementares/chunks.jsonl",
        "sources": records,
    }
    manifest_body = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    chunk_body = "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in chunks).encode()
    run_id = digest(manifest_body)[:16]
    immutable_write(RAW / "runs" / f"{run_id}-manifest.json", manifest_body)
    immutable_write(RAW / "runs" / f"{run_id}-chunks.jsonl", chunk_body)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_bytes(manifest_body)
    (RAW / "chunks.jsonl").write_bytes(chunk_body)
    return (
        0
        if all(r["status"] == "downloaded" and not r.get("last_failed_attempt") for r in records)
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
