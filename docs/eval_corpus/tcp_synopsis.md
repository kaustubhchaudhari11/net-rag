# TCP connection establishment (eval fixture)

A TCP connection is opened with a **three-way handshake**:

1. Client sends **SYN** (synchronize sequence numbers).
2. Server replies **SYN-ACK** (synchronize and acknowledge).
3. Client sends **ACK** to acknowledge the server’s SYN.

This exchange establishes bidirectional sequence numbers before data transfer.
