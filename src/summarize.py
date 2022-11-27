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
import logging
import urllib.parse

from dbmodels import HackerNewsStory, StorySummary
import hnapi
from github_api import github_readme_text
import telegram_bot


# the model we use for summarization
OPENAI_ENGINE="text-davinci-002"

# The temperature passed to the language model; higher values closer to 1 allow the model to choose
# less probable words.  a value of 0 is results in deterministic but potentially less creative results.
MODEL_TEMPERATURE=0.2


MAX_INPUT_TOKENS=2800   # the maximum number of input tokens we will process 
MAX_OUTPUT_TOKENS=880   # the maximum number of output tokens we will request


# the PROMPT_PREFIX is prepended to the url content before sending to the language model
PROMPT_PREFIX = "Provide a detailed summary of the following web page, including what type of content it is (e.g. news article, essay, technical report, blog post, product documentation, content marketing, etc). If there is anything controversial please highlight the controversy. If there is something surprising, unique, or clever, please highlight that as well:\n"

# prompt prefix for Github Readme files
GITHUB_PROMPT_PREFIX = "Provide a summary of the following github project readme file, including the purpose of the project, what problems it may be used to solve, and anything the author mentions that differentiates this project from others:"



# Configure Logging
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(filename)s %(lineno)4d %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


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
    message =  f"*{story.title}*\n"
    message += f"https://news.ycombinator.com/item?id={story.id}\n"
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

    if "html" not in resp.headers['Content-Type']:
        raise Exception(f"Unsupported content type: {resp.headers['Content-Type']}")

    if resp.status_code != 200:
        raise Exception(f"Unable to get URL ({resp.status_code})")

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
            logger.info(story)
            session.add(story)
            session.commit()
            
            if not story.url:
                logger.info(f"{story.title} has no url to summarize")
                continue

            HOPELESS = ["youtube.com",
                        "www.youtube.com"]
            if urllib.parse.urlparse(story.url).netloc in HOPELESS:
                logger.info(f"skipping hopeless {story.url}")
                continue
            
            # we have a url to process
            try:
                story_text, percentage_used = url_to_truncated_text_content(story.url, MAX_INPUT_TOKENS)
            except Exception as e:
                logger.exception(f"Error processing: {story}")
                continue
            logger.info(f"input length:   {len(story_text)}")
            
            prompt = compose_prompt(story, story_text, percentage_used < 100)

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
            logger.info(f"output length:  {len(summary_text)}")
            telegram_bot.send_message(message)

            

if __name__ == "__main__":
    logger.info("init")
    while True:
        try:
            process_news()
        except Exception as e:
            logger.exception("process_news")
        logger.info("sleeping...")
        sleep(60)

