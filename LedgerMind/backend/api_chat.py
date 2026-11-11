# backend/api_chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from integrations import recall_context, remember_interaction
from backend.stubs import answer_question

router = APIRouter(prefix="/api/chat", tags=["chat"])

class ChatRequest(BaseModel):
    question: str
    user_id: int = 1

@router.post("/")
def ask_ledgermind(request: ChatRequest):
    # 1. Recall past context using the Hindsight API
    past_memories = recall_context(query=request.question, limit=3)
    
    # 2. Combine question and memory (Member 1 will handle this deeply later)
    enriched_question = f"Context: {past_memories}\nQuestion: {request.question}"
    
    # 3. Get the answer from the AI Agent (using stub for now)
    try:
        ai_response = answer_question(enriched_question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Agent failed: {str(e)}")
    
    # 4. Save the interaction back to Hindsight so the agent remembers it next time
    memory_text = f"User asked: {request.question} | LedgerMind answered: {ai_response.get('answer')}"
    remember_interaction(text=memory_text, metadata={"user_id": request.user_id, "type": "chat"})
    
    return {
        "question": request.question,
        "answer": ai_response.get("answer"),
        "sources": ai_response.get("sources", []),
        "hindsight_memories_used": len(past_memories)
    }