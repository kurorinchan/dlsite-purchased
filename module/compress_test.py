from os import remove
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from regex import P
from . import compress
from pathlib import Path


class CompressTest(unittest.TestCase):

    def testFilterFilesRemoveWav(self):
        config = compress.CompressConfig(
            remove_flags=[compress.RemoveFlag.WAV],
        )

        files = [Path("any.mp3"), Path("any.wav")]
        filtered = compress._GetFilesToKeep(files, config)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].name, "any.mp3")

    def testFilterFilesRemoveNoSoundEffect(self):
        config = compress.CompressConfig(
            remove_flags=[compress.RemoveFlag.NO_SOUND_EFFECT],
        )
        files = [
            Path("10_NOSE.wav"),
            Path("NOSE/10.wav"),
            Path("効果音なし.wav"),
            Path("効果音なし/01.wav"),
            Path("3_NoSE.wav"),
            Path("NoSE/03.wav"),
            Path("any.mp3"),
            Path("SEなし.wav"),
            Path("SEなし/1.wav"),
        ]
        filtered = compress._GetFilesToKeep(files, config)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].name, "any.mp3")

    # Verify that filtering happens case-insensitively on file extensions.
    def testFilterFilesVerifyCaseInsensitiveOnFileExtension(self):
        config = compress.CompressConfig(
            remove_flags=[compress.RemoveFlag.WAV],
        )

        files = [Path("any.WAV"), Path("any.Wav")]
        filtered = compress._GetFilesToKeep(files, config)
        self.assertEqual(len(filtered), 0)

    def testGroupFiles(self):
        config = compress.CompressConfig(
            remove_flags=[compress.RemoveFlag.NO_SOUND_EFFECT, compress.RemoveFlag.WAV],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            (tmpdir / Path("10_NOSE.wav")).touch()
            (tmpdir / Path("NOSE")).mkdir(parents=True, exist_ok=True)
            (tmpdir / Path("NOSE/10.wav")).touch()

            (tmpdir / Path("効果音なし.wav")).touch()
            (tmpdir / Path("効果音なし")).mkdir(parents=True, exist_ok=True)
            (tmpdir / Path("効果音なし/01.wav")).touch()

            (tmpdir / Path("3_NoSE.wav")).touch()
            (tmpdir / Path("NoSE")).mkdir(parents=True, exist_ok=True)
            (tmpdir / Path("NoSE/03.wav")).touch()
            (tmpdir / Path("somethingsomethingnose")).mkdir(parents=True, exist_ok=True)
            (tmpdir / Path("somethingsomethingnose/03.mp3")).touch()

            (tmpdir / Path("any.mp3")).touch()
            # This wav file should be removed too.
            (tmpdir / Path("any.wav")).touch()

            (tmpdir / Path("SEなし.wav")).touch()
            (tmpdir / Path("SEなし")).mkdir(parents=True, exist_ok=True)
            (tmpdir / Path("SEなし/1.wav")).touch()

            result = compress.GroupFiles(config, Path(tmpdir))
            self.assertEqual(len(result.keep), 1)
            self.assertEqual(len(result.filtered), 10)

    # Verify ConvertWav2Flac works.
    @patch("subprocess.run")
    @patch("subprocess.Popen")
    def testConvertWav2Flac(self, mock_popen, mock_run):
        """Test convert_audio without using a real WAV file."""

        # Mock FFprobe response (fake duration = 300 seconds)
        mock_run.return_value.stdout = "300.0\n"

        # Mock Popen (simulating FFmpeg)
        mock_process = MagicMock()
        mock_process.stdout = iter(
            [
                "frame=0 fps=0.0 q=0.0 time=00:00:10.000\n",
                "frame=0 fps=0.0 q=0.0 time=00:00:20.000\n",
                "frame=0 fps=0.0 q=0.0 time=00:05:00.000\n",
            ]
        )
        mock_process.wait.return_value = 0  # Simulate successful execution
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Call the function with mock paths
        success = compress.ConvertWav2Flac(
            Path("fake_input.wav"), Path("fake_output.flac")
        )

        # Assertions
        self.assertTrue(success)  # Should return True on success
        mock_run.assert_called_once()  # Ensure ffprobe was called
        mock_popen.assert_called_once()  # Ensure ffmpeg was called
