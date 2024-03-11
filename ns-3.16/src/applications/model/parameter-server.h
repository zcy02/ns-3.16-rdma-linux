/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2007,2008,2009 INRIA, UDCAST
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
 * Author: Amine Ismail <amine.ismail@sophia.inria.fr>
 *                      <amine.ismail@udcast.com>
 *
 */

#ifndef PARAMETER_SERVER_H
#define PARAMETER_SERVER_H

#include "ns3/application.h"
#include "ns3/event-id.h"
#include "ns3/ptr.h"
#include "ns3/address.h"
#include "packet-loss-counter.h"
namespace ns3 {


/**
 * \ingroup psworker
 * \class ParameterServer
 * \brief A Udp server. Receives UDP packets from a remote host. UDP packets
 * carry a 32bits sequence number followed by a 64bits time stamp in their
 * payloads. The application uses, the sequence number to determine if a packet
 * is lost, and the time stamp to compute the delay
 */
class ParameterServer : public Application
{
public:
  static TypeId GetTypeId (void);
  ParameterServer ();
  virtual ~ParameterServer ();

  /**
   * \brief set the remote address and port
   * \param ip remote IP address
   * \param port remote port
   */
  void SetRemote (Ipv4Address ip, uint16_t port);
  void SetRemote (Ipv6Address ip, uint16_t port);
  void SetRemote (Address ip, uint16_t port);
  void SetPG (uint16_t pg);

protected:
  virtual void DoDispose (void);

private:

  virtual void StartApplication (void);
  virtual void StopApplication (void);

  void ScheduleTransmit (Time dt);
  void Send (void);
  void HandleRead (Ptr<Socket> socket);
  void Reset (Ptr<Socket> socket);
  void GetParameters (void);

  uint32_t m_count;// Max number of packets
  uint64_t m_allowed;
  Time m_interval;// Time btw packets
  uint32_t m_size;// Packet size [14, 1500] Bytes

  uint32_t m_sent;// Counter for sent packets
  uint32_t m_received;// Number of received packets
  Ptr<Socket> m_socket;
  Ptr<Socket> m_socket6;
  Address m_peerAddress;// The Dst address of the outbound packets
  uint16_t m_peerPort;// The Dst port
  EventId m_sendEvent;// Event to send the next packet
  PacketLossCounter m_lossCounter;

  uint16_t m_pg;// The priority group of this flow

};

} // namespace ns3

#endif /* UDP_SERVER_H */
