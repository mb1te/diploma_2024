import asyncio
import json
import os
import time
from datetime import datetime
from queue import Queue
from typing import Any, Dict, List, Optional, Tuple

import websockets
from fastapi import WebSocket, WebSocketDisconnect

from datamodel import AgentWorkFlowConfig, Message, SocketMessage
from utils import extract_successful_code_blocks, get_modified_files, summarize_chat_history
from workflowmanager import AutoGenWorkFlowManager


class AutoGenChatManager:
    def __init__(self, message_queue: Queue) -> None:
        self.message_queue = message_queue

    def send(self, message: str) -> None:
        if self.message_queue is not None:
            self.message_queue.put_nowait(message)

    def chat(
        self,
        message: Message,
        history: List[Dict[str, Any]],
        flow_config: Optional[AgentWorkFlowConfig] = None,
        connection_id: Optional[str] = None,
        user_dir: Optional[str] = None,
        **kwargs,
    ) -> Message:
        work_dir = os.path.join(user_dir, message.session_id, datetime.now().strftime("%Y%m%d_%H-%M-%S"))
        os.makedirs(work_dir, exist_ok=True)

        if flow_config is None:
            raise ValueError("flow_config must be specified")

        flow = AutoGenWorkFlowManager(
            config=flow_config,
            history=history,
            work_dir=work_dir,
            send_message_function=self.send,
            connection_id=connection_id,
        )

        message_text = message.content.strip()

        start_time = time.time()
        flow.run(message=f"{message_text}", clear_history=False)
        end_time = time.time()

        metadata = {
            "messages": flow.agent_history,
            "summary_method": flow_config.summary_method,
            "time": end_time - start_time,
            "files": get_modified_files(start_time, end_time, source_dir=work_dir),
        }

        print("Modified files: ", len(metadata["files"]))

        output = self._generate_output(message_text, flow, flow_config)

        output_message = Message(
            user_id=message.user_id,
            root_msg_id=message.root_msg_id,
            role="assistant",
            content=output,
            metadata=json.dumps(metadata),
            session_id=message.session_id,
        )

        return output_message

    def _generate_output(
        self, message_text: str, flow: AutoGenWorkFlowManager, flow_config: AgentWorkFlowConfig
    ) -> str:
        output = ""
        if flow_config.summary_method == "last":
            successful_code_blocks = extract_successful_code_blocks(flow.agent_history)
            last_message = flow.agent_history[-1]["message"]["content"] if flow.agent_history else ""
            successful_code_blocks = "\n\n".join(successful_code_blocks)
            output = (last_message + "\n" + successful_code_blocks) if successful_code_blocks else last_message
        elif flow_config.summary_method == "llm":
            model = flow.config.receiver.config.llm_config.config_list[0]
            status_message = SocketMessage(
                type="agent_status",
                data={"status": "summarizing", "message": "Generating summary of agent dialogue"},
                connection_id=flow.connection_id,
            )
            self.send(status_message.dict())
            output = summarize_chat_history(task=message_text, messages=flow.agent_history, model=model)

        elif flow_config.summary_method == "none":
            output = ""
        return output


class WebSocketConnectionManager:
    def __init__(
        self, active_connections: List[Tuple[WebSocket, str]] = None, active_connections_lock: asyncio.Lock = None
    ) -> None:
        """
        Initializes WebSocketConnectionManager with an optional list of active WebSocket connections.

        :param active_connections: A list of tuples, each containing a WebSocket object and its corresponding client_id.
        """
        if active_connections is None:
            active_connections = []
        self.active_connections_lock = active_connections_lock
        self.active_connections: List[Tuple[WebSocket, str]] = active_connections

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        await websocket.accept()
        async with self.active_connections_lock:
            self.active_connections.append((websocket, client_id))
            print(f"New Connection: {client_id}, Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self.active_connections_lock:
            try:
                self.active_connections = [conn for conn in self.active_connections if conn[0] != websocket]
                print(f"Connection Closed. Total: {len(self.active_connections)}")
            except ValueError:
                print("Error: WebSocket connection not found")

    async def disconnect_all(self) -> None:
        for connection, _ in self.active_connections[:]:
            await self.disconnect(connection)

    async def send_message(self, message: Dict, websocket: WebSocket) -> None:
        try:
            async with self.active_connections_lock:
                await websocket.send_json(message)
        except WebSocketDisconnect:
            print("Error: Tried to send a message to a closed WebSocket")
            await self.disconnect(websocket)
        except websockets.exceptions.ConnectionClosedOK:
            print("Error: WebSocket connection closed normally")
            await self.disconnect(websocket)
        except Exception as e:
            print(f"Error in sending message: {str(e)}")
            await self.disconnect(websocket)

    async def broadcast(self, message: Dict) -> None:
        message_dict = {"message": message}

        for connection, _ in self.active_connections[:]:
            try:
                if connection.client_state == websockets.protocol.State.OPEN:
                    # Call send_message method with the message dictionary and current WebSocket connection
                    await self.send_message(message_dict, connection)
                else:
                    print("Error: WebSocket connection is closed")
                    await self.disconnect(connection)
            except (WebSocketDisconnect, websockets.exceptions.ConnectionClosedOK) as e:
                print(f"Error: WebSocket disconnected or closed({str(e)})")
                await self.disconnect(connection)
