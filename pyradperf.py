#! /usr/bin/env python3

from pyrad.client import Client
from pyrad.dictionary import Dictionary
import pyrad.packet
import six
import asyncio
import socket
import ipaddress
import argparse
import time
import datetime

class Config:
    def __init__(self) -> None:
        self.count = None
        self.times = None
        self.delay = None
        self.wait = None
        self.startIp = None
        self.usernameBase = "hoge-"
        self.msisdnBase = 10000001
        self.server = None
        self.secret = six.b("")
        self.pkt = None
        self.loop = False
        self.noStart = False
        self.noInterim = False
        self.noStop = False

        current_time = int(time.time())
        self.unique_id = hex(current_time)[2:]

    def setSecret(self, string):
        self.secret = six.b(string)
    
    def setStartIp(self, string):
        self.startIp = ipaddress.ip_address(string)

    def setServer(self, string):
        self.server = ipaddress.ip_address(string)
    
    def getServerStr(self):
        return str(self.server)

    def getNextIpStr(self, n):
        return str(self.startIp + n)

    def setPacket(self):
        server = self.getServerStr()
        radclient = Client(server=server, secret=self.secret, dict=Dictionary("dictionary"))
        self.pkt = radclient.CreateAcctPacket(code=pyrad.packet.AccountingRequest)
    
    def setAccountingPkt(self, n):
        #self.pkt["User-Name"] = self.usernameBase + str(n)
        self.pkt["Calling-Station-Id"] = str(self.msisdnBase + n)
        self.pkt["Framed-IP-Address"] = self.getNextIpStr(n)
        self.pkt["Acct-Session-Id"]=str(self.unique_id)+str(n).zfill(8)

    def setAccountingType(self, string):
        self.pkt["Acct-Status-Type"] = string


async def send(udp, Config, n):
    server = Config.getServerStr()
    usec = Config.delay*0.000001
    wait = Config.wait*0.1

    Config.setAccountingPkt(n)

    Config.setAccountingType("Start")
    pktStart = Config.pkt.RequestPacket()

    Config.setAccountingType("Interim-Update")
    pktUpdate = Config.pkt.RequestPacket()

    Config.setAccountingType("Stop")
    pktStop = Config.pkt.RequestPacket()

    if Config.noStart != True:
        time.sleep(usec)

        udp.sendto(pktStart, (server, 1813))
        await asyncio.sleep(wait)

    if Config.noInterim != True:
        time.sleep(usec)

        udp.sendto(pktUpdate, (server, 1813))
        await asyncio.sleep(wait)

    if Config.noStop != True:
        time.sleep(usec)

        udp.sendto(pktStop, (server, 1813))


async def async_main(Config):
    count = Config.count
    server = Config.server
    secret = Config.secret
    start = 0
    max = count

    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM);

    startDT = datetime.datetime.now()
    print("Start sending at " + str(startDT))
    if Config.times > 0:
        for n in range(Config.times):
            cors = [send(udp, Config, i) for i in range(start,max)]
            await asyncio.gather(*cors)
            if not Config.loop:
                start+=count
                max+=count
    else:
        while True:
            cors = [send(udp, Config, i) for i in range(start,max)]
            await asyncio.gather(*cors)
            if not Config.loop:
                start+=count
                max+=count

    endDT = datetime.datetime.now()
    print("All packets have been sent at " + str(endDT))
    print("Running duration: " + str(endDT-startDT))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Send RADIUS accouting packets')
    parser.add_argument("-c", "--count", type=int, default=100, help="how many of the same type of accounting packet will be sent before sending the next type")
    parser.add_argument("-t", "--times", type=int, default=10, help="number of repeating")
    parser.add_argument("-d", "--delay", type=int, default=10, help="delay between sending each packet (unit: 1 usec) NOTE: it might not be accurate if you specify a value <1000.")
    parser.add_argument("-w", "--wait", type=int, default=1, help="timer to wait to send the next type of accounting packet (unit: 100 msec)")
    parser.add_argument("-s", "--server", type=str, default="127.0.0.1")
    parser.add_argument("-p", "--secret", type=str, default="secret")
    parser.add_argument("-m", "--msisdn", type=int, default="10000001")
    parser.add_argument("-sip", "--startip", type=str, default="10.0.0.1")

    parser.add_argument("-nst", "--nostart", action="store_true")
    parser.add_argument("-ni", "--nointerim", action="store_true")
    parser.add_argument("-ns", "--nostop", action="store_true")

    parser.add_argument("-l", "--loop", action="store_true")
    args = parser.parse_args()

    cnf = Config()
    cnf.count = args.count
    cnf.times = args.times
    cnf.delay = args.delay
    cnf.wait = args.wait
    cnf.msisdnBase = args.msisdn
    cnf.noStart = args.nostart
    cnf.noInterim = args.nointerim
    cnf.noStop = args.nostop
    cnf.loop = args.loop
    cnf.setServer(args.server)
    cnf.setSecret(args.secret)
    cnf.setStartIp(args.startip)
    cnf.setPacket()
    
    Times = 0

    if cnf.noStart == False:
        Times += 1
    if cnf.noInterim == False:
        Times += 1
    if cnf.noStop == False:
        Times += 1

    if cnf.loop == False:
        print("target:"+args.server+", Total packets: "+str(args.count*Times*args.times))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main(cnf))
    loop.close()
