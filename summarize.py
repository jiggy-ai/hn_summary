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


# the tokenizer for helping to enforce the MAX_INPUT_TOKENS constraint
# GPT3 apparently uses the same tokenizer as gpt2
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")


def compose_prompt(title, story_text, truncated=False):
    # compose the prompt that will be fed to the language model
    prompt = PROMPT_PREFIX
    prompt += f"Title: {title}\n"
    prompt += story_text
    if truncated:
        prompt += "<truncated>"
    return prompt


def compose_message(story, summary_text, percentage_used):
    # compose the message that will be sent to the chat
    message = story.title + "\n"
    message += f"https://news.ycombinator.com/item?id={story.id}\n"
    message += summary_text.lstrip()
    if percentage_used < 100:
        message += "(Summary based on {percentage_used}% of story text.)\n"
    return message




def extract_text_from_html(content):
    soup = BeautifulSoup(content, 'html.parser')
    text = soup.find_all(text=True)
    output = ''
    blacklist = ['[document]','noscript','header','html','meta','head','input','script', "style"]
    # there may be more elements you don't want

    for t in text:
        if t.parent.name not in blacklist:
            output += '{} '.format(t)
    return output


def url_to_text_content(url, max_tokens):
    """
    query the url and return the text content, subject to max_tokens
    Uses GPT tokenizer to truncate the text to max_tokens
    raises exception if unable to adequately parse content
    returns the text and int percentage (0-100) of the text that was used to make the
    """
    resp = requests.get(url)

    if "html" not in resp.headers['Content-Type']:
        raise Exception(f"Unsupported content type: {resp.headers['Content-Type']}")

    if resp.status_code != 200:
        raise Exception("Unable to get URL")

    doc = Document(resp.text)
    text = extract_text_from_html(doc.summary())
    
    if not len(text) or text.isspace():
        raise Exception("Unable to extract text data from url")
    
    token_count = len(tokenizer(text)['input_ids'])
    
    if token_count > max_tokens:
        # crudely truncate longer texts to get it back down to approximately the target MAX_INPUT_TOKENS
        # TODO: enhance to truncate at sentence boundaries using actual token counts
        split_point = int((float(MAX_INPUT_TOKENS)/token_count)*len(text))
        percent = int(100*split_point/len(text))
        text = text[:split_point]
    else:
        percent = 100
        
    print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print(url)
    print(text)
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    return text, percent



def process_news():
    # get the top stories and process any new ones we haven't seen before
    with Session(engine) as session:    
        for story_id in hnapi.get_topstories():
            story = session.get(HackerNewsStory, story_id)
            if story:
                continue
            # we haven't seen this story before, add it to the database and process it

            item = hnapi.get_item(story_id)
            story = HackerNewsStory(**item)

            print(story)    
            session.add(story)
            session.commit()
            
            if not story.url:
                print(f"{story.title} has no url to summarize")
                continue
            print(story.title)

            # we have a url to process
            try:
                story_text, percentage_used = url_to_text_content(story.url, MAX_INPUT_TOKENS)
            except Exception as e:
                print("Error processing: ", story.url)
                print(e)
                continue

            prompt = compose_prompt(story.title, story_text, percentage_used < 100)

            completion = openai.Completion.create(engine=OPENAI_ENGINE,
                                                  prompt=prompt,
                                                  temperature=MODEL_TEMPERATURE,
                                                  max_tokens=MAX_OUTPUT_TOKENS)
            summary_text = completion.choices[0].text

            message = compose_message(story, summary_text, percentage_used)

            summary = StorySummary(story_id = story.id,
                                   model    = OPENAI_ENGINE,
                                   prompt   = prompt,
                                   summary  = summary_text)
            
            session.add(summary)
            session.commit()
            telegram_bot.send_message(message)

            
process_news()
"""
if __name__ == "__main__":
    while True:
        try:
            process_news()
        except Exception as e:
            print(e)
        sleep(60)
"""
