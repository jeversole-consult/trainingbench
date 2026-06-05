"""
Power Search module for querying external AI services (Gemini, ChatGPT, Grok).
"""

import os
import httpx
from typing import Dict, List, Optional
import asyncio


class PowerSearchService:
    """Service for querying multiple external AI providers."""

    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.grok_api_key = os.getenv("GROK_API_KEY", "")

        # API endpoints
        self.gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
        self.openai_endpoint = "https://api.openai.com/v1/chat/completions"
        self.grok_endpoint = "https://api.x.ai/v1/chat/completions"

    def get_available_services(self) -> List[str]:
        """Return list of services that have API keys configured."""
        services = []
        if self.gemini_api_key:
            services.append("gemini")
        if self.openai_api_key:
            services.append("chatgpt")
        if self.grok_api_key:
            services.append("grok")
        return services

    async def query_gemini(self, question: str, timeout: int = 60) -> Dict:
        """Query Google Gemini API."""
        if not self.gemini_api_key:
            return {
                "service": "gemini",
                "error": "Gemini API key not configured",
                "answer": None
            }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.gemini_endpoint}?key={self.gemini_api_key}",
                    json={
                        "contents": [{
                            "parts": [{
                                "text": question
                            }]
                        }]
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response")
                    return {
                        "service": "gemini",
                        "answer": answer,
                        "error": None,
                        "model": "gemini-pro"
                    }
                else:
                    return {
                        "service": "gemini",
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "answer": None
                    }
        except Exception as e:
            return {
                "service": "gemini",
                "error": str(e),
                "answer": None
            }

    async def query_chatgpt(self, question: str, model: str = "gpt-4o-mini", timeout: int = 60) -> Dict:
        """Query OpenAI ChatGPT API."""
        if not self.openai_api_key:
            return {
                "service": "chatgpt",
                "error": "OpenAI API key not configured",
                "answer": None
            }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.openai_endpoint,
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "user", "content": question}
                        ]
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("choices", [{}])[0].get("message", {}).get("content", "No response")
                    return {
                        "service": "chatgpt",
                        "answer": answer,
                        "error": None,
                        "model": model
                    }
                else:
                    return {
                        "service": "chatgpt",
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "answer": None
                    }
        except Exception as e:
            return {
                "service": "chatgpt",
                "error": str(e),
                "answer": None
            }

    async def query_grok(self, question: str, model: str = "grok-beta", timeout: int = 60) -> Dict:
        """Query xAI Grok API."""
        if not self.grok_api_key:
            return {
                "service": "grok",
                "error": "Grok API key not configured",
                "answer": None
            }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.grok_endpoint,
                    headers={
                        "Authorization": f"Bearer {self.grok_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "user", "content": question}
                        ]
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("choices", [{}])[0].get("message", {}).get("content", "No response")
                    return {
                        "service": "grok",
                        "answer": answer,
                        "error": None,
                        "model": model
                    }
                else:
                    return {
                        "service": "grok",
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "answer": None
                    }
        except Exception as e:
            return {
                "service": "grok",
                "error": str(e),
                "answer": None
            }

    async def query_multiple(self, question: str, services: List[str]) -> Dict:
        """
        Query multiple AI services in parallel.

        Args:
            question: The question to ask
            services: List of service names ("gemini", "chatgpt", "grok")

        Returns:
            Dictionary with results from each service
        """
        tasks = []

        for service in services:
            if service == "gemini":
                tasks.append(self.query_gemini(question))
            elif service == "chatgpt":
                tasks.append(self.query_chatgpt(question))
            elif service == "grok":
                tasks.append(self.query_grok(question))

        results = await asyncio.gather(*tasks)

        return {
            "question": question,
            "results": results,
            "services_queried": services
        }
