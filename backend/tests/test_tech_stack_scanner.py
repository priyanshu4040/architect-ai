"""Tests for deterministic tech stack scanner."""

import json
import os
import tempfile
import unittest

from backend.app.analyzers.tech_stack_scanner import scan_tech_stack, validate_source_project


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class TechStackScannerTests(unittest.TestCase):
    def test_react_vite_project(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            _write(
                os.path.join(td, "package.json"),
                json.dumps({
                    "dependencies": {"react": "^18", "vite": "^5"},
                    "devDependencies": {},
                }),
            )
            _write(os.path.join(td, "src", "App.tsx"), "export default function App() { return null; }\n")
            _write(os.path.join(td, "vite.config.ts"), "export default {}\n")
            r = scan_tech_stack(td)
            self.assertTrue(r.get("valid"))
            self.assertIn("React", r.get("frameworks", []))
            self.assertIn("Vite", r.get("build_tools", []))
            self.assertIn("React", r.get("evidence", {}))

    def test_spring_boot_maven(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            _write(
                os.path.join(td, "pom.xml"),
                "<project><dependencies><dependency>spring-boot-starter-web</dependency>"
                "<dependency>mysql-connector-java</dependency></dependencies></project>",
            )
            _write(os.path.join(td, "src", "main", "java", "App.java"), "public class App {}\n")
            r = scan_tech_stack(td)
            self.assertIn("Spring Boot", r.get("frameworks", []))
            self.assertIn("MySQL", r.get("databases", []))

    def test_fastapi_python(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            _write(os.path.join(td, "requirements.txt"), "fastapi\nuvicorn\npsycopg2\n")
            _write(os.path.join(td, "main.py"), "from fastapi import FastAPI\napp = FastAPI()\n")
            r = scan_tech_stack(td)
            self.assertIn("FastAPI", r.get("frameworks", []))
            self.assertIn("PostgreSQL", r.get("databases", []))

    def test_fullstack_react_fastapi(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            _write(
                os.path.join(td, "frontend", "package.json"),
                json.dumps({"dependencies": {"react": "^18", "axios": "^1"}}),
            )
            _write(os.path.join(td, "frontend", "src", "main.tsx"), "import React from 'react'\n")
            _write(os.path.join(td, "backend", "requirements.txt"), "fastapi\n")
            _write(os.path.join(td, "backend", "main.py"), "from fastapi import FastAPI\n")
            r = scan_tech_stack(td)
            self.assertIn("React", r.get("frameworks", []))
            self.assertIn("FastAPI", r.get("frameworks", []))
            self.assertIn("Axios", r.get("libraries", []))

    def test_dockerized(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            _write(os.path.join(td, "Dockerfile"), "FROM python:3.11\n")
            _write(os.path.join(td, "docker-compose.yml"), "services:\n  api:\n    build: .\n")
            _write(os.path.join(td, "requirements.txt"), "flask\n")
            _write(os.path.join(td, "app.py"), "from flask import Flask\n")
            r = scan_tech_stack(td)
            self.assertIn("Docker", r.get("deployment", []))
            self.assertIn("Flask", r.get("frameworks", []))

    def test_no_source_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            _write(os.path.join(td, "README.md"), "# docs only\n")
            r = scan_tech_stack(td)
            self.assertFalse(r.get("valid"))
            ok, msg = validate_source_project(r)
            self.assertFalse(ok)
            self.assertIn("valid source-code", msg.lower())

    def test_language_percentages(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            for i in range(3):
                _write(os.path.join(td, f"a{i}.py"), "x = 1\n")
            for i in range(2):
                _write(os.path.join(td, f"b{i}.js"), "console.log(1)\n")
            r = scan_tech_stack(td)
            pcts = r.get("language_percentages", {})
            self.assertGreater(pcts.get("Python", 0), pcts.get("JavaScript", 0))


if __name__ == "__main__":
    unittest.main()
