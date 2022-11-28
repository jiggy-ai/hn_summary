# HTTP API to hn_summary

from __future__ import annotations

import logging
from typing import List, Optional
from pydantic import conint

from fastapi import FastAPI, Path, Query, HTTPException, UploadFile, File, Depends
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer 
from fastapi.routing import APIRouter
from fastapi.responses import Response
from time import time
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3 import Retry
import os
from sqlmodel import Session, create_engine, SQLModel, select
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.exc import MultipleResultsFound
from datetime import datetime
import hnapi

from dbmodels import *




# Configure Logging
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(filename)s %(lineno)4d %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


# DB Config
db_host = os.environ['HNSUM_POSTGRES_HOST']
user    = os.environ['HNSUM_POSTGRES_USER']
passwd  = os.environ['HNSUM_POSTGRES_PASS']

DBURI = 'postgresql+psycopg2://%s:%s@%s:5432/hnsum' % (user, passwd, db_host)
engine = create_engine(DBURI, pool_pre_ping=True, echo=False)


app = FastAPI(
    title='news-api',
    version='0.0',
    summary='Jiggy News API',
    description='',
    contact={},
    servers=[{'url': 'https://news.jiggy.ai/'}],
)


    
@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)


top_stories = hnapi.get_topstories()
last_top_stories = time()


def cached_top_stories():
    global top_stories
    global last_top_stories
    if (time() - last_top_stories) > 60:
        top_stories = hnapi.get_topstories()
        last_top_stories = time()
    return top_stories
    

@app.get('/', response_class=HTMLResponse)
def get_root():
    result = "<html>"
    count = 0
    t0 = time()

    
    with Session(engine) as session:
        top30_ids = top_stories[:30]
        stories = session.exec(select(HackerNewsStory).where(HackerNewsStory.id.in_(top30_ids))).all()
        summaries = session.exec(select(StorySummary).where(StorySummary.story_id.in_(top30_ids))).all()
        summaries = {s.story_id: s for s in summaries}
        for story in stories:
            #result += f"<a href={story.url}>{story.title}</a><br>"
            result += f"<b>{story.title}</b><br>"
            result += f"<a href={story.url}>{story.url}</a><br>"
            ycurl   = f"https://news.ycombinator.com/item?id={story.id}"            
            result += f"<a href={ycurl}>{ycurl}</a><br>"
            try:
                result += summaries[story.id].summary + "<br><br>"
            except:
                result += "(no summary)<br><br>"
    result += "</html>"
    logger.info(f"{time()-t0} s")
    return result
