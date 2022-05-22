import urllib.request
import urllib.parse
import json
from requests import put, get

from flask import Flask, request
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)


class GrammarCheck(Resource):
    # def get(self):
    #     return {'hello': request.form['username']}
    # def put(self):
    #     return {"put_hello": request.form['username']}
    # def post(self):
    #     return {"posted_hello": "res"}
    def get(self):
        url = 'https://languagetool.org/api/v2/check?language=en-US&text='
        example = 'check?language=en-US&text=my+text'

        new_data = request.headers.get("data").replace(' ', '+')

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
        if not bool(num_dict):
            return {"correct": True}
        else:
            return {"correct": False, "most": sorted(num_dict.items(), key=lambda x: x[1], reverse=True)[0], "error": error_list[:]}
        
        
class StringCheck(Resource):
    def get(self):
        userData = request.form['userData']
        groundTruth = request.form['groundTruth']

        lem = WordNetLemmatizer()

        stop_words = set(stopwords.words('english'))
        word_tokens = word_tokenize(userData)
        print(word_tokens)
        keywordUser = [lem.lemmatize(w) for w in word_tokens if not w in stop_words]
        print(keywordUser)
        stop_words = set(stopwords.words('english'))
        word_tokens = word_tokenize(groundTruth)
        print(word_tokens)
        keywordGround = [lem.lemmatize(w) for w in word_tokens if not w in stop_words]
        print(keywordGround)
        for i in range(min(len(keywordUser), len(keywordGround))):
            if keywordUser[i] != keywordGround[i]:
                print("Wrong index " + str(i))
                return {"Message": "Wrong Word", "WrongWord": keywordUser[i], "GroundTruth": keywordGround[i]}
        if len(keywordUser) != len(keywordGround):
            print("Miss or More keywords")
            return {"Message": "Missing or Extra Keywords"}
        print("Correct")
        return {"Message": "Correct"}



api.add_resource(GrammarCheck, '/grammarCheck')
api.add_resource(StringCheck, '/stringCheck')


if __name__ == "__main__":
    app.run()
