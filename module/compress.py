from dataclasses import dataclass
from pathlib import Path

# Files that do not have sound effects.
# Any alphabet are case-insensitive.
_NO_SOUND_EFFECT_KEYWORDS = ["効果音なし", "SEなし", "nose"]


@dataclass
class CleanConfig:
    # Try to keep these flags to be "non-negating", to keep things easier to read (understand).
    # For example remove_X = False which is equivalent to keep_X = True, but the former requires
    # a little more thinking to understand, the latter is easier.

    # Keep no sound effect files.
    keep_no_sound_effect_files: bool = False

    # Keep wav files.
    keep_wav: bool = True

    # Compress all wav files to flac.
    # If keep_wav = False then this has no effect.
    compress_wav_to_flac = True


def _GetAllFiles(directory: Path) -> list[Path]:
    dir_path = Path(directory)
    return [p.resolve() for p in dir_path.rglob("*") if p.is_file()]


def _ContainsNoSoundEffectKeyword(target: str):
    return any(
        keyword.lower() in target.lower() for keyword in _NO_SOUND_EFFECT_KEYWORDS
    )


def _FilterFiles(files: list[Path], config: CleanConfig) -> list[Path]:
    if not config.keep_wav:
        files = [f for f in files if not f.name.lower().endswith(".wav")]

    if not config.keep_no_sound_effect_files:
        filtered: list[Path] = []
        for f in files:
            if _ContainsNoSoundEffectKeyword(str(f)):
                continue
            filtered.append(f)

        files = filtered
    return files


def GetFilesToKeep(config: CleanConfig, directory: Path) -> list[Path]:
    keep_files = _GetAllFiles(directory)
    return _FilterFiles(keep_files, config)
