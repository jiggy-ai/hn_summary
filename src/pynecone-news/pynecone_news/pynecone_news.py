"""Welcome to Pynecone! This file outlines the steps to create a basic app."""
from pcconfig import config
from typing import Optional
import pynecone as pc
from .hnapi import get_topstories


from sqlmodel import Field, SQLModel


class HackerNewsStory(pc.Model, table=True):
    # partial state of HN Story item. See https://github.com/HackerNews/API#items
    # we dont include "type" since we are only recording type='story' here.    
    id:             int = Field(primary_key=True, description="The item's unique id.")
    by:             str = Field(index=True, description="The username of the item's author.")
    time:           int = Field(index=True, description="Creation date of the item, in Unix Time.")
    title:          str = Field(description="The title of the story, poll or job. HTML.")    
    text: Optional[str] = Field(description="The comment, story or poll text. HTML.")
    url:  Optional[str] = Field(description="The url associated with the Item.")


class StorySummary(pc.Model, table=True):
    id:       int = Field(primary_key=True, description="The summary unique id.")
    story_id: int = Field(index=True, description="The story id.")
    model:    str = Field(description="The model used to summarize a story")
    prompt:   str = Field(max_length=65535, description="The prompt used to create the summary.")
    summary:  str = Field(max_length=65535, description="The summary we got back from the model.")
    upvotes:  Optional[int] = Field(default=0, description="The number of upvotes for this summary.")
    votes:    Optional[int] = Field(default=0, description="The total number of votes for this summary.")
    


class Story(pc.Base):
    story: HackerNewsStory
    summaries: list[StorySummary] = []



from time import time

class State(pc.State):
    stories : list[Story] = []

    @pc.var
    def get_stories(self) -> list[Story]:
        self.stories = []
        print("BAR")
        t0 = time()
        with pc.session() as session:
            top30_ids = get_topstories()[:100]
            storiesl = session.exec(HackerNewsStory.select.where(HackerNewsStory.id.in_(top30_ids))).all()
            stories = {s.id : s for s in storiesl}
            #ss = session.exec(StorySummary.select.where(StorySummary.story_id.in_(top30_ids))).all()
            for sid in top30_ids:
                if sid in stories:
                    self.stories.append(Story(story = stories[sid]))
        print(time()-t0)
        return self.stories



def story_text(story):
    return pc.text(story.story.title)

def index():
    print("FOO")                                   
    x = pc.vstack(pc.foreach(State.stories, story_text),
                  spacing="1em",
                  font_size="1em")
    return x
                                
    




# Add state and page to the app.
app = pc.App(state=State)
app.add_page(index)
app.compile()
