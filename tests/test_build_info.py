import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tests.support import ROOT
from letenky.infrastructure import build_info


class BuildInfoTests(unittest.TestCase):
    def test_offline_bundle_reads_embedded_metadata_without_git(self):
        data = {"built_at": "2026-09-23T10:00:00+00:00", "python": "3.13.7",
                "git_tag": "v1.0", "git_commit": "a" * 40, "dirty": False}
        with patch.object(build_info.sys, "frozen", True, create=True), \
             patch.object(Path, "read_text", return_value=json.dumps(data)), \
             patch.object(build_info.subprocess, "run", side_effect=AssertionError("Git must not run")):
            self.assertEqual(build_info.get_build_info(), data)

    def test_missing_bundle_metadata_does_not_query_git(self):
        with patch.object(build_info.sys, "frozen", True, create=True), \
             patch.object(Path, "read_text", side_effect=FileNotFoundError), \
             patch.object(build_info.subprocess, "run", side_effect=AssertionError("Git must not run")):
            self.assertEqual(build_info.get_build_info()["git_commit"], "Nedostupný")

    def test_source_archive_without_git_and_build_timestamp(self):
        with TemporaryDirectory() as directory, \
             patch.object(build_info.subprocess, "run", side_effect=FileNotFoundError):
            source = build_info.collect_build_info(directory)
            built = build_info.collect_build_info(directory, built=True)
        self.assertIsNone(source["built_at"])
        self.assertIsNotNone(built["built_at"])
        self.assertEqual(built["git_tag"], "Nedostupný")

    def test_exact_tags_commit_and_dirty_state(self):
        from subprocess import CompletedProcess
        outputs = ["a" * 40, "v1.0\nv1.0-stable\n", " M file.py\n"]
        with patch.object(build_info.subprocess, "run", side_effect=[
                CompletedProcess([], 0, value, "") for value in outputs]):
            data = build_info.collect_build_info(ROOT, built=True)
        self.assertEqual(data["git_tag"], "v1.0, v1.0-stable")
        self.assertTrue(data["dirty"])
        self.assertEqual(data["git_commit"], "a" * 40)
