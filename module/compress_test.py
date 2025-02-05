import unittest

from regex import P
from . import compress
from pathlib import Path


class CompressTest(unittest.TestCase):

    def testFilterFilesRemoveWav(self):
        config = compress.CleanConfig(
            keep_wav=False,
        )

        files = [Path("any.mp3"), Path("any.wav")]
        filtered = compress._FilterFiles(files, config)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].name, "any.mp3")

    def testFilterFilesRemoveNoSoundEffect(self):
        config = compress.CleanConfig(
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
        filtered = compress._FilterFiles(files, config)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].name, "any.mp3")

    # Verify that filtering happens case-insensitively on file extensions.
    def testFilterFilesVerifyCaseInsensitiveOnFileExtension(self):
        config = compress.CleanConfig(
            keep_wav=False,
        )

        files = [Path("any.WAV"), Path("any.Wav")]
        filtered = compress._FilterFiles(files, config)
        self.assertEqual(len(filtered), 0)

    def testFilterFilesVerifyCaseInsensitiveOnPath(self):
        pass
