#!/usr/bin/env python3.9

##
## Get the prompt used for the specific story
##

import os
import sys
from sqlmodel import Session, create_engine, SQLModel, select, delete
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.exc import MultipleResultsFound

from dbmodels import HackerNewsStory, StorySummary


# DB Config
db_host = os.environ['HNSUM_POSTGRES_HOST']
user    = os.environ['HNSUM_POSTGRES_USER']
passwd  = os.environ['HNSUM_POSTGRES_PASS']

DBURI = 'postgresql+psycopg2://%s:%s@%s:5432/hnsum' % (user, passwd, db_host)

engine = create_engine(DBURI, pool_pre_ping=True, echo=False)

# Create DB Engine
SQLModel.metadata.create_all(engine)

    
sid = sys.argv[-1]

with Session(engine) as session:
    for summary in session.exec(select(StorySummary).where(StorySummary.story_id == sid)):
        print("\nvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv\n")
        print(summary.prompt)
