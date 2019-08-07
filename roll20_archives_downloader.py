import json

import requests
import base64


def main():
    # Edit these 3 fields to be your secret email, password, and chat archives number.
    email = "aaaaa@bbbbb.com"
    password = "12345678"
    chat_archives_number = "4494321"
    all_chat_messages = download_logs(email, password, chat_archives_number)
    # that's it! now you have all messages in the game.
    # Now you can do this, for example: print all of the text (non-roll) messages.
    text_messages = filter_out_rolls(all_chat_messages)
    print("Printing all text messages...")
    for m in text_messages:
        print(message_to_string(m))
    print("Done.")


def download_logs(email, password, chat_archives_number):
    s = requests.Session()
    s.post("https://app.roll20.net/sessions/create", data={"email": email, "password": password})
    assert "rack.session" in s.cookies._cookies[".roll20.net"]["/"], "Login failed!"
    all_messages = []
    page_number = 1
    while True:
        messages = []
        response = s.get(f"https://app.roll20.net/campaigns/chatarchive/{chat_archives_number}/?p={page_number}", allow_redirects=False)
        if response.status_code == 302:
            break  # reached the end, asked for a nonexistent page, got redirected
        assert "msgdata" in response.text, "You're not a player in that campaign!"
        msgdata_index = response.text.index("msgdata")
        end_of_msgdata = response.text.index(";\nObject.defineProperty")
        msgdata = response.text[msgdata_index + 11:end_of_msgdata - 1]
        decoded_msgdata = base64.b64decode(msgdata)
        json_of_logs = json.loads(decoded_msgdata)
        for x in json_of_logs:
            for k, v in x.items():
                messages.append(v)
        all_messages.extend(reversed(messages))
        print(f"Downloaded page {page_number}.")
        page_number += 1
    print(f"Done downloading all {page_number - 1} pages ({len(messages)} messages in total).")
    all_messages = list(reversed(all_messages))
    return all_messages


def filter_out_rolls(all_messages):
    def is_not_a_roll(m):
        return "inlinerolls" not in m and "rolltemplate" not in m and "origRoll" not in m

    return [m for m in all_messages if is_not_a_roll(m)]


def message_to_string(message):
    return f'{message["who"]}: {message["content"]}'


if __name__ == '__main__':
    main()
