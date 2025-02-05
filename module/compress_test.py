import tempfile
import unittest

from regex import P
from . import compress
from pathlib import Path


class CompressTest(unittest.TestCase):

    def testFilterFilesRemoveWav(self):
        config = compress.CompressConfig(
            keep_wav=False,
        )

        files = [Path("any.mp3"), Path("any.wav")]
        filtered = compress._FilterOutFiles(files, config)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].name, "any.mp3")

    def testFilterFilesRemoveNoSoundEffect(self):
        config = compress.CompressConfig(
            keep_no_sound_effect_files=False,
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
        filtered = compress._FilterOutFiles(files, config)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].name, "any.mp3")

    # Verify that filtering happens case-insensitively on file extensions.
    def testFilterFilesVerifyCaseInsensitiveOnFileExtension(self):
        config = compress.CompressConfig(
            keep_wav=False,
        )

        files = [Path("any.WAV"), Path("any.Wav")]
        filtered = compress._FilterOutFiles(files, config)
        self.assertEqual(len(filtered), 0)

    def testGroupFiles(self):
        config = compress.CompressConfig(
            keep_no_sound_effect_files=False,
            keep_wav=False,
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

            (tmpdir / Path("any.mp3")).touch()
            # This wav file should be removed too.
            (tmpdir / Path("any.wav")).touch()

            (tmpdir / Path("SEなし.wav")).touch()
            (tmpdir / Path("SEなし")).mkdir(parents=True, exist_ok=True)
            (tmpdir / Path("SEなし/1.wav")).touch()

            result = compress.GroupFiles(config, Path(tmpdir))
            self.assertEqual(len(result.keep), 1)
            self.assertEqual(len(result.filtered), 9)
