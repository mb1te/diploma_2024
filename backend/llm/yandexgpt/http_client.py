import asyncio
import logging
import aiohttp

from llm.yandexgpt.dto import CompletionRequest, CompletionResponse


class YandexGPTApiClient:
    _session: aiohttp.ClientSession | None = None

    def __init__(self, token: str) -> None:
        self._token = token
    
    async def create_session(self):
        self._session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Api-Key {self._token}",
            },
            raise_for_status=True,
        )
    async def close_session(self):
        await self._session.close()

    async def completion(self, request: CompletionRequest) -> CompletionResponse:
        if self._session is None:
            await self.create_session()

        request_id = await self._id_of_completion(request=request)
        while True:
            response = await self._result_of_completions(request_id)
            if response.get("done"):
                return CompletionResponse(**response["response"])
            
            await asyncio.sleep(1)

    async def _id_of_completion(self, request: CompletionRequest) -> str:
        async with self._session.post("https://llm.api.cloud.yandex.net/foundationModels/v1/completionAsync", data=request.model_dump_json()) as response:
            response_json = await response.json()
            return response_json["id"]
    
    async def _result_of_completions(self, id: str) -> dict:
        async with self._session.get(f"https://operation.api.cloud.yandex.net/operations/{id}") as response:
            return await response.json()
