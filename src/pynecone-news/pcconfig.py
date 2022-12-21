import os
import pynecone as pc


# DB Config
db_host = os.environ['HNSUM_POSTGRES_HOST']
user    = os.environ['HNSUM_POSTGRES_USER']
passwd  = os.environ['HNSUM_POSTGRES_PASS']

DBURI = 'postgresql+psycopg2://%s:%s@%s:5432/hnsum' % (user, passwd, db_host)

config = pc.Config(
    app_name="pynecone_news",
    db_url=DBURI,
    env=pc.Env.DEV,
)
