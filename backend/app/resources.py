import firebase_admin
import os
import asyncio
import weaviate

from dotenv import load_dotenv
from groq import AsyncGroq
from sentence_transformers import SentenceTransformer
from weaviate.classes.init import AdditionalConfig, Timeout


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

weaviate_url = os.getenv("WEAVIATE_URL")
weaviate_key = os.getenv("WEAVIATE_API_KEY")

groq_key = os.getenv("GROQ_API_KEY")
groq_model = os.getenv("GROQ_MODEL")

embedding_model = os.getenv("EMBEDDING_MODEL")

COLLECTION_NAME = os.getenv(
    "WEAVIATE_COLLECTION_NAME",
    "GGI_Knowledge_Base"
)


# ============================================================
# SHARED RESOURCES
# ============================================================

weaviate_client = None
groq_client = None
embedding_model_instance = None
firebase_app = None


# ============================================================
# RESOURCE INITIALIZATION
# ============================================================

async def initialize_resources():
    """
    Initialize all shared resources once at application startup.
    """

    global weaviate_client
    global groq_client
    global embedding_model_instance
    global firebase_app

    if any(resource is not None for resource in (
        weaviate_client,
        groq_client,
        embedding_model_instance,
        firebase_app
    )):
        raise RuntimeError("Resources are already initialized.")

    required_variables = {
        "WEAVIATE_URL": weaviate_url,
        "WEAVIATE_API_KEY": weaviate_key,
        "GROQ_API_KEY": groq_key,
        "GROQ_MODEL": groq_model,
        "EMBEDDING_MODEL": embedding_model
    }
    
   

    missing = [
        name for name, value in required_variables.items()
        if not value
    ]

    if missing:
        raise ValueError(
            f"Missing environment variables: {', '.join(missing)}"
        )

    client = None
    groq = None
    firebase = None

    try:

        
        # 4. Initialize Firebase Admin SDK
        firebase = firebase_admin.initialize_app()
        

        # 1. Weaviate asynchronous connection
        client = weaviate.use_async_with_weaviate_cloud(
            cluster_url=weaviate_url,
            auth_credentials=weaviate.auth.AuthApiKey(weaviate_key),
            additional_config=AdditionalConfig(
                timeout=Timeout(
                    init=30,
                    query=60,
                    insert=120
                )
            )
        )

        await client.connect()

        # 2. Groq asynchronous client
        groq = AsyncGroq(
            api_key=groq_key
        )

        # 3. Load embedding model without blocking event loop
        model = await asyncio.to_thread(
            SentenceTransformer,
            embedding_model
        )

        # Assign initialized resources
        weaviate_client = client
        groq_client = groq
        embedding_model_instance = model
        firebase_app = firebase

        print("All Wonka resources initialized successfully.")

    except Exception:
        if client is not None:
            await client.close()

        if groq is not None:
            await groq.close()

        
        if firebase is not None:
            firebase_admin.delete_app(firebase)
        raise

# ============================================================
# RESOURCE CLEANUP
# ============================================================

async def close_resources():
    """
    Close network clients and release model reference.
    """

    global weaviate_client
    global groq_client
    global embedding_model_instance
    global firebase_app

    if weaviate_client is not None:
        await weaviate_client.close()
        weaviate_client = None

    if groq_client is not None:
        await groq_client.close()
        groq_client = None

    embedding_model_instance = None

    if firebase_app is not None:
        firebase_admin.delete_app(firebase_app)
        firebase_app = None

    print("All Wonka resources closed successfully.")
