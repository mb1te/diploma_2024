import asyncio
from dataclasses import dataclass

from llm.yandexgpt.dto import CompletionOptions, CompletionRequest, YandexGPTModelUri, Message as MessageYandexGPT
from llm.yandexgpt.http_client import YandexGPTApiClient


@dataclass
class Message:
    content: str | None


@dataclass
class Choice:
    message: Message


@dataclass
class ModelClientResponse:
    choices: list[Choice]
    model: str


class YandexGPTAutogenClient:
    def __init__(self, config: dict):
        self.api_client = YandexGPTApiClient(token=config.get("api_key", ""))
        self.model_name = config["model"]

    def create(self, params: dict) -> ModelClientResponse:
        if params.get("stream", False):
            raise NotImplemented
        
        request = CompletionRequest(
            modelUri=YandexGPTModelUri.YANDEX_GPT,
            completionOptions=CompletionOptions(
                stream=False,
                temperature=0.9,
                maxTokens=1000,
            ),
            messages=[MessageYandexGPT.from_autogen_json(autogen_json) for autogen_json in params["messages"]],
        )
        api_response = asyncio.get_event_loop().run_until_complete(self.api_client.completion(request=request))

        return ModelClientResponse(
            choices=[
                Choice(
                    message=Message(
                        content=api_response.alternatives[0].message.text,
                    )
                )
            ],
            model=self.model_name,
        )


    def message_retrieval(self, response):
        return [choice.message.content for choice in response.choices]

    def cost(self, response) -> float:
        response.cost = 0
        return response.cost

    @staticmethod
    def get_usage(response):
        return {}
