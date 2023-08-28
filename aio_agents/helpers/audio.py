import io
from typing import List, Tuple

import numpy as np
from pydub import AudioSegment
from scipy.io import wavfile

Vector = List[float]


def mp3_to_vect(binary_audio: bytes) -> Tuple[Vector, int]:
    """
    Converts the given audio to a vector
    """
    audio = AudioSegment.from_mp3(io.BytesIO(binary_audio))
    duration = audio.duration_seconds
    if audio.channels == 2:
        audio = audio.set_channels(1)
    wav_data = io.BytesIO(binary_audio)
    audio.export(wav_data, format="wav")
    wav_data.seek(0)
    _, audio_sample = wavfile.read(wav_data)
    fft_sample = np.fft.fft(audio_sample)
    combined_fft = np.concatenate((np.real(fft_sample), np.imag(fft_sample)))
    step_size = len(combined_fft) // 1536
    subsampled_embedding = combined_fft[::step_size][:1536]
    normalized_embedding = (
        subsampled_embedding / np.linalg.norm(subsampled_embedding)
    ).tolist()
    return normalized_embedding, duration
