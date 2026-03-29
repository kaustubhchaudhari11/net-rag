# Routing protocol notes (eval fixture)

**BGP** is a path-vector exterior gateway protocol: routers advertise **AS paths** and policy-aware reachability between autonomous systems.

**OSPF** is a link-state interior protocol: routers flood **LSAs** so every router in an area builds the same topology graph, then runs **Dijkstra** (SPF) for shortest paths.

Contrast: BGP emphasizes policy and inter-domain paths; OSPF emphasizes consistent link-state flooding within a domain.
