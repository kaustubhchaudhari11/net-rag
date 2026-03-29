# Local smoke reference (not an RFC)

## TCP three-way handshake

1. Client sends **SYN** to server (synchronize sequence numbers).
2. Server replies **SYN-ACK** (acknowledges SYN and sends its own SYN).
3. Client sends **ACK** to complete the handshake; data transfer can begin.

### Typical TCP state transitions (RFC-style names)

| Step | What is sent | Client state → | Server state → |
|------|----------------|----------------|----------------|
| 1 | Client **SYN** | **CLOSED** → **SYN-SENT** | **LISTEN** → **SYN-RECEIVED** |
| 2 | Server **SYN-ACK** | stays **SYN-SENT** until ACK is sent | stays **SYN-RECEIVED** until ACK arrives |
| 3 | Client **ACK** | **SYN-SENT** → **ESTABLISHED** | **SYN-RECEIVED** → **ESTABLISHED** |

After step 3, both sides are **ESTABLISHED** and may exchange data. (Exact ordering of internal substates can vary slightly by stack; use **RFC 793** in your corpus as the source of truth.)

## MPLS

**MPLS** stands for **Multiprotocol Label Switching**. Routers switch packets using short fixed **labels** instead of doing a longest-prefix IP lookup at every hop, which speeds forwarding and supports traffic engineering and VPN-style paths.

## IPv6 base header vs IPv4

The IPv6 base header is fixed 40 bytes: **Version**, **Traffic Class**, **Flow Label**, **Payload Length**, **Next Header**, **Hop Limit**, **Source Address**, **Destination Address**. IPv4 has variable options; fields like TTL map to Hop Limit, and fragmentation is handled differently (extension headers in IPv6).

## BGP vs link-state flooding

**BGP** advertises reachability between autonomous systems using path-vector messages (policy-rich, incremental updates between BGP speakers). **OSPF** (link-state) routers flood LSAs within an area so every router builds the same topology graph; convergence is based on synchronized link-state databases, not path vectors between ISPs.

## Routing table and longest-prefix match

A **routing table** lists destination prefixes and where to forward packets (next hop / interface). **Longest-prefix match** picks the most specific route: e.g. `10.1.1.0/24` wins over `10.0.0.0/8` for destination `10.1.1.5`.
