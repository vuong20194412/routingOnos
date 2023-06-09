# routingOnos

1) bazel run onos-local -- clean
2) upload onos-apps-link-measurement-oar.oar; activate apps: openflow,proxyarp,linkmeasurement(Mao Link Quality Measurement)
3) run create a mininet net: 
      example: 
        sudo mn --controller remote,ip=localhost --switch ovs,protocols=OpenFlow13 --topo torus,3,3
4)  run collect.py
5)  mininet>pingall
