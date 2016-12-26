
import re
import urllib2
import json
from HTMLParser import HTMLParser


class WiktionaryIPAParser(HTMLParser):
    # create a subclass and override the handler methods
    foundTag = False
    finished = False
    data = ""

    def handle_starttag(self, tag, attrs):
        if self.finished:
            return
        if tag == "span":
            c = dict(attrs).get("class")
            if c and c == "ipa":
                self.foundTag = True

    def handle_endtag(self, tag):
        if self.finished:
            return
        if self.foundTag and tag == "span":
            self.finished = True

    def handle_data(self, data):
        if self.finished:
            return
        if self.foundTag:
            self.data = data


def extract(html):
    parser = WiktionaryIPAParser()
    parser.feed(html)
    return parser.data


def word2ipa(word):
    url = "https://de.wiktionary.org/w/api.php?action=parse&format=json&prop=text&page={word}".format(word=word)
    data = json.loads(urllib2.urlopen(url).read())
    if data.get("error"):
        return False, word
    if data.get("parse"):
        return True, extract(data["parse"]["text"]["*"])

def removeSpecialChars(word):
    chars = "!?.-',()"
    for c in chars:
        word = word.replace(c, "")
    return word

def translate(text, dictionary):
    "translate text based on dictionary, ignore unknown words, ignore special chars"
    text = text.lower()
    for k, v in dictionary.iteritems():
        text = text.replace(k.lower(), v)
    return text


def lambda_handler(event, context):
    words = event.get("text")
    if not words:
        return {"error": "missing parameter text"}
    dictionary = {}
    #response = {"successFactor": 0}
    wordsSet = set(map(removeSpecialChars, words.split(" ")))
    for word in wordsSet:
        success, ipa = word2ipa(word)
        if not success:
            word = word.lower()
            success, ipa = word2ipa(word)
        if success:
            dictionary[word] = ipa

    return {"translation": translate(words, dictionary), "dictionary": dictionary}


if __name__ == "__main__":
    while True:
        word = raw_input(">>>")
        success, word = word2ipa(word)
        if not success:
            print "no translation found"
        else:
            print word
