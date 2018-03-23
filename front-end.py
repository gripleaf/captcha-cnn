# -*- coding: utf-8 -*-
#!/usr/bin/python
import redis
import time
import random
from flask import Flask, redirect, request
from main import run_fetch
import codecs
import os
import datetime

app = Flask(__name__)


@app.route("/")
def index():
    return '''
    <h1>hello world!</h1>
    <h2>输入你需要查询的公司名称：(每行一个，上限100个)</h2>
    <form action="/task/upload" method="POST">
        <textarea name="companys" style="width:600px;height:400px;"></textarea>
        <br/>
        <input type="submit" value="Submit" />
    </form>
    <br/>
    <hr/>
    <br/>
    <h2>输入你需要下载的编号：</h2>
    <form action="/download" method="GET">
        <input name="code" type="text" ></input>
        <input type="submit" value="Submit" />
    </form>
    '''


@app.route("/task/upload", methods=["POST"])
def upload_task():
    companys = request.form.get("companys")
    if companys is None:
        return "empty input!"
    companys = codecs.encode(companys, "utf-8")
    # print companys
    # return companys
    companys = companys.split("\n")
    zip_path = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    result = run_fetch.delay(companys, zip_path)
    # while not result.ready():
    #     time.sleep(1)
    # print "task done :{0}".format(result.get())
    # zip_path = result.get()
    # if zip_path.startswith("/static"):
    #     return zip_path[7:]
    # if zip_path.startswith("static"):
    #     return zip_path[6:]
    return """
    <h1>您的下载编号是 <b>{}</b></h1>
    """.format(zip_path)


@app.route("/download", methods=["GET"])
def download():
    path = request.args.get('code')
    if os.path.exists(os.path.join("static", path + ".tar")):
        return """Please download <a href="/static/{}">{}</a> """.format(
            path + ".tar", path)
    return "task is processing or not exists, please waiting..."


if __name__ == "__main__":
    from werkzeug.contrib.fixers import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app)
    app.run(port=8080, host="0.0.0.0", debug=True)
