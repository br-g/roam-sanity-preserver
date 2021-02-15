from typing import Dict
import dateutil.parser
from flask import Flask, render_template, request, jsonify
from roam_sanity.indexing import index

RESULTS_MAX = 1000
RESULTS_BATCH_SIZE = 50
N_CHARS_MAX = 200

app = Flask(__name__)


@app.route('/')
def render_index():
    return render_template('index.html')


@app.route('/about')
def render_about():
    return render_template('about.html')


def format_result(raw: Dict) -> str:
    content_short = raw['text']
    content_long = raw['text']

    if raw['source'] == 'roam-research':
        title = f"/{raw['database']} {raw['title']}"
        content_short = ''
        time_iso = raw['edit_time'] if 'edit_time' in raw else raw['create_time']

    elif raw['source'] == 'twitter':
        title = f"@{raw['author_screen_name']}"
        time_iso = raw['create_time']

    elif raw['source'] == 'slack':
        title = f"#{raw['channel']}"
        time_iso = raw['create_time']

        # Display only the first message
        thread_start = raw['text'].find('<NEXT_MESSAGE>')
        if thread_start > -1:
            content_short = raw['text'][:thread_start]
            content_long = content_long.replace('<NEXT_MESSAGE>',
                                                '<div class="message_sep">-----</div>')

        if 'url' not in raw:
            raw['url'] = ''

    if len(content_short) > N_CHARS_MAX:
        content_short = content_short[:N_CHARS_MAX-3] + '...'

    time = dateutil.parser.parse(time_iso).strftime('%m/%d/%y')

    if content_long != content_short:
        html_content_long = f'''
            <a class='show_more'>[more]</a>
            <div class='content long'>
                {content_long}
            </div>
            <a class='show_less'>[less]</a>
        '''
    else:
        html_content_long = ''

    html = f'''
        <div class='search_result'>
            <a href="{raw['url']}" target='_blank'
               class='title{" link_missing" if not raw["url"] else ""}'>
                <img src="static/img/{raw['source']}.png" alt="{raw['source']}">
                {title}
            </a>
            <span class='time'>({time})</span>
            <div class='content short'>
                {content_short}
            </div>
            {html_content_long}
        </div>
    '''
    return html


@app.route('/search')
def search():
    query = request.args.get('query', 0, type=str)
    offset = request.args.get('offset', 0, type=int)

    if offset >= RESULTS_MAX:
        return jsonify(html='', n_results=0)

    k = min(RESULTS_MAX, offset+RESULTS_BATCH_SIZE)
    res = [e[1] for e in index.search(query, k=k)[offset:]]
    res_html = '\n'.join([format_result(e) for e in res])

    return jsonify(html=res_html, n_results=len(res))


if __name__ == '__main__':
    app.debug = False
    app.run(host='0.0.0.0')
