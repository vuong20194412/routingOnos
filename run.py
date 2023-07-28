import requests;
from requests.auth import HTTPBasicAuth;
import json;
import heapq;
from time import time, sleep, strftime, gmtime;

SLEEP_TIME = 3;
EXEC_TIME = 1;
ROUND_TIME = SLEEP_TIME + EXEC_TIME;
MAX_TIME = ROUND_TIME * 3600;

UNSPECIFIED = -1;

PREFIX_URL = 'http://%(controllerIp)s:8181/onos/v1' % {'controllerIp': 'localhost'};

_has_expect = False;

TIMEOUT_FLOW_TIME = SLEEP_TIME;
LIFE_FLOW_TIME = ROUND_TIME;

TOTAL_RATE = 1/3;
LOSS_PACKETS_PERCENT = 1/3;
LATENCY = 1 - TOTAL_RATE - LOSS_PACKETS_PERCENT;

def postJson(fixUrl, params, data, prefixUrl=PREFIX_URL):

    headers = {'Content-Type': 'application/json','Accept': 'application/json',};
    try:
        return requests.post(prefixUrl+fixUrl, auth=HTTPBasicAuth('onos', 'rocks'), params=params, headers=headers, data=data).json();
    except:
        global _has_expect;
        _has_expect = True;
        return {};

def get(fixUrl, label, prefixUrl=PREFIX_URL):
	
    try: 
        return requests.get(prefixUrl+fixUrl, auth=HTTPBasicAuth('onos', 'rocks')).json()[label];
    except:
        global _has_expect;
        _has_expect = True;
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

def findDistanceAndMinElement(arr):
    maxElement = max(arr);
    minElement = maxElement;
    unspecifiedCount = 0;
    
    for e in arr:
        if e != UNSPECIFIED:
            if e < minElement: minElement = e;
        else: unspecifiedCount += 1;
    
    distance = maxElement - minElement + 10**-8;

    return [distance, minElement, unspecifiedCount];

def prepareDijkstra(data):
    if len(data['totalRate(Bps)']) == 0: return {};
    # calculate distance min totalRate
    distanceTotalRate, minTotalRate, unspecifiedTotalRateCount = findDistanceAndMinElement(data['totalRate(Bps)']);
    if unspecifiedTotalRateCount > 0: print("NUM_TOTAL_RATE_UNSPECIFIED:", unspecifiedTotalRateCount);
    # calculate distance min lossPacketsPercent
    distanceLossPacketsPercent, minLossPacketsPercent, unspecifiedLossPacketsPercentCount = findDistanceAndMinElement(data['lossPkts(%)']);
    if unspecifiedLossPacketsPercentCount > 0: print("NUM_LOSS_PACKETS_PERCENT_UNSPECIFIED:", unspecifiedLossPacketsPercentCount);
    # calculate distance min latency
    distanceLatency, minLatency, unspecifiedLatencyCount = findDistanceAndMinElement(data['latency(ms)']);
    if unspecifiedLatencyCount > 0: print("NUM_LATENCY_UNSPECIFIED:", unspecifiedLatencyCount);
    # adj[deviceId] = [{{'cost': ,'outCurrentPort': ,'nextDeviceId': , 'inNextPort': }}...]
    adj = {};

    for i in range(len(data['deviceSrc'])):
        #root node
        currentDeviceId = data['deviceSrc'][i];
        #out port of root node 
        outCurrentPort = data['portSrc'][i];
        #next node of root node
        nextDeviceId = data['deviceDst'][i];
        #in port of next node
        inNextPort = data['portDst'][i];
        #calculate cost from totalRate, lossPacketsPercent, latency
        cost = 1000;
        totalRate = data['totalRate(Bps)'][i];
        lossPacketsPercent = data['lossPkts(%)'][i];
        latency = data['latency(ms)'][i];
        if (latency != UNSPECIFIED and totalRate != UNSPECIFIED and lossPacketsPercent != UNSPECIFIED):
            totalRate = (totalRate - minTotalRate) / distanceTotalRate;
            lossPacketsPercent = (lossPacketsPercent - minLossPacketsPercent) / distanceLossPacketsPercent;
            latency = (latency - minLatency) / distanceLatency;
            cost = totalRate * TOTAL_RATE + lossPacketsPercent * LOSS_PACKETS_PERCENT + latency * LATENCY;
        if currentDeviceId not in adj: adj[currentDeviceId] = [];
        adj[currentDeviceId].append({'cost': cost,'outCurrentPort': outCurrentPort,'nextDeviceId': nextDeviceId, 'inNextPort': inNextPort});
    
    return adj;

def dijkstra(adj):
    # path[currentDeviceId][DstDeviceId] = {"next": nextDeviceId, "inNextPort": inNextPort, "outPort": outCurrentPort}
    path = {}
   
    for deviceId in adj:
        # iNode[currentDeviceId] = (preDeviceId, outPrePort, inCurrentPort)
        iNode = {deviceId: (deviceId, 0, 0)};
        iDist = {deviceId: 0};
        PQ = [];

        heapq.heappush(PQ, (iDist[deviceId], deviceId));

        while PQ:
            u = heapq.heappop(PQ)[1];
            if u not in adj: continue;
            for l in adj[u]:
                cost = l['cost'];
                up = l['outCurrentPort'];
                v = l['nextDeviceId'];
                vp = l['inNextPort'];
                if v not in iDist or cost + iDist[u] < iDist[v]:
                    iDist[v] = cost + iDist[u];
                    iNode[v] = (u, up, vp);
                    heapq.heappush(PQ, (iDist[v], v));

        # Because iNode[currentDeviceId] unknown outport
        # => dao nguoc tuyen duong deviceId -> ... -> node thanh node -> ... -> deviceId
        # iNode thanh dang: iNode[currentDeviceId] = (nextDeviceId, inNextPort, outCurrentPort)
        for node in iNode:
            if node == deviceId: continue;
            if node not in path: path[node] = {};
            path[node][deviceId] = {"next": iNode[node][0], "inNextPort": iNode[node][1], "outPort": iNode[node][2]}

    return path;

# get host macs in every deviceId
def getDeviceMacs():

    # deviceMac[deviceId] = {hostMac: port}
    deviceMac = {};
    devices = get("/devices", 'devices');

    for device in devices:
        if device['available'] == True:
            deviceMac[device['id']] = {};

    hosts = get("/hosts", 'hosts');

    for host in hosts:
        locations = host['locations'];
        for location in locations:
            deviceId = location['elementId'];
            if deviceId in deviceMac:
                hostMac = host['mac'];
                deviceMac[deviceId][hostMac] = location['port'];

    return deviceMac;

def createFlow(deviceId, outPort, inPort, dstMac):
    flow = { "tableId": "0", "groupId": 0, "packets": 0, "bytes": 0, 
            "liveType": "IMMEDIATE", "timeout": TIMEOUT_FLOW_TIME, 
            "priority": "MAX_PRIORITY", "isPermanent": False,
        "deviceId": deviceId, "state": "ADDED", "life": LIFE_FLOW_TIME, "appId": "org.onosproject.net.intent",
        "treatment": {
            "instructions": [
                { "type": "OUTPUT", "port": outPort}
            ],
            "deferred": []
        },
        "selector": {
            "criteria": [
                { "type": "IN_PORT", "port": inPort},
                { "type": "ETH_DST", "mac": dstMac }
            ]
        }
    } 

    if inPort == -1: flow["selector"]["criteria"].pop(0);

    return flow;

def createFlows(path):
    deviceMac = getDeviceMacs();
    flows = [];
    for deviceId1 in deviceMac:
        if deviceId1 not in path: continue;
        # case: hostMac is dstMac
        for hostMac in deviceMac[deviceId1]:
            port = deviceMac[deviceId1][hostMac];
            flows.append(createFlow(deviceId1, port, -1, hostMac));
        for deviceId2 in deviceMac:
            if deviceId2 == deviceId1: continue;
            if deviceId2 not in path: continue;
            for hostMac2 in deviceMac[deviceId2]:
                port2 = deviceMac[deviceId2][hostMac2];
                # host2 direct connect device1
                if hostMac2 in deviceMac[deviceId1]: continue;
                inPort = -1;
                deviceId = deviceId1;
                while deviceId != deviceId2:
                    flows.append(createFlow(deviceId, path[deviceId][deviceId2]['outPort'], inPort, hostMac2));
                    inPort = path[deviceId][deviceId2]['inNextPort'];
                    deviceId = path[deviceId][deviceId2]['next'];
                flows.append(createFlow(deviceId, port2, inPort, hostMac2));
    return flows;

def updateFlowRule(flows):

    response = postJson('/flows', params={'appId': 'org.onosproject.net.intent'}, data=json.dumps({"flows": flows}));

    _flows = get('/flows/application/org.onosproject.net.intent', 'flows');

    states = {'total': len(_flows)};
    for _flow in _flows:
        if _flow["state"] not in states:
            states[_flow["state"]] = 0;
        states[_flow["state"]] += 1;
    
    print(strftime("%Y-%m-%d %H:%M:%S", gmtime(time())),":");
    print("\tstate flow rule:",states);
    print("\tposted:",len(flows),"flows");

if __name__ == '__main__':

    t = time();

    while t + MAX_TIME > time():

        _has_expect = False;

        t1 = time();
        #get link params
        data = getLinkParams();

        #prepare dijkstra
        if not _has_expect: adj = prepareDijkstra(data);

        #dijkstra
        if not _has_expect: path = dijkstra(adj);

        #create flows
        if not _has_expect: flows = createFlows(path);

        #update flow rule
        if not _has_expect: updateFlowRule(flows);

        print("\ttime exec:", time() - t1, "s");

        t += ROUND_TIME;
        sleep(SLEEP_TIME);
        print("-----------------------------------------------------------\n")