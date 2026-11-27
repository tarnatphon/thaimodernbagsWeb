#!/usr/bin/env python3
"""Local-only SEO drafting helper that sends requests to a local Ollama instance."""
from __future__ import annotations

import html.parser
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = Path(__file__).with_name("seo_assistant.html")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
MAX_BODY = 16_000


class TextOnly(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "svg", "head"}:
            self.skip += 1
        if tag in {"p", "h1", "h2", "h3", "li", "section", "br"} and not self.skip:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg", "head"} and self.skip:
            self.skip -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip:
            value = " ".join(data.split())
            if value:
                self.parts.append(value)


def read_site_copy() -> str:
    page = ROOT / "index.html"
    parser = TextOnly()
    parser.feed(page.read_text(encoding="utf-8"))
    return " ".join(parser.parts)[:7000]


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalSEOHelper/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        print("[seo-helper] " + fmt % args)

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _is_local_request(self) -> bool:
        host = self.headers.get("Host", "").split(":", 1)[0].strip("[]").lower()
        if host not in {"localhost", "127.0.0.1", "::1"}:
            return False
        origin = self.headers.get("Origin")
        if origin:
            return origin in {"http://localhost:8765", "http://127.0.0.1:8765", "http://[::1]:8765"}
        return True

    def do_GET(self) -> None:
        if not self._is_local_request():
            self._send_json(403, {"error": "This helper is available only from this computer."})
            return
        if self.path not in {"/", "/assistant"}:
            self._send_json(404, {"error": "Not found"})
            return
        body = DASHBOARD.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if not self._is_local_request():
            self._send_json(403, {"error": "This helper is available only from this computer."})
            return
        if self.path != "/api/draft":
            self._send_json(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > MAX_BODY:
                self._send_json(413, {"error": "Please keep the project notes under 16 KB."})
                return
            data = json.loads(self.rfile.read(length))
            business_facts = str(data.get("businessFacts", "")).strip()
            goal = str(data.get("goal", "")).strip()
            if len(business_facts) < 20:
                self._send_json(400, {"error": "Add a few real business details first so the suggestions are specific."})
                return
            if len(business_facts) > 10_000 or len(goal) > 500:
                self._send_json(400, {"error": "Please shorten the notes and try again."})
                return
        except (ValueError, TypeError, json.JSONDecodeError):
            self._send_json(400, {"error": "The request could not be read. Please try again."})
            return

        system_prompt = (
            "You are a careful SEO editor for a small bag design and production business. "
            "Create useful, people-first recommendations using only the supplied business facts and existing page copy. "
            "Never invent experience, awards, certifications, customer results, materials, manufacturing processes, "
            "locations served, prices, addresses, or contact details. If something important is unknown, ask a clear "
            "question instead of filling it in. Do not promise rankings or keyword positions. Apply E-E-A-T by recommending "
            "ways real people can demonstrate first-hand experience and trust; do not claim E-E-A-T is a score. "
            "Return only valid JSON with these keys: metaTitle (string, aim for 50-60 characters), "
            "metaDescription (string, aim for 140-160 characters), primaryTopic (string), "
            "pageImprovements (array of 3 objects with title and reason), eeatActions (array of 4 practical actions), "
            "factsToVerify (array of questions for the owner), contentIdeas (array of 3 ideas grounded in first-hand experience), "
            "structuredData (array of objects with type and reason; recommend suitable schema types but do not output fabricated schema values). "
            "Write in clear, natural English. Avoid keyword stuffing and generic filler."
        )
        user_prompt = (
            f"Owner-provided business details (treat as unverified notes until the owner confirms them):\n{business_facts}\n\n"
            f"SEO/content goal:\n{goal or 'Improve the existing home page for relevant searchers.'}\n\n"
            f"Current website copy:\n{read_site_copy()}"
        )
        request_body = json.dumps({
            "model": OLLAMA_MODEL,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }).encode("utf-8")
        request = Request(
            f"{OLLAMA_URL}/api/chat",
            data=request_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=180) as response:
                ollama_data = json.loads(response.read().decode("utf-8"))
            content = ollama_data.get("message", {}).get("content", "")
            result = json.loads(content)
            self._send_json(200, {"result": result, "model": OLLAMA_MODEL})
        except HTTPError as exc:
            detail = exc.read(1200).decode("utf-8", errors="replace")
            self._send_json(502, {"error": f"Ollama returned an error ({exc.code}). Is the model installed? {detail[:500]}"})
        except (URLError, TimeoutError) as exc:
            self._send_json(502, {"error": f"Could not reach Ollama at {OLLAMA_URL}. Start Ollama and try again. Details: {exc}"})
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            self._send_json(502, {"error": f"Ollama did not return valid JSON. Try again or choose another model. Details: {exc}"})


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("Thai Modern Bags SEO helper is local-only: http://127.0.0.1:8765")
    print(f"Ollama endpoint: {OLLAMA_URL} | model: {OLLAMA_MODEL}")
    print("Press Ctrl+C to stop. This tool drafts suggestions; it never publishes changes.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local SEO helper.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
