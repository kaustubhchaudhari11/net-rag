# IPv6 header sketch (eval fixture)

The **IPv6 base header** is **40 octets** fixed length (unlike IPv4’s variable header with options).

Notable fields include **Version (6)**, **Traffic Class**, **Flow Label**, **Payload Length**, **Next Header**, **Hop Limit**, **Source Address**, and **Destination Address**.

Extension headers chain after the base header when options are needed.
