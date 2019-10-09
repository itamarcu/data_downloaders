import os
import shutil
import requests
from bs4 import BeautifulSoup


class Deviation:
    def __init__(self, deviation_name: str, artist_username: str, url: str):
        self.deviation_name = deviation_name
        self.artist_username = artist_username
        self.url = url


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

    collection_page_response = requests.get(collection_url)
    collection_page_soup = BeautifulSoup(collection_page_response.content, "html.parser")

    collection_name = collection_page_soup.select(".uUWfu")[0].text
    print(f" ♢ Found collection: {collection_name}")
    print(f" ♢ Collecting info about all deviations…")
    deviations = []
    for thing in collection_page_soup.select("._2Pnr5"):
        style_text = thing.select("._3ApeV.RZk0d")[0]["style"]
        deviations.append(Deviation(
            deviation_name=thing.select("._1TFfi")[0].text,
            artist_username=thing.select(".user-link._2diFW")[0]["title"],
            url=thing.select("._2vta_")[0]["href"],
        ))

    if output_folder is None:
        current_directory = os.getcwd()
        images_directory = os.path.join(current_directory, collection_name)
    else:
        images_directory = output_folder
    if name_format is None:
        name_format = "{deviation_name} by {artist_username}"
    if not os.path.exists(images_directory):
        os.makedirs(images_directory)
    print(f" ♢ Downloading everything into {images_directory}")
    total_size = 0
    for dev in deviations:
        deviation_response = requests.get(dev.url)
        deviation_soup = BeautifulSoup(deviation_response.content, "html.parser")
        image_picture_url = deviation_soup.select("._1LGGs > div > img")[0]["src"]
        response = requests.get(image_picture_url, stream=True)
        content_length = int(response.headers['Content-length'])
        total_size += content_length
        mb_size = f"{content_length / 1_048_576:.2f} MB"
        name = name_format.format(deviation_name=dev.deviation_name, artist_username=dev.artist_username)
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
