"""Student startup controls use synthetic values, vendor fakes and no providers."""
import io
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import setup_environment
from premier_demo import startup
from premier_demo.contract import MissingContractInput, VendorChanged


class DoctorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "uv.lock").write_text('[[package]]\nname = "rasa-pro"\nversion = "3.21.0.dev5"\n')
        self.values = {name: "private-synthetic-value-" + name for name in startup.KEYS}
        self.output = io.StringIO()

    def call(self, environ=None, vendor=None, installed=None):
        with patch("socket.create_connection", side_effect=AssertionError("network forbidden")):
            return startup.doctor(self.root, self.values if environ is None else environ,
                                  self.output, vendor or (lambda _: False),
                                  installed or (lambda _: "3.21.0.dev5"))

    def test_missing_names_explain_acquisition_without_creating_state(self):
        self.assertEqual(self.call(environ={}), 1)
        text = self.output.getvalue()
        for name in startup.KEYS:
            self.assertIn(name + ": MISSING", text)
        for address in ("https://github.com/settings/codespaces", "https://rasa.com/developer-edition",
                        "https://platform.openai.com/api-keys", "https://console.deepgram.com/"):
            self.assertIn(address, text)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["uv.lock"])

    def test_present_names_and_locked_runtime_pass_without_exposing_values(self):
        self.assertEqual(self.call(), 0)
        for value in self.values.values():
            self.assertNotIn(value, self.output.getvalue())
        self.assertIn("value not checked with provider", self.output.getvalue())

    def test_missing_vendor_does_not_expose_exception_content(self):
        vendor = Mock(side_effect=MissingContractInput("private-file-content"))
        self.assertEqual(self.call(vendor=vendor), 1)
        text = self.output.getvalue()
        self.assertIn("BankingHub_Premier_api_specs.zip", text)
        self.assertIn("https://developer.fiserv.com/", text)
        self.assertIn("MissingContractInput", text)
        self.assertNotIn("private-file-content", text)

    def test_compatible_newer_vendor_is_accepted(self):
        self.assertEqual(self.call(vendor=lambda _: True), 0)
        self.assertIn("COMPATIBLE NEWER FILE", self.output.getvalue())

    def test_changed_operation_is_refused_without_leaking_vendor_content(self):
        self.assertEqual(self.call(vendor=Mock(side_effect=VendorChanged(["private-schema-value"]))), 1)
        self.assertIn("VendorChanged", self.output.getvalue())
        self.assertNotIn("private-schema-value", self.output.getvalue())

    def test_runtime_must_match_selected_lock_instead_of_a_hardcoded_version(self):
        (self.root / "uv.lock").write_text('[[package]]\nname = "rasa-pro"\nversion = "3.21.4"\n')
        self.assertEqual(self.call(installed=lambda _: "3.21.4"), 0)
        self.output = io.StringIO()
        self.assertEqual(self.call(installed=lambda _: "3.21.0.dev5"), 1)
        self.assertIn("Run make setup", self.output.getvalue())

    def test_vendor_check_uses_selected_folder_without_creating_state(self):
        contract = Mock(newer_archive=True, newer_files=False)
        with patch("premier_demo.contract.PremierContract.from_path", return_value=contract) as load:
            self.assertTrue(startup.check_vendor(self.root))
            self.assertEqual(load.call_args.args[0], self.root / "vendor-inputs/BankingHub_Premier_api_specs.zip")
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["uv.lock"])

    def test_safe_error_allowlist_never_prints_provider_error_or_dynamic_type_name(self):
        error = type("SecretTokenClass", (Exception,), {})("private-token-url")
        hint = startup.failure_hint(error)
        self.assertIn("ProviderError", hint)
        self.assertNotIn("SecretTokenClass", hint)
        self.assertNotIn("private-token-url", hint)
        self.assertIn("uncertain result", hint)


class SetupTests(unittest.TestCase):
    def test_two_setups_keep_existing_environment_and_journal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            env = root / ".venv"
            (env / "bin").mkdir(parents=True)
            (env / "bin/python").write_text("synthetic executable")
            (env / "pyvenv.cfg").write_text("version_info = 3.12.11.final.0\n")
            (root / "journal.sqlite3").write_bytes(b"private-journal-fixture")
            inode = env.stat().st_ino
            runner = Mock()
            setup_environment.ensure(root, runner)
            setup_environment.ensure(root, runner)
            self.assertEqual(runner.call_count, 2)
            self.assertEqual(env.stat().st_ino, inode)
            self.assertEqual((root / "journal.sqlite3").read_bytes(), b"private-journal-fixture")
            self.assertEqual(runner.call_args.args[0], ["uv", "sync", "--locked", "--python", "3.12", "--project", str(root)])

    def test_incomplete_or_different_python_environment_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".venv/bin").mkdir(parents=True)
            (root / ".venv/bin/python").write_text("synthetic executable")
            for config in (None, "version = 3.13.0\n"):
                if config:
                    (root / ".venv/pyvenv.cfg").write_text(config)
                runner = Mock()
                with self.assertRaises(ValueError):
                    setup_environment.ensure(root, runner)
                runner.assert_not_called()
                self.assertTrue((root / ".venv/bin/python").is_file())

    def test_symlink_environment_is_not_modified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "elsewhere").mkdir()
            (root / ".venv").symlink_to(root / "elsewhere", target_is_directory=True)
            runner = Mock()
            with self.assertRaises(ValueError):
                setup_environment.ensure(root, runner)
            runner.assert_not_called()
            self.assertTrue((root / ".venv").is_symlink())


class MakeBoundaryTests(unittest.TestCase):
    def project(self, root):
        source = Path(__file__).resolve().parents[1]
        for name in ('Makefile', 'setup_environment.py'):
            (root / name).write_bytes((source / name).read_bytes())

    def test_default_is_help_and_missing_environment_doctor_creates_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.project(root)
            before = sorted(p.name for p in root.iterdir())
            result = subprocess.run(['make'], cwd=root, capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('make doctor', result.stdout)
            result = subprocess.run(['make', 'doctor'], cwd=root, capture_output=True, text=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('make setup', result.stdout)
            self.assertFalse((root / '.venv').exists())
            self.assertEqual(sorted(p.name for p in root.iterdir()), before)

    def test_checked_environment_doctor_failure_prevents_launch_without_uv(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.project(root)
            calls = root / 'calls'
            (root / '.venv/bin').mkdir(parents=True)
            (root / '.venv/pyvenv.cfg').write_text('version = 3.12.11\n')
            python = root / '.venv/bin/python'
            python.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$STARTUP_CALLS"\nexit 1\n')
            python.chmod(0o755)
            uv = root / 'uv'
            uv.write_text('#!/bin/sh\necho unexpected-uv >> "$STARTUP_CALLS"\nexit 9\n')
            uv.chmod(0o755)
            environ = dict(os.environ, PATH=str(root)+os.pathsep+os.environ['PATH'], STARTUP_CALLS=str(calls))
            result = subprocess.run(['make', 'run'], cwd=root, env=environ, capture_output=True, text=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(calls.read_text().splitlines(), ['-B -m premier_demo.startup doctor'])


if __name__ == '__main__':
    unittest.main()
