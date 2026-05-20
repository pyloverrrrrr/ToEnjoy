import json
import logging

from fastapi import APIRouter, Depends, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.middleware.identity_router import get_request_context, RequestContext
from app.core.agent.orchestrator import Orchestrator
from app.models.conversation import Conversation
from app.schemas.chat import (
    ChatRequest,
    ChatHistoryItem,
    ChatHistoryResponse,
    ChatDetailMessage,
    ChatDetailResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])
orchestrator = Orchestrator()


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    background_tasks: BackgroundTasks,
    ctx: RequestContext = Depends(get_request_context),
):
    async def event_generator():
        full_response = ""
        try:
            async for chunk in orchestrator.run(
                message=req.message,
                role=ctx.role.value,
                role_value=ctx.role.value,
                session_id=req.session_id,
                user_id=ctx.user_id,
            ):
                if chunk.get("type") == "chunk":
                    full_response += chunk.get("content", "")
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            # Schedule memory save after streaming completes
            background_tasks.add_task(
                orchestrator.memory_service.save_turn,
                user_id=ctx.user_id,
                session_id=req.session_id,
                user_message=req.message,
                assistant_response=full_response,
                intent="chat",
            )
        except Exception as e:
            logger.exception(f"Chat stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': '系统繁忙，请稍后再试'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/history", response_model=ChatHistoryResponse)
async def chat_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    subq = (
        select(
            Conversation.session_id,
            func.min(Conversation.id).label("min_id"),
            func.count(Conversation.id).label("message_count"),
            func.max(Conversation.created_at).label("last_message_at"),
        )
        .where(Conversation.user_id == ctx.user_id)
        .group_by(Conversation.session_id)
        .subquery()
    )

    total_result = await db.execute(select(func.count()).select_from(subq))
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        select(subq.c.session_id, subq.c.message_count, subq.c.last_message_at, subq.c.min_id)
        .order_by(desc(subq.c.last_message_at))
        .offset(offset)
        .limit(page_size)
    )
    session_rows = result.all()

    items: list[ChatHistoryItem] = []
    for row in session_rows:
        first_msg_result = await db.execute(
            select(Conversation.content).where(Conversation.id == row.min_id)
        )
        first_msg = first_msg_result.scalar() or ""
        items.append(ChatHistoryItem(
            session_id=row.session_id,
            first_message=first_msg[:100] if first_msg else "",
            message_count=row.message_count,
            last_message_at=row.last_message_at.isoformat() if row.last_message_at else "",
        ))

    return ChatHistoryResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/history/{session_id}", response_model=ChatDetailResponse)
async def chat_detail(
    session_id: str,
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.session_id == session_id,
            Conversation.user_id == ctx.user_id,
        )
        .order_by(Conversation.created_at)
    )
    messages = result.scalars().all()

    return ChatDetailResponse(
        session_id=session_id,
        messages=[
            ChatDetailMessage(
                id=m.id,
                role=m.role,
                content=m.content,
                intent=m.intent,
                sources=m.sources,
                created_at=m.created_at.isoformat() if m.created_at else "",
            )
            for m in messages
        ],
    )


@router.delete("/session/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single session's conversations from MySQL and short-term memory from Redis."""
    import app.core.memory.short_term as stm

    await db.execute(
        select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.user_id == ctx.user_id,
        )
    )
    # Actually delete them
    result = await db.execute(
        select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.user_id == ctx.user_id,
        )
    )
    for conv in result.scalars().all():
        await db.delete(conv)
    await db.commit()

    # Clear short-term memory for this session
    try:
        short_term = stm.ShortTermMemory()
        await short_term.delete(session_id)
    except Exception:
        pass


@router.delete("/history", status_code=204)
async def clear_history(
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """Delete all conversation history, short-term, and long-term memory for the current user."""
    import app.core.memory.short_term as stm
    import app.core.memory.long_term as ltm

    # 1. Collect all unique session_ids BEFORE deleting conversations
    result = await db.execute(
        select(Conversation.session_id).where(Conversation.user_id == ctx.user_id).distinct()
    )
    session_ids = [row[0] for row in result.all()]

    # 2. Delete all conversations from MySQL for this user
    result = await db.execute(
        select(Conversation).where(Conversation.user_id == ctx.user_id)
    )
    for conv in result.scalars().all():
        await db.delete(conv)
    await db.commit()

    # 3. Clear short-term memory for every session (Redis keys)
    short_term = stm.ShortTermMemory()
    for sid in session_ids:
        try:
            await short_term.delete(sid)
        except Exception:
            pass

    # 4. Clear long-term memory from ChromaDB
    try:
        long_term = ltm.LongTermMemory()
        await long_term.delete_by_user(ctx.user_id)
    except Exception:
        pass

    logger.info(f"Cleared all history and memory for user {ctx.user_id} ({len(session_ids)} sessions)")
