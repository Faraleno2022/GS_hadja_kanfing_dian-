import hashlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app_version import APP_VERSION
import desktop_updater


class FakeResponse:
    def __init__(self, content: bytes, url: str, content_length: bool = True):
        self._stream = io.BytesIO(content)
        self._url = url
        self.headers = {
            "Content-Length": str(len(content)) if content_length else ""
        }

    def read(self, size: int = -1):
        return self._stream.read(size)

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class DesktopUpdaterTests(unittest.TestCase):
    def test_versions_are_compared_numerically(self):
        self.assertTrue(desktop_updater.is_newer_version("desktop-v1.10.0", "1.9.9"))
        self.assertFalse(desktop_updater.is_newer_version("v1.3.0", "1.3.0"))
        self.assertFalse(desktop_updater.is_newer_version("v1.2.9", "1.3.0"))

    def test_release_selects_installer_matching_tag(self):
        release = {
            "tag_name": "desktop-v1.3.0",
            "assets": [
                {"name": "MySchoolGN_Setup_v1.2.0.exe"},
                {"name": "MySchoolGN_Setup_v1.3.0.exe"},
            ],
        }
        selected = desktop_updater.find_installer_asset(release)
        self.assertEqual(selected["name"], "MySchoolGN_Setup_v1.3.0.exe")

    def test_release_rejects_installer_from_another_version(self):
        release = {
            "tag_name": "desktop-v1.3.0",
            "assets": [{"name": "MySchoolGN_Setup_v1.2.0.exe"}],
        }
        with self.assertRaises(desktop_updater.UpdateError):
            desktop_updater.find_installer_asset(release)

    def test_installer_default_version_matches_application(self):
        installer_script = Path("installer_myschool.iss").read_text(
            encoding="utf-8-sig"
        )
        self.assertIn(f'#define MyAppVersion "{APP_VERSION}"', installer_script)

    def test_checksum_companion_is_accepted(self):
        digest = "a" * 64
        installer = {"name": "MySchoolGN_Setup_v1.3.0.exe"}
        release = {
            "assets": [
                installer,
                {
                    "name": "MySchoolGN_Setup_v1.3.0.exe.sha256",
                    "browser_download_url": (
                        "https://github.com/Faraleno2022/GS_hadja_kanfing_dian-/"
                        "releases/download/desktop-v1.3.0/checksum.sha256"
                    ),
                },
            ]
        }

        def opener(_request, timeout):
            self.assertGreater(timeout, 0)
            return FakeResponse(
                f"{digest} *MySchoolGN_Setup_v1.3.0.exe\n".encode(),
                release["assets"][1]["browser_download_url"],
            )

        self.assertEqual(
            desktop_updater.expected_installer_digest(
                release, installer, opener=opener
            ),
            digest,
        )

    def test_download_is_verified_before_becoming_installable(self):
        content = b"verified installer payload"
        digest = hashlib.sha256(content).hexdigest()
        url = (
            "https://github.com/Faraleno2022/GS_hadja_kanfing_dian-/"
            "releases/download/desktop-v1.3.0/MySchoolGN_Setup_v1.3.0.exe"
        )
        asset = {
            "name": "MySchoolGN_Setup_v1.3.0.exe",
            "browser_download_url": url,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"LOCALAPPDATA": temp_dir}):
                result = desktop_updater.download_installer(
                    asset,
                    digest,
                    opener=lambda _request, timeout: FakeResponse(content, url),
                )
                self.assertEqual(result.read_bytes(), content)
                self.assertFalse(Path(f"{result}.part").exists())

    def test_bad_checksum_is_deleted(self):
        content = b"altered installer"
        url = (
            "https://github.com/Faraleno2022/GS_hadja_kanfing_dian-/"
            "releases/download/desktop-v1.3.0/MySchoolGN_Setup_v1.3.0.exe"
        )
        asset = {
            "name": "MySchoolGN_Setup_v1.3.0.exe",
            "browser_download_url": url,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"LOCALAPPDATA": temp_dir}):
                with self.assertRaises(desktop_updater.UpdateError):
                    desktop_updater.download_installer(
                        asset,
                        "0" * 64,
                        opener=lambda _request, timeout: FakeResponse(content, url),
                    )
                update_dir = Path(temp_dir) / "MySchoolGN" / "updates"
                self.assertEqual(list(update_dir.glob("*")), [])


if __name__ == "__main__":
    unittest.main()
