#!/usr/bin/env python
# -*- coding: utf-8 -*-
usage = """
=== Google PAA CLI Usage ===
Usage:
    google_paa.py query <keyword> [--query_template=<filename] [--num=<qnum>] [--skip-paa] [--skip-fs] [--tsv]
     [--output_paa=<filename>] [--output_fs=<filename>] [--headless] [--cleantext]
    google_paa.py (-h | --help)

Options:
    -h --help                 Show this message and exit
    --query-template=<filename> Filename for template to substitute query into [default: ]
    --skip-paa                Whether to skip paa output
    --skip-fs                 Whether to skip feature snippet output
    --tsv                     Save output in tab separated format
    --output_paa=<filename>   Filename for saving the tsv output of people also asked [default: ./output/paa_results.csv]
    --output_fs=<filename>    Filename for saving the tsv output of featured snippets [default: ./output/fs_results.csv] 
    --num=<qnum>              The number of questions to be crawled for each query [default: 20]
    
Examples:
    google_paa.py query "truck driver"              Search "truck driver" and output to a tsv file with default name
    google_paa.py query "input/queries.txt"         Search all the queries specified in "queries.txt"
    google_paa.py query "truck driver" --headless   Search headlessly 
    google_paa.py query "truck driver" --cleantext  Search "truck driver" and clean the answer text before output 
    google_paa.py query "truck driver" --num=10     Search and output 10 questions for "truck driver"
    google_paa.py query "truck driver" --output_paa="out.tsv"  Search "truck driver" and output to "out.tsv"
    google_paa.py -h                                Print this message

"""

import logging
import os
import platform
import plistlib
import sys
from glob import glob
from random import uniform
from time import sleep, time

import pandas as pd
from docopt import docopt
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from webdrivermanager import ChromeDriverManager
from selenium.common.exceptions import StaleElementReferenceException

# Google SERP html class constants
FEATURED_SNIPPET_DIV_CLASS = "ifM9O"
FEATURED_SNIPPET_TEXT_CLASS = "e24Kjd"


def hideGBar():
    # Hide Google Bar to prevent ClickInterceptionError
    try:
        browser.execute_script('document.getElementById("searchform").style.display = "none";')
    except:
        pass


def update_webdriver_to_matched_version(os_name, chromedriver_dir):
    if "Darwin" in os_name:
        chromeapp_path = "/Applications/Google Chrome.app/Contents/Info.plist"
        with open(chromeapp_path, "rb") as file:
            chromeapp_version = ".".join(plistlib.load(file)["CFBundleShortVersionString"].split(".")[:-1])
        chromedriver_manager = ChromeDriverManager(link_path="SKIP")
        chromedriver_manager.download_and_install(
            version=chromeapp_version, dl_path=chromedriver_dir, extract_dir=chromedriver_dir
        )
        logging.info("Downloaded chrome driver to match browser version: {}".format(chromeapp_version))
    else:
        logging.warning("Can't detect browser version for {} OS. Try to download the latest driver".format(os_name))
        chromedriver_manager = ChromeDriverManager(link_path="SKIP")
        chromedriver_manager.download_and_install(dl_path=chromedriver_dir, extract_dir=chromedriver_dir)


def initBrowser(headless=False):
    chromedriver_dir = os.path.join(os.path.dirname(__file__), "driver")
    os_name = platform.system()
    chrome_options = Options()
    chrome_options.add_argument("--incognito")
    chrome_options.add_experimental_option("prefs", {"intl.accept_languages": "en,en_US"})
    chrome_options.add_argument("--disable-features=NetworkService")
    if headless:
        chrome_options.add_argument("headless")
    try:
        driver_folder_path = os.path.join(os.path.dirname(__file__), "driver/chromedriver*")
        print(driver_folder_path)
        print(glob(driver_folder_path))
        chromedriver_path = os.path.join(os.path.dirname(__file__), glob(driver_folder_path)[0])
    except IndexError:
        print(glob(driver_folder_path))
        update_webdriver_to_matched_version(os_name, chromedriver_dir)
        return initBrowser(headless)
    try:
        return webdriver.Chrome(options=chrome_options, executable_path=chromedriver_path)
    except Exception as e:
        logging.warning(e)
        logging.info("Removing existing drivers ...")
        for file in glob("driver/chromedriver*"):
            os.remove(os.path.join(os.path.dirname(__file__), file))
        update_webdriver_to_matched_version(os_name, chromedriver_dir)
        return initBrowser(headless)


def clickNTimes(el, n=1):
    # Click on questions N times
    for i in range(n):
        el.click()
        sleep(uniform(0.3, 1))


def tabNTimes(N=2):
    actions = ActionChains(browser)
    for _ in range(N):
        actions = actions.send_keys(Keys.TAB)
    actions.perform()


def getAnswerText(el, max_attempts=10):
    attempt = 1
    while True:
        try:
            ans = el.find_elements_by_class_name("mod")
            return ans[0].text
        except StaleElementReferenceException:
            if attempt == max_attempts:
                logging.warning("Unable to locate the answer text!")
                return ""
            attempt += 1


def getAnswerLink(el):
    try:
        div = el.find_elements_by_class_name("r")
        ans_link = div[0].find_element_by_css_selector("a").get_attribute("href")
    except Exception as e:
        print(e)
        logging.warning("Unable to locate the answer link!")
        ans_link = ""
    return ans_link


def newSearch(browser, query, lang="en"):
    if lang == "en":
        browser.get("https://www.google.com?hl=en")
        searchbox = browser.find_element_by_xpath("//input[@aria-label='Search']")
    elif lang == "es":
        browser.get("https://www.google.com?hl=es")
        searchbox = browser.find_element_by_xpath("//input[@aria-label='Buscar']")
    else:
        logging.warning("Only English and Spanish are supported by this script for now.")
        logging.warning("Terminating ...")
        browser.close()
        sys.exit(0)

    searchbox.send_keys(query)
    sleep(uniform(0.3, 1))
    tabNTimes()
    if lang == "en":
        searchbtn = browser.find_elements_by_xpath("//input[@aria-label='Google Search']")
    else:
        searchbtn = browser.find_elements_by_xpath("//input[@aria-label='Buscar con Google']")
    try:
        searchbtn[-1].click()
    except:
        searchbtn[0].click()
    # sleep(1)
    try:
        fs = browser.find_element_by_xpath(
            "//span[contains(@class,'{}')]//ancestor::div[contains(@class,'{}')]".format(
                FEATURED_SNIPPET_TEXT_CLASS, FEATURED_SNIPPET_DIV_CLASS
            )
        )
    except:
        fs = None
    try:
        paa = browser.find_elements_by_class_name("related-question-pair")
    except:
        paa = []
    hideGBar()
    return (fs, paa)


def retrieveFeaturedAnswer(fs):
    if fs is None:
        return None
    try:
        answer_text = fs.find_element_by_xpath(
            "//span[contains(@class, '{}')]".format(FEATURED_SNIPPET_TEXT_CLASS)
        ).text
        answer_link = fs.find_element_by_xpath("//div[@class='r']//a").get_attribute("href")
        match = (answer_text, answer_link)
        logging.info(match)
    except:
        match = None
        logging.info("No featured snippet found")
    return match


def crawlQuestions(start_paa):
    new_questions = []
    paa_list = []
    rank = 0
    for el in start_paa:
        attempt = 1
        question_text = ""
        while attempt <= 10:
            attempt += 1
            try:
                q = el.find_element_by_xpath(".//div[contains(@class,'match-mod-horizontal-padding')]")
                question_text = q.text
                break
            except StaleElementReferenceException:
                if attempt >= 10:
                    logging.warning("Unable to locate the answer text!")
        if question_text == "" or "Dictionary" in question_text:
            continue
        logging.info("clicking on ... %s" % question_text)
        clickNTimes(q)
        answer_text = getAnswerText(el)
        answer_link = getAnswerLink(el)
        paa_list.append((rank, question_text, answer_text, answer_link))
        rank += 1
        new_questions.append(question_text)
    return new_questions, paa_list


def main(root_query, browser, threshold=20, skip_fs=True, skip_paa=False):
    query_queue = [root_query]
    faqs = []
    answers = []
    try:
        while query_queue and len(faqs) < threshold:
            query = query_queue.pop(0)
            logging.info("Running query '{}'...".format(query))
            try:
                fs, start_paa = newSearch(browser, query, "en")
            except:
                logging.error("Error creating new search!")
                raise
            if not start_paa:
                logging.warning("No PAA found for " + query)
                continue
            if not skip_fs:
                try:
                    answer = retrieveFeaturedAnswer(fs)
                except:
                    logging.error("Error retrieving answer!")
                    raise
                if answer is not None:
                    answers.append((query, answer[0], answer[1]))
                    logging.info("Adding featured snippet...")
            if not skip_paa:
                new_questions, crawl_paas = crawlQuestions(start_paa)
                faqs.extend([(query, r[0], r[1], r[2], r[3]) for r in crawl_paas])
                logging.info("Adding {:,} questions...".format(len(new_questions)))
                query_queue.extend(new_questions)

        logging.info(root_query + " Done.")
        return (faqs, answers)
    except:
        return ([], [])


def cleanTextInplace(dataframe):
    dataframe.replace("\n", " ", regex=True, inplace=True)
    dataframe.replace("[\.][\.][\.]", "", regex=True, inplace=True)
    dataframe.replace("[a-zA-Z]{3} [0-9]{1,2}, [0-9]{4}", "", regex=True, inplace=True)
    dataframe.replace("More items", "", regex=True, inplace=True)
    dataframe.replace("\s+", " ", regex=True, inplace=True)
    dataframe.replace("[^a-zA-Z0-9.,:?\s\-'\(\)/$]", "", regex=True, inplace=True)
    return dataframe


def write_to_output(dataframe, filepath, tsv=False):
    if tsv:
        return dataframe.to_csv(filepath, sep="\t", escapechar="\\", doublequote=False, index=False)
    return dataframe.to_csv(filepath, index=False)


if __name__ == "__main__":
    start_time = time()
    logging.basicConfig(level=logging.INFO)
    args = docopt(usage)
    print(args)

    query_template_file = args["--query_template"]
    if query_template_file is not None:
        with open(query_template_file) as f:
            query_template_items = [line.rstrip("\n") for line in f]
            query_template_items = [r for r in query_template_items if len(r) > 0]
    else:
        query_template_items = ["{}"]

    keyword_arg = args["<keyword>"]
    if keyword_arg.endswith(".txt") or keyword_arg.endswith(".csv"):
        with open(keyword_arg) as f:
            query_keywords = [line.rstrip("\n") for line in open(keyword_arg)]
    else:
        query_keywords = [keyword_arg]

    queries = [y.format(x) for x in query_keywords for y in query_template_items]
    print("Queries: {:,}".format(len(queries)))

    do_cleantext = args["--cleantext"]

    if args["--headless"]:
        browser = initBrowser(True)
    else:
        browser = initBrowser()
    try:
        featured_answers = []
        dfs = []
        for query in queries:
            (faqs, answers) = main(query, browser, int(args["--num"]), args["--skip-fs"], args["--skip-paa"])
            if faqs:
                df = pd.DataFrame(faqs)
                df = df.reset_index(drop=True)
                df.columns = ["query", "rank", "question", "answer", "link"]
                df["origin_query"] = query
                df = df[["origin_query", "query", "rank", "question", "answer", "link"]]
                dfs.append(df)
            if len(answers) > 0:
                featured_answers.extend(answers)
            sleep(uniform(0.3, 2))
        if len(dfs) > 0:
            df_out = pd.concat(dfs)
            if do_cleantext:
                # some post-processing to clean up the text a bit
                df_out = cleanTextInplace(df_out)
            df_out["answer"] = df_out["answer"].str.strip('"')
            df_out["answer"] = df_out["answer"].str.strip("”")
            write_to_output(df_out, args["--output_paa"], args["--tsv"])
        else:
            logging.info("No query datasets!")
        if len(featured_answers) > 0:
            df_answers = pd.DataFrame(featured_answers)
            df_answers.reset_index(drop=True, inplace=True)
            df_answers.columns = ["query", "answer", "link"]
            if do_cleantext:
                df_answers = cleanTextInplace(df_answers)
            write_to_output(df_answers, args["--output_fs"], args["--tsv"])
    finally:
        browser.close()
        print("--- %s seconds ---" % round((time() - start_time)))
