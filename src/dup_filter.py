# filter duplicates via various mechanisms

import os
import logging
from db import engine
from sqlmodel import Session, select

from dbmodels import HackerNewsStory, StorySummary


# maintain sets of all titles and urls we have seen
# (eventually migrate these to db index or embedding index)
titles = set()
urls = set()
    
def add(story):
    titles.add(story.title)
    urls.add(story.url)


def is_duplicate(story):
    """
    return true if the story is a duplicate of those we have already seen
    add this story to the set of stories seen
    """
    dup = story.title in titles or story.url and story.url in urls
    add(story)
    return dup


# add all db items at startup
with Session(engine) as session:    
    for story in session.exec(select(HackerNewsStory)):
        add(story)
        


