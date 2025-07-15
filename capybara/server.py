import datetime
import os
from typing import Any, Dict, List, Optional

# Load environment variables
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from prisma import Prisma

load_dotenv()

# --- Pydantic Models for Request and Response ---


class ConversationData(BaseModel):
    id: str
    name: str
    inputs: Dict[str, Any] = {}  # Returning empty dict as it's not in the DB schema
    status: str
    created_at: int
    updated_at: int


class ConversationResponse(BaseModel):
    limit: int
    has_more: bool
    data: List[ConversationData]


# --- FastAPI Application ---

app = FastAPI()
db = Prisma()

# --- Database Connection Events ---


@app.on_event("startup")
async def startup():
    """Connect to the database when the application starts."""
    await db.connect()


@app.on_event("shutdown")
async def shutdown():
    """Disconnect from the database when the application shuts down."""
    if db.is_connected():
        await db.disconnect()


# --- Authentication Dependency ---


async def get_token_header(authorization: str = Header(...)):
    """
    Dependency to validate the Authorization header.
    Checks for a 'Bearer' token.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization scheme. Use 'Bearer <token>'.",
        )
    return authorization.split(" ")[1]


# --- API Endpoints ---


@app.get(
    "/v1/conversations",
    response_model=ConversationResponse,
    summary="Get a list of conversations for a user",
)
async def get_conversations(
    user: str,
    last_id: Optional[str] = Query(
        None,
        description="The ID of the last item from the previous page for pagination.",
    ),
    limit: int = Query(20, ge=1, le=100, description="The number of items to return."),
    token: str = Depends(get_token_header),
):
    """
    Fetches a paginated list of conversations for a specific user.
    """
    if token != "hrai-4486e6088c5bbfaf88e90c8d5dce08ce":
        raise HTTPException(status_code=401, detail="Invalid token")
    query_options = {
        "where": {"user": user, "is_deleted": False},
        "take": limit + 1,  # Fetch one extra to check if there are more pages
        "order_by": {"created_at": "desc"},
    }

    if last_id:
        query_options["cursor"] = {"id": last_id}
        query_options["skip"] = 1  # Skip the cursor item itself

    conversations = await db.conversation.find_many(**query_options)

    has_more = len(conversations) > limit
    results = conversations[:limit]

    response_data = [
        ConversationData(
            id=conv.id,
            name=conv.name,
            status="normal",  # 'is_deleted' is always false here
            created_at=int(conv.created_at.timestamp()),
            updated_at=int(conv.updated_at.timestamp()),
        )
        for conv in results
    ]

    return ConversationResponse(limit=limit, has_more=has_more, data=response_data)


# To run this server, use the command:
# uvicorn capybara.server:app --host 0.0.0.0 --port 8000 --reload
