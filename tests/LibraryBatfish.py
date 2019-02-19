from pybatfish.client.commands import bf_logger, bf_init_snapshot
from pybatfish.question.question import load_questions, list_questions
from pybatfish.question import bfq
from pybatfish.datamodel.flow import TcpFlags, MatchTcpFlags
from pybatfish.datamodel.flow import HeaderConstraints, PathConstraints
from robot.api import logger
import logging

class LibraryBatfish(object):
    def __init__(self, snapshot):
        bf_logger.setLevel(logging.ERROR)
        load_questions()
        bf_init_snapshot(snapshot)

    def check_bgp_peers(self):
        not_established_peers = list()
        bgp_peers = bfq.bgpSessionStatus().answer()
        for peer in bgp_peers.rows:
            if peer.get('Established_Status') != 'ESTABLISHED':
                not_established_peers.append(dict.fromkeys(peer.get('Local_IP').split(), peer.get('Remote_IP').get('value')))

        if len(not_established_peers) == 0:
            return 1
        else:
            logger.warn('BGP neighbors are not in an established state:')
            for neighborship in not_established_peers:
                for peer in neighborship:
                    logger.warn('{} - {}'.format(peer, neighborship.get(peer)))
            return 0

    def check_routes(self, node, protocol):
        routes = bfq.routes(nodes=node, protocols=protocol).answer()
        return len(routes.rows)

    def check_isis_neighbors(self, description):
        not_isis_enabled_links = list()
        for link in self._get_isis_enabled_links(description):
            if link not in self._get_isis_neighbors():
                not_isis_enabled_links.append(link)

        if len(not_isis_enabled_links) == 0:
            return 1
        else:
            for link in not_isis_enabled_links:
                logger.warn('{} {} has no IS-IS neighbor'.format(link.get('hostname'), link.get('interface')))
            return 0

    def ping(self, source_ip, destination_ip):
        ip_owners = bfq.ipOwners().answer()
        traceroute = self._get_traceroute_status(source_ip, destination_ip, ip_owners)
        reverse_traceroute = self._get_traceroute_status(destination_ip, source_ip, ip_owners)

        if  traceroute == True and reverse_traceroute == True:
            self._show_trace(source_ip, destination_ip, ip_owners)
            return 1
        else:
            logger.warn('Ping {} -> {} failed'.format(source_ip, destination_ip))
            return 0

    def _get_traceroute_status(self, source_ip, destination_ip, addresses):
        tracert = self._unidirectional_virtual_traceroute(source_ip, destination_ip, addresses)
        if tracert != None and tracert.rows[0].get('Traces')[0].get('disposition') == 'ACCEPTED':
            return True
        else:
            return False

    def _get_paths(self, source_ip, destination_ip, addresses):
        tracert = self._unidirectional_virtual_traceroute(source_ip, destination_ip, addresses)
        traces = tracert.rows[0].get('Traces')
        paths = dict()
        path_number = 1
        for trace in traces:
            if trace.get('disposition') == 'ACCEPTED':
                path = list()
                for hop in trace.get('hops'):
                    path.append(hop.get('node').get('name'))
                paths[path_number] = path
                path_number += 1

        return paths

    def _unidirectional_virtual_traceroute(self, source_ip, destination_ip, addresses):
        for address in addresses.rows:
            if address.get('IP') == source_ip:
                node = address.get('Node').get('name')
                int = address.get('Interface')

        headers = HeaderConstraints(srcIps=source_ip, dstIps=destination_ip, ipProtocols=['ICMP'])
        try:
            tracert = bfq.traceroute(startLocation="{}[{}]".format(node,int), headers=headers).answer()
            return tracert
        except:
            logger.warn('{} address has not been found'.format(source_ip))

    def _get_isis_enabled_links(self, description='core-link'):
        isis_enabled_links = list()
        interfaces = bfq.interfaceProperties().answer()
        for int in interfaces.rows:
            if int.get('Description') != None and description in int.get('Description'):
                isis_enabled_links.append({'hostname' : int.get('Interface').get('hostname'),
                                           'interface' : int.get('Interface').get('interface')})

        return isis_enabled_links

    def _get_isis_neighbors(self):
        isis_neighbors = list()
        isis_adjacencies = bfq.edges(edgeType='isis').answer()
        for neighbor in isis_adjacencies.rows:
            isis_neighbors.append(neighbor.get('Interface'))

        return isis_neighbors

    def _show_trace(self, source_ip, destination_ip, addresses):
        logger.console('\nTraceroute to {} from {}'.format(destination_ip, source_ip))
        paths = self._get_paths(source_ip, destination_ip, addresses)
        path_num = 1
        for path in paths:
            n = 1
            logger.console('\n  Path N{}'.format(path_num))
            for hop in paths.get(path):
                logger.console('  {} {}'.format(n, hop))
                n += 1
            path_num += 1
