##
## Summarize new Hacker News top stories as they appear using GPT-3 API and
## send the summaries to a telegram Channel
##

import os
from sqlmodel import Session, create_engine, SQLModel, select
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.exc import MultipleResultsFound
from time import sleep
from bs4 import BeautifulSoup, NavigableString, Tag
from transformers import GPT2Tokenizer
import openai
from readability import Document    # https://github.com/buriy/python-readability
import string
import requests

from dbmodels import HackerNewsStory, StorySummary
import hnapi
import telegram_bot


# the model we use for summarization
OPENAI_ENGINE="text-davinci-002"

# The temperature passed to the language model; higher values closer to 1 allow the model to choose
# less probable words.  a value of 0 is results in deterministic but potentially less creative results.
MODEL_TEMPERATURE=0.2


MAX_INPUT_TOKENS=2800   # the maximum number of input tokens we will process 
MAX_OUTPUT_TOKENS=880   # the maximum number of output tokens we will request


# the PROMPT_PREFIX is prepended to the url content before sending to the language model
PROMPT_PREFIX = "Provide a detailed summary of the following web page, including what type of content it is (e.g. news article, essay, technical report, blog post, product documentation, content marketing, etc). If there is anything controversial please highlight the controversy. If there is something unique or clever, please highlight that as well:\n"



# DB Config
db_host = os.environ['HNSUM_POSTGRES_HOST']
user    = os.environ['HNSUM_POSTGRES_USER']
passwd  = os.environ['HNSUM_POSTGRES_PASS']

DBURI = 'postgresql+psycopg2://%s:%s@%s:5432/hnsum' % (user, passwd, db_host)

engine = create_engine(DBURI, pool_pre_ping=True, echo=False)

# Create DB Engine
SQLModel.metadata.create_all(engine)

import urllib.parse
from github_api import github_readme_text
with Session(engine) as session:
    #print(session.exec(select(StorySummary).where(StorySummary.story_id == 33754010)).first())
    for story in session.exec(select(HackerNewsStory)):
        if not story.url: continue        
        site = urllib.parse.urlparse(story.url).netloc
        if site != "github.com": continue
        print(story.id, story.url)
        #text = github_readme_text(story.url)



