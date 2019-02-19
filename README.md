# batfish-habr
## Introduction

Одной из проблем современных сетей является их сложность. Обилие правил фильтрации, политик обмена маршрутной информации, протоколов динамического роутинга делают сети запутанными и хрупкими. Авария на сети можно невольно случиться при внесении ошибочных изменений в ACL или route-map. Нам определено не хватает pre-deployment инструмента, позволяющего оценить поведение сети с новой конфигурацией перед внесением изменений в prod. Хочется точно знать – Будет ли мне доступна сеть A, если я отфильтрую часть анонсов от провайдера B? Каким маршрутом пойдут пакеты из сети C к серверу D, если на одном из транзитных линков я увеличу IGP метрику в два раза? Встречайте Batfish!

## Batfish ovweview

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
