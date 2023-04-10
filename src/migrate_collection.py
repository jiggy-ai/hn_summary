# database engine
import os
from sqlmodel import create_engine, SQLModel, Session, exists

from pydantic import BaseModel
from typing import List, Optional, Union
from enum import Enum
from extract_metadata import extract_metadata_from_document
import datetime
from hnapi import PrefixSession
from retry import retry
from gpt_gateway import upsert
from db import engine
from dbmodels import StorySummary, HackerNewsStory


if __name__ == "__main__":

    with Session(engine) as session:
        #hns = session.get(StorySummary, 11249)
        #print(f'"{hns.summary}"')
        for ss in session.query( StorySummary ).order_by( StorySummary.id.desc() ):
            hns = session.get(HackerNewsStory, ss.story_id)
            try:
                upsert(ss, hns)
            except:
                pass
    
