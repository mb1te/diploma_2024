from enum import StrEnum
from pydantic import BaseModel


class YandexGPTModelUri(StrEnum):
    YANDEX_GPT = "gpt://b1gbmv781ng5j6vl23br/yandexgpt/latest"
    YANDEX_GPT_LITE = "gpt://b1gbmv781ng5j6vl23br/yandexgpt-lite/latest"
    YANDEX_GPT_PRO = "gpt://b1gbmv781ng5j6vl23br/yandexgpt-pro/latest"


class Message(BaseModel):
    role: str
    text: str

    @staticmethod
    def from_autogen_json(autogen_json: dict):
        return Message(role=autogen_json["role"], text=autogen_json["content"])


class CompletionOptions(BaseModel):
    stream: bool
    temperature: float
    maxTokens: int


class CompletionRequest(BaseModel):
    modelUri: YandexGPTModelUri
    completionOptions: CompletionOptions
    messages: list[Message]


class CompletionAlternative(BaseModel):
    message: Message
    status: str


class CompletionUsage(BaseModel):
    inputTextTokens: str
    completionTokens: str
    totalTokens: str


class CompletionResponse(BaseModel):
    alternatives: list[CompletionAlternative]
    usage: CompletionUsage
    modelVersion: str
