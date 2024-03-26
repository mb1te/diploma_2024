import logging
import os
import autogen

from llm.yandexgpt.autogen_client import YandexGPTAutogenClient

logging.basicConfig(level=logging.DEBUG)

autogen.runtime_logging.start(logger_type="sqlite", config={"dbname": "logs.db"})


config_list = [
    {
        "model": "yandexgpt",
        "model_client_cls": "YandexGPTAutogenClient",
        "api_key": "removed",
        "device": "cpu",
        "n": 1,
        "params": {
            "max_length": 1000,
        }
    }
]

llm_config = {"config_list": config_list, "cache_seed": 42}
user_proxy = autogen.UserProxyAgent(
    name="User_proxy",
    system_message="A human admin.",
    human_input_mode="TERMINATE",
    llm_config=llm_config,
    code_execution_config=False,
)
user_proxy.register_model_client(YandexGPTAutogenClient)

coder = autogen.AssistantAgent(
    name="Coder",
    llm_config=llm_config,
)
coder.register_model_client(YandexGPTAutogenClient)

pm = autogen.AssistantAgent(
    name="Product_manager",
    system_message="Creative in software product ideas.",
    llm_config=llm_config,
)
pm.register_model_client(YandexGPTAutogenClient)


groupchat = autogen.GroupChat(agents=[user_proxy, coder, pm], messages=[], max_round=12)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)
manager.register_model_client(YandexGPTAutogenClient)

print("Result: ", user_proxy.initiate_chat(
    manager, message="Реши задачу классификации комментариев на негативные и позитивные"
).summary)