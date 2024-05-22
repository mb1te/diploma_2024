from datetime import datetime
from typing import Dict, List, Optional, Union

import autogen

from datamodel import AgentConfig, AgentFlowSpec, AgentWorkFlowConfig, Message, SocketMessage
from utils import clear_folder, get_skills_from_prompt, sanitize_model
from yandexgpt.autogen_client import YandexGPTAutogenClient


class AutoGenWorkFlowManager:
    """
    AutoGenWorkFlowManager class to load agents from a provided configuration and run a chat between them
    """

    def __init__(
        self,
        config: AgentWorkFlowConfig,
        history: Optional[List[Message]] = None,
        work_dir: str = None,
        clear_work_dir: bool = True,
        send_message_function: Optional[callable] = None,
        connection_id: Optional[str] = None,
    ) -> None:
        self.send_message_function = send_message_function
        self.connection_id = connection_id
        self.work_dir = work_dir or "work_dir"
        if clear_work_dir:
            clear_folder(self.work_dir)
        self.config = config
        self.sender = self.load(config.sender)
        self.receiver = self.load(config.receiver)
        self.agent_history = []

        if history:
            self.populate_history(history)

    def process_message(
        self,
        sender: autogen.Agent,
        receiver: autogen.Agent,
        message: Dict,
        request_reply: bool = False,
        silent: Optional[bool] = False,
        sender_type: str = "agent",
    ) -> None:
        message = message if isinstance(message, dict) else {"content": message, "role": "user"}
        message_payload = {
            "recipient": receiver.name,
            "sender": sender.name,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "sender_type": sender_type,
            "connection_id": self.connection_id,
            "message_type": "agent_message",
        }
        
        if request_reply is not False or sender_type == "groupchat":
            self.agent_history.append(message_payload)
            if self.send_message_function:
                socket_msg = SocketMessage(type="agent_message", data=message_payload, connection_id=self.connection_id)
                self.send_message_function(socket_msg.dict())

    def _sanitize_history_message(self, message: str) -> str:
        to_replace = ["execution succeeded", "exitcode"]
        for replace in to_replace:
            message = message.replace(replace, "")
        return message

    def populate_history(self, history: List[Message]) -> None:
        for msg in history:
            if isinstance(msg, dict):
                msg = Message(**msg)
            if msg.role == "user":
                self.sender.send(
                    msg.content,
                    self.receiver,
                    request_reply=False,
                    silent=True,
                )
            elif msg.role == "assistant":
                self.receiver.send(
                    msg.content,
                    self.sender,
                    request_reply=False,
                    silent=True,
                )

    def sanitize_agent_spec(self, agent_spec: AgentFlowSpec) -> AgentFlowSpec:
        agent_spec.config.is_termination_msg = agent_spec.config.is_termination_msg or (
            lambda x: "TERMINATE" in x.get("content", "").rstrip()[-20:]
        )

        def get_default_system_message(agent_type: str) -> str:
            if agent_type == "assistant":
                return autogen.AssistantAgent.DEFAULT_SYSTEM_MESSAGE
            else:
                return "You are a helpful AI Assistant."

        if agent_spec.config.llm_config is not False:
            config_list = []
            for llm in agent_spec.config.llm_config.config_list:
                sanitized_llm = sanitize_model(llm)
                config_list.append(sanitized_llm)
            agent_spec.config.llm_config.config_list = config_list
        
        if agent_spec.config.code_execution_config is not False:
            code_execution_config = agent_spec.config.code_execution_config or {}
            code_execution_config["work_dir"] = self.work_dir
            code_execution_config["use_docker"] = False
            agent_spec.config.code_execution_config = code_execution_config

            if agent_spec.skills:
                skills_prompt = ""
                skills_prompt = get_skills_from_prompt(agent_spec.skills, self.work_dir)
                if agent_spec.config.system_message:
                    agent_spec.config.system_message = agent_spec.config.system_message + "\n\n" + skills_prompt
                else:
                    agent_spec.config.system_message = (
                        get_default_system_message(agent_spec.type) + "\n\n" + skills_prompt
                    )

        return agent_spec

    def load(self, agent_spec: AgentFlowSpec) -> autogen.Agent:
        agent_spec = self.sanitize_agent_spec(agent_spec)
        if agent_spec.type == "groupchat":
            agents = [
                self.load(self.sanitize_agent_spec(agent_config)) for agent_config in agent_spec.groupchat_config.agents
            ]
            group_chat_config = agent_spec.groupchat_config.dict()
            group_chat_config["agents"] = agents
            groupchat = autogen.GroupChat(**group_chat_config)
            agent = ExtendedGroupChatManager(
                groupchat=groupchat, **agent_spec.config.dict(), message_processor=self.process_message
            )
            return agent

        else:
            agent = self.load_agent_config(agent_spec.config, agent_spec.type)
            return agent

    def load_agent_config(self, agent_config: AgentConfig, agent_type: str) -> autogen.Agent:
        if agent_type == "assistant":
            agent = ExtendedConversableAgent(**agent_config.dict(), message_processor=self.process_message)
        elif agent_type == "userproxy":
            agent = ExtendedConversableAgent(**agent_config.dict(), message_processor=self.process_message)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

        return agent

    def run(self, message: str, clear_history: bool = False) -> None:
        self.sender.initiate_chat(
            self.receiver,
            message=message,
            clear_history=clear_history,
        )


class ExtendedConversableAgent(autogen.ConversableAgent):
    def __init__(self, message_processor=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_processor = message_processor
        print(self.system_message)
        self.register_model_client(YandexGPTAutogenClient)

    def receive(
        self,
        message: Union[Dict, str],
        sender: autogen.Agent,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ):
        if self.message_processor:
            self.message_processor(sender, self, message, request_reply, silent, sender_type="agent")
        super().receive(message, sender, request_reply, silent)


class ExtendedGroupChatManager(autogen.GroupChatManager):
    def __init__(self, message_processor=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_processor = message_processor
        self.register_model_client(YandexGPTAutogenClient)

    def receive(
        self,
        message: Union[Dict, str],
        sender: autogen.Agent,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ):
        if self.message_processor:
            self.message_processor(sender, self, message, request_reply, silent, sender_type="groupchat")
        super().receive(message, sender, request_reply, silent)
