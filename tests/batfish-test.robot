*** Settings ***
Library  LibraryBatfish.py  tmp/habr

*** Variables ***
${ISIS-ENABLED-LINK-DESCRIPTION}  ISIS-LINK
${NODE}  HKI-CORE-01
${PROTOCOL}  ebgp
${RIB-SIZE}  1

*** Test Cases ***
ISIS
    [Documentation]  Test if all ISIS neighbors are up
    ${result}=  Check ISIS Neighbors  ${ISIS-ENABLED-LINK-DESCRIPTION}
    Should Be Equal As Integers  ${result}  1

BGP
    [Documentation]  Test if all BGP peers are established
    ${result}=  Check BGP Peers
    Should Be Equal As Integers  ${result}  1

Routes
    [Documentation]  Validate the size of ${PROTOCOL} routing table on ${NODE}
    ${result}=  Check routes  ${NODE}  ${PROTOCOL}
    Should Be Equal As Integers  ${result}  ${RIB-SIZE}

Ping
    [Documentation]  Test end-to-end ICMP connectivity & show traceroute
    ${result}=  Ping  135.65.0.1  140.0.0.1
    Should Be Equal As Integers  ${result}  1
