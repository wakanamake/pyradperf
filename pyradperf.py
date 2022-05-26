from pyrad.client import Client
from pyrad.dictionary import Dictionary
import pyrad.packet
from itertools import count
import six
import asyncio
import socket
import ipaddress
import argparse

def sendAccountingPkt(udp, pkt, n, type):
    #print("Sending Packet#"+str(n))
    ip = ipaddress.ip_address('10.0.0.1') + n
    username = "hoge-" + str(n)
    msisdn = "0123456" + str(n)

    pkt["Acct-Status-Type"]=type
    pkt["User-Name"]=username
    pkt["Calling-Station-Id"]=msisdn
    pkt["Framed-IP-Address"]=str(ip)
    pkt["Acct-Session-Id"]=str(n)

    udp.sendto(pkt.RequestPacket(), ("172.17.150.27", 1813))

async def send(udp, pkt, n, semaphore: asyncio.Semaphore):
    async with semaphore:
        sendAccountingPkt(udp, pkt, n, "Start")
        await asyncio.sleep(1)
        sendAccountingPkt(udp, pkt, n, "Stop")

async def async_main(server, secret, n, loop):
    count = 0
    max = n
    s = asyncio.Semaphore(value=n)

    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM);
    radclient=Client(server=server, secret=six.b(secret), dict=Dictionary("dictionary"))
    pkt = radclient.CreateAcctPacket(code=pyrad.packet.AccountingRequest)

    while True:
        cors = [send(udp, pkt, i, semaphore=s) for i in range(count,max)]
        await asyncio.gather(*cors)
        if not loop:
            count+=n
            max+=n
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Send RADIUS accouting packets')
    parser.add_argument("-c", "--count", type=int, default=10)
    parser.add_argument("-s", "--server", type=str, default="127.0.0.1")
    parser.add_argument("-p", "--secret", type=str, default="secret")
    parser.add_argument("-l", "--loop", action="store_true")
    args = parser.parse_args()

    print("target:"+args.server+", pps: "+str(args.count*2))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main(args.server, args.secret, args.count, args.loop))
    loop.close()