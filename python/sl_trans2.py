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

COMPUTER_PATH = r'.//data//3_computer_words.txt'
ART_PATH = r'.//data//4_art_words.txt'
FILTER_POS = ('q', 'uzhe', 'ule', 'uguo', 'ude1', 'ude2', 'ude3', 'usuo', 'udeng',
              'uyy', 'udh', 'uls', 'uzhi', 'ulian', 'e', 'y', 'o', 'x', 'xe', 'xm', 'xu', 'xx',
              'w', 'wkz', 'wky', 'wyz', 'wyy', 'wj', 'wt', 'wd', 'wf', 'wn', 'wm', 'ws', 'wp', 'wb', 'wh')
num_keyword = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '零']
num_regex = re.compile("([一二三四五六七八九十百千万零]{1,8})")


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
        # self.wsd_crf = crf()
        self.sentence = ''
        pynlpir.open()
        nlpir.ImportUserDict(USER_DICT.encode('utf-8'), 1)  # 导入用户自定义词典

    def getClassNum(self,num):
        if num in self.num_dict or num in self.num_syn_dict.keys():
            return "Sign",[]
        return "",[]
    def getClass(self,seg):
        if seg[0] != ' ':
            if seg[1] in FILTER_POS and seg[0] not in self.unfilter_words and not seg[0].encode(
                    'UTF-8').isalpha():  # 对过滤词的处理
                return "Filter",[]
            elif seg[0] in self.stop_words:  # 对停用词进行处理
                return "Filter",[]
            elif seg[0] in ['？', '?']:  # 对问号进行处理
                return "Filter",[]
            elif seg[0] in self.sign_dict or seg[0] in self.num_dict:  # 手语词典查找
                return "Sign", []
            elif seg[1] in ['m', 'mq', 't']:  # 对数字进行处理
                return "Number",[]
            elif seg[0] in self.num_syn_dict.keys():  # 数字近义词词典查找
                return "NumberSyn_Synonym_ExtendSyn",self.num_syn_dict[seg[0]]
            elif seg[0] in self.extend_dict:  # 扩充词典查找
                return "Sign",[]
            elif seg[0] in self.seg_dict.keys():  # 组合表达词典查找
                return "Compound_CompoundSyn",self.seg_dict[seg[0]]
            elif seg[0] in self.syn_dict.keys():  # 近义词词典查找
                return "NumberSyn_Synonym_ExtendSyn",self.syn_dict[seg[0]]
            elif seg[0] in self.extend_syn_dict.keys():  # 扩充词语的近义词词典查找
                return "NumberSyn_Synonym_ExtendSyn",self.extend_syn_dict[seg[0]]
            elif seg[0] in self.seg_syn_dict.keys():  # 组合词语的近义词词典查找
                return "Compound_CompoundSyn",self.seg_syn_dict[seg[0]]
            elif seg[0] in self.char_dict:
                return "Sign",[]
            else:  # 针对词典未登录词语进行拆分查找，'Type'字段设置为0，用于词语日志记录
                return "Unsign",[]

    def getVisual(self,word):
        if word in self.visual_info.keys():
            return self.visual_info[word]
        return None
    def getPolySemy(self,word):
        if word in self.polysemy_info.keys():
            return  word if self.polysemy_info[word] == '1' else word +self.polysemy_info[word], 1, 1
        return word,1,None
    def start(self, sentence, role='customer'):
        self.sentence = sentence
        word_sequence = []
        # if sentence in self.poetry_info:
        #     for word in self.poetry_info[sentence][2]:
        #         word_sequence.append(self.word_encode(word))
        #     return word_sequence
        word_pos_list = self.sentence_seg(sentence)
        visual = self.visual_info.get(sentence.replace("，", "").replace("。", ""))
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

    def digit_encode_export(self, digit):
        #word_state = dict(Word=None, State=1, Type=None, Other=None, Md5=None, Visual=None, Emotion=None)
        if digit in self.num_dict:
            return digit
        elif digit in self.num_syn_dict.keys():
            return self.num_syn_dict[digit]
        return None

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
        #if word in self.emotion_dict.keys():  # 分析词语的情感
        #    word_state['Emotion'] = self.emotion_dict[word]
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
    def char_encode_export(self, char):
        """
        针对单个字符进行查找，未找到词语采用手指语，其中对于'Z''C''S',要区分'ZH''CH''SH'的情况
        :param char: 传入的单个字符
        :return: 单个字符的处理结果
        """
        if char in self.sign_dict:
            return char
        elif char in self.extend_dict:
            return char
        elif char in self.syn_dict.keys():  # 近义词词典查找
            return self.syn_dict[char]
        elif char in self.extend_syn_dict.keys():  # 扩充词语的近义词词典查找
            return self.extend_syn_dict[char]
        else:
            py = pinyin(char, style=Style.FIRST_LETTER)[0][0].upper()
        if py in ['Z', 'C', 'S'] and u'\u4e00' <= char <= u'\u9fa5':
            py = py + 'H' if pinyin(char, style=Style.NORMAL)[0][0][
                                                                 1].upper() == 'H' else py
        return py

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

State_parse={"1":"存在词语","2":"近义词替换","3":"组合词汇表达","5":"过滤词语"}
Type_parse={"0":"未登录词","1":"多义词","2":"旧版手语词汇","3":"千博新增词汇"}
Emotion_parse=  {"PA":"快乐","PE":"安心","PD":"尊敬","PH":"赞扬","PG":"相信","PB":"喜爱","PK":"祝愿","NA":"愤怒","NB":"悲伤","NJ":"失望","NH":"疚","PF":"思","NI":"慌","NC":"恐惧","NG":"羞","NE":"烦闷","ND":"憎恶","NN":"贬责","NK":"妒忌","NL":"怀疑","PC":"惊奇","0":"积极","1":"消极","2":"中立"}

if __name__ == "__main__":
    trans = Translate()
    sent = '这家餐厅的菜单上多了几道我喜欢吃的菜'
    #sent = '我家养了22只小鸭'
    # tester  customer
    # print(trans.digit_encode('0'))

    print(trans.sentence_seg(sent))
    out_put1 = trans.start(sent, 'customer')
    print(out_put1)
    out_by_json = json.dumps({"WordSequence": out_put1}, ensure_ascii=False, indent=4)
    print(out_by_json)
    # 打开数据库连接
    db = pymysql.connect("175.6.20.113", "data_analyst", "QBd@ta2019", "DataCollection", charset='utf8')

    # 使用cursor()方法获取操作游标
    cursor = db.cursor()

    # SQL 查询语句
    sql = "SELECT content FROM nlp_search Where Id <-1"
    try:
        # 执行SQL语句
        cursor.execute(sql)
        # 获取所有记录列表
        results = cursor.fetchall()
        book = xlwt.Workbook()  # 创建excel对象
        sheet = book.add_sheet('sheet1')  # 添加一个表
        c = 0  # 保存当前列
        for row in results:
            sent = row[0]
            if len(sent)<2:
                continue
            #if sent[0] in PUNC:
            #    sent=sent[2:]
            out_put1 = trans.start(sent, 'customer')
            sheet.write(c, 0, sent)
            for index in range(len(out_put1)):  # 将每一个元组中的每一个单元存到每一列
                out_str=out_put1[index]['Word']
                sheet.write(c, 1, out_str)
                out_str=State_parse[str(out_put1[index]['State'])]
                sheet.write(c, 2, out_str)
                if out_put1[index]['Type']:
                    out_str=Type_parse[str(out_put1[index]['Type'])]
                    sheet.write(c, 3, out_str)
                if out_put1[index]['Emotion']:
                    out_str =Emotion_parse[str(out_put1[index]['Emotion'])]
                    sheet.write(c, 4, out_str)
                c+=1
            print(out_put1)
            out_by_json = json.dumps({"WordSequence": out_put1}, ensure_ascii=False, indent=4)
            print(out_by_json)
        book.save("test.xls")  # 保存excel

    except:
        print
        "Error: unable to fecth data"

    # 关闭数据库连接
    db.close()