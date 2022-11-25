<p align="center">
<img src="https://github.com/jiggy-ai/hn_summary/blob/master/HN_Summary.jpg" alt="HN Summary Bot avatar" width=256> 
</p>

**HN Summary**  is an open source bot which sumarizes top stories on Hacker News and publishes the summaries to a Telegram channel.

Whenever a new story appears on the Hacker News API /topstories.json endpoint, this bot summarizes it (currently using OpenAI GPT-3 text-davinci-002) and sends the Story title, summary, and url to the hn_summary channel on Telegram.

The purpose of this project is to build intuition on the capabilities of current generation of large language models while making a broader swath of top Hacker News content accessible.

Join the HN Summary channel on Telegram to see the bot in action and enjoy the story summaries.

https://t.me/hn_summary

## Limitations

Large language models such as GPT-3 are prone to hallucinations and sometimes make things up while writing in a very authoritative tone.

The code for extracting text from html is very basic and error prone. (PR's welcome.)  In addition many sites (such as news sites) are either paywalled or make it difficult to extract text. 

Links to PDFs or content other than HTML is currently ignored.

Text extraction from github and twitter links is broken.  

Telegram messages are limited to 4K. Currently the response is truncated to 4K.

See [examples.md](https://github.com/jiggy-ai/hn_summary/blob/master/examples.md) for a few examples of the output.

## Major Dependencies

**OpenAI**

* OPENAI_API_KEY # your OpenAI API key


**PostgresQL** 

Database for keeping track of items we have already seen and associated item info.

The following environment variables are used to inject database info and credentials for the database:


- HNSUM_POSTGRES_HOST  # The database FQDN
- HNSUM_POSTGRES_USER  # The database username
- HNSUM_POSTGRES_PASS  # The database password

**Telegram**
  
* HNSUM_TELEGRAM_API_TOKEN # The bot's telegram API token



