# DNS Exfil Writeup

## Challenge Details

| Field | Value |
| --- | --- |
| Challenge | DNS Exfil |
| Category | Forensics |
| Difficulty | Medium |
| Points | 300 |
| Author | Tanmay M |
| Tag | FORENSICS PCAP DNS-EXFILTRATION |
| Flag Format | `ZeroSecure_CTF{...}` |

## Description

Our network sensors captured suspicious traffic leaving the internal network. The malware appears to be smuggling data out over DNS, a common covert channel that can bypass firewalls and DLP rules.

The goal is to analyze the provided packet capture, `capture.pcap`, reconstruct the stolen payload, and recover the flag.

## Given File

```text
capture.pcap
```

## Initial Analysis

Since the challenge specifically mentions DNS exfiltration, the first step is to inspect DNS query traffic in the PCAP.

DNS exfiltration commonly hides data inside subdomain labels. For example, malware may send queries such as:

```text
<encoded-data>.attacker-domain.com
```

When inspecting the DNS queries in the capture, a suspicious repeated domain appears:

```text
xerops-exfil.local
```

The leftmost labels before this domain look like encoded data.

## Suspicious DNS Queries

The DNS queries contained the following encoded labels:

```text
5a65726f.xerops-exfil.local
53656375.xerops-exfil.local
72655f43.xerops-exfil.local
54467b62.xerops-exfil.local
61736533.xerops-exfil.local
325f646e.xerops-exfil.local
735f6c61.xerops-exfil.local
62656c73.xerops-exfil.local
5f6c6561.xerops-exfil.local
6b5f6576.xerops-exfil.local
65727974.xerops-exfil.local
68696e67.xerops-exfil.local
5f613462.xerops-exfil.local
32636132.xerops-exfil.local
377d.xerops-exfil.local
```

The first label of each query is hexadecimal data.

## Reconstructing the Payload

Extract the first label from each query:

```text
5a65726f
53656375
72655f43
54467b62
61736533
325f646e
735f6c61
62656c73
5f6c6561
6b5f6576
65727974
68696e67
5f613462
32636132
377d
```

Concatenate the chunks in packet order:

```text
5a65726f5365637572655f4354467b6261736533325f646e735f6c6162656c735f6c65616b5f65766572797468696e675f61346232636132377d
```

Then decode the result as hexadecimal.

## Python Solver

```python
chunks = [
    "5a65726f",
    "53656375",
    "72655f43",
    "54467b62",
    "61736533",
    "325f646e",
    "735f6c61",
    "62656c73",
    "5f6c6561",
    "6b5f6576",
    "65727974",
    "68696e67",
    "5f613462",
    "32636132",
    "377d",
]

hex_payload = "".join(chunks)
flag = bytes.fromhex(hex_payload).decode()

print(flag)
```

Output:

```text
ZeroSecure_CTF{base32_dns_labels_leak_everything_a4b2ca27}
```

## Flag

```text
ZeroSecure_CTF{base32_dns_labels_leak_everything_a4b2ca27}
```

## Takeaway

DNS exfiltration can hide stolen data inside subdomain labels. In this challenge, each DNS query contained one hex-encoded chunk of the flag. By extracting the chunks in order and decoding them as hexadecimal, the hidden payload was recovered.

