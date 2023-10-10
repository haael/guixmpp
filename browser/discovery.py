#!/usr/bin/python3


import logging

#logging.basicConfig(level=logging.DEBUG)

import asyncio
import aioxmpp
import aioxmpp.ibr
import aioxmpp.errors


jid = aioxmpp.JID.fromstr('nope')
password = 'xxxxxxxx'


async def register_account():
	metadata = aioxmpp.make_security_layer(None)
	_, stream, features = await aioxmpp.node.connect_xmlstream(aioxmpp.JID.fromstr('dw.live'), metadata)
	print(list(features))
	info = await aioxmpp.ibr.get_registration_fields(stream)
	if info:
		#print(info.instructions)
		for ns, field in aioxmpp.ibr.get_used_fields(info):
			print(field + ":", getattr(info, field))
	
	await asyncio.sleep(0.5)
	stream.close()


async def main():
	client = aioxmpp.PresenceManagedClient(jid, aioxmpp.make_security_layer(password))
	disco = aioxmpp.DiscoClient(client)
	try:
		async with client.connected() as stream:
			#info = await disco.query_info(aioxmpp.JID.fromstr('dw.live'))
			#info_dict = info.to_dict()
			#print(info_dict['identities'])
			#print(info_dict['features'])
			#print(info_dict['forms'])
			
			#async for level, sjid, info in service_discovery(disco, aioxmpp.JID.fromstr('muc.poez.io')):
			#	print(" " * level, sjid, [(_iden.category, _iden.name) for _iden in info.identities] if info else None)
			
			await asyncio.sleep(0.5)
			client.stop()
	except aioxmpp.errors.MultiOSError as error:
		print([repr(_e) for _e in error.exceptions])


async def service_discovery(disco, jid, level=0):
	info = await disco.query_info(jid)
	yield level, jid, info
	#features = frozenset(_feature for _feature in info.features)
	if 'http://jabber.org/protocol/disco#items' in info.features:
		items = await disco.query_items(jid)
		for item in items.items:
			if str(item.jid).endswith(str(jid)):
				async for subnode in service_discovery(disco, item.jid, level + 1):
					yield subnode
			else:
				try:
					info = await disco.query_info(item.jid)
				except aioxmpp.errors.XMPPWaitError:
					pass
				else:
					yield level + 1, item.jid, info


if __name__ == '__main__':
	asyncio.run(main())

