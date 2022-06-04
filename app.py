import re
import urllib.request
import urllib.parse
import json

import urllib3
from flask import Flask, request
from flask_restful import Resource, Api

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk import PorterStemmer

from nltk.stem.wordnet import WordNetLemmatizer

nltk.download('stopwords')
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('omw-1.4')

app = Flask(__name__)
api = Api(app)

def diff(a: str, b: str):
    return a != b


def get_edit_dist(x: list, y: list):
    gap_penalty = 0.7
    mismatch_penalty = 1
    m = len(x)
    n = len(y)
    E = []

    for i in range(0, m + 1):
        E.append([])
        for j in range(0, n + 1):
            E[i].append(0)

    for i in range(0, m + 1):
        E[i][0] = i * gap_penalty
    for j in range(1, n + 1):
        E[0][j] = j * gap_penalty

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            E[i][j] = min(gap_penalty + E[i-1][j], gap_penalty + E[i][j-1],
                          diff(x[i - 1], y[j - 1]) * mismatch_penalty + E[i-1][j-1])

    return E[m][n]


def get_alignment(long_text: str, short_text: str):
    x_wordlevel = long_text.split(" ")
    y_wordlevel = short_text.split(" ")
    res = 1e9
    min_i = min_j = -1
    for i in range(0, len(x_wordlevel)):
        for j in range(i + 1, len(x_wordlevel)):
            cur = get_edit_dist(x_wordlevel[i:j], y_wordlevel)
            if res > cur:
                res = cur
                min_i = i
                min_j = j
    return res, min_i, min_j, len(x_wordlevel), x_wordlevel[min_i:min_j]


class GrammarCheck(Resource):
    def get(self):
        data = request.headers.get("data")
        # data = request.form['data']
        http = urllib3.PoolManager()
        r = http.request('POST', 'http://bark.phon.ioc.ee/punctuator', fields={'text': data})
        print(r.data)
        data = r.data.decode()

        url = 'https://languagetool.org/api/v2/check?language=en-US&text='
        example = 'check?language=en-US&text=my+text'

        new_data = data.replace(' ', '+')
        url = url + new_data
        rst = urllib.request.Request(url)
        html = urllib.request.urlopen(rst).read().decode('utf-8')

        list = ['Wrong article', 'Missing preposition', 'Agreement error', 'Possible grammar error',
                'Grammatical problem',
                'Missing preposition']
        num_dict = {}
        error_list = []
        matches = json.loads(html)['matches']
        for i in range(len(matches)):
            if matches[i]["shortMessage"] != '':
                print(matches[i])
                str = matches[i]["shortMessage"]
                error_dict = {}
                error_dict["errorSentence"] = matches[i]["sentence"]
                error_dict["errorType"] = str
                error_dict["errorAdvice"] = matches[i]["message"]
                error_dict["errorOffset"] = matches[i]["offset"]
                error_dict["errorLength"] = matches[i]["length"]
                error_dict["errorReplacement"] = matches[i]["replacements"]

                error_list.append(error_dict)
                if str in num_dict:
                    num_dict[str] = 1 + num_dict[str]
                else:
                    num_dict[str] = 1
        # return {"most": sorted(num_dict.items(), key=lambda x: x[1], reverse=True)[0], "error": error_list[:]}
        if not bool(num_dict):
            return {"correct": True}
        else:
            return {"correct": False, "most": sorted(num_dict.items(), key=lambda x: x[1], reverse=True)[0], "error": error_list[:]}


class StringCheck(Resource):
    def get(self):
        userData = request.headers.get("userData")
        groundTruth = request.headers.get("groundTruth")

#        userData = request.form['userData']
#        groundTruth = request.form['groundTruth']

        lem = WordNetLemmatizer()
        string4 = re.sub('\W', ' ', groundTruth)  # 把非单词字符全部替换为空，恰好与\w相反
        ud = re.sub('\W', ' ', userData)  # 把非单词字符全部替换为空，恰好与\w相反

        string4 = lem.lemmatize(string4)
        ud = lem.lemmatize(ud)
        res, min_i, min_j, num_wordlevel, longLine = get_alignment(string4, ud)

        st = str(' '.join([str(s) for s in longLine]))

        stop_words = set(stopwords.words('english'))
        word_tokens = word_tokenize(ud)
        print(word_tokens)
        keywordUser = [w for w in word_tokens if not w in stop_words]
        print(keywordUser)
        stop_words = set(stopwords.words('english'))
        word_tokens = word_tokenize(st)
        print(word_tokens)
        keywordGround = [w for w in word_tokens if not w in stop_words]
        print(keywordGround)

        if len(keywordUser) <= 3:
            print("too short to calculate")
            return {"status": "TSTC"}
        for i in range(min(len(keywordUser), len(keywordGround))):
            if keywordUser[i] != keywordGround[i]:
                print("Wrong word" + keywordUser[i])
                return {"status": "WI", "wrong word": i}
        if len(keywordUser) != len(keywordGround):
            print("Miss or More keywords")
            return {"status": "MOMK"}
#         print(min_j)
#         print(num_wordlevel)
        if min_j >= num_wordlevel - 2:
            print("Almost finish reading")
            return {"status": "F"}
        print("Correct")
        return {"status": "C"}


api.add_resource(GrammarCheck, '/grammarCheck')
api.add_resource(StringCheck, '/stringCheck')


if __name__ == "__main__":
    app.run()
