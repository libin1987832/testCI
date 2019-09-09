# -*- coding: utf-8 -*-
"""
Author : Xiaobo Cheng
Contact: shawbown@foxmail.com
Date   : 2019/2/12 9:45
Desc   : 
"""
#import jieba
import numpy as np
from gensim.models.word2vec import Word2Vec
#from gensim.corpora.dictionary import Dictionary
#from keras.preprocessing import sequence

import yaml
from keras.models import model_from_yaml
np.random.seed(1337)  # For Reproducibility
import sys
sys.setrecursionlimit(1000000)

# define parameters
maxlen = 100


from collections import defaultdict
import os 
#import sys

from aip import AipNlp





def resource_path(relative_path): 
    """ Get absolute path to resource, works for dev and for PyInstaller """ 
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))) 
    return os.path.join(base_path, relative_path)


# eg: {'爱护' , '爱情' , '爱人'}
def load_sign_dict(*params):  # 读取手语词表词语
    sign_words = []
    for param in params:
        # print(resource_path(param))
        with open(resource_path(param), 'r', encoding='utf-8') as sf:
            for line in sf.readlines():
                line_words = line.strip().split(' ')
                for word in line_words:
                    sign_words.append(word)
    return set(sign_words)


# eg: {'大姨'：'阿姨'，'姨娘'：'阿姨'}
def load_syn_dict(syn_dict_path):  # 读取手语近义词词典
    syn_word_dict = defaultdict(str)
    with open(resource_path(syn_dict_path), 'r', encoding='utf-8') as sf:
        for line in sf.readlines():
            line_words = line.splitlines()[0].strip().split(' ')
            tag = line_words[0]
            for word in line_words[1:]:
                syn_word_dict[word] = tag
    return syn_word_dict


# eg: {'国标':['国家','标准'], '正常人':['正常','人']}
def load_seg_dict(seg_dict_path):  # 读取词语分割字典
    seg_dict = defaultdict(list)
    with open(resource_path(seg_dict_path), 'r', encoding='utf-8') as seg_f:
        for line in seg_f.readlines():
            line_words = line.splitlines()[0].strip().split(' ')
            seg_word = line_words[0]
            seg_dict[seg_word] = line_words[1:]
    return seg_dict


# eg: {'二百', '三百'}， {'200':'二百', '两百':'二百', '300':'三百'}
def load_extend_dict(extend_dict_path):  # 读取扩充词汇
    extend_dict = []
    extend_syn_dict = defaultdict(str)
    with open(resource_path(extend_dict_path), 'r', encoding='utf-8') as sf:
        for line in sf.readlines():
            line_words = line.splitlines()[0].strip().split(' ')
            extend_dict.append(line_words[0])
            for word in line_words[1:]:
                extend_syn_dict[word] = line_words[0]
    return set(extend_dict), extend_syn_dict


# eg: {'国家标准':['国家','标准']}
def load_seg_syn_dict(seg_syn_dict_path, seg_dict):  # 读取组合表达词汇的近义词
    seg_syn_dict = defaultdict(str)
    with open(resource_path(seg_syn_dict_path), 'r', encoding='utf-8') as sf:
        for line in sf.readlines():
            line_words = line.splitlines()[0].strip().split(' ')
            tag = line_words[0]
            express_word = seg_dict[tag]
            for word in line_words[1:]:
                seg_syn_dict[word] = express_word
    return seg_syn_dict


# eg: {'啊', '哦'}
def load_stop_words(stop_word_path):  # 去除停用词
    stop_words = []
    with open(resource_path(stop_word_path), mode="r", encoding='utf-8') as rf:
        for line in rf.readlines():
            word = line.strip()
            stop_words.append(word)
    stop_words = set(stop_words)
    return stop_words


def load_unfilter_words(unfilter_word_path):  # 非过滤词
    unfilter_words = []
    with open(resource_path(unfilter_word_path), mode='r', encoding='utf-8') as rf:
        for line in rf.readlines():
            word = line.strip()
            unfilter_words.append(word)
    unfilter_words = set(unfilter_words)
    return unfilter_words


def load_emotion_dict(emotion_dict_path):
    with open(resource_path(emotion_dict_path), 'r', encoding='utf-16') as ef:
        emotion_dict = defaultdict(str)
        for line in ef.readlines():
            line_elements = line.strip().split('\t')
            emotion_dict[line_elements[0]] = line_elements[4]
            emotion_dict[line_elements[0]+'-i'] = line_elements[5]
            emotion_dict[line_elements[0]+'-n'] = line_elements[6]
            if line_elements[6] == '3':
                emotion_dict[line_elements[0] + '-n'] = '0'
    return emotion_dict


def load_visualization_info(visualization_info_path):  # 读取词语具象化信息
    visual_info = dict()
    with open(resource_path(visualization_info_path), 'r', encoding='utf-8') as sf:
        for line in sf.readlines():
            split = line.splitlines()[0].strip().split(' ', 1)
            if len(split) != 2:
                continue
            visual_info[split[0]] = split[1]
    return visual_info


def load_polysemy_info(polysemy_info_path):  # 一词多义优先级
    polysemy_info = dict()
    with open(resource_path(polysemy_info_path), 'r', encoding='utf-8') as rf:
        for line in rf.readlines():
            line = line.strip().split(' ')
            polysemy_info[line[0]] = line[1]
    return polysemy_info


def load_poetry_info(poetry_info_path):  # 读取古诗词
    poetry_info = dict()

    with open(resource_path(poetry_info_path), 'r', encoding='utf-8') as rf:
        for line in rf.readlines():
            direct_trans, free_trans = [], []
            line = line.strip().split(',')
            for word in line[1].strip().split(' '):
                direct_trans.append(word)
            for word in line[3].strip().split(' '):
                free_trans.append(word)
            poetry_info[line[0]] = [direct_trans, line[2].strip(), free_trans]
    return poetry_info


def load_computer_dict(computer_path):  # 读取计算机词汇
    computer_dict = defaultdict(str)
    with open(resource_path(computer_path), 'r', encoding='utf-8') as sf:
        for line in sf.readlines():
            line_words = line.splitlines()[0].strip().split(' ')
            tag = line_words[0]
            computer_dict[tag] = tag
    return computer_dict


def load_art_dict(art_path):  # 读取美术词汇
    art_dict = defaultdict(str)
    with open(resource_path(art_path), 'r', encoding='utf-8') as sf:
        for line in sf.readlines():
            line_words = line.splitlines()[0].strip().split(' ')
            tag = line_words[0]
            art_dict[tag] = tag
    return art_dict

#def input_transform(path):
def load_word2vec(path):
    #words=jieba.lcut(string)
    #words=np.array(words).reshape(1,-1)
    #model=Word2Vec.load('../model/Word2vec_model.pkl')
    #_,_,combined=create_dictionaries(model,words)
    #return combined
    model = Word2Vec.load(path)
    return model


#def lstm_predict(string):
def load_lstm_weight(path_yml,path_h5):
    print('loading model......')
    #with open('../model/lstm.yml', 'r') as f:
    with open(path_yml, 'r') as f:
        yaml_string = yaml.load(f)
    model = model_from_yaml(yaml_string)
    print('loading weights......')
    #model.load_weights('../model/lstm.h5')
    model.load_weights(path_h5)
    model.compile(loss='categorical_crossentropy',
                  optimizer='adam',metrics=['accuracy'])
    return model
    #data=input_transform(string)
    #data.reshape(1,-1)
    #print data
    #result=model.predict_classes(data)
    # print result # [[1]]
    #if result[0]==1:
    #    print(string,' positive')
    #elif result[0]==0:
    #    print(string,' neural')
    #else:
    #    print(string,' negative')

def baidu_emotion():
    """ 你的 APPID AK SK """
    APP_ID = '16843089'
    API_KEY = 'TC0FYrt0Vk3vR34faeUVzEXt'
    SECRET_KEY = 'QUir6y7Kp6PptE4y9nicznpX59IpB6aO'
    client = AipNlp(APP_ID, API_KEY, SECRET_KEY)
    return client


if __name__ == '__main__':
    res = load_poetry_info('.//data//12_poetry.txt')
    print(res)
