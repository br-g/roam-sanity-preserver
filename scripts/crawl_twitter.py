"""
Queries the latest tweets:
1) from some predefined accounts
2) mentioning some predefined accounts
3) containing some predefined hashtags
4) quoted or retweeted by tweets from 1), 2) or 3).

If you think some other accounts or hashtags should be added, please suggest it
on Slack or create a Github issue.

The following script uses both the Twitter API and Twint for the following
reasons:
- The Twitter API can't search for tweets older than 7 days
- Twint can't retrieve the tweet being quoted or retweeted.

Twint is a bit buggy in practice, so we sometimes use the Python package and
sometimes, the CLI. All in all, this seems to be working properly.

You can get Twitter credentials here: https://developer.twitter.com/en/docs/twitter-api
"""

from typing import Dict, List, Iterator, Tuple, Optional
import os
import re
from datetime import datetime, timedelta
import tempfile
import shutil
import json
from pathlib import Path
import pytz
import click
import twint
import twitter
from tqdm import tqdm
from loguru import logger
from roam_sanity.util import run_in_subprocess, save_as_json


HASHTAGS = [
    'roamcult',
    'RoamGames',
]

USERNAMES = [
    'Conaw',
    'RoamTemplates',
    'RoamBrain',
    'RoamStack',
    'RoamResearch',
]

parsing_time = datetime.now().astimezone(pytz.utc).isoformat()
api = None


def get_date_intervals(n_days: int) -> Iterator[Tuple[str, str]]:
    """Returns date intervals for querying day per day."""
    cur = datetime.now() + timedelta(days=1)

    for _ in range(n_days):
        prev = cur - timedelta(days=1)
        yield prev.strftime('%Y-%m-%d'), cur.strftime('%Y-%m-%d')
        cur = prev


def url_to_tweet_id(url: str) -> int:
    m = re.search(r'^https:\/\/\w*\.?twitter\.com\/[\w_]+\/status\/([\d]+).*$', url)
    if not m:
        raise ValueError(url)
    return int(m.group(1))


def get_tweet(tweet_id: int) -> twitter.models.Status:
    assert api
    return api.GetStatus(tweet_id)


def format_api_tweet(tweet: twitter.models.Status) -> Iterator[Dict]:
    def _date_to_iso(date: str) -> str:
        return pytz.utc.localize(
            datetime.strptime(date, '%a %b %d %H:%M:%S +0000 %Y')
        ).isoformat()

    yield {
        'source': 'twitter',
        'parsing_time': parsing_time,
        'create_time': _date_to_iso(tweet.created_at),
        'id': tweet.id_str,
        'lang': tweet.lang,
        'text': clean_up_text(tweet.full_text),
        'in_reply_to': tweet.in_reply_to_screen_name,
        'url': f'https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}',
        'author_screen_name': tweet.user.screen_name,
        'author_name': tweet.user.name,
    }


def format_twint_tweet(raw: Dict) -> Iterator[Dict]:
    def _date_to_iso(date: str) -> str:
        """The following is for the Paris timezone. You may need to change it."""
        if not date:
            return date

        try:
            dtm = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        except:
            dtm = datetime.strptime(date, '%Y-%m-%d')

        return pytz.timezone('Europe/Paris').localize(dtm).isoformat()

    # If retweet, consider the retweeted tweet instead
    if raw['retweet']:
        try:
            yield from format_api_tweet(get_tweet(raw['id']).retweeted_status)  # pylint: disable=no-member
        except twitter.error.TwitterError:  # If the tweet has been deleted
            pass
    else:
        yield {
            'source': 'twitter',
            'parsing_time': parsing_time,
            'create_time': _date_to_iso(raw['date']),
            'id': raw['id'],
            'conversation_id': raw['conversation_id'],
            'text': clean_up_text(raw['tweet']),
            'url': raw['link'],
            'author_screen_name': raw['username'],
            'author_name': raw['name'],
            'user_id': raw['user_id'],
            'lang': raw['language'],
            'urls': raw['urls'],
            'photos': raw['photos'],
            'hashtags': raw['hashtags'],
            'quote_url': raw['quote_url'],
            'video': raw['video'],
            'thumbnail': raw['thumbnail'],
            'user_rt_id': raw['user_rt_id'],
            'reply_to': [e['screen_name'] for e in raw['reply_to']],
        }

    # If there is a quote, also get the quoted tweet
    if raw['quote_url']:
        try:
            quoted_id = url_to_tweet_id(raw['quote_url'])
        except ValueError:
            return
        try:
            yield from format_api_tweet(get_tweet(quoted_id))
        except twitter.error.TwitterError:  # If the tweet has been deleted
            return


def query_twint_cli(cmd: str, since: Optional[str] = None,
                    until: Optional[str] = None) -> Iterator[Dict]:
    dirpath = Path(tempfile.mkdtemp())
    filepath = dirpath / 'res.jsonl'

    full_cmd = f'{cmd} -o {filepath} --json --hide-output'

    if since:
        full_cmd += f' --since {since}'
    if until:
        full_cmd += f' --until {until}'

    run_in_subprocess(full_cmd)

    # No results
    if not filepath.is_file():
        return

    with open(filepath) as f:
        for line in f:
            yield from format_twint_tweet(json.loads(line))

    shutil.rmtree(dirpath)


def query_twint_package(config, since: Optional[str] = None,
                        until: Optional[str] = None) -> Iterator[Dict]:
    config.Pandas = True
    config.Hide_output = True

    if since:
        config.Since = since
    if until:
        config.Until = until

    twint.run.Search(config)
    res_df = twint.storage.panda.Tweets_df
    res_dict = res_df.to_dict('records')

    for e in res_dict:
        yield from format_twint_tweet(e)


def query_user(username: str, *args, **kwargs) -> Iterator[Dict]:
    return query_twint_cli(f'twint -u {username} --timeline', *args, **kwargs)


def query_mentions(username: str, *args, **kwargs) -> Iterator[Dict]:
    """Returns tweets that mention a username"""
    config = twint.Config()
    config.Search = f'@{username}'
    return query_twint_package(config, *args, **kwargs)


def query_hashtag(hashtag: str, *args, **kwargs) -> Iterator[Dict]:
    config = twint.Config()
    config.Search = f'#{hashtag}'
    return query_twint_package(config, *args, **kwargs)


def clean_up_text(text: str) -> str:
    text = text.strip(' ')
    text = text.strip('\n')
    return text


def save_all(tweets: List[Dict]):
    for tw in tweets:
        save_as_json(tw)


@click.command()
@click.option('--n_days', type=int, default=1, nargs=1, show_default=True)
@click.option('--consumer_key', type=str, default=os.environ['RSP_TWITTER_CONSUMER_KEY'] if 'RSP_TWITTER_CONSUMER_KEY' in os.environ else None, nargs=1, show_default=False)
@click.option('--consumer_secret', type=str, default=os.environ['RSP_TWITTER_CONSUMER_SECRET'] if 'RSP_TWITTER_CONSUMER_SECRET' in os.environ else None, nargs=1, show_default=False)
@click.option('--access_token_key', type=str, default=os.environ['RSP_TWITTER_TOKEN_KEY'] if 'RSP_TWITTER_TOKEN_KEY' in os.environ else None, nargs=1, show_default=False)
@click.option('--access_token_secret', type=str, default=os.environ['RSP_TWITTER_TOKEN_SECRET'] if 'RSP_TWITTER_TOKEN_SECRET' in os.environ else None, nargs=1, show_default=False)
def main(n_days: int, *args, **kwargs):
    global api  # pylint: disable=global-statement
    api = twitter.Api(tweet_mode='extended', sleep_on_rate_limit=True,
                      *args, **kwargs)

    count = 0
    for since, until in tqdm(list(get_date_intervals(n_days))):
        for username in USERNAMES:
            res = list(query_user(username, since=since, until=until)) \
                  + list(query_mentions(username, since=since, until=until))
            count += len(res)
            save_all(res)

        for hashtag in HASHTAGS:
            res = list(query_hashtag(hashtag, since=since, until=until))
            count += len(res)
            save_all(res)

    logger.info(f'Retrieved {count} tweets')


if __name__ == '__main__':
    main()
