from langchain_openai import ChatOpenAI
from langchain_openrouter import ChatOpenRouter
from langchain_google_genai import ChatGoogleGenerativeAI




def get_chat_model(model_name: str, temperature: float | None = None) -> ChatOpenAI | ChatGoogleGenerativeAI:
    if model_name == "gpt-4o-mini":
        model = ChatOpenAI(model="gpt-4o-mini", temperature=temperature if temperature is not None else 0.2)
    elif model_name == "gpt-3.5-turbo":
        model = ChatOpenAI(model="gpt-3.5-turbo", temperature=temperature if temperature is not None else 0.2)
    elif model_name == "gemini-3.1-flash-lite":
        model = ChatGoogleGenerativeAI(model="models/gemini-3.1-flash-lite-preview", temperature=temperature if temperature is not None else 0.2)
    elif model_name == "gemini-1.5-pro":
        model = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=temperature if temperature is not None else 0.2  )
    else:
        raise ValueError(f"Unsupported model: {model_name}")

    return model
