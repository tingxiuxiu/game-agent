import os
import json
import requests
from typing import List, Dict, Any, Iterator, Optional, Union
from dataclasses import dataclass, field
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .logger import get_logger, log_api_call

logger = get_logger(__name__)

load_dotenv()


@dataclass
class Message:
    role: str
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class LLMAPIError(Exception):
    pass


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3,
    ):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        self.base_url = base_url or os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1/chat/completions")
        self.model = model or os.getenv("NVIDIA_MODEL", "meta/llama-4-maverick-17b-128e-instruct")
        self.timeout = timeout
        self.max_retries = max_retries
        self.conversation_history: List[Message] = []

        if not self.api_key:
            raise ValueError("API key must be provided either via parameter or NVIDIA_API_KEY environment variable")

    def add_message(self, role: str, content: str) -> None:
        self.conversation_history.append(Message(role=role, content=content))

    def add_user_message(self, content: str) -> None:
        self.add_message("user", content)

    def add_assistant_message(self, content: str) -> None:
        self.add_message("assistant", content)

    def clear_conversation(self) -> None:
        self.conversation_history = []

    def get_conversation_history(self) -> List[Dict[str, str]]:
        return [msg.to_dict() for msg in self.conversation_history]

    @log_api_call
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException, LLMAPIError)),
    )
    def _make_request(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs: Any
    ) -> Union[Dict[str, Any], Iterator[str]]:
        logger.info(f"Making API request to {self.model}, stream={stream}")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if stream else "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            **kwargs,
        }

        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
                stream=stream,
            )
            response.raise_for_status()
            logger.debug(f"API request successful, status code: {response.status_code}")

            if stream:
                return self._stream_response(response)
            else:
                return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise LLMAPIError(f"API request failed: {str(e)}") from e

    def _stream_response(self, response: requests.Response) -> Iterator[str]:
        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        parsed = json.loads(data)
                        if "choices" in parsed and len(parsed["choices"]) > 0:
                            delta = parsed["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                    except json.JSONDecodeError:
                        continue

    def chat_completion(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        stream: bool = False,
        use_conversation_history: bool = True,
        **kwargs: Any
    ) -> Union[str, Iterator[str]]:
        if messages is None:
            messages = []

        if use_conversation_history:
            full_messages = self.get_conversation_history() + messages
        else:
            full_messages = messages

        if stream:
            return self._chat_completion_stream(full_messages, **kwargs)
        else:
            return self._chat_completion_non_stream(full_messages, **kwargs)

    def _chat_completion_non_stream(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        response = self._make_request(messages, stream=False, **kwargs)
        if "choices" in response and len(response["choices"]) > 0:
            content = response["choices"][0]["message"]["content"]
            self.add_assistant_message(content)
            return content
        raise LLMAPIError("Unexpected response format from API")

    def _chat_completion_stream(self, messages: List[Dict[str, str]], **kwargs: Any) -> Iterator[str]:
        full_content = []
        for chunk in self._make_request(messages, stream=True, **kwargs):
            full_content.append(chunk)
            yield chunk
        self.add_assistant_message("".join(full_content))
