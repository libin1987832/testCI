import logging
import re
from sl_trans2 import Translate
logger = logging.getLogger("simple_example")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# 设置日志格式
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)
class Resource:
        tran = Translate()

        @classmethod
        def getClassName(self,word):
            return self.tran.getClass(word)

        @classmethod
        def sentence_seg(self,sentence):
            return self.tran.sentence_seg(sentence)

        @classmethod
        def char_encode_export(self,ch):
            return self.tran.char_encode_export(ch)

        @classmethod
        def getClassNum(self,num):
            return self.tran.getClassNum(num)

        @classmethod
        def getViusal(self,word):
            return self.tran.getVisual(word)

        @classmethod
        def getPolysem(self,word):
            return self.tran.getPolySemy(word)
class Factory:
    model_module = __import__('model')
    @classmethod
    def getWord(self, class_name, word ,chara,sentence):
        obj_class_name = getattr(self.model_module, class_name)
        # 实例化对象
        obj = obj_class_name(word,chara,sentence)
        obj.visual = Resource.getViusal(word)
        logger.debug("toWord_obj:"+str(word)+class_name)
        # 根据子类名称从m.py中获取该类
        return obj

class Symbol(object):
    '词汇类和句子类的父类'
    def __init__(self,sym):
        self.algorithm = None
        self.symbol = sym
        self.relateWord = None
        self.visual = None


    def toWord_obj(self, wordChara,sentence):
        class_name, relate = Resource.getClassName(wordChara)

        obj = Factory.getWord(class_name, wordChara[0],wordChara[1],sentence)
        if relate:
            obj.relateWord = relate
        return obj

    def process(self):
        raise NotImplementedError('请实现process方法,处理具体的功能')

    def toJson(self):
        raise NotImplementedError('请实现toJson方法,输出格式')

    def toString(self):
        print(self.symbol)

class Sentence(Symbol):

    def __init__(self,sym):
        super().__init__(sym)
        self.word_list = []

    def split(self):
        #word_seq = algorithm.split(self.symbol)
        wordChara = Resource.sentence_seg(self.symbol)
        self.word_list = [self.toWord_obj(wc, self) for wc in wordChara]

    def process(self):
        self.split()
        [getattr(obj, 'process')() for obj in self.word_list]

    def toJson(self):
        return [getattr(obj, 'toJson')() for obj in self.word_list]


class Word(Symbol):

    def __init__(self,w,chara, s, t, se):
        super().__init__(w)
        self.type = t
        self.state = s
        self.sentence = se
        self.other = None
        self.character = chara

    def toJson(self):
        if not self.other:
            return dict(Word=self.symbol, State=self.state, Type=self.type, Other=self.other, Md5=None, Visual=self.visual,
                        Emotion=None)
        else:
            Other = [other.toJson() for other in self.other]
            return dict(Word=self.symbol, State=self.state, Type=self.type, Other=Other, Md5=None, Visual=self.visual,
                        Emotion=None)



class Sign(Word):

    def __init__(self, w,ch,se):
        super().__init__( w,ch,1, None, se)

    def process(self):
        self.symbol,self.state,self.type=Resource.getPolysem(self.symbol)

    def toJson(self):
        return super().toJson()


class Number(Word):

    def __init__(self, w, ch, se):
        super().__init__(w, ch, 3, None, se)

    def num_chinese_process(self, num):
        if Resource.getClassNum(num) == "Sign":
            self.other =Factory.getWord("Sign",num, 'n', self.sentence)
            getattr(self.other[0], 'process')()
        else:
            self.chinese_number_encode(num)

    def chinese_number_encode(self, num):
        num_keyword = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '零']
        num_words = []

        for num_chr in num:
            num_words.append(num_chr)
        if num_words[-1] in num_keyword:
            num_words.append('个')
        for index, item in enumerate(num_words):
            if item == '万':
                if num_words[index-1] in num_keyword:
                    obj = Factory.getWord('Sign', num_words[index-1], 'n', self.sentence)
                    self.other.append(obj)
                    getattr(self.other[0], 'process')()
                obj = Factory.getWord('Sign', '万', 'n', self.sentence)
                self.other.append(obj)
                getattr(self.other[0], 'process')()
            elif item in ['个', '十', '百', '千'] and index != 0 and num_words[index - 1] in num_keyword:
                # 实例化对象
                if item == '个':
                    obj = Factory.getWord('Sign', num_words[index - 1], 'n', self.sentence)
                else:
                    obj = Factory.getWord('Sign', num_words[index - 1] + item, 'n', self.sentence)
                self.other.append(obj)
                getattr(self.other[0], 'process')()
    def small_digit(self,num):
        num_keyword = {'0':'零','1':'一', '2':'二', '3':'三', '4':'四', '5':'五', '6':'六', '7':'七', '8':'八', '9':'九'}
        num_w = ['','十', '百', '千']
        shu=[]
        listnum = list(num)
        lennum = len(listnum) - 1
        preCh=""
        for item in listnum:
            if preCh != '0' or item != '0':
                shu.append(num_keyword[item])  # 先取输入数字中的第一个数对应的中文大写加到shu列表里，后续循环
                preCh = item
            if item != '0':
                shu.append(num_w[lennum])  # 例：4位数就取dic_unit中3对应的“仟”加到shu的第一个数字后面，后续循环
            lennum -= 1
        if shu[-1] == '零':
            shu[-1]=''
        return ''.join(shu)

    def to_chinese_digit(self):
        listnum = list(self.symbol)
        lennum = len(listnum)
        if lennum <5:
            return self.small_digit(self.symbol)
        elif lennum < 9:
            return self.small_digit(self.symbol[0:lennum-4])+"万"+self.small_digit(self.symbol[lennum-4:])
        else:
            return self.small_digit(self.symbol[0:lennum-8]) + "亿" + self.small_digit(self.symbol[lennum-8:lennum-4])+ "万" + self.small_digit(self.symbol[lennum-4:])

    def process(self):
        self.other=[]
        if self.symbol.encode('UTF-8').isdigit() and int(self.symbol) != 0:
            num_word = self.to_chinese_digit()
            chinese_num_list = re.split(re.compile("([一二三四五六七八九十百千万零]{1,15})"), num_word)
        else:
            self.state = 2
            chinese_num_list = re.split(re.compile("([一二三四五六七八九十百千万零]{1,15})"), self.symbol)
        logger.debug("chinese number:"+self.symbol+","+str(chinese_num_list))
        for index, word in enumerate(chinese_num_list):
            if index % 2 == 1:
                self.num_chinese_process(word)
            elif index % 2 == 0 and word != '':
                self.state = 1

    def toJson(self):
        return super().toJson()

class Filter(Word):

    def __init__(self, w,ch,se):
        super().__init__( w,ch, 5, None, se)

    def process(self):
        pass

    def toJson(self):
        return super().toJson()

class NumberSyn_Synonym_ExtendSyn(Word):

    def __init__(self, w,ch,se):
        super().__init__( w,ch, 2, None, se)

    def setRelate(self,relate):
        self.relateWord=relate

    def process(self):
        class_name , relate= Resource.getClassName([self.relateWord,'n'])
        self.other = [Factory.getWord(class_name,self.relateWord, 'n', self.sentence)]
        getattr(self.other[0], 'process')()

    def toJson(self):
        return super().toJson()

class Compound_CompoundSyn(Word):

    def __init__(self, w,ch,se):
        super().__init__( w, ch,3, None, se)

    def setRelate(self,relate):
        self.relateWord=relate

    def process(self):
        self.other=[]
        for seg in self.relateWord:
            other=Factory.getWord(seg, 'n', self.sentence)
            getattr(other, 'process')()
            self.other.append(other)

    def toJson(self):
        return super().toJson()

class Unsign(Word):

    def __init__(self, w,ch,se):
        super().__init__( w,ch, 3, 0, se)

    def process(self):
        self.other = []
        for c in self.symbol:
            other = Factory.getWord('Sign', Resource.char_encode_export(c), 'n', self.sentence)
            self.other.append(other)

    def toJson(self):
        return super().toJson()

if __name__ == "__main__":
    sent = '我家养了22只小鸭'
    ss=Sentence(sent)
    ss.process()
    print(ss.toJson())
