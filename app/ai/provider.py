import os
import json
import requests
from app.ai.prompts import SYSTEM_PROMPT, STUCK_MODE_SYSTEM

class AIProvider:
    def get_response(self, prompt: str, context_json: str = None) -> str:
        raise NotImplementedError

    def get_stuck_response(self, stage: int, user_input: str) -> str:
        raise NotImplementedError


class LocalProvider(AIProvider):
    """Fallback offline local rule-based assistant."""
    def get_response(self, prompt: str, context_json: str = None) -> str:
        p = prompt.lower().strip()
        
        # Simple local conversational intents
        if any(x in p for x in ["hello", "hi", "hey", "greetings"]):
            return "Hello! I am FocusBuddy. How can I support your study or work session today?"
        
        if "how are you" in p:
            return "I'm doing great, thank you! Ready to help you stay focused and tackle your goals."
            
        if "thank you" in p or "thanks" in p:
            return "You're very welcome! I'm here to support you."
            
        if "help" in p:
            return ("You can ask me 'what's next?', 'what is my schedule today?', "
                    "'start a 25 minute focus session', or tell me 'I'm stuck' or 'I'm distracted'.")

        return "I understand. Let's keep making progress on our schedule today!"

    def get_stuck_response(self, stage: int, user_input: str) -> str:
        """
        Stage 0: Ask what the problem is.
        Stage 1: Ask what inputs and outputs are.
        Stage 2: Ask user to solve a small example manually.
        Stage 3: Give small conceptual hint.
        Stage 4: Give stronger hint.
        Stage 5: Give full solution (last resort).
        """
        prompts = {
            0: "Let's debug this together. Calm down and take a breath. What exactly is the problem you're trying to solve?",
            1: "Got it. Let's break it down. What are the inputs, and what is the expected output for this problem?",
            2: "Makes sense. Before writing any code or text, let's solve a simple example manually. Can you write down the step-by-step logic of how you'd get the output from a small input?",
            3: "Perfect! Now let's map that to a concept. Have you thought about what data structure or algorithm fits this best? (e.g. a loop, a hash map, or sorting?) Give it a quick try.",
            4: "Here is a stronger hint: Try writing a basic structure or pseudocode. If it's a loop, trace what variables change. Focus on the core logic block first.",
            5: "No worries! Here is the complete solution. Let's review it line-by-line so you can implement it and understand the logic: [Step 1: Parse the input. Step 2: Apply the algorithm. Step 3: Return the output.] You've got this!"
        }
        return prompts.get(stage, "Let's keep coding! What's the next task?")


# Backwards compatibility alias
RuleBasedProvider = LocalProvider


class GroqProvider(AIProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "llama-3.3-70b-versatile"

    def get_response(self, prompt: str, context_json: str = None) -> str:
        if not self.api_key:
            raise ValueError("Groq API key not configured.")
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        system_instruction = SYSTEM_PROMPT
        if context_json:
            system_instruction += f"\n\nCurrent Context:\n{context_json}"
            
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 200,
            "temperature": 0.7
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=8.0)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()

    def get_stuck_response(self, stage: int, user_input: str) -> str:
        if not self.api_key:
            raise ValueError("Groq API key not configured.")
            
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"The user is STUCK on a task. Current stuck wizard stage: {stage}/5. User's latest input: '{user_input}'. Guidelines: Stage 0: Prompt user to explain. Stage 1: Ask for input/output. Stage 2: Prompt small manual example. Stage 3: Give small conceptual hint (no code). Stage 4: Give stronger hint (e.g. pseudocode). Stage 5: Full solution. Generate response for Stage {stage} under 4 sentences."
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": STUCK_MODE_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 150,
            "temperature": 0.7
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=8.0)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "gemini-1.5-flash"

    def get_response(self, prompt: str, context_json: str = None) -> str:
        if not self.api_key:
            raise ValueError("Gemini API key not configured.")
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {
            "Content-Type": "application/json"
        }
        
        system_instruction = SYSTEM_PROMPT
        if context_json:
            system_instruction += f"\n\nCurrent Context:\n{context_json}"
            
        data = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "generationConfig": {
                "maxOutputTokens": 200,
                "temperature": 0.7
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=8.0)
        response.raise_for_status()
        result = response.json()
        
        # Parse response content
        return result["candidates"][0]["content"]["parts"][0]["text"].strip()

    def get_stuck_response(self, stage: int, user_input: str) -> str:
        if not self.api_key:
            raise ValueError("Gemini API key not configured.")
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {
            "Content-Type": "application/json"
        }
        
        prompt = f"The user is STUCK on a task. Current stuck wizard stage: {stage}/5. User's latest input: '{user_input}'. Guidelines: Stage 0: Prompt user to explain. Stage 1: Ask for input/output. Stage 2: Prompt small manual example. Stage 3: Give small conceptual hint (no code). Stage 4: Give stronger hint (e.g. pseudocode). Stage 5: Full solution. Generate response for Stage {stage} under 4 sentences."
        
        data = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": STUCK_MODE_SYSTEM}]
            },
            "generationConfig": {
                "maxOutputTokens": 150,
                "temperature": 0.7
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=8.0)
        response.raise_for_status()
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"].strip()


class OpenRouterProvider(AIProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "google/gemini-2.5-flash:free" # Default free model

    def get_response(self, prompt: str, context_json: str = None) -> str:
        if not self.api_key:
            raise ValueError("OpenRouter API key not configured.")
            
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/FocusBuddyAI",
            "X-Title": "FocusBuddy AI"
        }
        
        system_instruction = SYSTEM_PROMPT
        if context_json:
            system_instruction += f"\n\nCurrent Context:\n{context_json}"
            
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 200,
            "temperature": 0.7
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=8.0)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()

    def get_stuck_response(self, stage: int, user_input: str) -> str:
        if not self.api_key:
            raise ValueError("OpenRouter API key not configured.")
            
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/FocusBuddyAI",
            "X-Title": "FocusBuddy AI"
        }
        
        prompt = f"The user is STUCK on a task. Current stuck wizard stage: {stage}/5. User's latest input: '{user_input}'. Guidelines: Stage 0: Prompt user to explain. Stage 1: Ask for input/output. Stage 2: Prompt small manual example. Stage 3: Give small conceptual hint (no code). Stage 4: Give stronger hint (e.g. pseudocode). Stage 5: Full solution. Generate response for Stage {stage} under 4 sentences."
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": STUCK_MODE_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 150,
            "temperature": 0.7
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=8.0)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
