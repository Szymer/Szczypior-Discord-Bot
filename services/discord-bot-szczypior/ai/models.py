from langchain_openai import ChatOpenAI
from langchain_openrouter import ChatOpenRouter
from langchain_google_genai import ChatGoogleGenerativeAI




def get_chat_model(model_name: str):
    if model_name == "gpt-4o-mini":
        return ChatOpenAI(model="gpt-4o-mini")
    elif model_name == "gpt-3.5-turbo":
        return ChatOpenAI(model="gpt-3.5-turbo")
    elif model_name == "gemini-3.1-flash-lite":
        return ChatGoogleGenerativeAI(model="models/gemini-3.1-flash-lite-preview")
    elif model_name == "gemini-1.5-pro":
        return ChatGoogleGenerativeAI(model="gemini-1.5-pro")
    else:
        raise ValueError(f"Unsupported model: {model_name}")
    
