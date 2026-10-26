import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("manage", Path(__file__).resolve().parents[1] / "scripts/manage.py")
manage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manage)
TEST_DIR = manage.ROOT / ".runtime" / "tests"
TEST_DIR.mkdir(parents=True, exist_ok=True)


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=TEST_DIR)
        self.root = Path(self.temp.name)
        self.patches = [patch.object(manage, "STATE", self.root), patch.object(manage, "CONFIG", self.root / "config"), patch.object(manage, "BINARY", self.root / "bin/prime-agent")]
        for item in self.patches:
            item.start()
        manage.initialize()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_repeat_setup_and_privacy_guard(self):
        manage.configure()
        first = (manage.CONFIG / "models.json").read_bytes()
        manage.configure()
        self.assertEqual(first, (manage.CONFIG / "models.json").read_bytes())
        manage.verify_profile()
        data = json.loads(first)
        data["providers"][manage.PROVIDER]["compat"]["openRouterRouting"]["zdr"] = False
        (manage.CONFIG / "models.json").write_text(json.dumps(data))
        with self.assertRaisesRegex(RuntimeError, "ZDR template"):
            manage.verify_profile()

    def test_state_stays_inside_profile(self):
        with patch.dict(os.environ, {"PRIME_AGENT_SESSION_DIR": "/foreign", "PRIME_AGENT_DAEMON_SOCKET": "/foreign.sock"}):
            env = manage.environment()
        self.assertNotIn("PRIME_AGENT_SESSION_DIR", env)
        for key in ("PRIME_AGENT_CODING_AGENT_DIR", "PRIME_AGENT_KERNEL_VENV", "PRIME_AGENT_DAEMON_SOCKET", "UV_CACHE_DIR", "UV_PYTHON_INSTALL_DIR", "UV_PYTHON_BIN_DIR", "TMPDIR"):
            self.assertTrue(Path(env[key]).is_relative_to(self.root), key)

    def test_profiles_have_separate_configs_and_daemons(self):
        manage.configure()
        environments = [manage.environment(profile) for profile in manage.PROFILES]
        self.assertEqual(len({env["PRIME_AGENT_CODING_AGENT_DIR"] for env in environments}), 3)
        self.assertEqual(len({env["PRIME_AGENT_DAEMON_SOCKET"] for env in environments}), 3)
        for profile in manage.PROFILES:
            manage.verify_profile(profile)
        with self.assertRaisesRegex(RuntimeError, "Choose a profile"):
            manage.environment("invalid")

    def test_removing_model_pin_is_detected(self):
        manage.configure()
        path = manage.CONFIG / "settings.json"
        settings = json.loads(path.read_text())
        settings.pop("allowedModels")
        path.write_text(json.dumps(settings))
        with self.assertRaisesRegex(RuntimeError, "Pinned-model"):
            manage.verify_profile()

    def test_other_model_is_refused_before_credentials_or_execution(self):
        manage.configure()
        for arguments in (["--model", "openai/gpt-4o", "-p", "hello"], ["--provider=another-provider"]):
            with patch.object(manage, "api_key") as key, patch.object(manage.os, "execve") as execute:
                with self.assertRaisesRegex(RuntimeError, "profile pins"):
                    manage.run(arguments)
                key.assert_not_called()
                execute.assert_not_called()

    def test_key_is_private_and_environment_takes_priority(self):
        path = self.root / "openrouter.key"
        manage.write_private(path, "dummy-stored-key\n")
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "dummy-env-key"}):
            self.assertEqual(manage.api_key(), "dummy-env-key")
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            self.assertEqual(manage.api_key(), "dummy-stored-key")
            path.unlink()
            with self.assertRaisesRegex(RuntimeError, "locally"):
                manage.api_key()

    def test_archive_cannot_escape_or_create_symlinks(self):
        for name, kind in (("../escape", tarfile.REGTYPE), ("symlink", tarfile.SYMTYPE)):
            archive = self.root / "unsafe.tar.gz"
            with tarfile.open(archive, "w:gz") as output:
                entry = tarfile.TarInfo(name)
                entry.type = kind
                output.addfile(entry, io.BytesIO())
            with self.assertRaisesRegex(RuntimeError, "Unsafe"):
                manage.unpack(archive, self.root / "unpack")

    def test_corrupt_release_never_extracts(self):
        arch = manage.target()
        archive = self.root / "downloads" / f"prime-agent-{manage.VERSION}-{arch}.tar.gz"
        archive.write_bytes(b"corrupt release")
        with patch.object(manage, "unpack") as unpack:
            with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
                manage.install()
            unpack.assert_not_called()
        self.assertFalse(archive.exists())


if __name__ == "__main__":
    unittest.main()
