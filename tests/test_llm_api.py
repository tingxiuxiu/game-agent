import pytest
from unittest.mock import patch, MagicMock
import json
from typing import Iterator
from tenacity import RetryError

from game_agent.llm_api import LLMClient, Message, LLMAPIError


class TestMessage:
    def test_message_to_dict(self):
        msg = Message(role='user', content='test content')
        assert msg.to_dict() == {'role': 'user', 'content': 'test content'}


class TestLLMClient:
    def test_initialization_with_api_key(self):
        client = LLMClient(api_key='test_key')
        assert client.api_key == 'test_key'
        assert client.conversation_history == []

    @patch('game_agent.llm_api.os.getenv')
    def test_initialization_from_env(self, mock_getenv):
        mock_getenv.side_effect = lambda key, default=None: {
            'NVIDIA_API_KEY': 'env_key',
            'NVIDIA_BASE_URL': 'https://test.url',
            'NVIDIA_MODEL': 'test-model'
        }.get(key, default)
        
        client = LLMClient()
        assert client.api_key == 'env_key'
        assert client.base_url == 'https://test.url'
        assert client.model == 'test-model'

    @patch('game_agent.llm_api.os.getenv')
    def test_initialization_no_api_key(self, mock_getenv):
        mock_getenv.return_value = None
        with pytest.raises(ValueError):
            LLMClient(api_key=None)

    def test_add_message(self):
        client = LLMClient(api_key='test_key')
        client.add_message('user', 'hello')
        client.add_message('assistant', 'hi')
        assert len(client.conversation_history) == 2
        assert client.conversation_history[0].role == 'user'
        assert client.conversation_history[1].role == 'assistant'

    def test_add_user_message(self):
        client = LLMClient(api_key='test_key')
        client.add_user_message('test user message')
        assert len(client.conversation_history) == 1
        assert client.conversation_history[0].role == 'user'

    def test_add_assistant_message(self):
        client = LLMClient(api_key='test_key')
        client.add_assistant_message('test assistant message')
        assert len(client.conversation_history) == 1
        assert client.conversation_history[0].role == 'assistant'

    def test_clear_conversation(self):
        client = LLMClient(api_key='test_key')
        client.add_user_message('hello')
        client.clear_conversation()
        assert len(client.conversation_history) == 0

    def test_get_conversation_history(self):
        client = LLMClient(api_key='test_key')
        client.add_user_message('hello')
        client.add_assistant_message('hi')
        history = client.get_conversation_history()
        assert len(history) == 2
        assert history[0] == {'role': 'user', 'content': 'hello'}
        assert history[1] == {'role': 'assistant', 'content': 'hi'}

    @patch('game_agent.llm_api.requests.post')
    def test_chat_completion_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'test response'}}]
        }
        mock_post.return_value = mock_response
        
        client = LLMClient(api_key='test_key')
        result = client.chat_completion(messages=[{'role': 'user', 'content': 'hello'}], use_conversation_history=False)
        assert result == 'test response'

    @patch('game_agent.llm_api.requests.post')
    def test_chat_completion_with_history(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'test response'}}]
        }
        mock_post.return_value = mock_response
        
        client = LLMClient(api_key='test_key')
        client.add_user_message('previous message')
        result = client.chat_completion(messages=[{'role': 'user', 'content': 'new message'}])
        
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert len(payload['messages']) == 2
        assert payload['messages'][0]['content'] == 'previous message'
        assert payload['messages'][1]['content'] == 'new message'

    @patch('game_agent.llm_api.requests.post')
    def test_chat_completion_api_error(self, mock_post):
        import requests
        mock_post.side_effect = requests.exceptions.RequestException('API down')
        
        client = LLMClient(api_key='test_key')
        with pytest.raises(RetryError):
            client.chat_completion(messages=[{'role': 'user', 'content': 'hello'}], use_conversation_history=False)

    @patch('game_agent.llm_api.requests.post')
    def test_chat_completion_unexpected_format(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'invalid': 'response'}
        mock_post.return_value = mock_response
        
        client = LLMClient(api_key='test_key')
        with pytest.raises(LLMAPIError):
            client.chat_completion(messages=[{'role': 'user', 'content': 'hello'}], use_conversation_history=False)

    @patch('game_agent.llm_api.requests.post')
    def test_chat_completion_stream(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_lines.return_value = [
            b'data: {"choices":[{"delta":{"content":"t"}}]}',
            b'data: {"choices":[{"delta":{"content":"e"}}]}',
            b'data: {"choices":[{"delta":{"content":"s"}}]}',
            b'data: {"choices":[{"delta":{"content":"t"}}]}',
            b'data: [DONE]',
        ]
        mock_post.return_value = mock_response
        
        client = LLMClient(api_key='test_key')
        result = client.chat_completion(messages=[{'role': 'user', 'content': 'hello'}], stream=True, use_conversation_history=False)
        
        full_content = []
        for chunk in result:
            full_content.append(chunk)
        
        assert ''.join(full_content) == 'test'
        assert len(client.conversation_history) == 1
        assert client.conversation_history[0].content == 'test'

    @patch('game_agent.llm_api.requests.post')
    def test_stream_response_skip_invalid_json(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_lines.return_value = [
            b'data: invalid json',
            b'data: {"choices":[{"delta":{"content":"valid"}}]}',
            b'data: [DONE]',
        ]
        mock_post.return_value = mock_response
        
        client = LLMClient(api_key='test_key')
        result = client.chat_completion(messages=[{'role': 'user', 'content': 'hello'}], stream=True, use_conversation_history=False)
        
        full_content = []
        for chunk in result:
            full_content.append(chunk)
        
        assert ''.join(full_content) == 'valid'
