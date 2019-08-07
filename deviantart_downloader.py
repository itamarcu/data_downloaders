import os
import re
import shutil
import requests
from bs4 import BeautifulSoup


class Deviation:
    def __init__(self, combined_name: str, url: str, image_url: str):
        self.combined_name = combined_name
        self.url = url
        self.image_url = image_url


def download_collection(collection_url, output_folder=None, name_format=None):
    """Will download images for all deviations in the collection URL into the
    output folder.

    If output_folder is None (default), it will create a
    directory next to where you ran the script from, with the collection's
    name, and download everything into it.

    Picture names are formatted like this by default (you may enter a similar
    template as name_format if you want to change it):
    {deviation_name} by {artist_username}

    Enjoy!"""
    print(f" ♢ Connecting to DeviantArt ({collection_url})…")

    collection_page = requests.get(collection_url)
    collection_page_soup = BeautifulSoup(collection_page.content, "html.parser")

    collection_name = collection_page_soup.select(".folder-title")[0].text
    print(f" ♢ Found collection: {collection_name}")
    print(f" ♢ Collecting info about all deviations…")
    deviations = []
    for thing1 in collection_page_soup.select("#gmi-"):
        for thing2 in thing1.findChildren("span", recursive=False):
            deviations.append(Deviation(
                combined_name=thing2["data-super-alt"],  # "X by Y"
                url=thing2["href"],
                image_url=thing2["data-super-full-img"],
            ))

    if output_folder is None:
        current_directory = os.getcwd()
        images_directory = os.path.join(current_directory, collection_name)
    else:
        images_directory = output_folder
    if not os.path.exists(images_directory):
        os.makedirs(images_directory)
    print(f" ♢ Downloading everything into {images_directory}")
    total_size = 0
    for dev in deviations:
        response = requests.get(dev.image_url, stream=True)
        content_length = int(response.headers['Content-length'])
        total_size += content_length
        mb_size = f"{content_length / 1_048_576:.2f} MB"
        deviation_name, artist_username = re.match("(.*) by (.*?)$", dev.combined_name).groups()
        name = name_format.format(deviation_name=deviation_name, artist_username=artist_username)
        name = name.replace("..", " ").replace("/", "_")
        print(mb_size+"\t "+name)
        with open(os.path.join(images_directory, f"{name}.png"), "wb") as out_file:
            shutil.copyfileobj(response.raw, out_file)
    print(f" ♢ Total size: {total_size / 1_048_576:.2f} MB")
    print(f" ♢ DONE ♢ ")
    print(f"ʕᵔᴥᵔʔ")


def main():
    collection_url = "[INSERT COLLECTION URL HERE]"
    download_collection(collection_url)

    # Example:
    # download_collection("https://www.deviantart.com/shemetz/favourites/77974139/Wallpaper-Material", "C:\Itamar\Pictures\Desktop Backgrounds", "{artist_username} - {deviation_name}")


if __name__ == '__main__':
    main()
