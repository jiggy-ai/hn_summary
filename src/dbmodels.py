#
# database objects for persisting items
#

from typing import Optional

from sqlmodel import Field, SQLModel


class HackerNewsStory(SQLModel, table=True):
    # partial state of HN Story item. See https://github.com/HackerNews/API#items
    # we dont include "type" since we are only recording type='story' here.    
    id:             int = Field(primary_key=True, description="The item's unique id.")
    by:             str = Field(index=True, description="The username of the item's author.")
    time:           int = Field(index=True, description="Creation date of the item, in Unix Time.")
    title:          str = Field(description="The title of the story, poll or job. HTML.")    
    text: Optional[str] = Field(description="The comment, story or poll text. HTML.")
    url:  Optional[str] = Field(description="The url associated with the Item.")


class StorySummary(SQLModel, table=True):
    id:       int = Field(primary_key=True, description="The summary unique id.")
    story_id: int = Field(index=True, description="The story id.")
    model:    str = Field(description="The model used to summarize a story")
    prompt:   str = Field(max_length=65535, description="The prompt used to create the summary.")
    summary:  str = Field(max_length=65535, description="The summary we got back from the model.")
    upvotes:  Optional[int] = Field(default=0, description="The number of upvotes for this summary.")
    votes:    Optional[int] = Field(default=0, description="The total number of votes for this summary.")
    
