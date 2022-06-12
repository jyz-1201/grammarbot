import re
import urllib.request
import urllib.parse
import json
import numpy as np

import urllib3
import paralleldots

from flask import Flask, request
from flask_restful import Resource, Api

import nltk
from nltk.corpus import stopwords

from nltk.corpus import wordnet
from nltk import word_tokenize, pos_tag


from nltk.stem.wordnet import WordNetLemmatizer
from requests import get

nltk.download('stopwords')
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('omw-1.4')
nltk.download('averaged_perceptron_tagger')

app = Flask(__name__)
api = Api(app)


def diff(a: str, b: str):
    return a != b


def get_min_edit_dist(x: list, y: list):
    x.insert(0, "")
    y.insert(0, "")
    shortened_penalty = 0.6
    gap_penalty = 0.7
    mismatch_penalty = 1
    m = len(x)
    n = len(y)

    E = np.arange(m * n, dtype='float')
    E = np.reshape(E, (m, n))

    res = 1e9
    min_i = min_j = -1
    min_k = min_l = -1

    for i in range(1, m):
        for j in range(1, n):
            for a in range(i - 1, m):
                E[a][j - 1] = (a - (i - 1)) * gap_penalty
            for a in range(j, n):
                E[i - 1][a] = (a - (j - 1)) * gap_penalty
            for k in range(i, m):
                for l in range(j, n):
                    E[k][l] = min(gap_penalty + E[k - 1][l], gap_penalty + E[k][l - 1],
                                  diff(x[k], y[l]) * mismatch_penalty + E[k - 1][l - 1])
                    dist = E[k][l] + shortened_penalty * (n - 1 - (l - j + 1))
                    if res > dist:
                        res = dist
                        min_i = i
                        min_j = j
                        min_k = k
                        min_l = l

    return res, min_i, min_k, x[min_i:min_k + 1], min_j, min_l, y[min_j:min_l + 1]



def get_alignment(long_text: str, short_text: str):
    long_text = long_text.lower()
    short_text = short_text.lower()

    x_wordlevel = long_text.split(" ")
    y_wordlevel = short_text.split(" ")

    res = get_min_edit_dist(x_wordlevel, y_wordlevel)
    res += (len(x_wordlevel), )
    return res


def get_wordnet_pos(treebank_tag):
    if treebank_tag.startswith('J'):
        return wordnet.ADJ
    elif treebank_tag.startswith('V'):
        return wordnet.VERB
    elif treebank_tag.startswith('N'):
        return wordnet.NOUN
    elif treebank_tag.startswith('R'):
        return wordnet.ADV
    else:
        return None


def lemmatize_sentence(sentence):
    res = []
    lemmatizer = WordNetLemmatizer()
    for word, pos in pos_tag(word_tokenize(sentence)):
        wordnet_pos = get_wordnet_pos(pos) or wordnet.NOUN
        res.append(lemmatizer.lemmatize(word, pos=wordnet_pos))
    return res


class GrammarCheck(Resource):
    def grammarCkeck(self, data):
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
            if matches[i]["shortMessage"] == 'Missing comma':
                continue
            str = ""
            if matches[i]["shortMessage"] != '':
                str = matches[i]["shortMessage"]
            else:
                str = "Others"
            print(matches[i])
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
        #         for i in range(len(matches)):
        #             if matches[i]["shortMessage"] == 'Missing comma':
        #                 continue
        #             if matches[i]["shortMessage"] != '':
        #                 print(matches[i])
        #                 str = matches[i]["shortMessage"]
        #                 error_dict = {}
        #                 error_dict["errorSentence"] = matches[i]["sentence"]
        #                 error_dict["errorType"] = str
        #                 error_dict["errorAdvice"] = matches[i]["message"]
        #                 error_dict["errorOffset"] = matches[i]["offset"]
        #                 error_dict["errorLength"] = matches[i]["length"]
        #                 error_dict["errorReplacement"] = matches[i]["replacements"]

        #                 error_list.append(error_dict)
        #                 if str in num_dict:
        #                     num_dict[str] = 1 + num_dict[str]
        #                 else:
        #                     num_dict[str] = 1
        # return {"most": sorted(num_dict.items(), key=lambda x: x[1], reverse=True)[0], "error": error_list[:]}
        if not bool(num_dict):
            return {"correct": True}
        else:
            return {"correct": False, "most": sorted(num_dict.items(), key=lambda x: x[1], reverse=True)[0],
                    "error": error_list[:]}
    def get(self):
#       data = request.form['data']
        data = request.headers.get("data")
        return self.grammarCkeck(data)


class StringCheck(Resource):
    def get(self):
        userData = request.headers.get("userData")
        groundTruth = request.headers.get("groundTruth")

#        userData = request.form['userData']
#        groundTruth = request.form['groundTruth']
        lem = WordNetLemmatizer()
        string4 = re.sub('\W', ' ', groundTruth)  # 把非单词字符全部替换为空，恰好与\w相反
        ud = re.sub('\W', ' ', userData)  # 把非单词字符全部替换为空，恰好与\w相反
        string4 = re.sub('\s+', ' ', string4)  # 删除多余的空格
        ud = re.sub('\s+', ' ', ud)  # 删除多余的空格

        userData = userData.split(" ")
        groundTruth = groundTruth.split(" ")

        string4 = lemmatize_sentence(string4)
        string4 = str(' '.join([str(s) for s in string4]))

        ud = lemmatize_sentence(ud)
        ud = str(' '.join([str(s) for s in ud]))

        res, min_i, min_j, longLine, min_u, min_v, y_wordlevel, num_wordlevel = get_alignment(string4, ud)


        st = str(' '.join([str(s) for s in longLine]))
        ud = str(' '.join([str(s) for s in y_wordlevel]))

        stop_words = set(stopwords.words('english'))
        word_tokens = word_tokenize(ud)
        print(word_tokens)
        keywordUser = [w for w in word_tokens if not w in stop_words]
        indexUser = [index for index, w in enumerate(word_tokens) if not w in stop_words]
        print(keywordUser)

        stop_words = set(stopwords.words('english'))
        word_tokens = word_tokenize(st)
        print(word_tokens)
        keywordGround = [w for w in word_tokens if not w in stop_words]
        indexGround = [index for index, w in enumerate(word_tokens) if not w in stop_words]
        print(keywordGround)

        if len(keywordUser) <= 3:
            print("too short to calculate")
            return {"status": "TSTC"}
        for i in range(min(len(keywordUser), len(keywordGround))):
            if keywordUser[i] != keywordGround[i]:
                print("Wrong word " + keywordUser[i])
                return {"status": "WI", "wrongWord": userData[indexUser[i]], "correctWord": groundTruth[indexGround[i]], "correctIndex": indexGround[i]}
        if len(keywordUser) != len(keywordGround):
            print("Miss or More keywords")
            return {"status": "MOMK"}
        print(min_j)
        print(num_wordlevel)
        if min_j >= num_wordlevel - 2:
            print("Almost finish reading")
            return {"status": "F"}
        print("Correct")
        return {"status": "C"}


class MeaningCheck(Resource):
    def get(self):
        userData = request.headers.get("userData")
        groundTruth = request.headers.get("groundTruth")

        paralleldots.set_api_key("WHdM81fnBed9S6mbvKrBcvgG2CxBPCnhychHXIRgbvE")
        response = paralleldots.similarity(userData, groundTruth)
        # print(response)
        if response['similarity_score'] > 0.6:
            print({"status": "C"})
            return {"status": "C", "similarity": str(response['similarity_score'])}
        print({"status": "P", "similarity": str(response['similarity_score'])})
        return {"status": "P", "similarity": str(response['similarity_score'])}


class KeywordCheck(Resource):
    def get(self):
        userData = request.headers.get("userData")
        groundTruth = request.headers.get("groundTruth")

        paralleldots.set_api_key("WHdM81fnBed9S6mbvKrBcvgG2CxBPCnhychHXIRgbvE")
        text = [userData, groundTruth]
        response = paralleldots.batch_keywords(text)
        print(response)
        keywordListUser = response['keywords'][0]
        keywordListGround = response['keywords'][1]
        keywordUser = []
        keywordGround = []

        for i in range(len(keywordListUser)):
            if keywordListUser[i]['confidence_score'] > 0.8:
                keywordUser.append(keywordListUser[i]['keyword'])
        for i in range(len(keywordListGround)):
            if keywordListGround[i]['confidence_score'] > 0.8:
                keywordGround.append(keywordListGround[i]['keyword'])
        for i in range(len(keywordGround)):
            print(keywordGround)
            if keywordGround[i] not in keywordUser:
                print({"status": "MK", "missingKeyword": keywordGround[i]})
                return {"status": "MK", "missingKeyword": keywordGround[i]}
        print({"status": "C"})
        return {"status": "C"}

class ScoreCheck(Resource):
    def toGrade(self, score):
        if score <= 60:
            return "E"
        if score <= 70:
            return "D"
        if score <= 80:
            return "C"
        if score <= 90:
            return "B"
        return "A"

    def get(self):
        userData = request.headers.get("userData")
        groundTruth = request.headers.get("groundTruth")

        # Calculate Semantic Score
        paralleldots.set_api_key("WHdM81fnBed9S6mbvKrBcvgG2CxBPCnhychHXIRgbvE")
        response = paralleldots.similarity(userData, groundTruth)
        SemanticScore = response['similarity_score'] * 100 * 0.91

        # Calculate Length Score
        Length = len(userData.split(" "))
        LengthScore = 100
        if Length <= 135:
            LengthScore = 90
        if Length <= 110:
            LengthScore = 80
        if Length <= 85:
            LengthScore = 70
        if Length <= 70:
            LengthScore = 60

        # Calculate Grammar Score
        grammarResult = GrammarCheck.grammarCkeck(GrammarCheck(), userData)
        ErrorList = grammarResult["error"]
        ErrorCnt = len(ErrorList)
        GrammarScore = 60
        if ErrorCnt <= 7:
            GrammarScore = 70
        if ErrorCnt <= 4:
            GrammarScore = 80
        if ErrorCnt <= 2:
            GrammarScore = 90
        if ErrorCnt <= 1:
            GrammarScore = 100

        AverageScore = (SemanticScore + LengthScore + GrammarScore) / 3
        return {"AverageScore": self.toGrade(AverageScore),
                "SemanticScore": self.toGrade(SemanticScore),
                "LengthScore": self.toGrade(LengthScore),
                "GrammarScore": self.toGrade(GrammarScore),
                }


api.add_resource(GrammarCheck, '/grammarCheck')
api.add_resource(StringCheck, '/stringCheck')
api.add_resource(MeaningCheck, '/meaningCheck')
api.add_resource(KeywordCheck, '/keywordCheck')
api.add_resource(ScoreCheck, '/scoreCheck')


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
