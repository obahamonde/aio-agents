import functools
import io
import re
import socket
import subprocess
from collections import Counter
from typing import List, Tuple

import numpy as np
import spacy
from aiofauna import *
from aiofauna.typedefs import Vector
from boto3 import Session
from pydub import AudioSegment
from scipy.io import wavfile

from .config import env
from .data import *

s3 = Session().client("s3")
nlp = spacy.load("en_core_web_sm")


def random_port() -> int:
    """Returns a random port number that is available for listening."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


def merge(*dicts):
    result = {}
    for dictionary in dicts:
        result.update(dictionary)
    return result


def snake_to_camel(s: str) -> str:
    """Converts snake_case to camelCase."""
    return "".join([x.capitalize() for x in s.split("_")])


def parse_env_string(env: str) -> List[str]:
    """Parses a string of environment variables into a list of strings."""
    return env.split(" ")


def nginx_config(name: str, port: int) -> str:
    """Generates an nginx configuration file."""
    text = f"""
server {{
    listen 80;
    server_name { name }.aiofauna.com;

    location / {{
        proxy_pass http://localhost:{ port };
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }}

    location /api/sse {{
        proxy_pass http://localhost:{ port };
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_buffering off;
        proxy_cache off;
        proxy_ignore_headers "Cache-Control" "Expires";
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    location /ws {{
        proxy_pass http://localhost:{ port };
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
    for path in (
        "/etc/nginx/sites-enabled",
        "/etc/nginx/conf.d",
        "/etc/nginx/sites-available",
    ):
        try:
            with open(f"{path}/{name}.conf", "w") as f:
                f.write(text)
        except FileNotFoundError:
            pass
    return subprocess.run(["nginx", "-s", "reload"], capture_output=True).stdout.decode(
        "utf-8"
    )


async def upload_handler(file: FileField, user: str, namespace: str):
    """Uploads a file to S3 and returns a FileData object"""
    key = f"{user}/{namespace}/{file.filename}"
    data = file.file.read()
    s3.put_object(Bucket=env.AWS_S3_BUCKET, Key=key, Body=data)
    return await FileData(
        user=user,
        namespace=namespace,
        name=file.filename,
        size=len(data),
        content_type=file.content_type,
        url=f"https://{env.AWS_S3_BUCKET}.s3.amazonaws.com/{key}",
    ).save()


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


def snakify(name: str) -> str:
    """Convert camel case to snake case."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def camelify(name: str) -> str:
    """Convert snake case to camel case."""
    return "".join(word.title() for word in name.split("_"))
