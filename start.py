import datetime
import os
import time
import requests
import xmltodict
import yaml
from apscheduler.schedulers.blocking import BlockingScheduler

from config import rsshub, twitterlist, proxies
from twitter import gentwiimg

twitter = {}


def time_printer(str):
    timeArray = time.localtime(time.time())
    Time = time.strftime("%Y-%m-%d %H:%M:%S", timeArray)
    print(Time, str)

def get_filectime(file):
    return datetime.datetime.fromtimestamp(os.path.getctime(file))

def cleancache(path='piccache/'):
    nowtime = datetime.datetime.now()
    deltime = datetime.timedelta(seconds=300)
    nd = nowtime - deltime
    for root, firs, files in os.walk(path):
        for file in files:
            if file[-4:] == '.png':
                filectime = get_filectime(path + file)
                if filectime < nd:
                    os.remove(path + file)
                    print(f"删除{file} (缓存{nowtime - filectime})")
                else:
                    print(f"跳过{file} (缓存{nowtime - filectime})")


def checktwitter():
    time_printer('检查推特列表')
    global twitter
    rss = requests.get(rsshub + 'twitter/list/' + twitterlist, proxies=proxies)
    listjson = xmltodict.parse(rss.text)
    if twitter == {}:
        twitter = listjson
        return
    if listjson['rss']['channel']['item'][0]['link'] != twitter['rss']['channel']['item'][0]['link']:
        time_printer('检测到列表变动')
        # 先去找原来的第一个在不在新的里面
        find = False
        i = 0
        for newtwis in listjson['rss']['channel']['item']:
            # 遍历新数据
            if newtwis['link'] == twitter['rss']['channel']['item'][0]['link']:
                time_printer('确认更新')
                find = True
                break
            i += 1
        if find:
            for a in range(0, i):
                b = i - 1 - a
                gentwiimg(listjson['rss']['channel']['item'][b])
                link = listjson['rss']['channel']['item'][b]['link']
                authorid = link[link.find('com/') + 4:link.find('/status')]
                time_printer("即将推送" + authorid)
                twiid = link[link.find('status/') + 7:]
                sendpush(authorid, twiid)
    twitter = listjson


def sendpush(authorid, twiid):
    with open('twitterpush.yaml', "r") as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    # 群推送
    try:
        groups = data['group'][authorid]
        for qunhao in groups:
            sendgroupmsg(qunhao, rf'[CQ:image,file=file:///{os.getcwd()}\piccache\{twiid}.png]', groupport)
    except KeyError:
        pass
    # 频道推送
    try:
        guilds = data['guild'][authorid]
        for channel_id in guilds:
            sendgroupmsg(channel_id, rf'[CQ:image,file=file:///{os.getcwd()}\piccache\{twiid}.png]', guildport)
    except KeyError:
        pass


def sendgroupmsg(qun, text, port=5678):
    return requests.get(rf'http://127.0.0.1:{port}/send_group_msg?group_id={qun}&message={text}').text


if __name__ == '__main__':
    checktwitter()
    scheduler = BlockingScheduler()
    scheduler.add_job(checktwitter, 'interval', seconds=30, id='checktwitter')
    scheduler.start()
