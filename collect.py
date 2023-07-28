import requests;
from requests.auth import HTTPBasicAuth;
import pandas;
import json;
from time import time, sleep, strftime, gmtime;

COLLECT_CSV_PATH = '/home/vantv/Desktop/routingserver/collection/collect.csv';

SLEEP_TIME = 3;
EXEC_TIME = 1;
ROUND_TIME = SLEEP_TIME + EXEC_TIME;
MAX_TIME = ROUND_TIME * 3600;

UNSPECIFIED = -1;

PREFIX_URL = 'http://%(controllerIp)s:8181/onos/v1' % {'controllerIp': 'localhost'};

def get(fixUrl, label, prefixUrl=PREFIX_URL):
	
    try: 
        return requests.get(prefixUrl+fixUrl, auth=HTTPBasicAuth('onos', 'rocks')).json()[label];
    except:
        return {};

def getLatencyFromMaoApp():

    # latency[deviceIdSrc/portSrc-deviceIdDst/portDst] = link['latency']
    latency = {}

    linksLatency = get("/test/getLinksLatency", 'LinksLanency', "http://localhost:8181/onos/linkmeasurement");

    for link in linksLatency:

        s = str(link['link']);
        s = s.replace("DefaultLink{", "{\"").replace('=', "\": \"").replace(', ', "\", \"").replace("}", "\"}");
        js = json.loads(s);

        latency[js['src']+"-"+js['dst']] = link['latency'];

    return latency;

def getLinkParams():
    data = {'deviceSrc':[], 'portSrc': [], 'deviceDst':[], 'portDst': [], 'totalRate(Bps)': [], 'lossPkts(%)': [], 'latency(ms)': [],};

    # find link totalRate, lossPacketsPercent
    links = get('/links', 'links');

    for link in links:

        src = link['src'];
        dst = link['dst'];

        responseSrc = get(f"/statistics/delta/ports/{src['device']}/{src['port']}", 'statistics');
        responseDst = get(f"/statistics/delta/ports/{dst['device']}/{dst['port']}", 'statistics');

        try:
            statisticSrc = responseSrc['statistics'][0]['ports'];
            statisticDst = responseDst['statistics'][0]['ports'];

            if len(statisticSrc) > 0 and len(statisticDst) > 0:

                statisticSrc = statisticSrc[0];
                statisticDst = statisticDst[0];

                # calculate totalRate
                sentRateSrc = float(statisticSrc['bytesSent'])/float(statisticSrc['durationSec']) if statisticSrc['durationSec'] > 0 else 0;
                sentRateDst = float(statisticDst['bytesSent'])/float(statisticDst['durationSec']) if statisticDst['durationSec'] > 0 else 0;
                totalRate =  sentRateSrc + sentRateDst;

                # calculate lossPacketsPercent
                totalSentPackets = float(statisticSrc['packetsSent']) + float(statisticDst['packetsSent']);
                lossPackets = totalSentPackets - float(statisticSrc['packetsReceived']) - float(statisticDst['packetsReceived']);
                if lossPackets < 0 or totalSentPackets < 0: #khong sao vi tre
                    lossPackets = 0;
                lossPacketsPercent = lossPackets / (totalSentPackets + 10**-8) * 100;
            else:
                totalRate = UNSPECIFIED;
                lossPacketsPercent = UNSPECIFIED;
        except:
            totalRate = UNSPECIFIED;
            lossPacketsPercent = UNSPECIFIED;
            
        # push to data
        data['deviceSrc'].append(src['device']);
        data['portSrc'].append(src['port']);
        data['deviceDst'].append(dst['device']);
        data['portDst'].append(dst['port']);
        data['totalRate(Bps)'].append(int(totalRate));
        data['lossPkts(%)'].append(int(lossPacketsPercent));
        
    # find link latency

    latency = getLatencyFromMaoApp();

    for i in range(len(data['deviceSrc'])):

        s = data['deviceSrc'][i]+"/"+data['portSrc'][i]+"-"+data['deviceDst'][i]+"/"+data['portDst'][i];

        if s in latency:
            data['latency(ms)'].append(int(latency[s]));
        else:
            data['latency(ms)'].append(UNSPECIFIED);
    
    return data;

if __name__ == '__main__':

    t = time();

    while t + MAX_TIME > time():

        t1 = time();
        #get link params
        data = getLinkParams();

        # export csv
        df = pandas.DataFrame(data);
        df.to_csv(COLLECT_CSV_PATH, index=False);

        print("\ttime exec:", time() - t1, "s");

        t += ROUND_TIME;
        sleep(SLEEP_TIME);
        print("-----------------------------------------------------------\n")