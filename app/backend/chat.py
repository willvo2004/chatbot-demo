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
from config import get_settings
import tiktoken
import os
from dotenv import load_dotenv

load_dotenv()
settings = get_settings()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Will be whatever deployment to frontend will be
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def initialize_clients():
    project = AIProjectClient.from_connection_string(
        conn_str=settings.CONNECTION_STRING, credential=DefaultAzureCredential()
    )

    search_connection = project.connections.get_default(
        connection_type=ConnectionType.AZURE_AI_SEARCH, include_credentials=True
    )

    index_client = SearchIndexClient(
        endpoint=search_connection.endpoint_url, credential=AzureKeyCredential(key=search_connection.key)
    )

    search_client = SearchClient(
        index_name=settings.AZURE_SEARCH_INDEX,
        endpoint=search_connection.endpoint_url,
        credential=AzureKeyCredential(key=search_connection.key),
    )

    return project, search_client, index_client


project, search_client, index_client = initialize_clients()
chat = project.inference.get_chat_completions_client()


class ChatQuery(BaseModel):
    query: str


class SearchResult(BaseModel):
    content: str
    source: str
    score: float


def get_embeddings(text: str) -> List[float]:
    try:
        messages = [
            {
                "role": "system",
                "content": """You are an AI assistant that generates search queries for Nestlé website content. 
                Given a user query, infer the user's intent and provide a search query. Format a JSON response 
                with a search_query field that would best find relevant information. 
                Examples: {"search_query": "Does Nestle sell kitkat chocolate"}""",
            },
            {"role": "user", "content": text},
        ]

        intent_response = chat.complete(model="gpt-4o-mini", messages=messages, temperature=0.7, max_tokens=150)
        search_query = intent_response.choices[0].message.content
        embeddings = project.inference.get_embeddings_client()
        response = embeddings.embed(model="text-embedding-ada-002", input=search_query, encoding_format="float")

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


def truncate_context(context_list: List[SearchResult], max_tokens: int = 600) -> Tuple[str, List[Dict]]:
    """Truncate context to fit within token limit while preserving the most relevant information."""
    truncated_contexts = []
    sources = []
    total_tokens = 0

    system_prompt = """You are a helpful assistant for the Nestlé website. 
    Use the provided context to answer questions accurately. 
    If you're not sure about something, say so rather than making assumptions.
    Always maintain a professional and friendly tone."""

    # Reserve tokens for system prompt, user query, and response
    reserved_tokens = count_tokens(system_prompt) + 250  # 150 for query and formatting
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
        Use the provided context to answer questions accurately and structure your responses like a product information card:

        1. Start with a direct answer to the question
        2. List specific product variations with their details in bullet points
        3. Include nutritional information when available
        4. Add a reference link when relevant
        
        Format your response as a JSON object with these fields:
        {
            "mainAnswer": "The primary response to the question",
            "productDetails": [
                {
                    "name": "Product name/variant",
                    "details": ["Detail 1", "Detail 2"]
                }
            ],
            "referenceLink": "URL or text reference",
            "followUpInfo": "Additional relevant information (optional)"
        }

        Example for calories question:
        {
            "mainAnswer": "The calorie content of a KitKat bar varies depending on the size and type:",
            "productDetails": [
                {
                    "name": "KITKAT 4-Finger Wafer Bar, Milk Chocolate (45 g)",
                    "details": ["Calories: 230 per bar"]
                },
                {
                    "name": "KITKAT mini Chocolate Wafer Bars Pack of 30",
                    "details": ["Calories: 100 per 2 bars (25g)"]
                }
            ],
            "referenceLink": "For more information, visit our nutrition page",
            "followUpInfo": "Calorie content may vary by region and recipe"
        }"""

        user_prompt = f"""Context: {context_text}\n\nQuestion: {query}\n\n
        Please provide a concise answer based on the context provided."""
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


def needs_context(query: str) -> bool:
    """Determine if a query needs context from the knowledge base."""
    query = query.lower().strip()

    # Patterns that indicate general/meta questions about the chatbot
    general_patterns = [
        "you",
        "your",
        "chatbot",
        "bot",
        "ai",
        "assistant",
        "help",
        "hello",
        "hi",
        "hey",
        "greetings",
        "what can",
        "how do",
        "who are",
        "what are",
    ]

    # Check if query is primarily about the chatbot itself
    if any(pattern in query for pattern in general_patterns):
        return False

    # Patterns that suggest we need Nestlé-specific context
    context_patterns = [
        "nestle",
        "nestlé",
        "product",
        "recipe",
        "food",
        "chocolate",
        "candy",
        "ingredients",
        "nutrition",
        "where can i",
        "how much",
        "what is",
        "when",
    ]

    # Return True only if we have indication we need Nestlé context
    return any(pattern in query for pattern in context_patterns)


@app.post("/api/chat")
async def chat_endpoint(query: ChatQuery):
    if not needs_context(query.query):
        # Return response without context
        return {
            "answer": "Hello! I am an AI assistant for the Made with Nestlé website. I can help you find recipes, cooking tips, and answer questions about Nestlé products.",
            "sources": [],  # Empty sources array
        }
    try:
        query_embedding = get_embeddings(query.query)
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
