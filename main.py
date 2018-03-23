# -*- coding: utf-8 -*-
#!/usr/bin/python
import os, sys
sys.path.append(os.path.dirname('/Library/Python/2.7/site-packages'))
sys.path.append(os.path.dirname('/usr/local/lib/python2.7/site-packages'))
from celery import Celery
import urllib, urllib2
from bs4 import BeautifulSoup
import re
import cookielib
import math
import urlparse
import hashlib
import datetime
import json
import tarfile, chardet, zipfile
import logging
from tensorflow_cnn import get_session, sess_predict_code
from PIL import ImageFilter, ImageEnhance, Image
import codecs

app = Celery(
    "zhongdeng",
    backend="redis://localhost:6379/0",
    broker='redis://localhost:6379/0')

sess = None


def init(key=None):
    global cookie, handler, opener, sess, predict, save_path, account, password, URL_PERFIX
    # init cookie
    cookie = cookielib.CookieJar()
    handler = urllib2.HTTPCookieProcessor(cookie)
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))

    # get session of tensorflow
    if sess is None:
        sess, predict = get_session()

    # create save path
    if key is None:
        save_path = os.path.join(
            "static", datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
    else:
        save_path = os.path.join("static", key)
    os.mkdir(save_path)
    account = "[need input account]"
    password = "[need input password]"

    URL_PERFIX = "http://www.zhongdengwang.org.cn"


def init_logger():
    global LOGGER
    logfile = os.path.join(save_path, "debug.log")
    LOGGER = logging.getLogger(logfile)
    LOGGER.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '[%(asctime)s] [%(funcName)s->%(lineno)d] [%(levelname)s]    %(message)s'
    )
    hdlr1 = logging.FileHandler(logfile)  #日志文件路径与文件名
    hdlr1.setFormatter(formatter)
    hdlr1.setLevel(logging.DEBUG)
    LOGGER.addHandler(hdlr1)
    hdlr2 = logging.StreamHandler(sys.stdout)  #添加标准输出的处理
    hdlr2.setFormatter(formatter)
    hdlr2.setLevel(logging.DEBUG)
    LOGGER.addHandler(hdlr2)


def download(url, filepath):
    '''
    download sepcify resource from url to filepath
    '''
    response = opener.open(url)
    with open(filepath, "w") as f:
        f.write(response.read())


def user_login():
    '''
    user login
    '''
    # 清空cookie
    cookie.clear()

    def encrypt_password(password, sessionId):
        '''
        encrypt the passwrod as they want
        '''
        return hashlib.md5(
            hashlib.md5(password).hexdigest().upper() +
            sessionId).hexdigest().upper()

    def get_auth_session():
        '''
        find the session id in html
        a little weak
        '''
        URL = URL_PERFIX + "/rs/main.jsp"
        response = opener.open(URL)
        key_prefix = 'var sessionId="'
        sessions = [
            line.strip()[len(key_prefix):-2] for line in response.readlines()
            if key_prefix in line
        ]
        if sessions.__len__() == 0:
            raise ValueError()
        return sessions[0]

    URL = URL_PERFIX + "/rs/login.do?method=login"
    sessionId = get_auth_session()
    code = get_code()
    values = {
        "userCode": account,
        "password": encrypt_password(password, sessionId),
        "validateCode": code
    }
    data = urllib.urlencode(values)
    req = urllib2.Request(URL, data)
    response = opener.open(req)
    return '"/rs/main.do"' in response.read()


def get_code(url="/rs/include/vcodeimage3.jsp"):
    '''
    downlod the captcha and predict it
    '''
    code_path = os.path.join(save_path, "login_code.jpg")
    download(URL_PERFIX + url, code_path)
    code = sess_predict_code(sess, predict, code_path)
    return code


def query_by_name(name):
    '''
    search company info by its name
    return html
    '''

    def analyze_query_html(html):
        '''
        analyze the html from query compay name
        find all the number between [15,25]
        only take the first 100(max download number)
        '''
        soup = BeautifulSoup(html, "html.parser")
        scp = [
            x
            for x in soup.find_all(
                "script", attrs={"type": "text/javascript"})
            if x.has_attr("src") == False
        ]
        scp = scp[0]
        if not "summaryData" in scp.string:
            raise ValueError()
        no_re = re.compile(r"','([0-9]{15,25})','")
        no_list = re.findall(no_re, scp.string)
        ids_list = [
            no_list[100 * x:100 * x + 100]
            for x in range(int(math.ceil(len(no_list) / 100.0)))
        ]
        return [",".join([i for i in ids]) for ids in ids_list]

    URL = URL_PERFIX + "/rs/conditionquery/byname.do?method=QueryByName"
    retry = 0
    while True:
        try:

            code = get_code("/rs/include/vcodeimage4.jsp")
            values = {"debttype": 1000, "name": name, "validateCode": code}
            data = urllib.urlencode(values)
            req = urllib2.Request(URL, data)
            response = opener.open(req)
            if "rs/sessiontimeout.jsp" in response.url:
                raise urllib2.HTTPError(response.url, 401, 'need login')
            ids = analyze_query_html(response.read())
            return ids
        # finally:
        except urllib2.HTTPError as exr:
            if exr.code == 401:
                LOGGER.warn("cookie may expired!")
                raise exr
        except Exception, e:
            pass
        retry += 1
        assert retry <= 3, "stop retry."


def download_zip_file(company, ids, code, zip_path):
    URL = URL_PERFIX + "/rs/conditionquery/byid.do?method=zipdownloadfile"
    values = {
        "ids": ids,
        "regno": "",
        "confirmNo": "",
        "type": "1",
        "resultNo": "",
        "businessType": "all",
        "validateCode": code
    }
    data = urllib.urlencode(values)
    req = urllib2.Request(URL, data)
    download(req, zip_path)
    unzip_file(zip_path)


def validate_download_code():
    '''
        before download file, need check validate code first, then use the code to download zip file.
    '''
    URL = URL_PERFIX + "/rs/conditionquery/byid.do?method=checkValidateCode"
    retry = 0
    while True:
        try:
            code = get_code()
            values = {"validateCode": code}
            data = urllib.urlencode(values)
            req = urllib2.Request(URL, data)
            response = opener.open(req)
            result = response.read()
            if result.upper() == "YES":
                return code
        # finally:
        except Exception, e:
            pass
        retry += 1
        assert retry <= 3, "stop retry"


def fetch_companies():
    '''
        fetch company's name from list file
        be sure the file is encoded by utf-8
    '''
    with open("company_list.txt", 'r') as f:
        return [company.strip(' \n\r\t') for company in f.readlines()]


#打包目录为zip文件（未压缩）
def make_zip(source_dir, output_filename):
    LOGGER.debug("zipping {} -> {}".format(source_dir, output_filename))
    with tarfile.open(output_filename, "w") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))


def unzip_file(zip_path, deleted=True):
    '''
    unzip file and remove the source zip file when deleted is True 
    '''
    if not os.path.exists(zip_path):
        return False
    if "_-_" in zip_path:
        temp_path = zip_path.split("_-_")[0]
    else:
        temp_path = zip_path[:-4]
    LOGGER.debug("unzipping {} -> {}".format(zip_path, temp_path))
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(path="{}".format(temp_path))
    os.remove(zip_path)

    filelist = os.listdir(temp_path)
    for file in filelist:
        if file.lower().endswith(".jpg"):
            enc = chardet.detect(file)["encoding"]
            try:
                os.rename(
                    os.path.join(temp_path, file),
                    os.path.join(temp_path,
                                 codecs.decode(file, enc).encode('utf-8')))
            except Exception, e:
                LOGGER.error("convert to utf-8 failed. err={}".format(e))

    files = [x for x in os.listdir(temp_path) if x.lower().endswith(".zip")]
    for f in files:
        # print("unzip file {}".format(f))
        unzip_file(os.path.join(temp_path, f))


def auth_login():
    '''
    user login with retry
    '''
    retry = 0
    while True:
        LOGGER.debug("user login...")
        if user_login():
            LOGGER.debug("login success!")
            break
        #ans = raw_input("login failed! try again?[Y|N]")
        #if ans == "Y":
        #    continue
        retry += 1
        assert retry <= 3, "user login failed, the script is shutting down ..."


def work_flow(companys=None):
    '''
    main work flow for download zip files
    '''
    auth_login()

    if companys is None:
        companys = fetch_companies()
    job_status = []
    for company in companys:
        retry = 0
        LOGGER.debug(">" * 30)
        LOGGER.debug("processing {}...[{}]".format(company, retry))
        while True:
            try:
                LOGGER.debug("query for name...")
                ids_list = query_by_name(company)
                if len(ids_list) == 0:
                    raise ValueError("nothing found to download!")
                for i, ids in enumerate(ids_list):
                    zip_path = os.path.join(save_path, "{}_-_{}.zip".format(
                        company, i))
                    LOGGER.debug(
                        "validating download captcha[{}]...".format(i))
                    code = validate_download_code()
                    LOGGER.debug(
                        "downloading zip file [{}] to {}".format(i, zip_path))
                    download_zip_file(company, ids, code, zip_path)
                job_status.append({
                    "name": company,
                    "result": "ok",
                    "batch": len(ids_list)
                })
                LOGGER.debug("=" * 30)
                break
            # finally:
            #     pass
            except urllib2.HTTPError as exr:
                if exr.code == 401:
                    LOGGER.warn(
                        "receive code={} msg='{}'".format(exr.code, exr.msg))
                    auth_login()
            except Exception, e:
                LOGGER.warning("something goes wrong! err msg={}".format(e))
            retry += 1
            if retry > 3:
                job_status.append({"name": company, "result": "fail"})
                LOGGER.warning("skip {}.".format(company))
                LOGGER.debug("!" * 30)
                break

    LOGGER.debug("save result")
    with open(os.path.join(save_path, "result.txt"), 'w') as f:
        json.dump(job_status, f)

    with open(os.path.join(save_path, 'nothing_download_list.txt'), 'w') as f:
        for sts in job_status:
            if sts["result"] == 'fail':
                f.write(sts["name"])
                f.write("\n")

    make_zip(save_path, save_path + ".tar")


@app.task
def run_fetch(companys, key):
    init(key)
    init_logger()
    LOGGER.debug("run in celery task ...")
    companys = [codecs.encode(x, 'utf-8').strip(' \r\n\t') for x in companys]
    work_flow(companys)
    LOGGER.debug("task is done!")
    return save_path


if __name__ == "__main__":
    init()
    init_logger()
    work_flow()
    # query_by_name("你好")
