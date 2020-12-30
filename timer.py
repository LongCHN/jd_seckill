# -*- coding:utf-8 -*-
import time
import requests
import json

from datetime import datetime
from datetime import date
from datetime import timedelta
from jd_logger import logger
from config import global_config
from exception import SKOverTimeException


class Timer(object):
    def __init__(self, sleep_interval=0.5):
        # '2018-09-28 22:45:50.000'
        today = date.fromtimestamp(time.time()).strftime("%Y-%m-%d")
        self.buy_time = datetime.strptime('%(day)s %(hour)s' % dict(day=today, hour=global_config.getRaw('config', 'buy_time')), "%Y-%m-%d %H:%M:%S.%f")
        # 抢5分钟就不抢了
        self.delta_time = 5
        self.last_buy_time = self.buy_time + timedelta(minutes=self.delta_time)
        self.before_buy_time = self.buy_time + timedelta(minutes=-self.delta_time)
        self.buy_time_ms = int(time.mktime(self.buy_time.timetuple()) * 1000.0 + self.buy_time.microsecond / 1000)
        self.last_buy_time_ms = int(time.mktime(self.last_buy_time.timetuple()) * 1000.0 + self.buy_time.microsecond / 1000)

        self.sleep_interval = sleep_interval

        self.diff_time = self.local_jd_time_diff()

    def jd_time(self):
        """
        从京东服务器获取时间毫秒
        :return:
        """
        url = 'https://a.jd.com//ajax/queryServerData.html'
        ret = requests.get(url).text
        js = json.loads(ret)
        return int(js["serverTime"])

    def local_time(self):
        """
        获取本地毫秒时间
        :return:
        """
        return int(round(time.time() * 1000))

    def local_jd_time_diff(self):
        """
        计算本地与京东服务器时间差
        :return:
        """
        return self.local_time() - self.jd_time()

    def get_real_time(self):
        return self.local_time() - self.diff_time

    def is_time_ready(self):
        return True

    def start(self):
        logger.info('正在等待到达设定时间:{}，检测本地时间与京东服务器时间误差为【{}】毫秒'.format(self.buy_time, self.diff_time))
        while True:
            # 本地时间减去与京东的时间差，能够将时间误差提升到0.1秒附近
            # 具体精度依赖获取京东服务器时间的网络时间损耗
            real_time = self.local_time() - self.diff_time
            if self.is_time_ready(real_time):
                if real_time > self.last_buy_time_ms:
                    logger.info('抢购时间已经超过%s分钟，等待下次抢购', self.delta_time)
                    tomorrow_time = self.before_buy_time + timedelta(days=1)
                    logger.info('等待明天继续%s', tomorrow_time)
                    time_sleep = int(time.mktime(tomorrow_time.timetuple())) - time.time()
                    logger.info('等待%s秒', time_sleep)
                    time.sleep(time_sleep)
                    logger.info('重新初始化参数')
                    self.__init__()
                    raise SKOverTimeException('等待下次抢购。。。。')
                else:
                    logger.info('时间到达，开始执行……')
                    break
            else:
                time.sleep(self.sleep_interval)


class ReserveTimer(Timer):
    def is_time_ready(self, real_time):
        return real_time >= self.before_buy_time


class BuyTimer(Timer):
    def is_time_ready(self, real_time):
        return real_time >= self.buy_time_ms
