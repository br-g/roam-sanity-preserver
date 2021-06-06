"""
Scraps the Slack Web interface.
Goes to the 'All unreads' section, opens threads one by one and saves their content.
"""

from typing import Dict, Iterator, Callable, Optional, Any, Set
import os
import time
import functools
from datetime import datetime
import pytz
import click
from loguru import logger
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from roam_sanity.util import save_as_json

parsing_time = datetime.now().astimezone(pytz.utc).isoformat()


def run_and_retry(fn: Callable, delay=1, n_try=5) -> Any:
    for try_idx in range(n_try):
        if try_idx > 0:
            logger.warning(f'Retrying ({try_idx}/{n_try-1})...')
        try:
            return fn()
        except Exception as e:
            logger.error(e)
        finally:
            time.sleep(delay)

    raise SystemError(f'Failed to run `{fn}`')


def scrap_slack(slack_email: str, slack_password: str, mark_as_read: bool,
                debug: bool) -> Iterator[str]:
    def get_driver():
        chrome_options = webdriver.ChromeOptions()
        if not debug:
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
        return webdriver.Chrome(
            ChromeDriverManager(version='90.0.4430.24').install(),
            options=chrome_options)

    def open_slack(driver):
        logger.info('Opening Slack')
        driver.get('https://roamresearch.slack.com/')
        time.sleep(3)

    def sign_in(driver):
        logger.info('Signing in')
        driver.find_element_by_css_selector('input#email').send_keys(slack_email)
        driver.find_element_by_css_selector('input#password').send_keys(slack_password)
        time.sleep(1)

        # Accept cookies (only in the EU)
        try:
            driver.find_element_by_css_selector('button#onetrust-accept-btn-handler').click()
            time.sleep(1)
        except NoSuchElementException:
            pass

        driver.find_element_by_css_selector('button#signin_btn').click()
        time.sleep(5)

        logger.info('Closing pop-ups')
        driver.execute_script('window.open()')
        driver.switch_to.window(driver.window_handles[1])
        driver.get('https://roamresearch.slack.com/')
        time.sleep(5)
        try:
            driver.find_element_by_css_selector('button.p-download_modal__not_now').click()
        except NoSuchElementException:
            # Sometimes, the pop-up is not there
            pass
        time.sleep(5)

        # Close "Learn more" message
        try:
            run_and_retry(
                driver.find_element_by_css_selector('button.c-button-unstyled.c-icon_button.c-icon_button--light.c-icon_button--size_medium.c-coachmark__close').click
            )
        except NoSuchElementException:
            pass

        time.sleep(3)

    def open_all_unreads(driver):
        logger.info("Opening 'All reads' section")

        try:
            run_and_retry(
                driver.find_element_by_xpath("//*[text()='More']").click
            )
        except NoSuchElementException:
            run_and_retry(
                driver.find_element_by_xpath("//*[text()='Browse Slack']").click
            )

        driver.find_element_by_xpath("//div[text()='All unreads']").click()
        time.sleep(3)

        # Remove header, so we can see messages' top lines
        header = driver.find_element_by_css_selector('div.p-view_header')
        driver.execute_script("arguments[0].style.display = 'none';", header)
        time.sleep(0.5)

    def do_mark_as_read(driver):
        try:
            driver.find_element_by_xpath("//button[text()='Mark All Messages Read']").click()
        except NoSuchElementException:
            logger.warning("Can't find button 'Mark All Messages Read'")
        time.sleep(1)

    def _fix_html(html):
        """I don't really understand why this is needed"""
        return html.replace(' c-file_gallery--mouse_mode', '')

    def _open_thread(driver, message):
        """Scrolls, hovers message and clicks on button to open thread."""
        action = webdriver.ActionChains(driver)
        action.move_to_element(message)
        action.perform()
        time.sleep(1)
        driver.find_element_by_css_selector('i.c-icon--comment-alt').click()

    def _get_thread_html(driver):
        return driver.find_element_by_css_selector('.p-flexpane--iap1').get_attribute('outerHTML')

    def _close_thread(driver):
        driver.find_element_by_css_selector('button.p-flexpane_header__control').click()
        time.sleep(1)

    def _is_end(driver) -> bool:
        """Returns whether the `Mark All Messages Read` is visible"""
        try:
            driver.find_element_by_xpath("//*[text()='Mark All Messages Read']")
            return True
        except:
            return False

    def open_and_save_threads(driver) -> Iterator[str]:
        logger.info('Opening and saving threads')

        seen = set()  # type: Set[str]
        while True:
            messages = driver.find_elements_by_css_selector('div.c-message_kit__gutter__right')

            # If we have reached the end of messages, stop
            if not messages:
                logger.warning("Can't find messages anymore")
                time.sleep(1)
                return

            if (seen and _fix_html(messages[-1].get_attribute('outerHTML')) in seen):
                assert _is_end(driver), 'No more messages, but the ' \
                                        '`Mark All Messages Read` sign is missing'
                logger.info('Completed `All unreads` section')
                time.sleep(1)
                return

            for message in messages:
                # We may have already seen this message
                if _fix_html(message.get_attribute('outerHTML')) in seen:
                    continue

                # Remove headers, so we can see messages' top lines
                driver.execute_script("""
                    var elems = document.getElementsByClassName('p-unreads_view__header');
                    for(i = 0; i < elems.length; i++) {
                      elems[i].style.display = 'none';
                    }
                """)
                time.sleep(0.5)

                # Align message to the top and open thread
                driver.execute_script('arguments[0].scrollIntoView();', message)
                seen.add(_fix_html(message.get_attribute('outerHTML')))
                time.sleep(1)

                # Sometimes, the following fails randomly.
                # We try multiple times and then skip eventually.
                try:
                    run_and_retry(
                        functools.partial(_open_thread, driver, message)
                    )
                except SystemError:
                    logger.warning("Can't open thread. Skipping.")

                try:
                    html = run_and_retry(
                        functools.partial(_get_thread_html, driver)
                    )
                    yield html
                except SystemError:
                    logger.warning("Can't get thread's HTML. Skipping.")
                finally:
                    time.sleep(0.5)
                    try:
                        _close_thread(driver)
                    except:
                        logger.warning("Can't close thread.")

                # Remove messages when done with them
                try:
                    driver.execute_script('''
                        var element = arguments[0];
                        element.parentNode.removeChild(element);
                        ''', message)
                except:
                    logger.warning("Can't remove message.")

                break


    driver = get_driver()
    open_slack(driver)
    sign_in(driver)
    open_all_unreads(driver)
    yield from open_and_save_threads(driver)

    if mark_as_read:
        do_mark_as_read(driver)
    driver.close()


def timestamp_to_iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).astimezone(pytz.utc).isoformat()


def clean_up_text(text: str) -> str:
    if text.endswith('\xa0(edited)\xa0'):
        text = text[:-len('\xa0(edited)\xa0')]

    text = text.strip(' ')
    text = text.strip('\n')
    return text


def parse_html_thread(html: str) -> Optional[Dict]:
    soup = BeautifulSoup(html, 'html.parser')
    channel_name = soup.find('span', {'class': ['c-channel_entity__name']}).text
    messages = soup.find_all('div', {'class': ['c-message_kit__gutter']})

    parsed = []
    for msg in messages:
        text = msg.find('div', {'class': ['p-rich_text_section']})
        name = msg.find('span', {'class': ['c-message_kit__sender']})
        timestamp = float(msg.find('a', {'class': ['c-timestamp']})['data-ts'])
        url = msg.find('a', {'class': ['c-timestamp']}).attrs['href']

        if not text:
            continue

        parsed.append({
            'create_time': timestamp_to_iso(timestamp),
            'text': clean_up_text(text.text),
            'author': name.text,
            'url': url,
            'is_reply': (msg != messages[0]),
        })

    if not parsed:
        return None

    # Return an aggregation of messages from the thread
    return {
        'source': 'slack',
        'channel': channel_name,
        'parsing_time': parsing_time,
        'create_time': parsed[0]['create_time'],
        'text': '<NEXT_MESSAGE>'.join([e['text'] for e in parsed]),
        # 'author': parsed[0]['author'],
        'url': parsed[0]['url'],
    }


@click.command()
@click.option('--slack_email', type=str, default=os.environ['RSP_SLACK_EMAIL'] if 'RSP_SLACK_EMAIL' in os.environ else None, nargs=1, show_default=False)
@click.option('--slack_password', type=str, default=os.environ['RSP_SLACK_PASSWORD'] if 'RSP_SLACK_PASSWORD' in os.environ else None, nargs=1, show_default=False)
@click.option('--mark_as_read', type=bool, default=False, nargs=1, show_default=True)
@click.option('--debug', type=bool, default=True, nargs=1, show_default=True)
def main(slack_email: str, slack_password: str, mark_as_read: bool, debug: bool):
    for html in scrap_slack(slack_email, slack_password, mark_as_read, debug):
        try:
            parsed = parse_html_thread(html)
        except:
            logger.warning("Can't parse message.")
            continue

        if parsed:
            save_as_json(parsed)


if __name__ == '__main__':
    main()
