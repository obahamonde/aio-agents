from io import BytesIO
from typing import List, Literal, Optional

from aiofauna import Document, Field, async_io
from boto3 import Session

LanguageCodeType = Literal[
    "arb",
    "cmn-CN",
    "cy-GB",
    "da-DK",
    "de-DE",
    "en-AU",
    "en-GB",
    "en-GB-WLS",
    "en-IN",
    "en-US",
    "es-ES",
    "es-MX",
    "es-US",
    "fr-CA",
    "fr-FR",
    "is-IS",
    "it-IT",
    "ja-JP",
    "hi-IN",
    "ko-KR",
    "nb-NO",
    "nl-NL",
    "pl-PL",
    "pt-BR",
    "pt-PT",
    "ro-RO",
    "ru-RU",
    "sv-SE",
    "tr-TR",
    "en-NZ",
    "en-ZA",
    "ca-ES",
    "de-AT",
    "yue-CN",
    "ar-AE",
    "fi-FI",
    "en-IE",
    "nl-BE",
]


class Polly(Document):
    Engine: Literal["standard", "neural"] = Field(
        default="standard",
        description="Specifies the engine for Amazon Polly to use when processing input text for speech synthesis.",
    )
    LanguageCode: LanguageCodeType = Field(
        default="es-MX",
        description="Optional language code for the Synthesize Speech request.",
    )
    LexiconNames: Optional[List[str]] = Field(
        default=None,
        description="List of one or more pronunciation lexicon names you want the service to apply during synthesis.",
    )
    OutputFormat: Literal["json", "mp3", "ogg_vorbis", "pcm"] = Field(
        default="mp3",
        description="The format in which the returned output will be encoded.",
    )
    SampleRate: str = Field(
        default="22050", description="The audio frequency specified in Hz."
    )
    SpeechMarkTypes: Optional[
        List[Literal["sentence", "ssml", "viseme", "word"]]
    ] = Field(
        default=None,
        description="The type of speech marks returned for the input text.",
    )
    Text: str = Field(..., description="Input text to synthesize.")
    TextType: Literal["ssml", "text"] = Field(
        default="text",
        description="Specifies whether the input text is plain text or SSML.",
    )
    VoiceId: str = Field(
        default="Mia", description="Voice ID to use for the synthesis."
    )

    @classmethod
    def load(cls, text: str, language: LanguageCodeType = "en-US"):
        return cls(Text=text, LanguageCode=language)

    @property
    def client(self):
        return Session().client("polly", region_name="us-east-1")

    def synthesize(self):
        return self.client.synthesize_speech(**self.dict(exclude_none=True))

    @async_io
    def get_audio(self):
        byte_stream = BytesIO()
        with self.synthesize()["AudioStream"] as stream:
            byte_stream.write(stream.read())
        byte_stream.seek(0)
        return byte_stream


class SentimentScore(Document):
    Mixed: float = Field(
        default=None,
        description="The level of confidence that Amazon Comprehend has in the accuracy of its detection of the MIXED sentiment.",
    )
    Negative: float = Field(
        default=None,
        description="The level of confidence that Amazon Comprehend has in the accuracy of its detection of the NEGATIVE sentiment.",
    )
    Neutral: float = Field(
        default=None,
        description="The level of confidence that Amazon Comprehend has in the accuracy of its detection of the NEUTRAL sentiment.",
    )
    Positive: float = Field(
        default=None,
        description="The level of confidence that Amazon Comprehend has in the accuracy of its detection of the POSITIVE sentiment.",
    )
    Sentiment: Literal["POSITIVE", "NEGATIVE", "NEUTRAL", "MIXED"] = Field(
        default=None,
        description="The inferred sentiment that Amazon Comprehend has the highest level of confidence in.",
    )


class Comprehend(Document):
    LanguageCode: LanguageCodeType = Field(
        default="en-US",
        description="The language of the input documents.",
    )
    Text: str = Field(
        ...,
        description="A UTF-8 text string. Each string must contain fewer that 5,000 bytes of UTF-8 encoded characters.",
    )

    @classmethod
    def load(cls, text: str, language: LanguageCodeType = "en-US"):
        return cls(Text=text, LanguageCode=language)

    @property
    def client(self):
        return Session().client("comprehend", region_name="us-east-1")

    @async_io
    def detect_sentiment(self):
        response = self.client.detect_sentiment(**self.dict(exclude_none=True))
        return SentimentScore(
            Sentiment=response["Sentiment"], **response["SentimentScore"]
        )


class Translate(Document):
    SourceLanguageCode: LanguageCodeType = Field(
        default="auto",
        description="The language code for the language of the source text. The language must be a language supported by Amazon Translate.",
    )
    TargetLanguageCode: LanguageCodeType = Field(
        default="en",
        description="The language code requested for the language of the target text. The language must be a language supported by Amazon Translate.",
    )
    Text: str = Field(
        ...,
        description="The text to translate. The text string can be a maximum of 5,000 bytes long. Depending on your character set, this may be fewer than 5,000 characters.",
    )

    @classmethod
    def load(
        cls,
        text: str,
        source: LanguageCodeType = "auto",
        target: LanguageCodeType = "en",
    ):
        return cls(Text=text, SourceLanguageCode=source, TargetLanguageCode=target)

    @property
    def client(self):
        return Session().client("translate", region_name="us-east-1")

    @async_io
    def translate_text(self):
        response = self.client.translate_text(**self.dict(exclude_none=True))
        return response["TranslatedText"]
