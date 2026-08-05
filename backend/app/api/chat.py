from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Any, Optional
from ..services.graph_sync import Neo4jSyncService
from ..core.database import get_db
from sqlalchemy.orm import Session
import os

router = APIRouter()

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str
    cypher: str
    results: List[Any]

@router.post("/chat", response_model=ChatResponse)
def text_to_cypher(request: ChatRequest, db: Session = Depends(get_db)):
    """智能问数：将自然语言转换为 Cypher 并执行"""
    query = request.query
    
    # 1. 模拟 LLM 转换逻辑 (未来对接 GPT-4/DB-GPT)
    # 简单的 Prompt 设计思路：
    # System: 你是一个 Neo4j 专家。
    # Schema: (Entity {id, name})-[INSTANCE_OF]->(Concept {id, name}), (Concept)-[BELONGS_TO]->(Concept)
    # User: 帮我找一下属于“用电客户”分类下的所有实体。
    
    # 模拟简单的规则转换 (演示用)
    cypher = ""
    if "用电客户" in query and "实体" in query:
        cypher = "MATCH (e:Entity)-[:INSTANCE_OF]->(c:Concept {name: '用电客户'}) RETURN e.name as name, e.id as id"
    elif "设备" in query:
        cypher = "MATCH (e:Entity)-[:INSTANCE_OF]->(c:Concept) WHERE c.name CONTAINS '设备' RETURN e.name, c.name"
    else:
        # 默认查询所有实体和分类
        cypher = "MATCH (e:Entity)-[:INSTANCE_OF]->(c:Concept) RETURN e.name as entity, c.name as category LIMIT 10"

    # 2. 在 Neo4j 中执行 Cypher
    sync_service = Neo4jSyncService()
    try:
        with sync_service.driver.session() as session:
            result = session.run(cypher)
            records = [dict(record) for record in result]
            
            # 3. 构造回复
            return ChatResponse(
                answer=f"为您查询到以下关于“{query}”的数据：",
                cypher=cypher,
                results=records
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neo4j Query Error: {str(e)}")
    finally:
        sync_service.close()
