# metrics/ber.py
"""Bit Error Rate (BER) and payload recovery accuracy metrics.

Implements the hidden-data preservation metrics from the research paper:
  BER = sum(b̂_k ≠ b_k) / N  (N = 968 bits)
  Payload_acc = 1 - CER(P̂, P) / |P|
"""

import editdistance


def compute_ber(original_bits: list, extracted_bits: list) -> float:
    """Compute Bit Error Rate between original and extracted LSB payload bits.

    Args:
        original_bits: List of original payload bits (0 or 1), length N.
        extracted_bits: List of extracted payload bits (0 or 1), length N.

    Returns:
        BER value in [0, 1]. 0.0 = perfect recovery, 0.5 = random noise.
    """
    N = len(original_bits)
    if N == 0:
        return 0.0
    errors = sum(o != e for o, e in zip(original_bits, extracted_bits, strict=False))
    return errors / N


def compute_payload_accuracy(original_payload: str, extracted_payload: str) -> float:
    """Compute character-level payload recovery accuracy.

    Args:
        original_payload: The original 121-character structured payload string.
        extracted_payload: The payload string decoded from extracted bits.

    Returns:
        Payload accuracy in [0, 1]. 1.0 = perfect recovery.
    """
    if len(original_payload) == 0:
        return 1.0
    cer = editdistance.eval(extracted_payload, original_payload) / len(original_payload)
    return max(0.0, 1.0 - cer)
