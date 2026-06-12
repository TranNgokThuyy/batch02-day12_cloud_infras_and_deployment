"""Small mock LLM used by the lab so no real API key is required."""
import random
import time


MOCK_RESPONSES = {
    "default": [
        "This is a mock AI response. In production this can call OpenAI or another LLM provider.",
        "The agent is running correctly. Ask another question to continue the conversation.",
        "Your question was received by the cloud-ready AI agent.",
    ],
    "docker": [
        "Docker packages the app and its dependencies so it runs the same way on a laptop and in the cloud."
    ],
    "deploy": [
        "Deployment is the process of moving code from your machine to a server or cloud platform."
    ],
    "health": [
        "The agent is healthy and ready for operational checks."
    ],
}


def ask(question: str, delay: float = 0.1) -> str:
    time.sleep(delay + random.uniform(0, 0.05))
    question_lower = question.lower()
    for keyword, responses in MOCK_RESPONSES.items():
        if keyword in question_lower:
            return random.choice(responses)
    return random.choice(MOCK_RESPONSES["default"])


def ask_stream(question: str):
    for word in ask(question).split():
        time.sleep(0.05)
        yield word + " "
