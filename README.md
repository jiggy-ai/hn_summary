**HN Summary** is a simple bot which sumarizes top stories on Hacker News (https://news.ycombinator.com) using a large language model (currently OpenAI text-davinci-002) and sends the summaries to the hn_summary channel on Telegram.

Join the HN Summary channel on Telegram to see the bot in action and enjoy the story summaries.

https://t.me/hn_summary

## Limitations

The code for extracting text from html is very basic and error prone. (PR's welcome.)  In addition many sites (such as news sites) are either paywalled or make it difficult to extract text. 

Links to PDFs or content other than HTML is currently ignored.

Text extraction from github links is currently broken.

Telegram messages are limited to 4K. Currently the response is truncated to 4K.

## Major Dependencies


**PostgresQL** 

Database for keeping track of items we have already seen and associated item info.

The following environment variables are used to inject database info and credentials for the database:


- HNSUM_POSTGRES_HOST  # The database FQDN
- HNSUM_POSTGRES_USER  # The database username
- HNSUM_POSTGRES_PASS  # The database password


**Telegram**
  
* HNSUM_TELEGRAM_API_TOKEN # The bot's telegram API token
