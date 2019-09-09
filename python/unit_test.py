from model import *
import sl_trans2
import unittest

class TestSentence(unittest.TestCase):

    def test_init(self):
        # sent = '我家养了22只小鸭'
        # ss = Sentence(sent)
        # ss.process()
        # trans = Translate()
        # out_put1 = trans.start(sent, 'customer')
        # self.assertEqual(str(ss.toJson()), str(out_put1))
        sent = '我家养了22只小鸭'
        # ss = Sentence(sent)
        # ss.process()
        # trans = Translate()
        # out_put1 = trans.start(sent, 'customer')
        # self.assertEqual(str(ss.toJson()), str(out_put1))
        #sent = '这家餐厅的菜单上多了几道我喜欢吃的菜'
        ss = Sentence(sent)
        ss.process()
        trans = Translate()
        out_put1 = trans.start(sent, 'customer')
        self.assertEqual(str(ss.toJson()), str(out_put1))

if __name__ == '__main__':
    unittest.main()