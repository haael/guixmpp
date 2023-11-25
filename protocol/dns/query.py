#!/usr/bin/python3

"Module used for creating DNS queries."

from struct import pack

# Opcodes
QUERY = 0
IQUERY = 1
STATUS = 2


def create_header(opcode, x_id):
    """ Function used to create a DNS query header.
    
    Args:
        opcode = opcode of the query. It can take the following values:
            QUERY = 0, IQUERY = 1, STATUS = 2

    Returns:
        The header

    """

    header = []
    flags = 0

    # Message ID
    header.append(pack(">H", x_id))

    # Flags (QR, opcode, AA, TC, RD, RA, Z, RCODE)
    if opcode == QUERY:
        # Standard DNS query
        flags = 0b0000000100000000
    elif opcode == IQUERY:
        flags = 0b0000100100000000
    elif opcode == STATUS:
        flags = 0b0001000100000000
    else:
        raise ValueError

    header.append(pack(">H", flags))

    # QDCOUNT
    header.append(pack(">H", 1))
    # ANCOUNT
    header.append(pack(">H", 0))
    # NSCOUNT
    header.append(pack(">H", 0))
    # ARCOUNT
    header.append(pack(">H", 0))

    return bytes().join(header)


def create_dns_query(domain_name, query_type, x_id):
    """ Function used to create a DNS query question section.
    
    Args:
        domain_name = the domain name that needs to be resolved
        query_type = the query type of the DNS message

    Returns:
        The DNS query question section.

    """

    # QNAME
    qname = dns_encode(domain_name)

    code = 0
    # QTYPE - query for A record
    if query_type == "A":
        # host address
        code = 1
    elif query_type == "NS":
        # authoritative name server
        code = 2
    elif query_type == "CNAME":
        # the canonical name for an alias
        code = 5
    elif query_type == "SOA":
        # start of a zone of authority
        code = 6
    elif query_type == "MX":
        # mail exchange
        code = 15
    elif query_type == "TXT":
        # text strings
        code = 16
        raise NotImplementedError
    elif query_type == "PTR":
        # domain name pointer
        code = 12
        raise NotImplementedError
    elif query_type == "AAAA":
        # AAAA record
        code = 28
    else:
        raise ValueError("Invalid query.")

    qtype = pack(">H", code)

    # QCLASS - internet
    qclass = pack(">H", 1)

    # whole question section
    question = bytes().join([create_header(QUERY, x_id), qname, qtype, qclass])

    return question


def dns_encode(domain_name):
    """ Function used to transfrom URL from normal form to DNS form.

    Args:
        domain_name = URL that needs to be converted

    Returns:
        The URL in DNS form

    Example:
        www.example.com to 3www7example3com0

    """

    if hasattr(domain_name, 'decode'):
        domain_name = domain_name.decode('ascii')

    qname = []

    split_name = domain_name.split('.')
    for atom in split_name:
        qname.append(pack(">B", len(atom)))
        qname.append(atom.encode('ascii'))
    qname.append(b'\x00')

    return bytes().join(qname)


if __debug__ and __name__ == '__main__':
    print([hex(_x) for _x in create_dns_query('www.github.com', 'AAAA', 0x1234)])
    print([hex(_x) for _x in create_dns_query('www.example.com', 'A', 0x1234)])
    print([hex(_x) for _x in create_dns_query('hotmail.com', 'MX', 0x1234)])





