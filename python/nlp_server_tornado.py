#!/usr/bin/python
# -*- coding: UTF-8 -*-
from flask import Flask, request, session, flash, redirect, url_for, render_template, jsonify
from sl_trans import Translate
from datetime import timedelta
#from pyhanlp import HanLP
import os
import sys
import threading
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
import logging

#from jpype import JClass, startJVM
#import jpype

LOGOUT_WORD_FILE = './/data//9a_log_logout_words.txt'   # 未登录词表日志文件
POLY_WORD_FILE = './/data//9b_log_poly_words.txt'       # 多义词日志文件
STOP_WORD_FILE = './/data//9c_log_stop_words.txt'       # 停用词日志文件

gen_log = logging.getLogger("tornado.general")
gen_log.setLevel('ERROR')
app = Flask(__name__)
app.config.from_object('config')
app.config['JSON_AS_ASCII'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=1)  # 管理员一分钟后需要重新登录
trans = Translate()


@app.route('/', methods=['GET', 'POST'])
def main_page():
    """主页面
    """
    return render_template('homepage.html')


@app.route("/split", methods=['POST', 'GET'])
@app.route("/shouyupy/split", methods=['POST', 'GET'])
def sent_trans():
    """
    进行文本和角色的获取，将文本进行分词处理
    :return: 分词结果的 JSON 字符串
    """
    if request.method == 'POST':
        text = request.form.get('text')
        role = request.form.get('role') if request.form.get('role') else 'customer'
        sentence = request.form.get('sentence')
        if text:
            results = trans.start(text, role)
            # t = threading.Thread(target=log_word, args=(results, text))
            # t.start()
            return jsonify({"WordSequence": results})
        elif sentence:
            results = trans.start(sentence, role)
            # t = threading.Thread(target=log_word, args=(results, sentence))
            # t.start()
            return render_template('sent_trans.html', results=results)
        else:
            return render_template('sent_trans.html')
    else:
        text = request.args.get('text')
        role = request.args.get('role') if request.args.get('role') else 'customer'
        if text:
            results = trans.start(text, role)
            # t = threading.Thread(target=log_word, args=(results, text))
            # t.start()
            return jsonify({"WordSequence": results})
        else:
            return render_template('sent_trans.html')


def log_word(word_list, sentence):
    # 打开一个文件
    thread_lock = threading.Lock()
    thread_lock.acquire()
    with open(LOGOUT_WORD_FILE, "a+", encoding='utf-8') as logout_file, open(POLY_WORD_FILE, "a+", encoding='utf-8') as poly_file, \
            open(STOP_WORD_FILE, "a+", encoding='utf-8') as stop_word_file:
        for word_item in word_list:
            if word_item['Type'] == 0:
                logout_file.write(word_item['Word'] + ' ==> ' + sentence + '\n')
            elif word_item['Type'] == 1:
                poly_file.write(word_item['Word'] + ' ==> ' + sentence + '\n')
            if word_item['State'] == 5:
                stop_word_file.write(word_item['Word'] + '\n')
    thread_lock.release()


@app.route('/predict', methods=['GET', 'POST'])
@app.route("/shouyupy/predict", methods=['POST', 'GET'])
def word_predict():
    """
    采用逻辑回归和组合向量进行词语预测，该功能暂时停止使用。
    :return:
    """
    return render_template('word_predict.html')


@app.route('/login', methods=['GET', 'POST'])
@app.route("/shouyupy/login", methods=['POST', 'GET'])
def admin_login():
    """
    管理员信息验证，用户名和密码
    :return:成功进入admin界面，错误返回login.html
    """
    if request.method == 'POST':
        if request.form['account'] != app.config['ACCOUNT']:
            error = 'Invalid account'
            return render_template('login.html', error=error)
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
            return render_template('login.html', error=error)
        else:
            session['logged_in'] = 'yes'
            flash('You were logged in')
            return redirect(url_for('admin'))
    else:
        return render_template('login.html')


@app.route('/admin', methods=['POST', 'GET'])
@app.route("/shouyupy/admin", methods=['POST', 'GET'])
def admin():
    """
    管理员界面
    :return:
    """
    if session.get('logged_in') == 'yes':
        return render_template('admin.html')
    else:
        return redirect(url_for('admin_login'))


@app.route('/admin/shutdown', methods=['POST', 'GET'])
@app.route("/shouyupy/admin/shutdown", methods=['POST', 'GET'])
def sys_shutdown():
    """
    系统关闭
    :return:
    """
    if session.get('logged_in') == 'yes':
        os._exit(0)
    else:
        return redirect(url_for('admin_login'))


@app.route('/admin/reboot', methods=['POST', 'GET'])
@app.route("/shouyupy/admin/reboot", methods=['POST', 'GET'])
def sys_reboot():
    """
    系统重启，重启后将重新加载文件信息。
    :return:
    """
    if session.get('logged_in') == 'yes':
        os.system('sh restart.sh')
    else:
        return redirect(url_for('admin_login'))


def resource_path(relative_path): 
    """ Get absolute path to resource, works for dev and for PyInstaller """ 
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))) 
    return os.path.join(base_path, relative_path)
    
    
if __name__ == '__main__':
    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(11123)
    IOLoop.instance().start()
