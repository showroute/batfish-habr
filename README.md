# Batfish-Habr

![alt text](https://github.com/showroute/batfish-habr/blob/master/images/batfish-logo.png)

## Introduction

Одной из проблем современных сетей является их сложность. Множество правил фильтраций, политик обмена маршрутной информации, протоколов динамического роутинга делают сети запутанными и хрупкими. Авария на сети может произойти ненамеренно при внесении ошибочных изменений в работу routing protocols, route-map или ACL ([один](https://www.popularmechanics.com/technology/news/a27971/google-accidentally-broke-japans-internet/), [два](https://www.theregister.co.uk/2016/06/20/telia_engineer_blamed_massive_net_outage/)).
Нам определено не хватает pre-deployment инструмента, позволяющего оценить поведение сети с новой конфигурацией перед внесением изменений в prod. Хочется точно знать, будет ли мне доступна сеть A, если я отфильтрую часть входящих анонсов провайдера B? Каким маршрутом пойдут пакеты из сети C к серверу D, если на одном из транзитных линков я увеличу IGP метрику в два раза? Ответить на эти и многие другие вопросы нам поможет Batfish!

## Batfish overview

Batfish – это open source инструмент для моделирования сети. Основным его назначением является тестирование
конфигурационных изменений перед внесением в production environment. Batfish так же можно использовать для анализа и проверки текущего состояния сети. Существующим CI/CD процессам в сетевом мире явно не хватает инструмента для тестирования новых конфигураций. Batfish позволяет решить эту проблему.

Batfish не требуется доступ на сетевое оборудование. Batfish моделирует поведение сети на основе конфигурационных файлов сетевых устройств. 

Batfish может:
* определить статус соседства протоколов динамической маршрутизации в сети (BGP, IS-IS, OSPF)
* просчитать RIB каждого сетевого элемента
* проверить настройки NTP, AAA, logging, MTU
* позволить определить, блокирует ли ACL прохождение сетевого трафика (аналог packet-tracer на Cisco ASA)
* проверить наличие end-to-end связности между хостами внутри сети
* показать путь для конкретного flow (virtual traceroute)

Поддерживаемые платформы:
* Arista
* Aruba
* AWS (VPCs, Network ACLs, VPN GW, NAT GW, Internet GW, Security Groups, etc…)
* Cisco (All Cisco NX-OS, IOS, IOS-XE, IOS-XR and ASA devices)
* Dell Force10
* Foundry
* iptables (on hosts)
* Juniper (All JunOS platforms: MX, EX, QFX, SRX, T-series, PTX)
* MRV
* Palo Alto Networks
* Quagga / FRR
* Quanta
* VyOS

![alt text](https://github.com/showroute/batfish-habr/blob/master/images/how-batfish-works.png)

Batfish – это Java приложение. Для удобного взаимодействия с ним был написан Pybatfish - python SDK.

Перейдем к практике. 

Я продемонстрирую Вам возможности Batfish на примере.

## Example

Под нашим управлением находится две автономные системы: AS 41214 и AS 10631. В качестве IGP в AS 41214 используется IS-IS, в AS 10631 – OSPF. Внутри каждой AS используется IBGP-fullmesh. LDN-CORE-01 анонсирует своим соседям via BGP префикс 135.65.0.0/19, MSK-CORE-01 – 140.0.0.0/24. Обмен маршрутной информацией между автономными системами происходит на стыке HKI-CORE-01 --- SPB-CORE-01.

**HKI-CORE-01, STH-CORE-01** - Junos routers

**LDN-CORE-01, AMS-CORE-01, SPB-CORE-01, MSK-CORE-01** - Cisco IOS routers

![alt text](https://github.com/showroute/batfish-habr/blob/master/images/topology1.png)

Установим контейнер с batfish и python sdk.
```
docker pull batfish/allinone
docker run batfish/allinone
```
Познакомимся с библиотекой через интерактивный режим python:
```
root@ea9a1559d88e:/# python3
--------------------
>>> from pybatfish.client.commands import bf_logger, bf_init_snapshot
>>> from pybatfish.question.question import load_questions
>>> from pybatfish.question import bfq
>>> import logging
>>> bf_logger.setLevel(logging.ERROR)
>>> load_questions()
>>> bf_init_snapshot('tmp/habr')

'ss_e8065858-a911-4f8a-b020-49c9b96d0381'
```

**/tmp/habr** – директория с конфигурационными файлами роутеров.

**bf_init_snapshot('tmp/habr')** - функция загружает конфигурационные файлы в Batfish и подготавливает их к анализу.
```
root@ea9a1559d88e:/tmp/habr# tree
.
`-- configs
    |-- AMS-CORE-01.cfg
    |-- HKI-CORE-01.cfg
    |-- LDN-CORE-01.cfg
    |-- MSK-CORE-01.cfg
    |-- SPB-CORE-01.cfg
    `-- STH-CORE-01.cfg

1 directory, 6 files
```

Теперь давайте определим статус BGP сессий на роутере LDN-CORE-01:
```
>>> bgp_peers = bfq.bgpSessionStatus(nodes='LDN-CORE-01').answer().frame()
>>> bgp_peers
          Node      VRF  Local_AS        Local_Interface     Local_IP  Remote_AS  Remote_Node    Remote_IP Session_Type Established_Status
0  ldn-core-01  default     41214  ldn-core-01:Loopback0  172.20.20.1      41214  sth-core-01  172.20.20.2         IBGP        ESTABLISHED
1  ldn-core-01  default     41214  ldn-core-01:Loopback0  172.20.20.1      41214  ams-core-01  172.20.20.3         IBGP        ESTABLISHED
2  ldn-core-01  default     41214  ldn-core-01:Loopback0  172.20.20.1      41214  hki-core-01  172.20.20.4         IBGP        ESTABLISHED
```
Ну, как? Похоже на правду?
```
LDN-CORE-01#show ip bgp summary
…
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
172.20.20.2     4        41214     629     669        9    0    0 00:56:51        0
172.20.20.3     4        41214     826     827        9    0    0 01:10:18        0
172.20.20.4     4        41214     547     583        9    0    0 00:49:24        1…..
```
Теперь давайте посмотрим, какие IS-IS маршруты есть в RIB на маршрутизаторе HKI-CORE-01 по мнению Batfish
```
>>> isis_routes = bfq.routes(nodes='HKI-CORE-01', protocols='isis').answer().frame()
>>> isis_routes
          Node      VRF         Network     Next_Hop Next_Hop_IP Protocol  Admin_Distance  Metric   Tag
0  hki-core-01  default  172.20.20.3/32  ams-core-01    10.0.0.6   isisL2              18      20  None
1  hki-core-01  default  172.20.20.2/32  sth-core-01    10.0.0.4   isisL2              18      10  None
2  hki-core-01  default     10.0.0.0/31  sth-core-01    10.0.0.4   isisL2              18      20  None
3  hki-core-01  default  172.20.20.1/32  ams-core-01    10.0.0.6   isisL2              18      30  None
4  hki-core-01  default     10.0.0.2/31  ams-core-01    10.0.0.6   isisL2              18      20  None
5  hki-core-01  default  172.20.20.1/32  sth-core-01    10.0.0.4   isisL2              18      30  None
```
В cli:
```
showroute@HKI-CORE-01# run show route table inet.0 protocol isis

inet.0: 18 destinations, 18 routes (18 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

10.0.0.0/31        *[IS-IS/18] 00:51:25, metric 20
                    > to 10.0.0.4 via ge-0/0/0.0
10.0.0.2/31        *[IS-IS/18] 00:51:45, metric 20
                    > to 10.0.0.6 via ge-0/0/1.0
172.20.20.1/32     *[IS-IS/18] 00:51:25, metric 30
                      to 10.0.0.4 via ge-0/0/0.0
                    > to 10.0.0.6 via ge-0/0/1.0
172.20.20.2/32     *[IS-IS/18] 00:51:25, metric 10
                    > to 10.0.0.4 via ge-0/0/0.0
172.20.20.3/32     *[IS-IS/18] 00:51:45, metric 20
                    > to 10.0.0.6 via ge-0/0/1.0
```
Отлично! Полагаю, Вам стало яснее, что есть Batfish.

В начале статьи я писал, что BF можно использовать для проверки конфигурационных изменений перед внесением в prod. Теперь я предлагаю рассмотреть процесс проведения тестирования сети на базе **RobotFramework**. Для этого я написал небольшой модуль на основе PyBatfish, позволяющий выполнять следующие проверки:
* Определять статус BGP пиров в сети
* Определять состояние IS-IS соседей
* Проверять наличие E2E связности между узлами в сети с демонстрацией трассировки
* Определять размер RIB на определенном роутере для определенного протокола динамической маршрутизации

[LibraryBatfish.py](https://github.com/showroute/batfish-habr/blob/master/tests/LibraryBatfish.py)

[batfish-test.robot](https://github.com/showroute/batfish-habr/blob/master/tests/batfish-test.robot)

## Case N1

![alt text](https://github.com/showroute/batfish-habr/blob/master/images/topology1.png)

Под моим управление находится все та же сеть. Допустим, мне требуется привести в порядок фильтры на границе **AS 41214** и **AS 10631** и заблокировать на стыке пакеты, содержащие в source или destination ip адреса из диапазона BOGONS.

Запускаем тест до внесения изменений.

![alt text](https://github.com/showroute/batfish-habr/blob/master/images/test1.png)

Тесты пройдены. 

Внесем изменения в тестовую конфигурацию роутера **HKI-CORE-01** - /tmp/habr/configs/HKI-CORE-01.cfg :
```
set firewall family inet filter BOGONS term TERM010 from address 0.0.0.0/8
set firewall family inet filter BOGONS term TERM010 from address 10.0.0.0/8
set firewall family inet filter BOGONS term TERM010 from address 100.64.0.0/10
set firewall family inet filter BOGONS term TERM010 from address 127.0.0.0/8
set firewall family inet filter BOGONS term TERM010 from address 169.254.0.0/16
set firewall family inet filter BOGONS term TERM010 from address 172.16.0.0/12
set firewall family inet filter BOGONS term TERM010 from address 192.0.2.0/24
set firewall family inet filter BOGONS term TERM010 from address 192.88.99.0/24
set firewall family inet filter BOGONS term TERM010 from address 192.168.0.0/16
set firewall family inet filter BOGONS term TERM010 from address 198.18.0.0/15
set firewall family inet filter BOGONS term TERM010 from address 198.51.100.0/24
set firewall family inet filter BOGONS term TERM010 from address 203.0.113.0/24
set firewall family inet filter BOGONS term TERM010 from address 224.0.0.0/4
set firewall family inet filter BOGONS term TERM010 from address 240.0.0.0/4
set firewall family inet filter BOGONS term TERM010 then discard
set firewall family inet filter BOGONS term PERMIT-IP-ANY-ANY then accept 
set interfaces ge-0/0/2.0 family inet filter input BOGONS 
set interfaces ge-0/0/2.0 family inet filter output BOGONS  
```
Запускаем тест.

![alt text](https://github.com/showroute/batfish-habr/blob/master/images/test2.png)

Oops. Я был очень близок, но как показывает вывод теста, после внесенных изменений BGP соседство 192.168.30.0 – 192.168.30.1 находится не в состоянии Established -> как следствие, теряется IP связность между точками 135.65.0.1 <-> 140.0.0.1. Что же не так? Смотрим внимательно в конфигурацию **HKI-CORE-01** и видим, что eBGP пиринг установлен на приватных адресах: 
```
showroute@HKI-CORE-01# show interfaces ge-0/0/2 | display set             
set interfaces ge-0/0/2 description SPB-CORE-01
set interfaces ge-0/0/2 unit 0 family inet filter input BOGONS
set interfaces ge-0/0/2 unit 0 family inet filter output BOGONS
set interfaces ge-0/0/2 unit 0 family inet address 192.168.30.0/31
```
Вывод: необходимо поменять адреса на стыке или добавить в исключение подсеть 192.168.30.0/31.

Добавлю сеть на стыке в исключение, вноь обновлю /tmp/habr/configs/HKI-CORE-01.cfg:
```
set firewall family inet filter BOGONS term TERM005 from address 192.168.0.0/31 
set firewall family inet filter BOGONS term TERM005 then accept               
```
Запускаем тест.

![alt text](https://github.com/showroute/batfish-habr/blob/master/images/test3.png)

Теперь нежелательный трафик не пройдет через ebgp стык  AS 41214 – AS10631. Можно смело вносить изменения на prod, не опасаясь последствий.

## Case N2

![alt text](https://github.com/showroute/batfish-habr/blob/master/images/topology2.png)

Здесь мне необходимо затерминировать сеть 150.0.0.0/24 на роутере **MSK-CORE-01** и обеспечить связность между точками 135.65.0.1 и 150.0.0.1

Добавляю следующие строки в тестовую конфигурацию маршрутизатора MSK-CORE-01 - tmp/habr/configs/MSK-CORE-01.cfg:
```
interface Loopback2
 ip address 150.0.0.1 255.255.255.255
!
ip route 150.0.0.0 255.255.255.0 Null0
!
router bgp 10631
 !
 address-family ipv4
  network 150.0.0.0 mask 255.255.255.0
!
```

Изменяю тестовый сценарий и запускаю проверку:
```
git diff HEAD~
diff --git a/batfish-robot.robot b/batfish-robot.robot
index 8d963c5..ce8cb6a 100644
--- a/batfish-robot.robot
+++ b/batfish-robot.robot
@@ -5,7 +5,7 @@ Library  LibraryBatfish.py  tmp/habr
 ${ISIS-ENABLED-LINK-DESCRIPTION}  ISIS-LINK
 ${NODE}  HKI-CORE-01
 ${PROTOCOL}  ebgp
-${RIB-SIZE}  1
+${RIB-SIZE}  2
 
 *** Test Cases ***
 ISIS
@@ -27,3 +27,8 @@ Ping
     [Documentation]  Test end-to-end ICMP connectivity & show traceroute
     ${result}=  Ping  135.65.0.1  140.0.0.1
     Should Be Equal As Integers  ${result}  1
+
+Ping2
+    [Documentation]  Test end-to-end ICMP connectivity & show traceroute
+    ${result}=  Ping  135.65.0.1  150.0.0.1
+    Should Be Equal As Integers  ${result}  1
```
*теперь я ожидаю увидеть два eBGP маршрута на роутере HKI-CORE-01, так же добавлена дополнительная проверка связности*

![alt text](https://github.com/showroute/batfish-habr/blob/master/images/test4.png)

Связности между 135.65.0.1 и 150.0.0.1 нет, к тому же на маршрутизаторе **HKI-CORE-01** всего один eBGP маршрут, вместо двух. 

Проверяем содержание RIB на **HKI-CORE-01** при добавлении новой конфигурации на роутер **MSK-CORE-01**:
```
showroute@HKI-CORE-01# run show route table inet.0 protocol bgp

inet.0: 20 destinations, 20 routes (19 active, 0 holddown, 1 hidden)
+ = Active Route, - = Last Active, * = Both

135.65.0.0/19      *[BGP/170] 02:25:38, MED 0, localpref 100, from 172.20.20.1
                      AS path: I, validation-state: unverified
                    > to 10.0.0.4 via ge-0/0/0.0
                      to 10.0.0.6 via ge-0/0/1.0
140.0.0.0/24       *[BGP/170] 01:38:02, localpref 100
                      AS path: 10631 I, validation-state: unverified
                    > to 192.168.30.1 via ge-0/0/2.0

showroute@HKI-CORE-01# run show route table inet.0 protocol bgp hidden detail

inet.0: 20 destinations, 20 routes (19 active, 0 holddown, 1 hidden)
150.0.0.0/24 (1 entry, 0 announced)
         BGP                 /-101
                Next hop type: Router, Next hop index: 563
                Address: 0x940f43c
                Next-hop reference count: 4
                Source: 192.168.30.1
                Next hop: 192.168.30.1 via ge-0/0/2.0, selected
                Session Id: 0x9
                State: <Hidden Ext>
                Local AS: 41214 Peer AS: 10631
                Age: 1:42:03
                Validation State: unverified
                Task: BGP_10631.192.168.30.1+179
                AS path: 10631 I
                Localpref: 100
                Router ID: 10.68.1.1
                Hidden reason: rejected by import policy
```
Обратите внимание на политику импорта префиксов, полученных от **SPB-CORE-01**:
```
set protocols bgp group AS10631 import FROM-AS10631
set protocols bgp group AS10631 neighbor 192.168.30.1 description SPB-CORE-01
set protocols bgp group AS10631 neighbor 192.168.30.1 peer-as 10631
set policy-options policy-statement FROM-AS10631 term TERM010 from route-filter 140.0.0.0/24 exact
set policy-options policy-statement FROM-AS10631 term TERM010 then accept
set policy-options policy-statement FROM-AS10631 term DENY then reject
```
Не хватает правила, разрешающего 150.0.0.0/24. Добавляем его в тестовую конфигурацию и запускаем проверку:
```
showroute@HKI-CORE-01# show | compare
[edit policy-options policy-statement FROM-AS10631 term TERM010 from]
       route-filter 140.0.0.0/24 exact { ... }
+      route-filter 150.0.0.0/24 exact;

[edit]
```

![alt text](https://github.com/showroute/batfish-habr/blob/master/images/test5.png)

Отлично, связность между сетями есть, все тесты пройдены! Можно вносить изменения на prod.

## Сonclusion
На мой взгляд, Batfish - это мощнейщий инструмент с огромным потенциалом. Но, к сожалению, его функционал пока еще далек от совершенства - отсутствует поддержка MPLS, Layer2 technologies etc. 

Если данная тема Вам интересна - присоединяйтесь в slack чат, разработчики Batfish с удовольсвтием отвечают на любые вопросы и быстро правят баги.

https://batfish-org.slack.com

Благодарю за внимание.

## Useful links

https://www.batfish.org/

https://www.intentionet.com/

https://www.youtube.com/channel/UCA-OUW_3IOt9U_s60KvmJYA

https://github.com/batfish/batfish

https://media.readthedocs.org/pdf/pybatfish/latest/pybatfish.pdf
