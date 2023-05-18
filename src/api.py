# serves news.jiggy.ai

from __future__ import annotations

import logging
from typing import List, Optional
from pydantic import conint
from time import sleep
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

import textwrap
wrapper = textwrap.TextWrapper(width=80)

import threading

HTML_RESPONSE = ""

ANALYTICS = """<!-- Global site tag (gtag.js) - Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-WQ986DBSZV"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'G-WQ986DBSZV');
</script>"""

def update_html():
    logger.info("update")
    result = f"<html>{ANALYTICS}"
    result += "Sponsored by <a href=https://jiggy.ai>JiggyBase</a>.  JiggyBase is ChatGPT powered by your data!<br><br>"
    result += "Join <a href=https://t.me/hn_summary>HN Summary</a> channel on Telegram to view realtime summaries of top HN Stories.<br>"
    result += "Results are from open source <a href=https://github.com/jiggy-ai/hn_summary>HN Summary</a> bot.<BR><br>"
    
    count = 0
    t0 = time()
    
    with Session(engine) as session:
        top30_ids = hnapi.get_topstories()[:100]
        stories = session.exec(select(HackerNewsStory).where(HackerNewsStory.id.in_(top30_ids))).all()
        stories = {s.id : s for s in stories}
        for sid in top30_ids:
            try:
                story = stories[sid]
            except:
                continue
            summaries = session.exec(select(StorySummary).where(StorySummary.story_id == story.id)).all()
            result += f"<b>{story.title}</b><br>"
            result += f"<a href={story.url}>{story.url}</a><br>"
            ycurl   = f"https://news.ycombinator.com/item?id={story.id}"            
            result += f"<a href={ycurl}>{ycurl}</a><br>"
            result += f"<a href=/prompt/{sid}>model prompt</a><br>"
            summaries.sort(key=lambda x: x.model)
            for summary in summaries:
                if not summary: continue
                result += f"{summary.model}:<br>"
                word_list = wrapper.wrap(text=summary.summary)
                for element in word_list:
                    result += element + "<br>"
                result += "<br>"
            result += "<br>"                
    result += "</html>"
    global HTML_RESPONSE
    HTML_RESPONSE = result
    logger.info(f"update {time()-t0} seconds")
    
    
def background():
    while True:
        try:
            update_html()
        except exception as e:
            logger.exception(e)
        sleep(120)

threading.Thread(target=background).start()


@app.get('/', response_class=HTMLResponse)
def get_root():
    return HTML_RESPONSE


@app.get('/prompt/{story_id}', response_class=HTMLResponse)
def get_prompt(story_id: str = Path(...)):
    with Session(engine) as session:
        summary = session.exec(select(StorySummary).where(StorySummary.story_id == story_id)).first()
        if not summary:
            return "None"
        return summary.prompt
