##
## Summarize new Hacker News top stories as they appear using GPT-3 API and
## send the summaries to a telegram Channel
##

import os
from sqlmodel import Session, select
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.exc import MultipleResultsFound
from time import sleep
from bs4 import BeautifulSoup, NavigableString, Tag
from transformers import GPT2Tokenizer
import openai
from readability import Document    # https://github.com/buriy/python-readability
import string
import requests
import logging
import urllib.parse

from dbmodels import HackerNewsStory, StorySummary
import hnapi
from github_api import github_readme_text
import telegram_bot
from pdf_text import pdf_text
from db import engine
import dup_filter

# the model we use for summarization
MODELS = ["text-davinci-003", "text-davinci-002"]

# The temperature passed to the language model; higher values closer to 1 allow the model to choose
# less probable words.  a value of 0 is results in deterministic but potentially less creative results.
MODEL_TEMPERATURE=0.2


MAX_INPUT_TOKENS=2800   # the maximum number of input tokens we will process 
MAX_OUTPUT_TOKENS=700   # the maximum number of output tokens we will request


# the PROMPT_PREFIX is prepended to the url content before sending to the language model
PROMPT_PREFIX = "Provide a detailed summary of the following web content, including what type of content it is (e.g. news article, essay, technical report, blog post, product documentation, content marketing, etc). If the content looks like an error message, respond 'content unavailable'. If there is anything controversial please highlight the controversy. If there is something surprising, unique, or clever, please highlight that as well:\n"

# prompt prefix for Github Readme files
GITHUB_PROMPT_PREFIX = "Provide a summary of the following github project readme file, including the purpose of the project, what problems it may be used to solve, and anything the author mentions that differentiates this project from others:"


# Configure Logging
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(filename)s %(lineno)4d %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)



# the tokenizer for helping to enforce the MAX_INPUT_TOKENS constraint
# GPT3 apparently uses the same tokenizer as gpt2
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")


def compose_prompt(story, story_text, truncated=False):
    # compose the prompt that will be fed to the language model
    site = urllib.parse.urlparse(story.url).netloc
    if site == "github.com":
        prompt = GITHUB_PROMPT_PREFIX
    else:
        prompt = PROMPT_PREFIX
    prompt += f"Title: {story.title}\n"
    prompt += f"Site: {site}\n"
    prompt += story_text
    if truncated:
        prompt += "<truncated>"
    return prompt


def compose_message(story, summary_text, percentage_used):
    # compose the message that will be sent to the channel
    message =  f"[{story.title}](https://news.ycombinator.com/item?id={story.id})\n"
    summary_text = summary_text.lstrip()
    if summary_text:
        message += summary_text
    else:
        message += "[Model failed to produce summary text]"
    if percentage_used < 100:
        message += f" (Summary based on {percentage_used}% of story text.)"
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


def get_url_text(url):
    """
    get url content and extract readable text
    returns the text
    """
    resp = requests.get(url, timeout=30)

    if resp.status_code != 200:
        raise Exception(f"Unable to get URL ({resp.status_code})")

    CONTENT_TYPE = resp.headers['Content-Type']
    
    if 'pdf' in CONTENT_TYPE:
        return pdf_text(resp.content)
    
    if "html" not in CONTENT_TYPE:
        raise Exception(f"Unsupported content type: {resp.headers['Content-Type']}")

    doc = Document(resp.text)
    text = extract_text_from_html(doc.summary())

    if not len(text) or text.isspace():
        raise Exception("Unable to extract text data from url")
    return text


def url_to_truncated_text_content(url, max_tokens):
    """
    return the text content associated with url, 
    truncating the content using GPT tokenizer to max_tokens length.
    raises exception if unable to get or adequately parse content
    returns the text and int percentage (0-100) of the text that was was used
    (e.g. percent=80 means that 20% of the content was discarded due to exceeding 
    max_tokens)
    """
    if urllib.parse.urlparse(url).netloc == 'github.com':
        # for github repos use api to attempt to find a readme file
        text = github_readme_text(url)
    else:
        text = get_url_text(url)

    # measure the text size in tokens
    token_count = len(tokenizer(text)['input_ids'])
    
    if token_count > max_tokens:
        # crudely truncate longer texts to get it back down to approximately the target MAX_INPUT_TOKENS
        # TODO: enhance to truncate at sentence boundaries using actual token counts
        split_point = int((float(MAX_INPUT_TOKENS)/token_count)*len(text))
        percent = int(100*split_point/len(text))
        text = text[:split_point]
    else:
        percent = 100        
    return text, percent



TOP_N_STORIES = 400   # only send messages for the top TOP_N_STORIES
logger.info(f"TOP_N_STORIES: {TOP_N_STORIES}")

current_top_stories = None
def update_top_stories():
    """
    update our story database to include new items in all of the hn api top stories
    this tries to guarantee that the currrent_top_stories is up to date and
    each story item has an entry in HackerNewsStory table
    """
    global current_top_stories
    current_top_stories = hnapi.get_topstories()
    
    with Session(engine) as session:
        for story_id in current_top_stories:
            if session.get(HackerNewsStory, story_id):
                continue  # already have it in the db
            item = hnapi.get_item(story_id)
            story = HackerNewsStory(**item)            
            logger.info(f"Found new story: {story}")
            session.add(story)
            session.commit()

def crawl_top_stories():
    """
    """
    

def process_new_story(story_id, rank):
    with Session(engine) as session:    
        item = hnapi.get_item(story_id)
        story = HackerNewsStory(**item)            
        logger.info(story)
        session.add(story)
        session.commit()

        if rank < TOP_N_STORIES:
            logger.info(f"{story.id} rankis_duplicate")            
            continue
        
        if dup_filter.is_duplicate(story):
            logger.info(f"{story.id} is_duplicate")
            return
                
        if not story.url:
            logger.info(f"{story.title} has no url to summarize")
            return

        HOPELESS = ["youtube.com",
                    "www.youtube.com"]
        if urllib.parse.urlparse(story.url).netloc in HOPELESS:
            logger.info(f"skipping hopeless {story.url}")
            return

        # we have a url to process
        try:
            story_text, percentage_used = url_to_truncated_text_content(story.url, MAX_INPUT_TOKENS)
        except Exception as e:
            logger.exception(f"Error processing: {story}")
            return
        logger.info(f"input length:   {len(story_text)}")

        prompt = compose_prompt(story, story_text, percentage_used < 100)

        for model in MODELS:
            completion = openai.Completion.create(engine=model,
                                                  prompt=prompt,
                                                  temperature=MODEL_TEMPERATURE,
                                                  max_tokens=MAX_OUTPUT_TOKENS)
            summary_text = completion.choices[0].text
            logger.info(f"output length:  {len(summary_text)}")

            summary = StorySummary(story_id = story.id,
                                   model    = model,
                                   prompt   = prompt,
                                   summary  = summary_text)            
            session.add(summary)
            session.commit()

            if model == "text-davinci-003":  # only send message for 003 model
                message = compose_message(story, summary_text, percentage_used)            
                telegram_bot.send_message(message)

            
def new_top_story_ids():
    """
    return (story_id, rank) for any new top stories
    """
    new_stories = []
    return new_stories

                            
def process_news():
    # get the top stories and process any new ones we haven't seen before
    for story_id, rank in new_top_story_ids():
        process_new_story(story_id, rank)


if __name__ == "__main__":
    logger.info("init")
    while True:
        try:
            process_news()
        except Exception as e:
            logger.exception("process_news")
        logger.info("sleeping...")
        sleep(60)

