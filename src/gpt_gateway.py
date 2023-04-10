# database engine
import os
from pydantic import BaseModel
from typing import List, Optional, Union
from enum import Enum
import datetime
from hnapi import PrefixSession
from retry import retry
from dbmodels import StorySummary, HackerNewsStory
import requests

class Source(str, Enum):
    email = "email"
    file = "file"
    chat = "chat"
    web  = "web"


class DocumentMetadata(BaseModel):
    source: Optional[Source] = None
    source_id: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[str] = None
    author: Union[str, List[str]] = None
    title: Optional[str] = None
    description: Optional[str] = None
    

class Document(BaseModel):
    id: Optional[str] = None
    text: str
    metadata: Optional[DocumentMetadata] = None

    
class UpsertRequest(BaseModel):
    documents: List[Document]


class DocumentMetadataFilter(BaseModel):
    document_id: Optional[str] = None
    source: Optional[Source] = None
    source_id: Optional[str] = None
    author: Optional[str] = None
    start_date: Optional[str] = None  # any date string format
    end_date: Optional[str] = None  # any date string format
    title: Optional[str] = None



class Query(BaseModel):
    query: str
    filter: Optional[DocumentMetadataFilter] = None
    top_k: Optional[int] = 3
    
class QueryRequest(BaseModel):
    queries: List[Query]



GPTG_API_KEY = os.environ['GPTG_API_KEY']


hnsummary_collection = PrefixSession('https://hackernews-summary.gpt-gateway.com')


def upsert(ss : StorySummary, hns : HackerNewsStory):
    """
    send the content of the story and story summary to the hackernews-summary embedding collection on gpt-gateway.com
    """
    resp = requests.post(f"https://api.gpt-gateway.com/gpt-gateway-v1/auth", json={'key': GPTG_API_KEY})
    gptg_jwt = resp.json()['jwt']
    hnsummary_collection.headers.update({"authorization": f"Bearer {gptg_jwt}"})

    
    document_id = f"hn-summary:{ss.id}"
    
    rsp = hnsummary_collection.get(f'/docs/{document_id}')
    assert(rsp.status_code == 200)
    if rsp.json():
        print(f'{document_id} already in collection')
        return

    
    dt = datetime.datetime.utcfromtimestamp(hns.time)
    iso_date = dt.isoformat()
    source_id = f"https://news.ycombinator.com/item?id={hns.id}"
    summary = ss.summary.strip()

    if not summary or summary.isspace():
        return
    description = f"The text is a summary of an article that was posted to Hacker News on the created_at date by user '{hns.by}' and summarized by model '{ss.model}'."

    dm = DocumentMetadata(source='web',
                          source_id=source_id,
                          url=hns.url,
                          title=hns.title,
                          description=description,
                          created_at=iso_date)
    doc = Document(id=document_id,
                   text=summary,
                   metadata=dm)

    ur = UpsertRequest(documents=[doc])
    print(doc.dict())
            
    @retry(tries=6)
    def post():
        rsp = hnsummary_collection.post('/upsert', json=ur.dict())
        print(rsp.content)
        if rsp.status_code >= 500:
            raise Exception('post failed')
    try:
        post()
    except Exception as e:
        print(f"upsert failed ({e})")

