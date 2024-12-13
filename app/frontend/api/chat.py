from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ConnectionType
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.identity import DefaultAzureCredential
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from azure.search.documents.models import VectorizedQuery
from typing import List, Tuple, Dict
from pydantic.main import BaseModel
import tiktoken
import os
from dotenv import load_dotenv

load_dotenv()


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Will be whatever deployment to frontend will be
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

project_connection_string = os.getenv("CONNECTION_STRING")
assert project_connection_string is not None

project = AIProjectClient.from_connection_string(
    conn_str=project_connection_string, credential=DefaultAzureCredential()
)

search_connection = project.connections.get_default(
    connection_type=ConnectionType.AZURE_AI_SEARCH, include_credentials=True
)

index_client = SearchIndexClient(
    endpoint=search_connection.endpoint_url, credential=AzureKeyCredential(key=search_connection.key)
)

search_client = SearchClient(
    index_name="product-vector-index",
    endpoint=search_connection.endpoint_url,
    credential=AzureKeyCredential(key=search_connection.key),
)


class ChatQuery(BaseModel):
    query: str


class SearchResult(BaseModel):
    content: str
    source: str
    score: float


def get_embeddings(text: List[str]) -> List[float]:
    try:
        embeddings = project.inference.get_embeddings_client()
        response = embeddings.embed(model="text-embedding-ada-002", input=text, encoding_format="float")

        floats_array = response.data[0].embedding
        return floats_array
    except Exception as e:
        print(f"Error generating embeddings {str(e)}")


def search_documents(query_vector: List[float], top_k: int = 3) -> List[SearchResult]:
    """Search documents using vector similarity in Azure Cognitive Search."""
    try:
        vector_query = VectorizedQuery(vector=query_vector, k_nearest_neighbors=top_k, fields="text_vector")

        results = search_client.search(
            search_text=None, vector_queries=[vector_query], select=["chunk", "title", "chunk_id", "parent_id"]
        )

        search_results = []
        for result in results:
            search_results.append(
                SearchResult(content=result["chunk"], source=result["parent_id"], score=result["@search.score"])
            )

        return search_results
    except Exception as e:
        print(f"Error searching documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to search documents")


def count_tokens(text: str) -> int:
    """Count the number of tokens in a text string."""
    try:
        encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        return len(encoding.encode(text))
    except Exception as e:
        print(f"Error counting tokens: {str(e)}. Using approximate count.")
        # Fallback to approximate count if tiktoken fails
        return int(len(text.split()) * 1.3)


def truncate_context(context_list: List[SearchResult], max_tokens: int = 500) -> Tuple[str, List[Dict]]:
    """Truncate context to fit within token limit while preserving the most relevant information."""
    truncated_contexts = []
    sources = []
    total_tokens = 0

    system_prompt = """You are a helpful assistant for the Nestlé website. 
    Use the provided context to answer questions accurately. 
    If you're not sure about something, say so rather than making assumptions.
    Always maintain a professional and friendly tone."""

    # Reserve tokens for system prompt, user query, and response
    reserved_tokens = count_tokens(system_prompt) + 150  # 150 for query and formatting
    remaining_tokens = max_tokens - reserved_tokens

    for result in sorted(context_list, key=lambda x: x.score, reverse=True):
        context_entry = f"Content: {result.content}\nSource: {result.source}"
        context_tokens = count_tokens(context_entry)

        if total_tokens + context_tokens <= remaining_tokens:
            truncated_contexts.append(context_entry)
            sources.append({"content": result.content, "source": result.source, "score": result.score})
            total_tokens += context_tokens
        else:
            # Try to fit a truncated version of the content
            words = result.content.split()
            for i in range(len(words), 0, -1):
                truncated_content = " ".join(words[:i])
                context_entry = f"Content: {truncated_content}\nSource: {result.source}"
                if count_tokens(context_entry) + total_tokens <= remaining_tokens:
                    truncated_contexts.append(context_entry)
                    sources.append({"content": truncated_content, "source": result.source, "score": result.score})
                    break
            break

    return "\n".join(truncated_contexts), sources


def generate_response(query: str, context: List[SearchResult]) -> str:
    """Generate response using Azure OpenAI with retrieved context."""
    try:
        # Prepare context from search results
        context_text, used_sources = truncate_context(context)
        # Create the prompt
        system_prompt = """You are a helpful assistant for the Nestlé website. 
        Use the provided context to answer questions accurately. 
        If you're not sure about something, say so rather than making assumptions.
        Always maintain a professional and friendly tone."""

        user_prompt = f"""Context: {context_text}\n\nQuestion: {query}\n\n
        Please provide a concise answer based on the context provided."""
        chat = project.inference.get_chat_completions_client()
        response = chat.complete(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.7,
            max_tokens=300,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating response: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate response")


@app.post("/api/chat")
async def chat_endpoint(query: ChatQuery):
    try:
        query_embedding = get_embeddings(list(query.query))
        search_results = search_documents(query_embedding)
        answer = generate_response(query.query, search_results)

        return {
            "answer": answer,
            "sources": [
                {"content": result.content, "source": result.source, "score": result.score} for result in search_results
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
