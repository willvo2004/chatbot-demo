import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
import httpx

app = FastAPI()
load_dotenv()
SEARCH_AUTH = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_ADMIN_KEY")

assert SEARCH_AUTH is not None
assert SEARCH_KEY is not None


class UserQuery(BaseModel):
    query: str


# Initialize search client (using your service endpoint and key)
search_client = SearchClient(
    endpoint=SEARCH_AUTH,
    index_name="product-index",
    credential=AzureKeyCredential(SEARCH_KEY),
)


async def call_openai(prompt: str) -> str:
    # Example call to Azure OpenAI:
    connection_string = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_KEY")
    endpoint = connection_string
    headers = {"Content-Type": "application/json", "api-key": api_key}
    payload = {"prompt": prompt, "max_tokens": 500, "temperature": 0.7}

    async with httpx.AsyncClient() as client:
        assert endpoint is not None
        response = await client.post(endpoint, headers=headers, json=payload)
        response_json = response.json()
        return response_json["choices"][0]["text"].strip()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust to specific frontend URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat")
async def ask(user_query: str):
    # Retrieve top documents from search
    results = search_client.search(user_query, top=3)
    docs = [doc for doc in results]

    # Extract content and build context
    context = "\n".join(
        [d.get("name", "") + ": " + d.get("brand", "") + " - " + str(d.get("nutrients", "")) for d in docs]
    )

    # Construct a prompt for OpenAI
    prompt = f"""
    You are a product assistant. Use the following context to answer the question.
    Context:
    {context}

    Question: {user_query}
    Answer:
    """

    answer = await call_openai(prompt)
    return {"answer": answer, "sources": [d.get("url") for d in docs]}
