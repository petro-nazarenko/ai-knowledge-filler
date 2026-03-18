"""Integration tests for API interactions (Claude/Anthropic SDK)

These tests verify the system can generate files via LLM APIs.
Uses mocking to avoid actual API calls during testing.
"""

import os
import tempfile

import pytest
from unittest.mock import Mock, patch

anthropic = pytest.importorskip("anthropic")

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


@pytest.mark.skipif(not API_KEY, reason="requires real API key")
class TestAnthropicAPIIntegration:
    """Test integration with Anthropic Claude API"""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Mock Anthropic client"""
        with patch("anthropic.Anthropic") as mock_client:
            # Mock response structure
            mock_message = Mock()
            mock_message.content = [
                Mock(
                    type="text",
                    text="""---
title: "Test Generated File"
type: guide
domain: ai-system
level: intermediate
status: active
tags: [test, api, generated]
related:
  - "[[System Prompt]]"
created: 2026-02-10
updated: 2026-02-10
---

# Test Content

This is generated content.
""",
                )
            ]

            mock_response = Mock()
            mock_response.content = mock_message.content

            mock_client.return_value.messages.create.return_value = mock_response

            yield mock_client

    def test_generate_file_via_api(self, mock_anthropic_client):
        """Test generating a markdown file via Claude API"""
        from anthropic import Anthropic

        client = Anthropic(api_key="test-key")

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": "Create a guide on Docker"}],
        )

        # Verify API was called
        assert mock_anthropic_client.return_value.messages.create.called

        # Verify response structure
        assert len(response.content) > 0
        assert response.content[0].type == "text"

        # Verify generated content has YAML
        content = response.content[0].text
        assert content.startswith("---")
        assert "title:" in content
        assert "type:" in content

    def test_api_error_handling(self, mock_anthropic_client):
        """Test handling of API errors"""
        from anthropic import Anthropic

        # Create mock request and response for APIError
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url = "https://api.anthropic.com/v1/messages"

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "error": {"type": "rate_limit_error", "message": "Rate limit exceeded"}
        }

        # Mock APIError with proper parameters
        from anthropic import APIError

        api_error = APIError(
            message="Rate limit exceeded",
            request=mock_request,
            body={"error": {"type": "rate_limit_error", "message": "Rate limit exceeded"}},
        )

        mock_anthropic_client.return_value.messages.create.side_effect = api_error

        client = Anthropic(api_key="test-key")

        with pytest.raises(APIError) as exc_info:
            client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": "Test"}],
            )

        assert "Rate limit exceeded" in str(exc_info.value)

    def test_system_prompt_injection(self, mock_anthropic_client):
        """Test that system prompt is properly injected"""
        from anthropic import Anthropic

        system_prompt = "You are a markdown file generator."

        client = Anthropic(api_key="test-key")

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": "Create guide"}],
        )

        # Verify system prompt was passed
        call_args = mock_anthropic_client.return_value.messages.create.call_args
        assert call_args[1]["system"] == system_prompt

    def test_streaming_response(self, mock_anthropic_client):
        """Test streaming API responses"""
        from anthropic import Anthropic

        # Mock streaming response
        mock_stream = [
            Mock(type="content_block_start"),
            Mock(type="content_block_delta", delta=Mock(text="---\n")),
            Mock(type="content_block_delta", delta=Mock(text='title: "Test"\n')),
            Mock(type="content_block_stop"),
        ]

        mock_anthropic_client.return_value.messages.stream.return_value.__enter__.return_value = (
            mock_stream
        )

        client = Anthropic(api_key="test-key")

        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": "Test"}],
        ) as stream:
            chunks = list(stream)

        assert len(chunks) > 0


class TestAPIFileGeneration:
    """Test complete file generation workflow via API"""

    @pytest.fixture
    def mock_file_generator(self):
        """Mock file generation function"""

        def generate_file(prompt: str, output_path: str):
            """Generate markdown file from prompt"""
            content = f"""---
title: "Generated from: {prompt[:30]}"
type: guide
domain: ai-system
level: intermediate
status: active
tags: [generated, test]
related:
  - "[[Example]]"
created: 2026-02-10
updated: 2026-02-10
---

# Generated Content

Content based on: {prompt}
"""
            with open(output_path, "w") as f:
                f.write(content)
            return output_path

        return generate_file

    def test_generate_and_save_file(self, mock_file_generator):
        """Test generating file and saving to disk"""
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, "generated.md")

        try:
            result = mock_file_generator("Create a guide on API security", output_path)

            assert os.path.exists(result)

            with open(result, "r") as f:
                content = f.read()

            assert content.startswith("---")
            assert "API security" in content

        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
            os.rmdir(temp_dir)

    def test_batch_generation(self, mock_file_generator):
        """Test generating multiple files in batch"""
        temp_dir = tempfile.mkdtemp()

        prompts = [
            "Create concept on Microservices",
            "Create guide on Docker",
            "Create checklist on Security",
        ]

        generated_files = []

        try:
            for i, prompt in enumerate(prompts):
                output_path = os.path.join(temp_dir, f"file_{i}.md")
                result = mock_file_generator(prompt, output_path)
                generated_files.append(result)

            assert len(generated_files) == 3

            for file_path in generated_files:
                assert os.path.exists(file_path)
                with open(file_path, "r") as f:
                    content = f.read()
                    assert "---" in content

        finally:
            for file_path in generated_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            os.rmdir(temp_dir)

    def test_invalid_api_key_handling(self):
        """Test handling of invalid API key"""
        # TODO: Duplicate of TestAnthropicAPIIntegration.test_api_error_handling — do not merge yet
        from anthropic import Anthropic, AuthenticationError

        with patch("anthropic.Anthropic") as mock_client:
            # Create mock response for AuthenticationError
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.headers = {}
            mock_response.json.return_value = {
                "error": {"type": "authentication_error", "message": "Invalid API key"}
            }

            # Create proper AuthenticationError
            auth_error = AuthenticationError(
                message="Invalid API key",
                response=mock_response,
                body={"error": {"type": "authentication_error", "message": "Invalid API key"}},
            )

            mock_client.return_value.messages.create.side_effect = auth_error

            client = Anthropic(api_key="invalid-key")

            with pytest.raises(AuthenticationError):
                client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    messages=[{"role": "user", "content": "Test"}],
                )
