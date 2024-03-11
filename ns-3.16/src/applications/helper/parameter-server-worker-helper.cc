/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2008 INRIA
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation;
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 * Author: Mohamed Amine Ismail <amine.ismail@sophia.inria.fr>
 */
#include "parameter-server-worker-helper.h"
#include "ns3/udp-server.h"
#include "ns3/udp-client.h"
#include "ns3/udp-trace-client.h"
#include "ns3/uinteger.h"
#include "ns3/string.h"

namespace ns3 {

WorkerHelper::WorkerHelper ()
{
}

WorkerHelper::WorkerHelper (uint16_t port)
{
  m_factory.SetTypeId (Worker::GetTypeId ());
  SetAttribute ("Port", UintegerValue (port));
}

void
WorkerHelper::SetAttribute (std::string name, const AttributeValue &value)
{
  m_factory.Set (name, value);
}

ApplicationContainer
WorkerHelper::Install (NodeContainer c)
{
  ApplicationContainer apps;
  for (NodeContainer::Iterator i = c.Begin (); i != c.End (); ++i)
    {
      Ptr<Node> node = *i;

      m_server = m_factory.Create<Worker> ();
      node->AddApplication (m_server);
      apps.Add (m_server);

    }
  return apps;
}

Ptr<Worker>
WorkerHelper::GetServer (void)
{
  return m_server;
}

ParameterServerHelper::ParameterServerHelper ()
{
}

ParameterServerHelper::ParameterServerHelper (Address address, uint16_t port)
{
  m_factory.SetTypeId (ParameterServer::GetTypeId ());
  SetAttribute ("RemoteAddress", AddressValue (address));
  SetAttribute ("RemotePort", UintegerValue (port));
}

ParameterServerHelper::ParameterServerHelper (Ipv4Address address, uint16_t port)
{
  m_factory.SetTypeId (ParameterServer::GetTypeId ());
  SetAttribute ("RemoteAddress", AddressValue (Address(address)));
  SetAttribute ("RemotePort", UintegerValue (port));
}

ParameterServerHelper::ParameterServerHelper (Ipv4Address address, uint16_t port, uint16_t pg)
{
	m_factory.SetTypeId (ParameterServer::GetTypeId ());
	SetAttribute ("RemoteAddress", AddressValue (Address(address)));
	SetAttribute ("RemotePort", UintegerValue (port));
	SetAttribute ("PriorityGroup", UintegerValue (pg));
}


ParameterServerHelper::ParameterServerHelper (Ipv6Address address, uint16_t port)
{
  m_factory.SetTypeId (ParameterServer::GetTypeId ());
  SetAttribute ("RemoteAddress", AddressValue (Address(address)));
  SetAttribute ("RemotePort", UintegerValue (port));
}

void
ParameterServerHelper::SetAttribute (std::string name, const AttributeValue &value)
{
  m_factory.Set (name, value);
}

ApplicationContainer
ParameterServerHelper::Install (NodeContainer c)
{
  ApplicationContainer apps;
  for (NodeContainer::Iterator i = c.Begin (); i != c.End (); ++i)
    {
      Ptr<Node> node = *i;
      Ptr<ParameterServer> client = m_factory.Create<ParameterServer> ();
      node->AddApplication (client);
      apps.Add (client);
    }
  return apps;
}

} // namespace ns3
