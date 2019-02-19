# batfish-habr
## Introduction

Одной из проблем современных сетей является их сложность. Обилие правил фильтрации, политик обмена маршрутной информации, протоколов динамического роутинга делают сети запутанными и хрупкими. Авария на сети можно невольно случиться при внесении ошибочных изменений в ACL или route-map. Нам определено не хватает pre-deployment инструмента, позволяющего оценить поведение сети с новой конфигурацией перед внесением изменений в prod. Хочется точно знать – Будет ли мне доступна сеть A, если я отфильтрую часть анонсов от провайдера B? Каким маршрутом пойдут пакеты из сети C к серверу D, если на одном из транзитных линков я увеличу IGP метрику в два раза? Встречайте Batfish!

## Batfish overview

Batfish – это инструмент для моделирования сети. Основным его назначением является тестирование
конфигурационных изменений перед внесением в production environment. Batfish так же можно использовать для анализа и проверки текущего состояния сети. Существующим CI/CD pipelines в сетевом мире явно не хватает инструмента для тестирования новых конфигураций. Batfish позволяет решить это проблему.

Batfish не требуется доступ на сетевое оборудование. Batfish моделирует поведение сети на основе конфигурационных файлов сетевых устройств. Для совершенствования сетевого анализа можно использовать дополнительную информацию - например, BGP анонсы, полученные от внешних источников.

Что Batfish может рассказать о сети:
* статус соседства протоколов динамической маршрутизации (BGP, IS-IS, OSPF)
* RIB каждого сетевого элемента
* настроенные параметры NTP, AAA, logging, MTU, etc
* позволяет определить, блокирует ли ACL прохождение сетевого трафика (aka packet-tracer на Cisco ASA)
* может проверить наличие end-to-end связности между хостами внутри сети
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

Batfish – это Java приложение, для удобного взаимодействия с ним был написан Pybatfish - python SDK.
Перейдем к практике. Я продемонстрирую возможности Batfish на примере.

## Example

Под нашим управлением находится две автономные системы, в качестве IGP в AS 41214 используется IS-IS, в AS 10631 – OSPF, внутри каждой AS используется IBGP-fullmesh. R1 анонсирует своим соседям via BGP префикс 135.65.0.0/19, R7 – 140.0.0.0/24. Обмен маршрутной информацией между автономными системами происходит на стыке HKI-CORE-01 --- SPB-CORE-01.

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

Давайте определим статус BGP сессий на роутере LDN-CORE-01:
```
>>> bgp_peers = bfq.bgpSessionStatus(nodes='LDN-CORE-01').answer().frame()
>>> bgp_peers
          Node      VRF  Local_AS        Local_Interface     Local_IP  Remote_AS  Remote_Node    Remote_IP Session_Type Established_Status
0  ldn-core-01  default     41214  ldn-core-01:Loopback0  172.20.20.1      41214  sth-core-01  172.20.20.2         IBGP        ESTABLISHED
1  ldn-core-01  default     41214  ldn-core-01:Loopback0  172.20.20.1      41214  ams-core-01  172.20.20.3         IBGP        ESTABLISHED
2  ldn-core-01  default     41214  ldn-core-01:Loopback0  172.20.20.1      41214  hki-core-01  172.20.20.4         IBGP        ESTABLISHED
```
Похоже на правду?
```
LDN-CORE-01#show ip bgp summary
…
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
172.20.20.2     4        41214     629     669        9    0    0 00:56:51        0
172.20.20.3     4        41214     826     827        9    0    0 01:10:18        0
172.20.20.4     4        41214     547     583        9    0    0 00:49:24        1…..
```
Awesome!

Давайте посмотрим, какие IS-IS маршруты есть в RIB на маршрутизаторе HKI-CORE-01 по мнению Batfish
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
В консоли:
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
Nice! Полагаю, теперь Вам стало яснее, что есть Batfish.

В начале статьи я писал, что BF можно использовать для проверки конфигурационных изменений перед внесением в prod. Далее я рассмотрю процесс проведения тестирования сети на базе **RobotFramework**, для этого я написал небольшой модуль на основе PyBatfish, позволяющий проводить следующие проверки:
* Определять статус BGP пиров в сети
* Определять состояние IS-IS соседей
* Проверять наличие E2E связности между узлами в сети с демонстрацией трассировки
* Определять размер RIB на определенном маршрутизаторе для определенного Routing protocol

Let’s treat the network like an application!

## Case N1

![alt text](https://github.com/showroute/batfish-habr/blob/master/images/topology1.png)

Под моим управление находится все та же сеть. Я решил привести в порядок фильтры на границе AS41214 и AS10631 и заблокировать на стыке пакеты, содержащие в source или destination ip адреса из диапазона BOGONS.

Запустим тест до внесения изменений.
![alt text](https://github.com/showroute/batfish-habr/blob/master/images/test1.png)

Тесты пройдены, внесем изменения в тестовую конфигурацию роутера **HKI-CORE-01** - /tmp/habr/configs/HKI-CORE-01.cfg :
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

Oops. Я был очень близок, но как, показывает вывод теста, после внесенных изменений BGP соседство 192.168.30.0 – 192.168.30.1 находится не в состоянии Established -> как следствие, теряется IP связность между точками 135.65.0.1 <-> 140.0.0.1. Что же не так? Смотрим внимательно в конфигурацию HKI-CORE-01 и видимо, что eBGP пиринг установлен на приватных адресах: 
```
showroute@HKI-CORE-01# show interfaces ge-0/0/2 | display set             
set interfaces ge-0/0/2 description SPB-CORE-01
set interfaces ge-0/0/2 unit 0 family inet filter input BOGONS
set interfaces ge-0/0/2 unit 0 family inet filter output BOGONS
set interfaces ge-0/0/2 unit 0 family inet address 192.168.30.0/31
```
Вывод: поменять адреса на стыке или добавить в исключение подсеть 192.168.30.0/31.

Добавлю сеть на стыке в исключение - снова обновлю /tmp/habr/configs/HKI-CORE-01.cfg:
```
set firewall family inet filter BOGONS term TERM005 from address 192.168.0.0/31 
set firewall family inet filter BOGONS term TERM005 then accept               
```
Запустим тест.

![alt text](https://github.com/showroute/batfish-habr/blob/master/images/test3.png)
