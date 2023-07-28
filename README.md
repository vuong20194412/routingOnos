# routingOnos
## only collect network params: python program collect network params and export to collect.csv
1) - bazel run onos-local -- clean
2) - upload:
      + onos-apps-link-measurement-oar.oar; 
   - activate apps: 
      + openflow,
      + fwd,
      + linkmeasurement(Mao Link Quality Measurement)
4) - run create a mininet net: 
      + example: 
        sudo mn --controller remote,ip=localhost --switch ovs,protocols=OpenFlow13 --topo torus,3,3
4)  - run collect.py
5)  - mininet>pingall
## routing: python program collect network params, link-state routing and add rule to onos
1) - bazel run onos-local -- clean
2) - upload:
      + onos-apps-link-measurement-oar.oar; 
   - activate apps: 
      + openflow,
      + proxyarp,
      + linkmeasurement(Mao Link Quality Measurement)
4) - run create a mininet net: 
      + example: 
        sudo mn --controller remote,ip=localhost --switch ovs,protocols=OpenFlow13 --topo torus,3,3
4)  - run run.py
5)  - mininet>pingall
## routing: python program collect network params, link-state routing in java
0) - edit file \...\onos\apps\fwd\src\main\java\org\onosproject\fwd\ReactiveForwarding.java same content in ReactiveForwarding.java
   - bazel build onos
1) - bazel run onos-local -- clean
2) - upload:
      + onos-apps-link-measurement-oar.oar; 
   - activate apps: 
      + openflow,
      + fwd,
      + linkmeasurement(Mao Link Quality Measurement)
4) - run create a mininet net: 
      + example: 
        sudo mn --controller remote,ip=localhost --switch ovs,protocols=OpenFlow13 --topo torus,3,3
4)  - run collect.py
5)  - mininet>pingall
