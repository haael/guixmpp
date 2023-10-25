#!/usr/bin/python3


import logging

#logging.basicConfig(level=logging.DEBUG)

import asyncio
import aioxmpp
import aioxmpp.ibr
import aioxmpp.errors


jid = aioxmpp.JID.fromstr('haael@dw.live')
password = 'deepweb.net:12345'


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
			
			
			async for level, sjid, snode, info in service_discovery(disco, aioxmpp.JID.fromstr('dw.live'), None):
				print(" " * level, sjid, snode, info.identities)
			
			#await asyncio.sleep(0.5)
			#client.stop()
	except aioxmpp.errors.MultiOSError as error:
		print([repr(_e) for _e in error.exceptions])


async def service_discovery(disco, jid, node, level=0):
	try:
		info = await disco.query_info(jid, node=node)
	except aioxmpp.errors.XMPPCancelError:
		#print("no info:", jid, node)
		return
	else:
		yield level, jid, node, info
		
		if 'http://jabber.org/protocol/commands' in info.features:
			async for subnode in service_discovery(disco, jid, 'http://jabber.org/protocol/commands', level + 1):
				yield subnode
	
	if (node is not None) or ('http://jabber.org/protocol/disco#items' in info.features):
		try:
			items = await disco.query_items(jid, node=node)
		except aioxmpp.errors.XMPPCancelError:
			#print("no items:", jid, node)
			return
		
		for item in items.items:
			if (node is None) and str(item.jid).endswith(str(jid)):
				async for subnode in service_discovery(disco, item.jid, item.node, level + 1):
					yield subnode
			else:
				try:
					info = await disco.query_info(item.jid, node=item.node)
				except aioxmpp.errors.XMPPWaitError:
					pass
				else:
					yield level + 1, item.jid, item.node, info


if __name__ == '__main__':
	asyncio.run(main())

