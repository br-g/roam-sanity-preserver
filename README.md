# Roam Sanity Preserver

A search engine for everything related to Roam Research on the Web.    
If you have any questions or suggestions, please create an issue, or join
[the Slack channel](https://app.slack.com/client/TNEAEL9QW/C01N1HSE7PD).


## 1. Installation

Install Elasticsearch [7.x] (see instructions [here](https://www.elastic.co/guide/en/elasticsearch/reference/7.x/install-elasticsearch.html))

Clone the repo:

    $ git clone git@github.com:br-g/roam-sanity-preserver.git

Install the `roam-sanity` package using pip (you need Python 3.6 or later):

    $ cd roam-sanity-preserver/
    $ pip install -U -e .


## 2. Get the data

Download and unzip the latest data:

    $ curl https://roamsanity.s3-eu-west-1.amazonaws.com/prod/public/data.zip -o data.zip
    $ unzip data.zip


## 3. Build the index

Make sure Elasticsearch is running, and then:

    $ python scripts/build_index.py --data_path data/


## 4. Start the app

Make sure Elasticsearch is running, and then:

    $ python app/main.py

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.


## [bonus] Run the crawling scripts

First, install some extra dependencies:

    $ pip install -U -e .[crawl]

Then set the path to your data folder:

    $ export RSP_DATA_PATH="data/"

To crawl Roam Research:

    $ python scripts/crawl_roam.py

To crawl Twitter:

    $ python scripts/crawl_twitter.py --help

To crawl Slack:

    $ python scripts/crawl_slack.py --help


## Help needed!

If you would like to help integrate new data sources or improve the service, please contribute!    
