"""Supported input schema and column-name mapping rules.

The schema follows the CICFlowMeter flow-feature naming used by CIC-IDS2017.
Aliases cover the common header variants (for example "Tot Fwd Pkts" and
"Total Fwd Packets"). Names are compared after normalisation, so case,
spaces and punctuation do not matter.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

SCHEMA_VERSION = "1.0"


def normalize_name(name: str) -> str:
    """Lower-case a column name and collapse non-alphanumerics to underscores."""
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


@dataclass(frozen=True)
class Feature:
    name: str
    description: str
    aliases: tuple[str, ...] = ()


FEATURES: tuple[Feature, ...] = (
    Feature("destination_port", "Destination port of the flow",
            ("Destination Port", "Dst Port")),
    Feature("protocol", "IP protocol number (6 = TCP, 17 = UDP)", ("Protocol",)),
    Feature("flow_duration", "Flow duration in microseconds", ("Flow Duration",)),
    Feature("total_fwd_packets", "Packets sent forward (source to destination)",
            ("Total Fwd Packets", "Tot Fwd Pkts")),
    Feature("total_bwd_packets", "Packets sent backward (destination to source)",
            ("Total Backward Packets", "Total Bwd Packets", "Tot Bwd Pkts")),
    Feature("total_fwd_bytes", "Total bytes in forward packets",
            ("Total Length of Fwd Packets", "TotLen Fwd Pkts", "Fwd Packets Length Total")),
    Feature("total_bwd_bytes", "Total bytes in backward packets",
            ("Total Length of Bwd Packets", "TotLen Bwd Pkts", "Bwd Packets Length Total")),
    Feature("fwd_packet_length_mean", "Mean forward packet length",
            ("Fwd Packet Length Mean", "Fwd Pkt Len Mean")),
    Feature("bwd_packet_length_mean", "Mean backward packet length",
            ("Bwd Packet Length Mean", "Bwd Pkt Len Mean")),
    Feature("flow_bytes_per_s", "Flow rate in bytes per second",
            ("Flow Bytes/s", "Flow Byts/s")),
    Feature("flow_packets_per_s", "Flow rate in packets per second",
            ("Flow Packets/s", "Flow Pkts/s")),
    Feature("flow_iat_mean", "Mean inter-arrival time between packets (microseconds)",
            ("Flow IAT Mean",)),
    Feature("syn_flag_count", "Packets with the TCP SYN flag set",
            ("SYN Flag Count", "SYN Flag Cnt")),
    Feature("ack_flag_count", "Packets with the TCP ACK flag set",
            ("ACK Flag Count", "ACK Flag Cnt")),
    Feature("rst_flag_count", "Packets with the TCP RST flag set",
            ("RST Flag Count", "RST Flag Cnt")),
)

FEATURE_NAMES: tuple[str, ...] = tuple(f.name for f in FEATURES)

# normalised alias -> canonical feature name
ALIAS_INDEX: dict[str, str] = {}
for _f in FEATURES:
    for _alias in (_f.name, *_f.aliases):
        ALIAS_INDEX[normalize_name(_alias)] = _f.name

# Columns that are deliberately NOT model inputs, with the reason shown to users.
EXCLUDED_COLUMNS: dict[str, str] = {
    "flow_id": "Identifier; would let the model memorise individual flows",
    "id": "Row identifier; not a traffic property",
    "source_ip": "Raw IP address; excluded to avoid memorising hosts",
    "src_ip": "Raw IP address; excluded to avoid memorising hosts",
    "destination_ip": "Raw IP address; excluded to avoid memorising hosts",
    "dst_ip": "Raw IP address; excluded to avoid memorising hosts",
    "source_port": "Ephemeral client port; excluded as a weak, unstable signal",
    "src_port": "Ephemeral client port; excluded as a weak, unstable signal",
    "timestamp": "Timestamp; excluded to avoid leaking the capture schedule",
}

LABEL_CANDIDATES: tuple[str, ...] = ("label", "attack", "attack_cat", "class", "traffic_type")
NORMAL_LABELS: frozenset[str] = frozenset({"benign", "normal", "normal_traffic", "legitimate"})
