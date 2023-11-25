#!/usr/bin/python3


"Module used for interpreting answers to queries."

from struct import unpack_from
from collections import namedtuple

### Tuples for message parts
Header = namedtuple("Header", [
    'x_id',
    'qr',
    'opcode',
    'aa',
    'tc',
    'rd',
    'ra',
    'rcode',
    'qdcount',
    'ancount',
    'nscount',
    'arcount',
    ])

Question = namedtuple("Question", [
    'qname',
    'qtype',
    'qclass',
    ])

Answer = namedtuple("Answer", [
    'name',
    'x_type',
    'x_class',
    'ttl',
    'rdlength',
    'rdata',
    ])

Reply = namedtuple("Reply", [
    'header',
    'question',
    'answer',
    ])


def get_serial(msg):
    return unpack_from(">H", msg, 0)[0]


def parse_dns_reply(msg):
    """ Function used to parse the DNS reply message.
        
    Args:
        msg: The message recieved from the DNS server

    Returns:
        The DNS reply message as a Reply namedtuple in the following
        form: (Header, Question, [Answer]).

    """

    offset = 0
    header, l = extract_header(msg, offset)
    offset += l
    question, l = extract_question(msg, offset)
    offset += l

    answer = []
    for _ in range(header.ancount):
        a, l = extract_answer(msg, offset)
        answer.append(a)
        offset += l

    for _ in range(header.nscount):
        a, l = extract_answer(msg, offset)
        answer.append(a)
        offset += l

    for _ in range(header.arcount):
        a, l = extract_answer(msg, offset)
        answer.append(a)
        offset += l

    return Reply(header, question, answer), offset


def extract_header(msg, offset):
    """ Function used to extract the header from the DNS reply message.
        
    Args:
        msg: The message recieved from the DNS server

    Returns:
        The header of the reply as a Header namedtuple in the following
        form: Header(x_id, qr, opcode, aa, tc, rd, ra, rcode, qdcount, 
        ancount, nscount, arcount)

    """

    raw_header = unpack_from(">HHHHHH", msg, offset)

    x_id = raw_header[0]
    flags = raw_header[1]

    qr = flags >> 15
    opcode = (flags & 0x7800) >> 11
    aa = (flags & 0x0400) >> 10
    tc = (flags & 0x0200) >> 9
    rd = (flags & 0x0100) >> 8
    ra = (flags & 0x0080) >> 7
    rcode = (flags & 0x000f)

    qdcount = raw_header[2]
    ancount = raw_header[3]
    nscount = raw_header[4]
    arcount = raw_header[5]

    return Header(x_id, qr, opcode, aa, tc, rd, ra, rcode, qdcount, ancount, nscount, arcount), 12


def extract_question(msg, offset):
    """ Function used to extract the question section from a DNS reply.
        
    Args:
        msg: The message recieved from the DNS server
        qname_len: The length of the name beign querried

    Returns:
        The question section of the reply as a Question namedtuple in the 
        following form: Question(qname, qtype, qclass)

    """

    # qname
    raw_qname = []
    byte = None
    while byte != 0:
        byte = unpack_from(">B", msg, offset)[0]
        raw_qname.append(byte)
        offset += 1

    qname = dns_decode(bytes(raw_qname))
    qtype = unpack_from(">H", msg, offset)[0]
    qclass = unpack_from(">H", msg, offset + 2)[0]

    return Question(qname, qtype, qclass), len(raw_qname) + 2 + 2


def extract_answer(msg, offset):
    """ Function used to extract a RR from a DNS reply.
        
    Args:
        msg: The message recieved from the DNS server
        offset: The number of bytes from the start of the message until the end
            of the question section (or until the end of the last RR)

    Returns:
        The resource record section of the reply that begins at the given offset
        and the offset from the start of the message to where the returned RR
        ends in the following form: (Answer(name, x_type, x_class, ttl, rdlength, 
        rdata), offset)

    If the DNS Response is not implemented or recognized, an error message is
    shown and the program will exit.

    """

    name, bytes_read = extract_name(msg, offset)
    offset += bytes_read

    aux = unpack_from(">HHIH", msg, offset)
    offset += 10

    x_type = aux[0]
    x_class = aux[1]
    ttl = aux[2]
    rdlength = aux[3]

    rdata = ''
    if x_type == 1:
        # A type
        a_type = 'A'
        rdata = extract_a_rdata(msg, offset, rdlength)
    elif x_type == 2:
        # NS type
        a_type = 'NS'
        rdata = extract_ns_rdata(msg, offset, rdlength)
    elif x_type == 5:
        # CNAME type
        a_type = 'CNAME'
        rdata = extract_cname_rdata(msg, offset, rdlength)
    elif x_type == 6:
        # SOA type
        a_type = 'SOA'
        rdata = extract_soa_rdata(msg, offset, rdlength)
    elif x_type == 15:
        # MX type
        a_type = 'MX'
        rdata = extract_mx_rdata(msg, offset, rdlength)
    elif x_type == 28:
        # AAAA type
        a_type = 'AAAA'
        rdata = extract_aaaa_rdata(msg, offset, rdlength)
    else:
        raise ValueError(f"DNS Response not recognized (x_type={x_type}).")

    return Answer(name, a_type, x_class, ttl, rdlength, rdata), bytes_read + 10 + rdlength


def extract_a_rdata(msg, offset, rdlength):
    """ Function used to extract the RDATA from an A type message.
        
    Args:
        msg: The message recieved from the DNS server
        offset: The number of bytes from the start of the message until the end
            of the question section (or until the end of the last RR)
        rdlength: The length of the RDATA section

    Returns:
        The RDATA field of the answer section as a string (an IPv4 address).

    """

    fmt_str = ">" + "B" * rdlength
    rdata = unpack_from(fmt_str, msg, offset)
    return '.'.join(str(_x) for _x in rdata)


def extract_aaaa_rdata(msg, offset, rdlength):
    """ Function used to extract the RDATA from an AAAA type message.
        
    Args:
        msg: The message recieved from the DNS server
        offset: The number of bytes from the start of the message until the end
            of the question section (or until the end of the last RR)
        rdlength: The length of the RDATA section

    Returns:
        The RDATA field of the answer section (an IPv6 address as a string)

    """

    fmt_str = ">" + "H" * (rdlength // 2)
    rdata = unpack_from(fmt_str, msg, offset)

    c = []
    for b in rdata:
        c.append(hex(b)[2:])

    return ':'.join(c)


def extract_ns_rdata(msg, offset, rdlength):
    """ Function used to extract the RDATA from a NS type message.
        
    Args:
        msg: The message recieved from the DNS server
        offset: The number of bytes from the start of the message until the end
            of the question section (or until the end of the last RR)
        rdlength: The length of the RDATA section

    Returns:
        The RDATA field of the answer section as a string and the offset from
        the start of the message until the end of the rdata field as a tuple:
        (rdata, field)

    """

    name, bytes_read = extract_name(msg, offset)
    return name


def extract_cname_rdata(msg, offset, rdlength):
    """ Function used to extract the RDATA from a CNAME type message.
        
    Args:
        msg: The message recieved from the DNS server
        offset: The number of bytes from the start of the message until the end
            of the question section (or until the end of the last RR)
        rdlength: The length of the RDATA section

    Returns:
        The RDATA field of the answer section as a string and the offset from
        the start of the message until the end of the rdata field as a tuple:
        (rdata, field)

    """

    name, bytes_read = extract_name(msg, offset)
    return name


def extract_soa_rdata(msg, offset, rdlength):
    """ Function used to extract the RDATA from a SOA type message.
        
    Args:
        msg: The message recieved from the DNS server
        offset: The number of bytes from the start of the message until the end
            of the question section (or until the end of the last RR)
        rdlength: The length of the RDATA section

    Returns:
        The RDATA field of the answer section as a tuple of the following form:
        (pns, amb, serial, refesh, retry, expiration, ttl)    

    """

    # extract primary NS
    (pns, bytes_read) = extract_name(msg, offset)
    offset += bytes_read
    # extract admin MB
    (amb, bytes_read) = extract_name(msg, offset)
    offset += bytes_read

    aux = unpack_from(">IIIII", msg, offset)

    serial = aux[0]
    refesh = aux[1]
    retry = aux[2]
    expiration = aux[3]
    ttl = aux[4]

    return (pns, amb, serial, refesh, retry, expiration, ttl)    


def extract_mx_rdata(msg, offset, rdlength):
    """ Function used to extract the RDATA from a MX type message.
        
    Args:
        msg: The message recieved from the DNS server
        offset: The number of bytes from the start of the message until the end
            of the question section (or until the end of the last RR)
        rdlength: The length of the RDATA section

    Returns:
        The RDATA field of the answer section as a tuple of the following form:
        (preference, mail_ex)

    """

    preference = unpack_from(">H", msg, offset)[0]
    offset += 2
    
    mail_ex, l = extract_name(msg, offset)
    return preference, mail_ex


def extract_name(msg, offset):
    """ Function used to extract the name field from the answer section.

    Args:
        msg: The message recieved from the DNS server
        offset: The number of bytes from the start of the message until the end
            of the question section (or until the end of the last RR)
        
    Returns: 
        Tuple containing the name and number of bytes read.

    """

    raw_name = []
    bytes_read = 1
    jump = False

    while True:
        byte = unpack_from(">B", msg, offset)[0]
        if byte == 0:
            offset += 1
            break

        # If the field has the first two bits equal to 1, it's a pointer
        if byte >= 192:
            next_byte = unpack_from(">B", msg, offset + 1)[0]
            # Compute the pointer
            offset = ((byte << 8) + next_byte - 0xc000) - 1
            jump = True
        else:
            raw_name.append(byte)

        offset += 1

        if jump == False:
            bytes_read += 1

    raw_name.append(0)
    if jump == True:
        bytes_read += 1

    name = dns_decode(bytes(raw_name))

    return name, bytes_read


def dns_decode(raw_name):
    """ Function used to convert an url from dns form to normal form.

    Args:
        The dns form of the url

    Returns:
        The normal form of the url

    Example: 
        3www7example3com0 to www.example.com

    """

    name = []
    pos = 0
    while pos < len(raw_name):
        l = raw_name[pos]
        if l == 0: break
        name.append(raw_name[pos + 1 : pos + 1 + l].decode('ascii'))
        pos += l + 1

    return ".".join(name)


if __debug__ and __name__ == '__main__':
    response = b'`V\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00\x03www\x07example\x03com\x00\x00\x01\x00\x01\xc0\x0c\x00\x01\x00\x01\x00\x00R\x9b\x00\x04]\xb8\xd8"'
    print(parse_dns_reply(response))

    response = bytes.fromhex('''
00 00 81 80 00 01 00 01  00 00 00 00 03 77 77 77
07 65 78 61 6d 70 6c 65  03 63 6f 6d 00 00 01 00
01 03 77 77 77 07 65 78  61 6d 70 6c 65 03 63 6f
6d 00 00 01 00 01 00 00  00 80 00 04 C0 00 02 01
    ''')
    print(parse_dns_reply(response))

    response = bytes.fromhex('''
0000 8580 0001 0001 0001 0002 0377 7777
0765 7861 6d70 6c65 0363 6f6d 0000 0100
01c0 0c00 0100 0100 093a 8000 0401 0203
04c0 1000 0200 0100 093a 8000 0b09 6c6f
6361 6c68 6f73 7400 c03d 0001 0001 0009
3a80 0004 7f00 0001 c03d 001c 0001 0009
3a80 0010 0000 0000 0000 0000 0000 0000
0000 0001                
    ''')
    print(parse_dns_reply(response))

    response = bytes.fromhex('''
24 1a 81 80 00 01
00 03 00 00 00 00 03 77  77 77 06 67 6f 6f 67 6c
65 03 63 6f 6d 00 00 01  00 01 c0 0c 00 05 00 01
00 05 28 39 00 12 03 77  77 77 01 6c 06 67 6f 6f
67 6c 65 03 63 6f 6d 00  c0 2c 00 01 00 01 00 00
00 e3 00 04 42 f9 59 63  c0 2c 00 01 00 01 00 00
00 e3 00 04 42 f9 59 68                         
    ''')
    print(parse_dns_reply(response))

