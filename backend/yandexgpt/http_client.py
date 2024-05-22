import requests
from time import sleep

from yandexgpt.dto import CompletionRequest, CompletionResponse


class YandexGPTApiClient:
    _session: requests.Session | None = None

    def __init__(self, token: str) -> None:
        self._headers = {"Authorization": f"Api-Key {token}"}

    def completion(self, request: CompletionRequest) -> CompletionResponse:
        request_id = self._id_of_completion(request=request)
        while True:
            response = self._result_of_completions(request_id)
            if response.get("done"):
                return CompletionResponse(**response["response"])
            
            sleep(1)
        
        return CompletionResponse(**response.json()["result"])

    def _id_of_completion(self, request: CompletionRequest) -> str:
        response = requests.post("https://llm.api.cloud.yandex.net/foundationModels/v1/completionAsync", json=request.model_dump(), headers=self._headers)
        print(request.model_dump_json(), self._headers, response.json())
        return response.json()["id"]
    
    def _result_of_completions(self, id: str) -> dict:
        response = requests.get(f"https://llm.api.cloud.yandex.net/operations/{id}", headers=self._headers)
        print(response.json())
        return response.json()
