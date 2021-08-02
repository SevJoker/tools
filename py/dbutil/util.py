#!/usr/bin/env Python
#coding=utf-8
import MySQLdb
import sys
import os
import codecs
import math
import json
import urllib
import time
import re
import string
import io
import pycurl
import StringIO
import datetime 
import logging
import multiprocessing
from address_conf import *
from action.charAction.pinyin import PinYin

today = str(datetime.datetime.now().strftime("%Y-%m-%d"))
now_time = str(datetime.datetime.now().strftime("%H_%M"))


default_mysql = mysql_address["test_219"]

def mysql_create_connection(mysql_profile = default_mysql):

    user = mysql_profile["user"]
    passwd = mysql_profile["passwd"]
    db = mysql_profile["db"]
    charset = mysql_profile["charset"]
    host = mysql_profile["host"]
    port = mysql_profile["port"]

    connection = MySQLdb.Connect( 
                            user = user,
                            passwd = passwd,
                            db = db,
                            host = host,
                            port = port)
    connection.set_character_set(charset)

    return {"connection":connection, "info":mysql_profile}

def mysql_reconnect(mysql_connection):
    mysql_info = mysql_connection["info"]
    connection = mysql_connection["connection"]

    try:
        connection.close()
    except:
        pass
    del connection


    max_sleep_time = 5
    sleep_time = 0.3
    while True:
        try:
            connection = mysql_create_connection(mysql_info)
            return connection
        except Exception, e:
            if e[0] == 2003 or e[0] == 2006 or e[0] == 2013:
                print e
                time.sleep(sleep_time)
                sleep_time *= 1.5
                sleep_time = min(max_sleep_time, sleep_time)
                continue
            else:
                raise e

def mysql_destroy_connection(mysql_connection):
    try:
        connection = mysql_connection["connection"]
        connection.close()
        del mysql_connection
    except:
        pass

def mysql_query_into_array(mysql_connection, sql, auto_reconnection = True):

    table = None
    while True:
        mysql_info = mysql_connection["info"]
        connection = mysql_connection["connection"]

        try:
            connection.query(sql)
            result_set = connection.store_result()

            table = result_set.fetch_row(0, 1)
            connection.commit()
            return table
        except Exception, e:
            if e[0] == 2006:
                mysql_connection = mysql_reconnect(mysql_connection)
                continue
            elif e[0] == 2013:
                mysql_connection = mysql_reconnect(mysql_connection)
                continue
            raise e

def mysql_execute(mysql_connection, sql, auto_reconnection = True):

    aff_rows = None
    while True:
        mysql_info = mysql_connection["info"]
        connection = mysql_connection["connection"]
        
        try:
            connection.query(sql)
            aff_rows = connection.affected_rows()
            connection.commit()
            break
        except Exception, e:
            if e[0] == 2006:
                mysql_connection = mysql_reconnect(mysql_connection)
                continue
            elif e[0] == 2013:
                mysql_connection = mysql_reconnect(mysql_connection)
                continue
            raise e
    return aff_rows


def write_log(name,new_context):
    if os.path.isdir(log_root_file+today):
        pass
    else:
        os.mkdir(log_root_file+today)
    f=file(log_root_file+today+'/'+name+'_'+now_time+".log","a+")
    new_context = str(new_context) +'\n'
    f.write(new_context)
    f.close()

def write_question_log(name,id,context):
    if os.path.isdir(log_root_file+today):
        pass
    else:
        os.mkdir(log_root_file+today)
    f=file(log_root_file+today+'/'+name+'_'+now_time+".log","a+")
    sdata = {}
    sdata['id']=id
    sdata['context']=context
    new_context = json.dumps(sdata) +'\n'
    f.write(new_context)
    f.close()


def get_last_range(name):
    try:
        with open(log_root_file+name,'r') as f:
            for i in f:
                # print i
                # print log_root_file+name
                pass
            range_min = int(i)
        return range_min

    except Exception, e:
        return 0

def write_last_range(name,ID):
    f = file(log_root_file+name,'a+')
    f.write(str(ID)+'\n')
    f.close()

# 检测是否在白名单中  在为False  不在为True
def check_is_right(QuestionID,LastModifyTime=None):
    mysql_conn_seven = mysql_create_connection(mysql_address['seven'])
    right_data = mysql_query_into_array(mysql_conn_seven,"SELECT QuestionID,AddTime FROM kbox_base_right_question WHERE QuestionID=%s"%(QuestionID))
    if not right_data:
        return True

    if LastModifyTime and LastModifyTime > right_data[0]['AddTime']:
        mysql_execute(mysql_conn_seven,"DELETE FROM kbox_base_right_question WHERE QuestionID=%s"%(QuestionID))
        return True

    return False





def check_if_susuan(ID,mysql_connection):
    if not ID or not mysql_connection:
        return False

    check_sql = '''
SELECT
    t3.QuestionID
FROM
kbox_base_relate_courseassistquestion t3
LEFT JOIN 
    kbox_base_coursesection t2
on t3.CourseSectionID = t2.CourseSectionID
LEFT JOIN 
kbox_base_teachingassist t1
on t2.TeachingAssistID = t1.TeachingAssistID
WHERE
    t1.JiaoCaiID = 5418
and t3.QuestionID=%s

    '''%ID

    if mysql_query_into_array(mysql_connection,check_sql):
        return False
    else:
        return True

Subject_Dict = {
     0:'数学',1:'语文',2:'英语',3:'物理',4: '化学',5:'生物',6:'历史',7:'地理',8:'政治',9:'其他',
}

QuestType_Dict = {
0:'选择题',1:'多选题',2:'解答题',3:'填空',4:'翻译',5:'完形',6:'阅读理解',7:'语法',
}

def strQ2B(ustring):
    """全角转半角"""
    rstring = ""
    for uchar in ustring:
        inside_code=ord(uchar)
        if inside_code == 12288:                              #全角空格直接转换            
            inside_code = 32 
        elif (inside_code >= 65281 and inside_code <= 65374): #全角字符（除空格）根据关系转化
            inside_code -= 65248

        rstring += unichr(inside_code)
    return rstring
    
def strB2Q(ustring):
    """半角转全角"""
    rstring = ""
    for uchar in ustring:
        inside_code=ord(uchar)
        if inside_code == 32:                                 #半角空格直接转化                  
            inside_code = 12288
        elif inside_code >= 32 and inside_code <= 126:        #半角字符（除空格）根据关系转化
            inside_code += 65248

        rstring += unichr(inside_code)
    return rstring

def get_cn_first_letter(str):
    pinyin = PinYin()
    # letters = PinYin()
    pinyin.load_word()
    letters = pinyin.hanzi2pinyin(string=str)

    if len(letters) < 1:
        print 'NO PINYIN'
        return ''
    else:
        return letters[0][0].upper()
