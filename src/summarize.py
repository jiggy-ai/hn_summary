##
## Summarize new Hacker News top stories as they appear using GPT-3 API and
## send the summaries to a telegram Channel
##

from langchain.docstore.document import Document as langchaindoc
from langchain.text_splitter import CharacterTextSplitter, TokenTextSplitter
from langchain.llms import OpenAI
from langchain import PromptTemplate
from langchain.chains.summarize import load_summarize_chain

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
#MODELS = ["text-davinci-003", "text-davinci-002"]
MODELS = ["text-davinci-003"]

# The temperature passed to the language model; higher values closer to 1 allow the model to choose
# less probable words.  a value of 0 is results in deterministic but potentially less creative results.
MODEL_TEMPERATURE=0.2


MAX_INPUT_TOKENS=2800   # the maximum number of input tokens we will process 
MAX_OUTPUT_TOKENS=700   # the maximum number of output tokens we will request

# Configure Logging
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(filename)s %(lineno)4d %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


llm = OpenAI(model=MODELS[0], temperature=MODEL_TEMPERATURE, max_tokens=MAX_OUTPUT_TOKENS)

# the prompt template for web content
REFINE_PROMPT_TMPL = (
    "Provide a detailed summary of the following web content, including what type of content it is "
    "(e.g. news article, essay, technical report, blog post, product documentation, content marketing, etc). "
    "If the content looks like an error message, respond 'content unavailable'. " 
    "If there is anything controversial please highlight the controversy. "
    "If there is something surprising, unique, or clever, please highlight that as well: "
    "We have provided an existing summary up to a certain point: {existing_answer}\n"
    "You have the opportunity to refine the existing summary "
    "(only if needed) with some more context below.\n"
    "------------\n"
    "{text}\n"
    "------------\n"
    "Given the new context, refine the original summary"
    "If the context isn't useful, return the original summary."
)
web_refine_prompt = PromptTemplate(
    input_variables=["existing_answer", "text"],
    template=REFINE_PROMPT_TMPL,
)


web_prompt_template = """
Provide a detailed summary of the following web content, including what type of content it is 
(e.g. news article, essay, technical report, blog post, product documentation, content marketing, etc). 
If the content looks like an error message, respond 'content unavailable'. 
If there is anything controversial please highlight the controversy. 
If there is something surprising, unique, or clever, please highlight that as well:
"{text}"
"""
PROMPT = PromptTemplate(template=web_prompt_template, input_variables=["text"])

web_prompt = PromptTemplate(template=web_prompt_template, 
                            input_variables=["text"])
 
web_chain = load_summarize_chain(llm, 
                                 chain_type="refine",
                                 question_prompt=web_prompt,
                                 refine_prompt=web_refine_prompt,
                                 return_intermediate_steps=False) # set to True for debugging
# prompt template for Github Readme files
github_prompt_template = """
Provide a summary of the following github project readme file, including the purpose of the project, 
what problems it may be used to solve, and anything the author mentions that differentiates this project from others:"
{text}
"""
print(github_prompt_template)
github_prompt = PromptTemplate(template=github_prompt_template, 
                                input_variables=["text"])
github_chain = load_summarize_chain(llm, 
                                 chain_type="refine", 
                                 question_prompt=web_prompt,
                                 refine_prompt=web_prompt,
                                 return_intermediate_steps=False) # set to True for debugging

# doesn't respect sentence boundaries
def token_chunker(text, chunk_size):
    text_splitter = TokenTextSplitter(chunk_size=chunk_size, chunk_overlap=0)
    texts = text_splitter.split_text(text)
    return texts

def summarize_web_url(url):
    try:
        text = get_url_text(url)
    except Exception as e:
        logger.exception(f"Error processing: {url}")
        raise
    logger.info(f"input length:   {len(text)}") 
    chunk_size = 4097 - MAX_OUTPUT_TOKENS - llm.get_num_tokens(web_prompt_template)
    texts = token_chunker(text, chunk_size)
    docs = [langchaindoc(page_content=t) for t in texts]
    print(chunk_size, len(text), len(docs))  
    ret = web_chain({"input_documents": docs}, return_only_outputs=True)
    print("ret", ret['output_text'])
    return ret['output_text'], text

def summarize_github_url(url):
    try:
        text = github_readme_text(url)
    except Exception as e:
        logger.exception(f"Error processing: {url}")
        raise
    logger.info(f"input length:   {len(text)}") 
    chunk_size = 4097 - MAX_OUTPUT_TOKENS - llm.get_num_tokens(github_prompt_template)
    texts = token_chunker(text, chunk_size)
    docs = [langchaindoc(page_content=t) for t in texts]
    print(chunk_size, len(text), len(docs))  
    ret = github_chain({"input_documents": docs}, return_only_outputs=True)
    print("ret", ret['output_text'])
    return ret['output_text'], text


# the tokenizer for helping to enforce the MAX_INPUT_TOKENS constraint
# GPT3 apparently uses the same tokenizer as gpt2
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

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


TOP_N_STORIES = 120   # only consider the top TOP_N_STORIES
logger.info(f"TOP_N_STORIES: {TOP_N_STORIES}")

def process_news():
    # get the top stories and process any new ones we haven't seen before
    with Session(engine) as session:    
        for story_id in hnapi.get_topstories()[:TOP_N_STORIES]:
            story = session.get(HackerNewsStory, story_id)
            if story:
                continue
            # we haven't seen this story before, add it to the database and process it

            item = hnapi.get_item(story_id)
            story = HackerNewsStory(**item)            
            logger.info(story)
            session.add(story)
            session.commit()

            if dup_filter.is_duplicate(story):
                logger.info(f"{story.id} is_duplicate")
                continue
                
            if not story.url:
                logger.info(f"{story.title} has no url to summarize")
                continue

            HOPELESS = ["youtube.com",
                        "www.youtube.com"]
            if urllib.parse.urlparse(story.url).netloc in HOPELESS:
                logger.info(f"skipping hopeless {story.url}")
                continue
            
            # we have a url to process          
            site = urllib.parse.urlparse(story.url).netloc
            if site == "github.com":
                summary_text, original_text = summarize_github_url(story.url)
            else:
                summary_text, original_text = summarize_web_url(story.url)

            logger.info(f"output length:  {len(summary_text)}")

            ###XXX not sure how to get the final prompt text
            summary = StorySummary(story_id = story.id,
                                    model    = MODELS[0],
                                    prompt   = original_text,
                                    summary  = summary_text)            
            session.add(summary)
            session.commit()

            message = compose_message(story, summary_text, 100)
            print(message)            
            telegram_bot.send_message(message)

if __name__ == "__main__":
    
    logger.info("init")
    while False:  #True:
        try:
            process_news()
        except Exception as e:
            logger.exception("process_news")
        logger.info("sleeping...")
        sleep(60)

