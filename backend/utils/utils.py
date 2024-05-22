import base64
import hashlib
import os
import re
import shutil
from typing import Dict, List, Tuple, Union

from dotenv import load_dotenv

import autogen

from datamodel import AgentConfig, AgentFlowSpec, AgentWorkFlowConfig, LLMConfig, Model, Skill
from version import APP_NAME
from yandexgpt.dto import CompletionOptions, CompletionRequest, Message, YandexGPTModelUri
from yandexgpt.http_client import YandexGPTApiClient

def md5_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def clear_folder(folder_path: str) -> None:
    if not os.path.exists(folder_path):
        return
    
    if not os.path.exists(folder_path):
        return
    
    for file in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file)
        if os.path.isfile(file_path):
            os.remove(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)


def get_file_type(file_path: str) -> str:
    CODE_EXTENSIONS = {
        ".py",
        ".js",
        ".jsx",
        ".java",
        ".c",
        ".cpp",
        ".cs",
        ".ts",
        ".tsx",
        ".html",
        ".css",
        ".scss",
        ".less",
        ".json",
        ".xml",
        ".yaml",
        ".yml",
        ".md",
        ".rst",
        ".tex",
        ".sh",
        ".bat",
        ".ps1",
        ".php",
        ".rb",
        ".go",
        ".swift",
        ".kt",
        ".hs",
        ".scala",
        ".lua",
        ".pl",
        ".sql",
        ".config",
    }

    CSV_EXTENSIONS = {".csv", ".xlsx"}
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".svg", ".webp"}
    VIDEO_EXTENSIONS = {".mp4", ".webm", ".ogg", ".mov", ".avi", ".wmv"}
    PDF_EXTENSION = ".pdf"

    _, file_extension = os.path.splitext(file_path)

    if file_extension in CODE_EXTENSIONS:
        file_type = "code"
    elif file_extension in CSV_EXTENSIONS:
        file_type = "csv"
    elif file_extension in IMAGE_EXTENSIONS:
        file_type = "image"
    elif file_extension == PDF_EXTENSION:
        file_type = "pdf"
    elif file_extension in VIDEO_EXTENSIONS:
        file_type = "video"
    else:
        file_type = "unknown"

    return file_type


def serialize_file(file_path: str) -> Tuple[str, str]:
    file_type = get_file_type(file_path)

    try:
        with open(file_path, "rb") as file:
            file_content = file.read()
            base64_encoded_content = base64.b64encode(file_content).decode("utf-8")
    except Exception as e:
        raise IOError(f"An error occurred while reading the file: {e}") from e

    return base64_encoded_content, file_type


def get_modified_files(start_timestamp: float, end_timestamp: float, source_dir: str) -> List[Dict[str, str]]:
    modified_files = []
    ignore_extensions = {".pyc", ".cache"}
    ignore_files = {"__pycache__", "__init__.py"}

    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if d not in ignore_files]
        files[:] = [f for f in files if f not in ignore_files and os.path.splitext(f)[1] not in ignore_extensions]

        for file in files:
            file_path = os.path.join(root, file)
            file_mtime = os.path.getmtime(file_path)

            if start_timestamp <= file_mtime <= end_timestamp:
                file_relative_path = (
                    "files/user" + file_path.split("files/user", 1)[1] if "files/user" in file_path else ""
                )
                file_type = get_file_type(file_path)

                file_dict = {
                    "path": file_relative_path,
                    "name": os.path.basename(file),
                    "extension": os.path.splitext(file)[1].lstrip("."),
                    "type": file_type,
                }
                modified_files.append(file_dict)

    modified_files.sort(key=lambda x: x["extension"])
    return modified_files


def init_app_folders(app_file_path: str) -> Dict[str, str]:
    app_name = f".{APP_NAME}"
    default_app_root = os.path.join(os.path.expanduser("~"), app_name)
    if not os.path.exists(default_app_root):
        os.makedirs(default_app_root, exist_ok=True)
    app_root = os.environ.get("AUTOGENSTUDIO_APPDIR") or default_app_root

    if not os.path.exists(app_root):
        os.makedirs(app_root, exist_ok=True)

    env_file = os.path.join(app_root, ".env")
    if os.path.exists(env_file):
        print(f"Loading environment variables from {env_file}")
        load_dotenv(env_file)

    files_static_root = os.path.join(app_root, "files/")
    static_folder_root = os.path.join(app_file_path, "ui")

    os.makedirs(files_static_root, exist_ok=True)
    os.makedirs(os.path.join(files_static_root, "user"), exist_ok=True)
    os.makedirs(static_folder_root, exist_ok=True)
    folders = {
        "files_static_root": files_static_root,
        "static_folder_root": static_folder_root,
        "app_root": app_root,
    }
    print(f"Initialized application data folder: {app_root}")
    return folders


def get_skills_from_prompt(skills: List[Skill], work_dir: str) -> str:
    instruction = """

While solving the task you may use functions below which will be available in a file called skills.py .
To use a function skill.py in code, IMPORT THE FUNCTION FROM skills.py  and then use the function.
If you need to install python packages, write shell code to
install via pip and use --quiet option.
"""
    prompt = ""
    for skill in skills:
        prompt += f"""
##### Begin of {skill.title} #####

{skill.content}

#### End of {skill.title} ####
"""

    if not os.path.exists(work_dir):
        os.makedirs(work_dir)

    with open(os.path.join(work_dir, "skills.py"), "w", encoding="utf-8") as f:
        f.write(prompt)

    return instruction + prompt


def delete_files_in_folder(folders: Union[str, List[str]]) -> None:
    if isinstance(folders, str):
        folders = [folders]

    for folder in folders:
        if not os.path.isdir(folder):
            print(f"The folder {folder} does not exist.")
            continue

        for entry in os.listdir(folder):
            path = os.path.join(folder, entry)
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
            except Exception as e:
                print(f"Failed to delete {path}. Reason: {e}")


def get_default_agent_config(work_dir: str) -> AgentWorkFlowConfig:
    llm_config = LLMConfig(
        config_list=[{"model": "gpt-4"}],
        temperature=0,
    )

    USER_PROXY_INSTRUCTIONS = "If the request has been addressed sufficiently, summarize the answer and end with the word TERMINATE. Otherwise, ask a follow-up question."

    userproxy_spec = AgentFlowSpec(
        type="userproxy",
        config=AgentConfig(
            name="user_proxy",
            human_input_mode="NEVER",
            system_message=USER_PROXY_INSTRUCTIONS,
            code_execution_config={
                "work_dir": work_dir,
                "use_docker": False,
            },
            max_consecutive_auto_reply=10,
            llm_config=llm_config,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
        ),
    )

    assistant_spec = AgentFlowSpec(
        type="assistant",
        config=AgentConfig(
            name="primary_assistant",
            system_message=autogen.AssistantAgent.DEFAULT_SYSTEM_MESSAGE,
            llm_config=llm_config,
        ),
    )

    flow_config = AgentWorkFlowConfig(
        name="default",
        sender=userproxy_spec,
        receiver=assistant_spec,
        type="default",
        description="Default agent flow config",
    )

    return flow_config


def extract_successful_code_blocks(messages: List[Dict[str, str]]) -> List[str]:
    successful_code_blocks = []
    code_block_regex = r"```[\s\S]*?```"

    for i, row in enumerate(messages):
        message = row["message"]
        if message["role"] == "user" and "execution succeeded" in message["content"]:
            if i > 0 and messages[i - 1]["message"]["role"] == "assistant":
                prev_content = messages[i - 1]["message"]["content"]
                code_blocks = re.findall(code_block_regex, prev_content)
                successful_code_blocks.extend(code_blocks)

    return successful_code_blocks


def sanitize_model(model: Model):
    if isinstance(model, Model):
        model = model.dict()
    valid_keys = ["model", "base_url", "api_key", "api_type", "api_version"]
    sanitized_model = {k: v for k, v in model.items() if (v is not None and v != "") and k in valid_keys}
    return sanitized_model

def test_model(model: Model):
    sanitized_model = sanitize_model(model)
    client = YandexGPTApiClient(token=sanitized_model["api_key"])
    response = client.completion(
        request=CompletionRequest(
            messages=[Message(role="user",text="2+2=")]
        )
    )
    return response.alternatives[0].message.text


def summarize_chat_history(task: str, messages: List[Dict[str, str]], model: Model):
    """
    Summarize the chat history using the model endpoint and returning the response.
    """

    sanitized_model = sanitize_model(model)
    client = YandexGPTApiClient(token=sanitized_model["api_key"])
    summarization_system_prompt = f"""
    You are a helpful assistant that is able to review the chat history between a set of agents (userproxy agents, assistants etc) as they try to address a given TASK and provide a summary. Be SUCCINCT but also comprehensive enough to allow others (who cannot see the chat history) understand and recreate the solution.

    The task requested by the user is:
    ===
    {task}
    ===
    The summary should focus on extracting the actual solution to the task from the chat history (assuming the task was addressed) such that any other agent reading the summary will understand what the actual solution is. Use a neutral tone and DO NOT directly mention the agents. Instead only focus on the actions that were carried out (e.g. do not say 'assistant agent generated some code visualization code ..'  instead say say 'visualization code was generated ..' ).
    """
    response = client.completion(
        request=CompletionRequest(
            messages=[
        
                Message(
                    role="system",
                    text=summarization_system_prompt,
                ),
                Message(
                    role="user",
                    text=f"Summarize the following chat history. {str(messages)}",
                ),
            ]
        )
    )
    return response.alternatives[0].message.text
