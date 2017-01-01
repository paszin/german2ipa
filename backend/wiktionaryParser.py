
import re
import urllib2
import json
import boto3
from HTMLParser import HTMLParser

class DynamoDBConnector:

    def  __init__(self):
        dynamodb = boto3.resource('dynamodb')
        self.table = dynamodb.Table('Dictionary')

    def get(self, word):
        item = self.table.get_item(
            Key={
            'word': word
            },
            AttributesToGet=['ipa']).get("Item")
        if item:
            return item.get("ipa")
        else:
            raise ValueError("Word not found")

    def put(self, word, ipa):
        item = self.table.put_item(
            Item={
            'word': word,
            'ipa': ipa
            })




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
    headers = { 'User-Agent' : 'paszin/german2ipa' }
    req = urllib2.Request(url, None, headers)
    data = json.loads(urllib2.urlopen(req).read())
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
#
def lookup(word, db):
    try:
        ipa, success = db.get(word), True
    except ValueError:
        ### lookup from dynamo db
        success, ipa = word2ipa(word)
    return success, ipa

def lambda_handler(event, context):
    words = event.get("text")
    if not words:
        return {"error": "missing parameter text"}
    dictionary = {}
    db = DynamoDBConnector()
    wordsSet = set(map(removeSpecialChars, words.split(" ")))
    for word in wordsSet:
        success, ipa = lookup(word, db)
        if not success:
            word = word.lower()
            success, ipa = lookup(word, db)
        if success:
            dictionary[word] = ipa
            db.put(word, ipa)

    return {"translation": translate(words, dictionary), "dictionary": dictionary}


if __name__ == "__main__":
    while True:
        word = raw_input(">>>")
        success, word = word2ipa(word)
        if not success:
            print "no translation found"
        else:
            print word
