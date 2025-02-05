from dataclasses import dataclass
from pathlib import Path
import subprocess
import logging

# Files that do not have sound effects.
# Any alphabet are case-insensitive.
_NO_SOUND_EFFECT_KEYWORDS = ["効果音なし", "SEなし", "nose"]


@dataclass
class _GroupResult:
    keep: set[Path]
    filtered: set[Path]


@dataclass
class CompressConfig:
    # Try to keep these flags to be "non-negating", to keep things easier to read (understand).
    # For example remove_X = False which is equivalent to keep_X = True, but the former requires
    # a little more thinking to understand, the latter is easier.

    # Keep no sound effect files.
    keep_no_sound_effect_files: bool = True

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


# Returns files that should be kept by filtering out files specified in `config`.
def _FilterOutFiles(files: list[Path], config: CompressConfig) -> list[Path]:
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


def GroupFiles(config: CompressConfig, directory: Path) -> _GroupResult:
    all_files = _GetAllFiles(directory)
    keep = set(_FilterOutFiles(all_files, config))
    filtered = set(all_files) - keep
    return _GroupResult(keep, filtered)


def GetAllWavFiles(files: list[Path]) -> list[Path]:
    return [f for f in files if f.suffix.lower() == ".wav"]


def RunFFmpegWav2Flac(wav_file: Path):
    command = [
        "ffmpeg",
        "-i",
        str(wav_file),
        "-c:a",
        "flac",
        str(wav_file.with_suffix(".flac")),
    ]

    try:
        # Run the command
        subprocess.run(command)
        return True  # Return True if the command was successful
    except subprocess.CalledProcessError as e:
        # Log the error
        logging.error(f"Command failed: {' '.join(command)}")
        logging.error(f"Exit code: {e.returncode}")
        logging.error(f"Error output: {e.stderr.strip()}")
        return False  # Return False if there was an error


def Compress(config: CompressConfig, directory: Path):
    result = GroupFiles(config, directory)
    keep = sorted(list(result.keep))

    print("Removing files first.")
    for f in sorted(list(result.filtered)):
        print(f"Removing {f}.")
        f.unlink()

    wav_files = GetAllWavFiles(keep)
    for wav_file in wav_files:
        print(f"Converting {wav_file} to flac.")
        if not RunFFmpegWav2Flac(wav_file):
            logging.error(
                f"Failed to convert wav to flac for {wav_file}. Keeping the file."
            )
        else:
            print(f"{wav_file} was converted to flac. Removing.")
            wav_file.unlink()

    return True
