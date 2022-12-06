import argparse
import requests
import scrapy
import bs4 as bs
from urllib.parse import quote
import re

from multiprocessing import cpu_count
from joblib import Parallel, delayed

import json

import os.path
import traceback

from termcolor import colored
import sys
import io
sys.stdout = sys.__stdout__ = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8', line_buffering=True)
sys.stderr = sys.__stderr__ = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8', line_buffering=True)

BASE_URL = "https://www.goodreads.com"
COOKIE = os.getenv("SESSION_ID")
COOKIE = "_session_id2=af580bdc632cba12edfcb7148e27664a"
# PAGES_PER_SHELF = int(os.getenv("PAGES_PER_SHELF"))
PAGES_PER_SHELF = 50
JOBS = cpu_count()
PROCESSING_RATIO_THRESHOLD = 1.0


def print_book(book):
    print("-" * 30)
    print(book["title"])
    print(book["isbn"])


class GoodreadsScraper():
    def __init__(self, skip_processed_shelves, use_saved_books, use_saved_books_urls):
        self.skip_processed_shelves = skip_processed_shelves
        self.use_saved_books = use_saved_books
        self.use_saved_books_urls = use_saved_books_urls
        self.shelves = []
        self.shelves_stats = {}

    def load_shelves(self):
        with open("shelves.txt", "r", encoding='utf-8') as f:
            self.shelves = f.read().splitlines()
            print(self.shelves)
        for year in range(2000, 2021):
            self.shelves.append(str(year))

    def scrap_shelves(self):
        for i in range(1, PAGES_PER_SHELF + 1):
            for shelf in self.shelves:
                self.scrap_shelf(shelf, i)

    def scrap_shelf(self, shelf, i):
        print(colored("Started - {} - page {}".format(shelf, i), 'yellow', attrs=['bold']))

        # Skip this shelf if already processed
        if self.skip_processed_shelves \
                and os.path.isfile("shelves_pages/{}_{}.json".format(shelf, i)) \
                and self.shelf_processing_ratio(shelf, i) >= PROCESSING_RATIO_THRESHOLD:
            print(colored("Finished - {} - page {} - already processed...".format(shelf, i), "magenta", attrs=['bold']))
            return -1

        # Get books urls (from disk or request)
        shelf_books_urls_path = "shelves_pages_books_urls/{}_{}.json".format(shelf, i)
        if self.use_saved_books_urls and os.path.isfile(shelf_books_urls_path):
            with open(shelf_books_urls_path, "r", encoding='utf-8') as f:
                books_urls = json.load(f)["books_urls"]
        else:
            shelf_url = BASE_URL + "/shelf/show/{}?page={}".format(shelf, i)
            headers = {"Cookie": COOKIE}
            try:
                source = requests.get(shelf_url, timeout=20, headers=headers)
            except Exception:
                return 0
            soup = bs.BeautifulSoup(source.content, features="html.parser")
            books_urls = []
            for elem in soup.find_all(class_="bookTitle"):
                url = elem.get("href")
                books_urls.append(BASE_URL + url)
            with open(shelf_books_urls_path, "w", encoding='utf-8') as f:
                json.dump(
                    {"books_urls": books_urls},
                    f,
                    indent=4,
                    separators=(',', ': '),
                    ensure_ascii=False
                )

        # Scrap books urls
        books = Parallel(n_jobs=JOBS, verbose=10)(delayed(self.scrap_book)(book_url) for book_url in books_urls)
        books = list(filter(lambda x: x is not None, books))
        with open("shelves_pages/{}_{}.json".format(shelf, i), "w", encoding='utf-8') as f:
            json.dump(
                {"books": books},
                f,
                indent=4,
                separators=(',', ': '),
                sort_keys=True,
                ensure_ascii=False
            )

        # Save shelf's stats
        self.shelves_stats["{}_{}".format(shelf, i)] = {"scraped": len(books), "expected": len(books_urls)}
        self.save_stats()

        print(colored("Finished - {} - page {} with {}/{} books".format(shelf, i, len(books), len(books_urls)), 'green',
                      attrs=['bold']))
        return len(books)

    def scrap_book(self, book_url):
        try:
            # Get book's source page (from disk or request)
            book_source_page_path = "./books_source_pages/{}".format(quote(book_url, safe=""))
            if self.use_saved_books and os.path.isfile(book_source_page_path):
                soup_book = bs.BeautifulSoup(open(book_source_page_path), "html.parser")
            else:
                source_book = requests.get(book_url, timeout=20)
                soup_book = bs.BeautifulSoup(source_book.content, features="html.parser")
                with open(book_source_page_path, "w", encoding='utf-8') as book_source_page:
                    book_source_page.write(str(soup_book))

            try:
                isbn = str(soup_book.find("meta", {"property": "books:isbn"}).get("content"))
            except:
                isbn = None
            if isbn == "null":
                isbn = None

            metacol = soup_book.find(id="metacol")

            title = metacol.find(id="bookTitle").text.strip()
            author = metacol.find(class_="authorName").text.strip()

            try:
                description = metacol.find(id="description").find_all("span")[-1].text.strip()
            except:
                description = None
            # try:
            #     img_url = soup_book.find(id="coverImage").get("src")
            # except:
            #     img_url = None
            try:
                rating_count = int(metacol.find("meta", {"itemprop": "ratingCount"}).get("content"))
            except:
                rating_count = None
            try:
                rating_average = float(metacol.find("span", {"itemprop": "ratingValue"}).text)
            except:
                rating_average = None
            try:
                pages = int(soup_book.find("meta", {"property": "books:page_count"}).get("content"))
            except:
                pages = None

            try:
                details = metacol.find(id="details")
            except:
                details = None

            try:
                book_format = details.find("span", {"itemprop": "bookFormat"}).text
            except:
                book_format = None
            try:
                language = details.find("div", {"itemprop": "inLanguage"}).text
            except:
                language = None

            try:
                buttons = details.find(class_="buttons")
                settings = buttons.find(id="bookDataBox").find_all(class_="infoBoxRowItem", recursive=False)[
                    0].getText().replace("\n", " ")
            except:
                settings = None

            try:
                publication = details.find_all(class_="row")[1].text.strip()
            except:
                publication = None
            try:
                date_published = str(publication.split("\n")[1].strip())
            except:
                date_published = None
            try:
                publisher = publication.split("\n")[2].strip()[3:]
            except:
                publisher = None

            try:
                genres = soup_book.find_all(class_="actionLinkLite bookPageGenreLink")
                genres = [genre.text for genre in genres]
            except:
                genres = []

            # try:
            #     reviews_divs = soup_book.find_all(class_="reviewText stacked")
            #     reviews = [review_div.find("span").find_all("span")[-1].text for review_div in reviews_divs]
            # except:
            #     reviews = []

            book = {
                "isbn": isbn,
                "title": title,
                "author": author,
                "settings": settings,
                "description": description,
                "publisher": publisher,
                "date_published": date_published,
                # "img_url": img_url,
                "rating_count": rating_count,
                "rating_average": rating_average,
                "book_format": book_format,
                "pages": pages,
                "language": language,
                "goodreads_url": book_url,
                "genres": genres
                # "reviews": reviews
            }

            # print_book(book)
            return book

        except Exception as e:
            print("-" * 30)
            print(colored("ERROR: {}\n{}URL: {}".format(e, traceback.format_exc(), book_url), 'red'))
            return

    def load_stats(self):
        # with open("stats/shelves_stats.json", "r", encoding='utf-8') as f:
        with open("stats/shelves_stats.json", "r", encoding='utf-8') as f:
            self.shelves_stats = json.load(f)

    def save_stats(self):
        with open("stats/shelves_stats.json", "w", encoding='utf-8') as f:
            json.dump(
                self.shelves_stats,
                f,
                indent=4,
                separators=(',', ': '),
                sort_keys=True,
                ensure_ascii=False
            )

    def shelf_processing_ratio(self, shelf, i):
        shelf_stats = self.shelves_stats["{}_{}".format(shelf, i)]
        try:
            return shelf_stats["scraped"] / shelf_stats["expected"]
        except ZeroDivisionError:
            return 0

    def check_cookie(self):
        print(colored("Checking session cookie...", 'yellow', attrs=['bold']))
        test_url = BASE_URL + "/shelf/show/mistery?page=2"
        headers = {"Cookie": COOKIE}
        source = requests.get(test_url, timeout=10, headers=headers)
        soup = bs.BeautifulSoup(source.content, features="html.parser")
        try:
            validation_clue = soup.body.findAll(text=re.compile('Showing 1'), limit=1)
            if len(validation_clue) > 0:
                raise
        except Exception:
            raise Exception('Must use a valid session cookie!')
        print(colored("Session cookie is OK!", 'green', attrs=['bold']))

    def run(self):
        self.check_cookie()
        # self.load_stats()
        self.load_shelves()
        self.scrap_shelves()
        self.save_stats()


parser = argparse.ArgumentParser(description='Goodreads books scraper')
parser.add_argument('--skip_processed_shelves', action='store_true', help='Skip already processed shelves.')
parser.add_argument('--use_saved_books', action='store_true', help='Use saved books source files.')
parser.add_argument('--use_saved_books_urls', action='store_true', help='Use saved books urls.')
args = parser.parse_args()

scraper = GoodreadsScraper(args.skip_processed_shelves, args.use_saved_books, args.use_saved_books_urls)
scraper.run()
