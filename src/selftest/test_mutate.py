"""Selftests de ``tools/mutate.py`` (perfil python-unittest).

Comprueban dos garantías que sostienen el bucle de reparación:

* el mutador restaura el fuente **y su mtime** (si no, `harness.py` cree
  que el TDD abrió una ronda nueva y el veredicto del judge caduca);
* el mutador rechaza archivos de tests (mutar la suite no prueba nada).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SELFTEST_DIR = Path(__file__).resolve().parent
KIT_ROOT = SELFTEST_DIR.parent
MUTATE = KIT_ROOT / "profiles" / "python-unittest" / "tools" / "mutate.py"
PY = sys.executable

SOURCE = '''"""Módulo de juguete para la prueba de mutación."""


def add(a: int, b: int) -> int:
    return a + b
'''

TEST = '''import unittest

from src.foo import add


class TestAdd(unittest.TestCase):
    def test_adds(self) -> None:
        self.assertEqual(add(2, 3), 5)

    def test_identity(self) -> None:
        self.assertEqual(add(0, 0), 0)
'''

FIXED_MTIME_NS = 1_700_000_000_000_000_000


class MutateTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "project"
        (self.root / "src").mkdir(parents=True)
        (self.root / "tests").mkdir()
        (self.root / "src" / "__init__.py").write_text("", encoding="utf-8")
        (self.root / "tests" / "__init__.py").write_text("", encoding="utf-8")
        self.source = self.root / "src" / "foo.py"
        self.source.write_text(SOURCE, encoding="utf-8")
        (self.root / "tests" / "test_foo.py").write_text(TEST, encoding="utf-8")
        os.utime(self.source, ns=(FIXED_MTIME_NS, FIXED_MTIME_NS))

    def mutate(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [PY, str(MUTATE), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
        )

    def test_restores_the_original_content(self) -> None:
        result = self.mutate("src/foo.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.source.read_text(encoding="utf-8"), SOURCE)

    def test_restores_the_original_mtime(self) -> None:
        result = self.mutate("src/foo.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.source.stat().st_mtime_ns, FIXED_MTIME_NS)

    def test_rejects_a_file_under_tests(self) -> None:
        result = self.mutate("tests/test_foo.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("tests", (result.stdout + result.stderr).lower())

    def test_rejects_a_test_prefixed_filename(self) -> None:
        helper = self.root / "src" / "test_helpers.py"
        helper.write_text("VALUE = 1\n", encoding="utf-8")
        result = self.mutate("src/test_helpers.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_a_green_suite_is_required_before_mutating(self) -> None:
        (self.root / "tests" / "test_foo.py").write_text(
            "import unittest\n\n\nclass T(unittest.TestCase):\n"
            "    def test_fails(self) -> None:\n        self.fail('rojo')\n",
            encoding="utf-8",
        )
        result = self.mutate("src/foo.py")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("roja", (result.stdout + result.stderr).lower())


if __name__ == "__main__":
    unittest.main()
