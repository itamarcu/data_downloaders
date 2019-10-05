import os
import re

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.http import Response


def scrape_chapter(response: Response):
    book_num = response.meta['book_num']
    file_name = response.url.replace("https://practicalguidetoevil.wordpress.com", "")
    file_name = file_name.strip("/").replace("/", "_")

    chapter_title = response.css("header > h1").xpath("text()").extract_first()
    paragraphs = response.xpath('//*[starts-with(@id, "post")]/div/div/p')
    with open(f"chapters/Book {book_num}/{file_name}.txt", "w", encoding="utf8") as file:
        # just makes a readable txt file - this removes useful stuff like italics/bold
        file.write(f"---{chapter_title}---")
        file.write("\r\n\r\n")
        for p in paragraphs:
            p_str = " ".join(p.xpath("*//text()").extract())
            if p_str == "":
                p_str = " ".join(p.xpath("text()").extract())
            file.write(p_str)
            file.write("\r\n")

    with open(f"sources/Book {book_num}/{file_name}.html", "w", encoding="utf8") as file:
        # "HTML" source
        file.write(response.xpath('//*[starts-with(@id, "post")]/div/div').extract_first())
    print(f"Scraped Book {book_num}: {chapter_title}")


class PGTEScraper(scrapy.Spider):
    name = "scryscraper"
    start_urls = ["https://practicalguidetoevil.wordpress.com/table-of-contents/"]
    book_count = 0

    def parse(self, response: Response):
        visited_links = set()
        for link_element in response.css("li > a"):
            link = link_element.xpath("@href").extract_first()
            if link in visited_links:
                continue
            visited_links.add(link)
            if "prologue" in link:
                self.book_count += 1
                os.makedirs(os.path.dirname(f"chapters/Book {self.book_count}/blah"), exist_ok=True)
                os.makedirs(os.path.dirname(f"sources/Book {self.book_count}/blah"), exist_ok=True)
            if link.startswith("https://practicalguidetoevil.wordpress.com/20"):  # 2015, 2016...
                request = response.follow(link_element, scrape_chapter)
                request.meta['link'] = link
                request.meta['book_num'] = self.book_count
                yield request


def print_pgte_stats():
    total_wordcount = 0
    total_chapter_count = 0
    root_dir = 'sources'
    print("Calculating statistics...")
    for directory_name, subdirectory_names, file_names in os.walk(root_dir):
        for file_name in file_names:
            file_path = os.path.join(directory_name, file_name)
            with open(file_path, encoding="utf8") as file:
                bad_words = file.read().split()
                words = []
                for word in bad_words:
                    if "entry-content" in word:
                        continue
                    if "atatags" in word:
                        break
                    word = re.sub(r'<\w+>', '', word)
                    word = re.sub(r'</\w+>', '', word)
                    words.append(word)
                chapter_wordcount = len(words)  # extra html stuff
                total_chapter_count += 1
                # print(f"{chapter_wordcount:5d} in {file_path}")
                total_wordcount += chapter_wordcount
    print(f"TOTAL WORDCOUNT: {total_wordcount} over {total_chapter_count } chapters."
          f" Average: {total_wordcount//total_chapter_count} words per chapter.")


if __name__ == "__main__":
    process = scrapy.crawler.CrawlerProcess({
        'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
    })
    process.settings.attributes["LOG_LEVEL"].set("WARNING", 0)
    process.crawl(PGTEScraper)
    process.start()
    print_pgte_stats()
