# update existing summaries with gpt-3.5-turbo

from __future__ import annotations

import logging
import os
from sqlmodel import Session, create_engine, SQLModel, select
from dbmodels import *
import hnapi
import openai



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



def update():   
    with Session(engine) as session:
        top_ids = hnapi.get_topstories()
        stories = session.exec(select(HackerNewsStory).where(HackerNewsStory.id.in_(top_ids))).all()
        stories = {s.id : s for s in stories}
        for sid in top_ids:
            try:
                story = stories[sid]
            except:
                continue
            summaries = session.exec(select(StorySummary).where(StorySummary.story_id == story.id)).all()
            if not summaries: continue
            if len(summaries) == 2: 
                continue

            MODEL = "gpt-3.5-turbo"
            prompt = summaries[0].prompt
            completion = openai.ChatCompletion.create(model=MODEL,
                                                       messages=[{'role':'user','content': prompt}],
                                                       temperature=.2)
            summary_text = completion['choices'][0]['message']['content']

            logger.info(f"output length:  {len(summary_text)}")

            summary = StorySummary(story_id = story.id,
                                   model    = MODEL,
                                   prompt   = prompt,
                                   summary  = summary_text)  
            print(summary_text)
            session.add(summary)
            session.commit()            
update()