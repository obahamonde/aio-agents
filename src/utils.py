import functools
import io
from collections import Counter
from typing import Awaitable, Callable, Tuple

import numpy as np
import requests
import spacy
from aiofauna import *
from aiofauna.typedefs import Vector
from boto3 import client
from pydub import AudioSegment
from scipy.io import wavfile

from aiofauna_llm import PineconeClient, Vector
from src.config import env
from src.schemas import *

s3 = client("s3", region_name="us-east-1")


async def upload_handler(file: FileField, user: str, namespace: str):
    """Uploads a file to S3 and returns a FileData object"""
    key = f"{user}/{namespace}/{file.filename}"
    data = file.file.read()
    s3.put_object(Bucket=env.AWS_S3_BUCKET, Key=key, Body=data)
    return await FileData(
        user=user,
        namespace=namespace,
        name=file.filename,
        size=file.file_size,
        content_type=file.content_type,
        last_modified=file.last_modified,
        url=f"https://{env.AWS_S3_BUCKET}.s3.amazonaws.com/{key}",
    ).save()


nlp = spacy.load("en_core_web_sm")


def word_cloud_handler(texts: List[str], namespace: str):
    """Generates a word cloud from the given texts"""
    word_count = Counter()
    for text in texts:
        doc = nlp(text)
        words = [
            token.text.lower() for token in doc if token.is_alpha and not token.is_stop
        ]
        word_count.update(words)
    sorted_word_count = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    return [{"word": word, "count": count} for word, count in sorted_word_count[:50]]


def word_cloud(text: str):
    """Generates a word cloud from the given texts"""
    word_count = Counter()
    doc = nlp(text)
    words = [
        token.text.lower() for token in doc if token.is_alpha and not token.is_stop
    ]
    word_count.update(words)
    sorted_word_count = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    return [{"word": word, "count": count} for word, count in sorted_word_count[:25]]


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
