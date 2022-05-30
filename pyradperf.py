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
        self.startIp = None
        self.usernameBase = "hoge-"
        self.msisdnBase = "0123456"
        self.server = None
        self.secret = six.b("")
        self.pkt = None
        self.loop = False

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
        self.pkt["Calling-Station-Id"] = self.msisdnBase + str(n)
        self.pkt["Framed-IP-Address"] = self.getNextIpStr(n)
        self.pkt["Acct-Session-Id"]=str(n)

    def setAccountingType(self, string):
        self.pkt["Acct-Status-Type"] = string


async def send(udp, Config, n):
    server = Config.getServerStr()
    usec = Config.delay*0.000001

    Config.setAccountingPkt(n)

    Config.setAccountingType("Start")
    pktStart = Config.pkt.RequestPacket()

    Config.setAccountingType("Interim-Update")
    pktUpdate = Config.pkt.RequestPacket()

    Config.setAccountingType("Stop")
    pktStop = Config.pkt.RequestPacket()

    time.sleep(usec)

    udp.sendto(pktStart, (server, 1813))
    await asyncio.sleep(1)

    udp.sendto(pktUpdate, (server, 1813))
    await asyncio.sleep(1)

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
    parser.add_argument("-c", "--count", type=int, default=100)
    parser.add_argument("-t", "--times", type=int, default=10)
    parser.add_argument("-d", "--delay", type=int, default=10)
    parser.add_argument("-s", "--server", type=str, default="127.0.0.1")
    parser.add_argument("-p", "--secret", type=str, default="secret")
    parser.add_argument("-sip", "--start", type=str, default="10.0.0.1")

    parser.add_argument("-l", "--loop", action="store_true")
    args = parser.parse_args()

    cnf = Config()
    cnf.count = args.count
    cnf.times = args.times
    cnf.delay = args.delay
    cnf.loop = args.loop
    cnf.setServer(args.server)
    cnf.setSecret(args.secret)
    cnf.setStartIp(args.start)
    cnf.setPacket()

    print("target:"+args.server+", Total packets: "+str(args.count*3*args.times))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main(cnf))
    loop.close()