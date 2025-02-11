from dataclasses import dataclass, field
from enum import Enum
import os
from pathlib import Path
from tqdm import tqdm
import subprocess
import logging
import sys
import re

# Files that do not have sound effects.
# Any alphabet are case-insensitive.
_NO_SOUND_EFFECT_KEYWORDS = ["効果音なし", "SEなし", "nose"]


@dataclass
class _GroupResult:
    keep: set[Path]
    filtered: set[Path]


# Enum for specifying which files to remove.
class RemoveFlag(Enum):
    # The string values will be used as flags on the command line, so make it human readable.
    # Also do not use the string values in code, keep using them as enums, e.g. RemoveFlag.WAV.
    WAV = "wav"
    NO_SOUND_EFFECT = "no_sound_effect"

    # Trick to use the string values as command line flags.
    def __str__(self):
        return self.value


@dataclass
class CompressConfig:
    remove_flags: list[RemoveFlag] = field(default_factory=list)
    # Compress all wav files to flac.
    compress_wav_to_flac: bool = True


def _GetAllFiles(directory: Path) -> list[Path]:
    dir_path = Path(directory)
    return [p.resolve() for p in dir_path.rglob("*") if p.is_file()]


def _ContainsNoSoundEffectKeyword(target: str):
    return any(
        keyword.lower() in target.lower() for keyword in _NO_SOUND_EFFECT_KEYWORDS
    )


# Returns files that should be kept by filtering out files specified in `config`.
def _GetFilesToKeep(files: list[Path], config: CompressConfig) -> list[Path]:
    if RemoveFlag.WAV in config.remove_flags:
        files = [f for f in files if not f.name.lower().endswith(".wav")]

    if RemoveFlag.NO_SOUND_EFFECT in config.remove_flags:
        keep: list[Path] = []
        for f in files:
            if _ContainsNoSoundEffectKeyword(str(f)):
                continue
            keep.append(f)

        files = keep
    return files


def GroupFiles(config: CompressConfig, directory: Path) -> _GroupResult:
    all_files = _GetAllFiles(directory)
    keep = set(_GetFilesToKeep(all_files, config))
    filtered = set(all_files) - keep
    return _GroupResult(keep, filtered)


def GetAllWavFiles(files: list[Path]) -> list[Path]:
    # On macOS with exfat, it creates these special files that start with this marker to save
    # metadata. When the real file is deleted these should be deleted as well.
    _METADATA_FILE_MARKER = "._"
    return [
        f
        for f in files
        if f.suffix.lower() == ".wav" and not f.name.startswith(_METADATA_FILE_MARKER)
    ]


# TODO this function probably does not belong here.
def ExtractWorkId(path: Path) -> str:
    """
    Extracts the "RJ" followed by numbers up to the first space from a directory name within a Path.

    Args:
        path: The pathlib.Path object to search within.

    Returns:
        The matched string (e.g., "RJ12345") or empty string if not found.
    """

    for part in path.parts:  # Iterate through the path components
        match = re.search(r"RJ(\d+)\s", part)  # Regular expression search
        if match:
            return "RJ" + match.group(1)  # Return "RJ" + the captured digits
    return ""


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


def ConvertWav2Flac(input_file: Path, output_file: Path) -> bool:
    """Convert audio using FFmpeg and show progress with tqdm.
    Returns True on success, False on failure."""

    def get_audio_duration(fp: Path):
        """Get audio duration in seconds using FFprobe."""
        try:
            # This outputs the duration of the audio file in decimal seconds.
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    fp,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            return float(result.stdout.strip())
        except Exception as e:
            logging.error(f"Failed to get duration of {fp}: {e}")
            return None

    total_duration = get_audio_duration(input_file)
    if total_duration is None:
        return False

    cmd = [
        "ffmpeg",
        "-i",
        input_file,
        "-c:a",
        "flac",
        output_file,
        "-progress",
        "pipe:1",
        "-y",
    ]

    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )

        if process.stdout is None:
            logging.error("Failed to capture FFmpeg output.")
            return False

        work_id = ExtractWorkId(input_file)
        with tqdm(
            total=total_duration,
            unit="sec",
            desc=f"{work_id}:{input_file.name}",
            dynamic_ncols=True,
            leave=False,
        ) as pbar:
            for line in process.stdout:
                sys.stdout.flush()

                # Match time output, handling both "ss.sss" and "hh:mm:ss.sss"
                match = re.search(r"time=([\d:.]+)", line)
                if match:
                    time_str = match.group(1)
                    if ":" in time_str:
                        h, m, s = map(float, time_str.split(":"))
                        current_time = h * 3600 + m * 60 + s
                    else:
                        current_time = float(time_str)

                    pbar.update(current_time - pbar.n)

        process.wait()

        if process.returncode == 0:
            logging.info(f"Audio conversion successful: {output_file}")
            return True
        else:
            logging.error(f"FFmpeg failed with exit code {process.returncode}")
            return False

    except Exception as e:
        logging.error(f"Error running FFmpeg: {e}")
        return False


def Compress(config: CompressConfig, directory: Path):
    result = GroupFiles(config, directory)
    keep = sorted(list(result.keep))

    print(f"Removing {len(result.filtered)} files.")
    for f in tqdm(sorted(list(result.filtered)), desc="Removing files", unit="file"):
        try:
            os.remove(f)
        except OSError as e:
            logging.error(f"Error removing {f}: {e}")  # Print the error for debugging

    wav_files = GetAllWavFiles(keep)
    with tqdm(
        wav_files, desc="Converting wav to flac", unit="file", dynamic_ncols=True
    ) as pbar:
        for wav_path in pbar:
            flac_path = wav_path.with_suffix(".flac")
            if ConvertWav2Flac(wav_path, flac_path):
                wav_path.unlink(missing_ok=True)
            else:
                logging.error(
                    f"Failed to convert wav to flac for {wav_path}. Keeping the file."
                )

    return True
