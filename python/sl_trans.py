#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time: 2018/12/3 10:29
import pynlpir
from pynlpir import nlpir
from pypinyin import pinyin, Style
import preload
import json
from itertools import groupby
# from wsd.process.WsdCrf import crf
import re

import pymysql
import xlrd,xlwt,xlutils
import jieba
import numpy as np
from gensim.models.word2vec import Word2Vec
from gensim.corpora.dictionary import Dictionary
from keras.preprocessing import sequence

import yaml
from keras.models import model_from_yaml
np.random.seed(1337)  # For Reproducibility
import sys
sys.setrecursionlimit(1000000)

# define parameters
maxlen = 100



MODEL_FILE = r'.//model//compressed_sgns.merge.wo.txt'  # 模型文件路径
SIGN_DICT_PATH = r'.//data//1_sign_dict.txt'
NUM_WORD_PATH = r'.//data//1a_num_dict.txt'
CHAR_WORD_PATH = r'.//data//1b_char_dict.txt'
LOCATION_PATH = r'.//data//1c_location_dict.txt'
SYNONYM_DICT_PATH = r'.//data//2_synonym_dict.txt'
SEG_DICT_PATH = r'.//data//3_seg_dict.txt'
EXTEND_DICT_PATH = r'.//data//4_extend_dict.txt'
SEG_SYN_PATH = r'.//data//5_seg_syn.txt'
STOP_WORDS_PATH = r'.//data//6_stop_words.txt'
UNFILTER_WORDS_PATH = r'.//data//6a_unfilter_words.txt'
VISUALIZATION_INFO = r'.//data//7_visualization_info.txt'
EMOTION_DICT = r'.//data//8_emotion_info.txt'  # 情感分类词典
POLYSEMY_INFO = r'.//data//10_polysemy.txt'
USER_DICT = r'.//data//11_user_dict.txt'
POETRY_DICT = r'.//data//12_poetry.txt'
WORD2VEC = r'.//data//Word2vec_model.pkl'
LSTM_YML = r'.//data//lstm.yml'
LSTM_H5 = r'.//data//lstm.h5'
COMPUTER_PATH = r'.//data//3_computer_words.txt'
ART_PATH = r'.//data//4_art_words.txt'
FILTER_POS = ('q', 'uzhe', 'ule', 'uguo', 'ude1', 'ude2', 'ude3', 'usuo', 'udeng',
              'uyy', 'udh', 'uls', 'uzhi', 'ulian', 'e', 'y', 'o', 'x', 'xe', 'xm', 'xu', 'xx',
              'w', 'wkz', 'wky', 'wyz', 'wyy', 'wj', 'wt', 'wd', 'wf', 'wn', 'wm', 'ws', 'wp', 'wb', 'wh')
num_keyword = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '零']
num_regex = re.compile("([一二三四五六七八九十百千万零]{1,8})")
PUNC = '，。！？：,.?!'



class Translate(object):
    def __init__(self, ):
        self.sign_dict = preload.load_sign_dict(SIGN_DICT_PATH, LOCATION_PATH)
        self.num_dict, self.num_syn_dict = preload.load_extend_dict(NUM_WORD_PATH)
        self.char_dict = preload.load_sign_dict(CHAR_WORD_PATH)
        self.syn_dict = preload.load_syn_dict(SYNONYM_DICT_PATH)
        self.seg_dict = preload.load_seg_dict(SEG_DICT_PATH)
        self.extend_dict, self.extend_syn_dict = preload.load_extend_dict(EXTEND_DICT_PATH)
        self.seg_syn_dict = preload.load_seg_syn_dict(SEG_SYN_PATH, self.seg_dict)
        self.stop_words = preload.load_stop_words(STOP_WORDS_PATH)
        self.unfilter_words = preload.load_unfilter_words(UNFILTER_WORDS_PATH)
        self.emotion_dict = preload.load_emotion_dict(EMOTION_DICT)
        self.visual_info = preload.load_visualization_info(VISUALIZATION_INFO)
        self.polysemy_info = preload.load_polysemy_info(POLYSEMY_INFO)
        self.poetry_info = preload.load_poetry_info(POETRY_DICT)
        self.word2vec = preload.load_word2vec(WORD2VEC)
        self.model = preload.load_lstm_weight(LSTM_YML,LSTM_H5)
        self.baidu = preload.baidu_emotion()
        # self.wsd_crf = crf()
        self.sentence = ''
        pynlpir.open()
        nlpir.ImportUserDict(USER_DICT.encode('utf-8'), 1)  # 导入用户自定义词典

    def start(self, sentence, role='customer'):
        self.sentence = sentence
        word_sequence = []
        # if sentence in self.poetry_info:
        #     for word in self.poetry_info[sentence][2]:
        #         word_sequence.append(self.word_encode(word))
        #     return word_sequence
        word_pos_list = self.sentence_seg(sentence)
        visual = self.visual_info.get(sentence.replace("，", "").replace("。", ""))
        npn1 = self.eomtion_predict(sentence)
        tran = {0:2,1:0,2:1}
        bai = self.baidu.sentimentClassify(sentence)
        npnb = 0
        if 'items' in bai.keys():
            if len(bai['items']) > 0:
                npnb = tran[bai['items'][0]['sentiment']]

        for seg in word_pos_list:
            if seg[0] != ' ':
                if seg[1] in FILTER_POS and seg[0] not in self.unfilter_words and not seg[0].encode('UTF-8').isalpha():  # 对过滤词的处理
                    word_sequence.append(
                        dict(Word=seg[0], State=5, Type=None, Other=None, Md5=None, Visual=visual,
                             Emotion=None))
                elif seg[0] in self.stop_words:  # 对停用词进行处理
                    word_sequence.append(
                        dict(Word=seg[0], State=5, Type=None, Other=None, Md5=None, Visual=visual,
                             Emotion=None))
                elif seg[0] in ['？', '?']:  # 对问号进行处理
                    word_sequence.append(
                        dict(Word=seg[0], State=2, Type=None, Other=[dict(Word='问号', State=1, Type=None, Other=None,
                                                                          Md5=None, Visual=visual,
                                                                          Emotion=None)],
                             Md5=None, Visual=visual, Emotion=None))
                elif seg[1] in ['m', 'mq', 't']:  # 对数字进行处理
                    num_words = [''.join(list(g)) for k, g in groupby(seg[0], key=lambda x: x.isdigit())]
                    for num_word in num_words:
                        if num_word.encode('UTF-8').isdigit() and int(num_word) != 0:
                            word_sequence.append(self.num_digit_process(num_word))
                        elif num_word.isdigit() and int(num_word) == 0:
                            word_sequence.append(dict(Word=num_word, State=3, Type=None, Other=[self.digit_encode(digit) for digit in num_word], Md5=None, Visual=None, Emotion=None))
                        else:
                            chinese_num_list = re.split(num_regex, num_word)
                            for index, word in enumerate(chinese_num_list):
                                if index % 2 == 1:
                                    word_sequence.append(self.num_chinese_process(word))
                                elif index % 2 == 0 and word != '':
                                    word_sequence.append(self.word_encode(word))
                else:  # 对普通词语进行处理
                    word_sequence.append(self.word_encode(seg[0], visual))
            else:
                word_sequence.append(
                    dict(Word=seg[0], State=5, Type=None, Other=None, Md5=None, Visual=visual, Emotion=None))
        # 临时的句子情感分析 start
        start_index = 0
        word_emotion = {}#记录所有的情感词的强度
        emotion_max_score = {}#记录每个情感词最大的分数
        word_emotion_index = {}#记录情感词对应的索引
        for index in range(len(word_sequence)):
            word = word_sequence[index]
            if word['Emotion']:#这个词在字典里面有
                if word['Emotion'] in word_emotion:#前面已经记录的情感词
                    word_emotion[word['Emotion']] = float(word_emotion[word['Emotion']]) + float(word['EmotionIntensity'])#将情感词的强度相加
                    if word['EmotionIntensity'] > emotion_max_score[word['Emotion']]:#记录最大的分数
                        emotion_max_score[word['Emotion']] = word['EmotionIntensity']
                else:#新的情感词目前还没有存入字典
                    word_emotion[word['Emotion']] = float(word['EmotionIntensity'])
                    emotion_max_score[word['Emotion']] = word['EmotionIntensity']
                if word['Emotion'] not in word_emotion_index:#建立索引
                    indexs = []
                    word_emotion_index[word['Emotion']] = indexs
                word_emotion_index[word['Emotion']].append(index)
                # word['Emotion'] = None
                # word['EmotionIntensity'] = None
            if word['Word'] in PUNC or index == len(word_sequence)-1:#最后的一个词,将一个词的句子进行总结
                #sorted(word_emotion.items(),key=lambda x:x[1],reverse=True)
                if not word_emotion:
                    start_index = index + 1
                    continue
                emotion = max(word_emotion, key=word_emotion.get)
                indextmp = word_emotion_index[emotion]
                npn2 = word_sequence[indextmp[0]]['Npn'];
                #intensity = word_emotion[emotion]
                # print(emotion)#将所有的词都复制成最大的那个词的强度(1+max/9)/2
                for id in range(start_index, index + 1):
                    if word_sequence[id]['Word'] not in PUNC:
                        word_sequence[id]['Emotion2'] = emotion
                        # word_sequence[id]['EmotionIntensity'] = float(emotion_max_score[emotion])/9
                        word_sequence[id]['EmotionIntensity2'] = 0.5 + 0.5 * float(emotion_max_score[emotion])/9
                        word_sequence[id]['Npn2'] = str(npn1)
                        word_sequence[id]['Npnb'] = str(npnb)
                        if npn2 != npn1:
                            # word_sequence[id]['EmotionIntensity'] = float(emotion_max_score[emotion])/9
                            word_sequence[id]['EmotionIntensity2'] = float(0)
                        if word_sequence[id]['Other']:
                            for other_word in word_sequence[id]['Other']:
                            #other_word = [0]
                                other_word['Emotion2'] = emotion
                                # other_word['EmotionIntensity'] = float(emotion_max_score[emotion])/9
                                other_word['EmotionIntensity'] = 0.5 + 0.5 * float(emotion_max_score[emotion])/9
                                other_word['Npn'] = str(npn1)
                                if npn2 != npn1:
                                    # word_sequence[id]['EmotionIntensity'] = float(emotion_max_score[emotion])/9
                                    other_word['EmotionIntensity'] = float(0)
                word_emotion.clear()
                start_index = index + 1
            #if word['Other']:
                #for other_word in word['Other']:
                    #other_word['Emotion'] = None
        # 临时的句子情感分析 end
        return word_sequence  # 返回list到服务器程序做后续处理

    @staticmethod
    def sentence_seg(sentence):
        """
        对句子进行分词处理
        :param sentence: 需要分词的句子
        :return: 分词后的结果 [(分词1，词性1)，(分词2，词性2)...]
        """
        pos_seg_list = pynlpir.segment(sentence + ',')
        return pos_seg_list[:-1]

    def num_digit_process(self, num):
        """
        针对是数字的情况进行处理
        :param num: 传入的数字
        :return: 对数字的处理结果
        """
        word_state = dict(Word=num, State=3, Type=None, Other=None, Md5=None, Visual=None, Emotion=None)
        if len(num) > 5:
            num_before = str(int(num) // 10000)
            num_after = str(int(num) % 10000)
            w_char = [dict(Word='万', State=1, Type=None, Other=None, Md5=None, Visual=None,
                           Emotion=None)]
            if num_after != '0':
                word_state['Other'] = self.num_digit_process(num_before)['Other'] + \
                                      w_char + \
                                      self.num_digit_process(num_after)['Other']
            else:
                word_state['Other'] = self.num_digit_process(num_before)['Other'] + w_char
        elif num in self.num_dict or num in self.num_syn_dict.keys():
            word_state = self.word_encode(num)
        else:
            word_state['Other'] = self.digit_number_encode(num)
        return word_state

    def num_chinese_process(self, num):
        """
        针对数字为汉字的情况进行处理
        :param num: 传入的数字
        :return: 对数字的处理结果
        """
        word_state = dict(Word=num, State=2, Type=None, Other=None, Md5=None, Visual=None, Emotion=None)
        if num in self.num_dict or num in self.num_syn_dict.keys():
            word_state = self.word_encode(num)
        else:
            word_state['Other'] = self.chinese_number_encode(num)
        return word_state

    def chinese_number_encode(self, num):
        num_words = []
        for num_chr in num:
            num_words.append(self.word_encode(num_chr))
        num_words_temp = []
        for item in num_words:
            if item['State'] != 1:
                num_words_temp.append(item['Other'][0])
            else:
                num_words_temp.append(item)
        num_words = num_words_temp
        for index, item in enumerate(num_words):
            if item['Word'] in ['十', '百', '千'] and index != 0 and num_words[index - 1]['Word'] in num_keyword:
                num_words.remove(item)
                num_words[index - 1]['Word'] += item['Word']  # 取【1】是为了将"一"规避掉
        return num_words

    def digit_number_encode(self, num):
        number_unit = [None,
                       dict(Word='十', State=1, Type=None, Other=None, Md5=None, Visual=None, Emotion=None),
                       dict(Word='百', State=1, Type=None, Other=None, Md5=None, Visual=None, Emotion=None),
                       dict(Word='千', State=1, Type=None, Other=None, Md5=None, Visual=None, Emotion=None),
                       dict(Word='万', State=1, Type=None, Other=None, Md5=None, Visual=None, Emotion=None)
                       ]
        h = len(num)
        t = 0
        number = int(num)
        while not number % 10:
            number = number // 10
            t += 1
        number_list = [self.digit_encode(n) for n in num[:h - t]]
        i = 0
        while i <= h - t - 1:
            number_list.insert(2 * i + 1, number_unit[t:h][-(i + 1)])  # number_unit[t:h] 为当前数值需要用到的数值单位
            i += 1
        number_list = [item for item in number_list if item is not None]
        number_list = self.rm_unit_zero(number_list)  # 去除连续出现的‘零“
        return number_list

    def digit_encode(self, digit):
        word_state = dict(Word=None, State=1, Type=None, Other=None, Md5=None, Visual=None, Emotion=None)
        if digit in self.num_dict:
            word_state['Word'] = digit
        elif digit in self.num_syn_dict.keys():
            word_state['Word'] = self.num_syn_dict[digit]
        return word_state

    @staticmethod
    def rm_unit_zero(num_list):
        """
        对数字的计数单位进行处理，对处理后的字符串中连续出现的‘零’进行去重
        :param num_list: 处理前的字符串
        :return: 处理后的字符串
        """
        for item in num_list[:]:
            if item['Word'] in ['十', '百', '千'] and num_list.index(item) != 0:
                if num_list[num_list.index(item) - 1]['Word'] != '零':
                    num_list[num_list.index(item) - 1]['Word'] += item['Word']
                num_list.remove(item)
        if num_list[0]['Word'] == '一十':
            num_list[0]['Word'] = '十'
        for i in range(len(num_list) - 1, -1, -1):
            if num_list[i]['Word'] == '零' and num_list[i] == num_list[i - 1]:
                num_list.pop(i)
        return num_list

    def word_encode(self, word, global_visual=None):
        """
        针对***普通用户***进行词语处理
        该用户可以使用手语词典（近义词词典）、非官方词典、计算机词典、美术词典、组合表达词典。
        :param word: 分词后的词语
        :param global_visual:
        :return: 词语查询结果，其中'State'值：1为存在词语，2为近义词替换，3为组合表达替换, 4为扩展词语, 5为扩展/组合表达的近义词；
        'Other'值：进行替换的词语；'Type':手指语表达词语，需要进行离线处理
        """
        word_state = dict(Word=word, State=None, Type=None, Other=None, Md5=None, Visual=global_visual,
                          Emotion=None)
        if word in self.visual_info.keys():  # 具象化图片查找
            word_state['Visual'] = self.visual_info[word]
        if word in self.emotion_dict.keys():  # 分析词语的情感
            word_state['Emotion'] = self.emotion_dict[word]
            word_state['EmotionIntensity'] = self.emotion_dict[word+'-i']
            word_state['Npn'] = self.emotion_dict[word + '-n']
        if word in self.sign_dict or word in self.num_dict:  # 手语词典查找
            if word in self.polysemy_info.keys():
                """
                该部分用于加入消歧模型进行计算
                self.sentence = self.sentence if self.sentence.endswith('。') else self.sentence + '。'
                try:
                    crf_data = {'word': word, 'sentence': re.findall(r'[^。]*?{}[^。]*?。'.format(word), self.sentence)[0]}
                    crf_url = "http://localhost:10124/wsd"
                    req = requests.get(crf_url, params=crf_data)
                    print(req.text)
                    text = req.text
                except:
                    print('{}-多义词分类错误'.format(word))
                    text = word
                word_state['Word'], word_state['State'], word_state['Type'] = text if text else word + self.polysemy_info[word], 1, 1
                """
                word_state['Word'], word_state['State'], word_state['Type'] = word if self.polysemy_info[
                                                                                          word] == '1' else word + \
                                                                                                            self.polysemy_info[
                                                                                                                word], 1, 1
                return word_state
            else:
                word_state['State'] = 1
                return word_state
        elif word in self.num_syn_dict.keys():  # 数字近义词词典查找
            word_state['State'], word_state['Other'] = 2, [self.word_encode(self.num_syn_dict[word], global_visual)]
            return word_state
        elif word in self.extend_dict:  # 扩充词典查找
            word_state['State'] = 1
            return word_state
        elif word in self.seg_dict.keys():  # 组合表达词典查找
            word_state['State'], word_state['Other'] = 3, [self.word_encode(seg) for seg in self.seg_dict[word]]
            return word_state
        elif word in self.syn_dict.keys():  # 近义词词典查找
            word_state['State'], word_state['Other'] = 2, [self.word_encode(self.syn_dict[word], global_visual)]
            return word_state
        elif word in self.extend_syn_dict.keys():  # 扩充词语的近义词词典查找
            word_state['State'], word_state['Other'] = 2, [self.word_encode(self.extend_syn_dict[word], global_visual)]
            return word_state
        elif word in self.seg_syn_dict.keys():  # 组合词语的近义词词典查找
            word_state['State'], word_state['Other'] = 3, [self.word_encode(word, global_visual) for word in
                                                           self.seg_syn_dict[word]]
            return word_state
        elif word in self.char_dict:
            word_state['State'] = 1
            return word_state
        else:  # 针对词典未登录词语进行拆分查找，'Type'字段设置为0，用于词语日志记录
            word_state['State'], word_state['Other'], word_state['Type'] = 3, [self.char_encode(c) for c in word], 0
            return word_state

    def char_encode(self, char):
        """
        针对单个字符进行查找，未找到词语采用手指语，其中对于'Z''C''S',要区分'ZH''CH''SH'的情况
        :param char: 传入的单个字符
        :return: 单个字符的处理结果
        """
        word_state = dict(Word=None, State=1, Type=None, Other=None, Md5=None, Visual=None, Emotion=None)
        if char in self.visual_info.keys():
            word_state['Visual'] = self.visual_info[char]
        if char in self.sign_dict:
            word_state['Word'] = char
        elif char in self.extend_dict:
            word_state['Word'] = char
        elif char in self.syn_dict.keys():  # 近义词词典查找
            word_state['Word'] = self.syn_dict[char]
        elif char in self.extend_syn_dict.keys():  # 扩充词语的近义词词典查找
            word_state['Word'] = self.extend_syn_dict[char]
        else:
            word_state['Word'] = pinyin(char, style=Style.FIRST_LETTER)[0][0].upper()
        if word_state['Word'] in ['Z', 'C', 'S'] and u'\u4e00' <= char <= u'\u9fa5':
            word_state['Word'] = word_state['Word'] + 'H' if pinyin(char, style=Style.NORMAL)[0][0][
                                                                 1].upper() == 'H' else word_state['Word']
        return word_state



    def create_dictionaries(self,combined=None):
        model = self.word2vec;
        if (combined is not None) and (model is not None):
            gensim_dict = Dictionary()
            gensim_dict.doc2bow(model.wv.vocab.keys(),
                            allow_update=True)
            #     freqxiao10->0 所以k+1
            w2indx = {v: k+1 for k, v in gensim_dict.items()}#所有频数超过10的词语的索引,(k->v)=>(v->k)
            w2vec = {word: model[word] for word in w2indx.keys()}#所有频数超过10的词语的词向量, (word->model(word))

            def parse_dataset(combined): # 闭包-->临时使用
                ''' Words become integers
                '''
                data=[]
                for sentence in combined:
                    new_txt = []
                    for word in sentence:
                        try:
                            new_txt.append(w2indx[word])
                        except:
                            new_txt.append(0) # freqxiao10->0
                    data.append(new_txt)
                return data # word=>index
            combined=parse_dataset(combined)
            combined= sequence.pad_sequences(combined, maxlen=maxlen)#每个句子所含词语对应的索引，所以句子中含有频数小于10的词语，索引为0
            return w2indx, w2vec,combined
        else:
            print('No data provided...')

    def eomtion_predict(self,string):
        words=jieba.lcut(string)
        words=np.array(words).reshape(1,-1)
        _,_,data=self.create_dictionaries(words)
        data.reshape(1, -1)
        result = self.model.predict_classes(data)
        # print result # [[1]]
        if result[0] == 1:
            ret = 'positive'
        elif result[0] == 0:
            ret = 'neural'
        else:
            ret = 'negative'
        return result[0]
State_parse={"1":"存在词语","2":"近义词替换","3":"组合词汇表达","5":"过滤词语"}
Type_parse={"0":"未登录词","1":"多义词","2":"旧版手语词汇","3":"千博新增词汇"}
Emotion_parse=  {"PA":"快乐","PE":"安心","PD":"尊敬","PH":"赞扬","PG":"相信","PB":"喜爱","PK":"祝愿","NA":"愤怒","NB":"悲伤","NJ":"失望","NH":"疚","PF":"思","NI":"慌","NC":"恐惧","NG":"羞","NE":"烦闷","ND":"憎恶","NN":"贬责","NK":"妒忌","NL":"怀疑","PC":"惊奇","1":"积极","2":"消极","0":"中立"}

if __name__ == "__main__":
    trans = Translate()
    print(trans.baidu.sentimentClassify("小鸡看到小鸭很高兴，就叫小鸭过来和他一起捉虫子。"))

    #sent = '这家餐厅的菜单上多了几道我喜欢吃的菜'
    #sent = '我家养了十只小鸭'
    # tester  customer
    # print(trans.digit_encode('0'))

    #print(trans.sentence_seg(sent))

    # 打开数据库连接
    db = pymysql.connect("175.6.20.113", "data_analyst", "QBd@ta2019", "DataCollection", charset='utf8')

    # 使用cursor()方法获取操作游标
    cursor = db.cursor()

    # SQL 查询语句
    sql = "SELECT content FROM nlp_search Where Id >184600"
    try:
        # 执行SQL语句
        cursor.execute(sql)
        # 获取所有记录列表
        results = cursor.fetchall()
        book = xlwt.Workbook()  # 创建excel对象
        sheet = book.add_sheet('sheet1')  # 添加一个表
        sheet2 = book.add_sheet('sheet2')  # 添加一个表
        c = 0  # 保存当前列
        index_c=0
        index_c_emotion = 0

        for row in results:
            sent = row[0]
            #sent = '我这期间最惨的是中国到内部的问题不会很严重吗，中国内部问题非常严重，中国人股票陪陵榨菜培培培培陵榨菜浮云夏彩福福福马路吃的话榨菜，中国的这个吃泡面的时候一定要加人这个业绩好说表示，中国到了一般的中下阶层的，他们是过得不错，日子，因为他们吃泡面可以加榨菜蛋，你知道吗，这个陪陵榨菜最最近一段时间股价大跌，为什么业绩大患，为什么业绩早年榨菜都吃不起了啥菜都吃不起了啥菜都吃不起睡着就是非常大气镶嵌冲全中国人民都绷紧神经神经组织'
            print(sent)
            if len(sent)<20 or len(sent)>30:
                continue
            index_c += 1
            if index_c >100:
                break
            if sent[0] in PUNC:
                sent=sent[1:]
            out_put1 = trans.start(sent, 'customer')
            emotion_npn = []
            emotion = []
            emotion_npn2 = []
            emotion_npnb = []
            emotion2 = []
            sheet.write(c, 0, index_c)
            sheet.write(c, 1, sent)
            for index in range(len(out_put1)):  # 将每一个元组中的每一个单元存到每一列
                out_str=out_put1[index]['Word']
                #if '组织' == out_str:
                #    print(out_str)
                sheet.write(c, 2, out_str)
                #print(out_str + '0')
                if out_put1[index]['State']:
                    out_str=State_parse[str(out_put1[index]['State'])]
                    sheet.write(c, 3, out_str)
                #   print(out_str + '-1')
                if out_put1[index]['Type']:
                    out_str=Type_parse[str(out_put1[index]['Type'])]
                    sheet.write(c, 4, out_str)
                #    print(out_str + '-2')
                if out_put1[index]['Emotion']:
                #    print(out_str + '-4')
                    out_str =Emotion_parse[str(out_put1[index]['Emotion'])]
                    emotion.append(out_str)
                #   print(out_str + '-3')
                    sheet.write(c, 5, out_str)
                 #   print(out_str+'1')
                    sheet.write(c, 6, str(out_put1[index]['EmotionIntensity']))
                #    print(out_str + '2')
                    out_str =Emotion_parse[str(out_put1[index]['Npn'])]
                    emotion_npn.append(out_str)
                    sheet.write(c,7, out_str)
                #    print(out_str + '3')
                    out_str = Emotion_parse[str(out_put1[index]['Emotion2'])]
                    sheet.write(c, 8, out_str)
                    emotion2.append(out_str)
                #    print(out_str + '4')
                    out_str = Emotion_parse[str(out_put1[index]['Npn2'])]
                    sheet.write(c, 9, out_str)
                    emotion_npn2.append(out_str)
                    out_str = Emotion_parse[str(out_put1[index]['Npnb'])]
                    sheet.write(c, 10, out_str)
                    emotion_npnb.append(out_str)
                 #   print(out_str + '5')
                c+=1
            if len(emotion)>0:
                sheet2.write(index_c_emotion,0,index_c)
                sheet2.write(index_c_emotion,1, sent)
                str_out=','.join(set(emotion))
                sheet2.write(index_c_emotion, 3, str_out)
                str_out = ','.join(set(emotion_npn))
                sheet2.write(index_c_emotion, 4, str_out)
                str_out=','.join(set(emotion2))
                sheet2.write(index_c_emotion, 5, str_out)
                str_out = ','.join(set(emotion_npn2))
                sheet2.write(index_c_emotion, 6, str_out)
                str_out = ','.join(set(emotion_npnb))
                sheet2.write(index_c_emotion, 7, str_out)
                index_c_emotion+=1
            # out_by_json = json.dumps({"WordSequence": out_put1}, ensure_ascii=False, indent=4)
            #print(out_by_json)
        book.save("test2.xls")  # 保存excel

    except ValueError as e:
        raise ValueError(e)

    # 关闭数据库连接
    db.close()