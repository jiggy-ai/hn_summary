##
## Summarize new Hacker News top stories as they appear using GPT-3 API and
## send the summaries to a telegram Channel
##

import os
from sqlmodel import Session, create_engine, SQLModel, select, delete
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


# DB Config
db_host = os.environ['HNSUM_POSTGRES_HOST']
user    = os.environ['HNSUM_POSTGRES_USER']
passwd  = os.environ['HNSUM_POSTGRES_PASS']

DBURI = 'postgresql+psycopg2://%s:%s@%s:5432/hnsum' % (user, passwd, db_host)

engine = create_engine(DBURI, pool_pre_ping=True, echo=False)

# Create DB Engine
SQLModel.metadata.create_all(engine)

PROMPT_PREFIX = "Provide a detailed summary of the following web content, including what type of content it is (e.g. news article, essay, technical report, blog post, product documentation, content marketing, etc). If the content looks like an error message, respond 'content unavailable'. If there is anything controversial please highlight the controversy. If there is something surprising, unique, or clever, please highlight that as well:\n"

tokenizer = GPT2Tokenizer.from_pretrained("gpt2")


import openai

# The temperature passed to the language model; higher values closer to 1 allow the model to choose
# less probable words.  a value of 0 is results in deterministic but potentially less creative results.
MODEL_TEMPERATURE=0.2
MAX_OUTPUT_TOKENS=700   # the maximum number of output tokens we will request

        

session = Session(engine)

top_stories = hnapi.get_topstories()


ALL_MODELS = {'text-davinci-002', 'text-davinci-003'}

    
for story in session.exec(select(HackerNewsStory).where(HackerNewsStory.id.in_(top_stories))).all():
    summaries = session.exec(select(StorySummary).where(StorySummary.story_id == story.id)).all()
    if not summaries: continue
    models = set([s.model for s in summaries])
    missing_models = ALL_MODELS - models
    prompt = summaries[0].prompt
    if not prompt: continue
    print(story.id, prompt)
    for model in list(missing_models):
        print(model)
        completion = openai.Completion.create(engine=model,
                                              prompt=prompt,
                                              temperature=MODEL_TEMPERATURE,
                                              max_tokens=MAX_OUTPUT_TOKENS)
        
        summary_text = completion.choices[0].text

        summary = StorySummary(story_id = story.id,
                               model    = model,
                               prompt   = prompt,
                               summary  = summary_text)
        session.add(summary)
        session.commit()
        print()
        print(summary_text)
        break
                             
    
